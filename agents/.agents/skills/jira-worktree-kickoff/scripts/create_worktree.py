#!/usr/bin/env python3
"""Acquire a Treehouse lease and create a Jira-named branch and workspace alias."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from treehouse_util import (
    git_status_clean,
    lexical_absolute,
    run_git,
    treehouse_return,
)


def return_lease(
    repo: Path,
    treehouse_path: Path,
    branch: str,
    base_sha: str,
    branch_created: bool,
) -> None:
    clean, reason = git_status_clean(treehouse_path)
    if not clean:
        print(f"cleanup_error={reason}", file=sys.stderr)
        print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)
        return

    if branch_created:
        detached = run_git(treehouse_path, "switch", "--detach", base_sha)
        if detached.returncode != 0:
            message = detached.stderr.strip() or detached.stdout.strip() or "git switch failed"
            print(f"cleanup_error={message}", file=sys.stderr)
            print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)
            return
        deleted = run_git(repo, "branch", "-D", branch)
        if deleted.returncode != 0:
            message = deleted.stderr.strip() or deleted.stdout.strip() or "git branch deletion failed"
            print(f"cleanup_error={message}", file=sys.stderr)
            print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)
            return

    if treehouse_return(treehouse_path):
        print(f"cleanup_returned={treehouse_path}", file=sys.stderr)
    else:
        print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-key", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--worktree-root", required=True)
    parser.add_argument("--base-branch", default="master")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the Jira-derived branch and alias without acquiring a Treehouse lease.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    workspace_root = Path(args.worktree_root).expanduser().resolve()

    if not repo.exists():
        print(f"Repo path does not exist: {repo}", file=sys.stderr)
        return 1

    slug = (
        re.sub(r"[^a-z0-9]+", "-", args.title.lower())
        if args.title
        else ""
    )
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    branch = f"{args.issue_key.lower()}-{slug}" if slug else args.issue_key.lower()
    alias_path = workspace_root / branch

    if alias_path.exists() or alias_path.is_symlink():
        print(f"Workspace alias already exists: {alias_path}", file=sys.stderr)
        return 2

    branch_check = run_git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    if branch_check.returncode == 0:
        print(f"Branch already exists: {branch}", file=sys.stderr)
        return 3

    base_ref = f"refs/heads/{args.base_branch}"
    valid_base = run_git(repo, "check-ref-format", base_ref)
    if valid_base.returncode != 0:
        print(f"Invalid base branch: {args.base_branch}", file=sys.stderr)
        return 4

    remote_base_ref = f"refs/remotes/origin/{args.base_branch}"
    fetched = run_git(
        repo,
        "fetch",
        "origin",
        f"+{base_ref}:{remote_base_ref}",
    )
    if fetched.returncode != 0:
        message = fetched.stderr.strip() or fetched.stdout.strip() or "git fetch failed"
        print(f"Could not fetch origin/{args.base_branch}: {message}", file=sys.stderr)
        return 4

    base = run_git(repo, "rev-parse", "--verify", f"{remote_base_ref}^{{commit}}")
    if base.returncode != 0 or not base.stdout.strip():
        print(f"Fetched base branch not found: origin/{args.base_branch}", file=sys.stderr)
        return 4
    base_sha = base.stdout.strip()

    if args.dry_run:
        print(f"branch={branch}")
        print(f"worktree={alias_path}")
        print(f"base_sha={base_sha}")
        return 0

    workspace_root.mkdir(parents=True, exist_ok=True)
    try:
        acquire = subprocess.run(
            ["treehouse", "get", "--lease", "--lease-holder", branch],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        print("treehouse command not found", file=sys.stderr)
        return 5
    if acquire.returncode != 0:
        message = acquire.stderr.strip() or acquire.stdout.strip() or "treehouse get failed"
        print(message, file=sys.stderr)
        return acquire.returncode

    treehouse_output = acquire.stdout.strip()
    if not treehouse_output:
        print("Treehouse returned no worktree path.", file=sys.stderr)
        return 5

    treehouse_path = lexical_absolute(Path(treehouse_output).expanduser())
    if not treehouse_path.exists():
        print(f"Treehouse returned a missing path: {treehouse_path}", file=sys.stderr)
        print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)
        return 6

    top_level = run_git(treehouse_path, "rev-parse", "--show-toplevel")
    if (
        top_level.returncode != 0
        or Path(top_level.stdout.strip()).resolve() != treehouse_path.resolve()
    ):
        print(f"Treehouse path is not a git worktree root: {treehouse_path}", file=sys.stderr)
        return_lease(repo, treehouse_path, branch, base_sha, False)
        return 7

    clean, reason = git_status_clean(treehouse_path)
    if not clean:
        print(f"Leased Treehouse worktree is not clean: {reason}", file=sys.stderr)
        return_lease(repo, treehouse_path, branch, base_sha, False)
        return 7

    create_branch = run_git(treehouse_path, "switch", "-c", branch, base_sha)
    if create_branch.returncode != 0:
        message = create_branch.stderr.strip() or create_branch.stdout.strip() or "git switch -c failed"
        print(message, file=sys.stderr)
        return_lease(repo, treehouse_path, branch, base_sha, False)
        return 7

    checked_out = run_git(treehouse_path, "rev-parse", "HEAD")
    clean, reason = git_status_clean(treehouse_path)
    if checked_out.returncode != 0 or checked_out.stdout.strip() != base_sha or not clean:
        message = reason or "new Jira branch did not start at the exact fetched base commit"
        print(message, file=sys.stderr)
        return_lease(repo, treehouse_path, branch, base_sha, True)
        return 7

    try:
        alias_path.symlink_to(treehouse_path, target_is_directory=True)
    except OSError as exc:
        print(f"Could not create workspace alias: {exc}", file=sys.stderr)
        return_lease(repo, treehouse_path, branch, base_sha, True)
        return 8

    print(f"branch={branch}")
    print(f"worktree={alias_path}")
    print(f"treehouse_worktree={treehouse_path}")
    print(f"base_sha={base_sha}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
