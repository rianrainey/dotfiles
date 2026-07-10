#!/usr/bin/env python3
"""
Create an isolated git worktree for reviewing a GitHub pull request.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


PR_NUMBER_RE = re.compile(r"/pull/(\d+)")


def run(cmd, cwd, capture_output=True):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def run_with_env(cmd, cwd, env, capture_output=True, check=True):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture_output,
        env=env,
    )


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def normalize_slug(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "review"


def parse_pr_number(pr_url):
    match = PR_NUMBER_RE.search(pr_url)
    if not match:
        fail(f"Could not parse a pull request number from URL: {pr_url}")
    return int(match.group(1))


def gh_pr_view(pr_url, repo_path, env):
    result = run_with_env(
        [
            "gh",
            "pr",
            "view",
            pr_url,
            "--json",
            "number,title,baseRefName,headRefName,url",
        ],
        cwd=repo_path,
        env=env,
    )
    return json.loads(result.stdout)


def op_read_secret(ref, repo_path):
    result = run_with_env(
        ["op", "read", ref],
        cwd=repo_path,
        env=os.environ.copy(),
        check=False,
    )
    if result.returncode != 0:
        return None
    secret = result.stdout.strip()
    return secret or None


def op_read_item_field(item_id, field_label, repo_path):
    result = run_with_env(
        ["op", "item", "get", item_id, f"--fields=label={field_label}"],
        cwd=repo_path,
        env=os.environ.copy(),
        check=False,
    )
    if result.returncode != 0:
        return None
    secret = result.stdout.strip()
    return secret or None


def github_token_from_1password(repo_path):
    if not shutil_which("op"):
        return None

    secret_ref = os.environ.get("GITHUB_PR_REVIEW_OP_SECRET_REF")
    if secret_ref:
        return op_read_secret(secret_ref, repo_path)

    item_id = os.environ.get("GITHUB_PR_REVIEW_OP_ITEM_ID")
    if not item_id:
        return None

    field_labels = []
    configured_field = os.environ.get("GITHUB_PR_REVIEW_OP_FIELD")
    if configured_field:
        field_labels.append(configured_field)
    field_labels.extend(["token", "Token", "credential", "password"])

    for field_label in field_labels:
        token = op_read_item_field(item_id, field_label, repo_path)
        if token:
            return token

    return None


def shutil_which(command):
    result = subprocess.run(
        ["which", command],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def gh_api_accessible(repo_path, env):
    result = run_with_env(
        ["gh", "api", "user", "--jq", ".login"],
        cwd=repo_path,
        env=env,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def build_gh_env(repo_path):
    env = os.environ.copy()
    if env.get("GH_TOKEN"):
        return env

    if env.get("GITHUB_TOKEN"):
        env["GH_TOKEN"] = env["GITHUB_TOKEN"]
        return env

    if gh_api_accessible(repo_path, env):
        return env

    token = github_token_from_1password(repo_path)
    if token:
        env["GH_TOKEN"] = token
        return env

    fail(
        "GitHub API authentication is not available. "
        "Make sure `gh auth status` succeeds, set `GH_TOKEN`, or configure "
        "`GITHUB_PR_REVIEW_OP_SECRET_REF` or `GITHUB_PR_REVIEW_OP_ITEM_ID` "
        "for a 1Password-backed token."
    )


def ensure_git_repo(repo_path):
    try:
        run(["git", "rev-parse", "--show-toplevel"], cwd=repo_path)
    except subprocess.CalledProcessError:
        fail(f"Not a git repository: {repo_path}")


def ensure_branch_missing(repo_path, branch_name):
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        cwd=repo_path,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        fail(f"Local branch already exists: {branch_name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr_url", help="GitHub pull request URL")
    parser.add_argument(
        "--repo-path",
        default="~/Documents/code/script_drop",
        help="Repository root containing the origin remote",
    )
    parser.add_argument(
        "--worktree-root",
        default="~/Documents/code/worktree_sd",
        help="Directory where review worktrees are created",
    )
    args = parser.parse_args()

    repo_path = Path(args.repo_path).expanduser().resolve()
    worktree_root = Path(args.worktree_root).expanduser().resolve()

    ensure_git_repo(repo_path)
    pr_number = parse_pr_number(args.pr_url)
    gh_env = build_gh_env(repo_path)
    pr_data = gh_pr_view(args.pr_url, repo_path, gh_env)

    slug = normalize_slug(f"pr-{pr_data['number']}-{pr_data['title']}")
    branch_name = slug
    worktree_path = worktree_root / slug

    if worktree_path.exists():
        fail(f"Worktree path already exists: {worktree_path}")

    ensure_branch_missing(repo_path, branch_name)
    worktree_root.mkdir(parents=True, exist_ok=True)

    try:
        run(
            [
                "git",
                "fetch",
                "origin",
                f"pull/{pr_number}/head:refs/heads/{branch_name}",
            ],
            cwd=repo_path,
            capture_output=False,
        )
        run(
            ["git", "fetch", "origin", pr_data["baseRefName"]],
            cwd=repo_path,
            capture_output=False,
        )
        run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            cwd=repo_path,
            capture_output=False,
        )
    except subprocess.CalledProcessError as exc:
        fail(
            "Failed to prepare the PR worktree. "
            f"Command exited with status {exc.returncode}."
        )

    print(
        json.dumps(
            {
                "pr_number": pr_data["number"],
                "pr_title": pr_data["title"],
                "pr_url": pr_data["url"],
                "base_branch": pr_data["baseRefName"],
                "head_branch": pr_data["headRefName"],
                "review_branch": branch_name,
                "worktree_path": str(worktree_path),
                "repo_path": str(repo_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
