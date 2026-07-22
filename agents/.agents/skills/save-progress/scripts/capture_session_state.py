#!/usr/bin/env python3
"""
Capture deterministic session state for the save-progress skill.

Read-only: gathers git state, worktree info, and existing plan metadata.
Does not modify any files.

Usage:
    python3 capture_session_state.py [--repo /path/to/repo] [--format json|text]
                                     [--obsidian-root ~/obsidian/work-brain]

Output:
    JSON with: git_root, branch, recent_commits, staged_count, unstaged_count,
    diff_stat, jira_key, repo_name, worktree_alias, existing_plans, timestamp.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────


def run(cmd, cwd=None, timeout=30):
    """Run a shell command, return (ok: bool, stdout: str, stderr: str)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd(),
            timeout=timeout,
        )
        ok = result.returncode == 0
        return ok, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return False, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "", f"timed out after {timeout}s"
    except Exception as exc:
        return False, "", str(exc)


def is_git_repo(path: str) -> bool:
    ok, _, _ = run(["git", "rev-parse", "--git-dir"], cwd=path)
    return ok


def get_git_root(path: str) -> str:
    ok, out, _ = run(["git", "rev-parse", "--show-toplevel"], cwd=path)
    return out if ok else ""


def get_branch(path: str) -> str:
    ok, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    return out if ok else ""


def get_head_hash(path: str, short: bool = True) -> str:
    fmt = "--short" if short else ""
    ok, out, _ = run(["git", "rev-parse", fmt, "HEAD"], cwd=path)
    return out if ok else ""


def get_head_subject(path: str) -> str:
    ok, out, _ = run(["git", "log", "-1", "--format=%s"], cwd=path)
    return out if ok else ""


def get_recent_commits(path: str, count: int = 10) -> list[dict]:
    fmt = f"--format=%h|||%s|||%ar"
    ok, out, _ = run(["git", "log", f"-{count}", fmt], cwd=path)
    if not ok or not out:
        return []
    commits = []
    for line in out.split("\n"):
        parts = line.split("|||", 2)
        if len(parts) == 3:
            commits.append({
                "hash": parts[0],
                "subject": parts[1],
                "relative_date": parts[2],
            })
    return commits


def get_status_counts(path: str) -> dict:
    ok, out, _ = run(["git", "status", "--porcelain"], cwd=path)
    if not ok:
        return {"staged": 0, "unstaged": 0, "untracked": 0}
    lines = out.split("\n") if out else []
    staged = sum(1 for l in lines if l and l[0] != " " and l[0] != "?" and l[0] != "!")
    unstaged = sum(1 for l in lines if len(l) > 1 and l[1] != " " and l[0] != "?")
    untracked = sum(1 for l in lines if l.startswith("??"))
    return {"staged": staged, "unstaged": unstaged, "untracked": untracked}


def get_diff_stat(path: str) -> list[str]:
    ok, out, _ = run(["git", "diff", "--stat"], cwd=path)
    if ok and out:
        return out.split("\n")
    # Also check staged diff
    ok, out, _ = run(["git", "diff", "--cached", "--stat"], cwd=path)
    return out.split("\n") if ok and out else []


def get_modified_files(path: str) -> list[str]:
    """Return list of modified (staged or unstaged) file paths."""
    ok, out, _ = run(["git", "status", "--porcelain"], cwd=path)
    if not ok or not out:
        return []
    files = []
    for line in out.split("\n"):
        if not line.strip():
            continue
        # porcelain format: XY filename
        # Handle renamed: XY old -> new
        entry = line[3:] if len(line) > 3 else ""
        # For renames (R), parse after ' -> '
        if " -> " in entry:
            entry = entry.split(" -> ")[-1]
        if entry and not line.startswith("?"):
            files.append(entry)
        elif line.startswith("??"):
            files.append(line[3:])
    return files


def extract_jira_key(branch: str) -> str:
    """Extract Jira key from branch name like sdrp-123-foo or feature/SDRP-123-bar."""
    match = re.search(r"([A-Z][A-Z0-9]+-[0-9]+)", branch, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""


def extract_branch_description(branch: str) -> str:
    """Extract a human-readable description slug from the branch name."""
    # Remove Jira key prefix and common prefixes like feature/, fix/, chore/
    slug = branch.split("/")[-1]  # Handle feature/branch-name
    # Remove leading Jira key if present
    slug = re.sub(r"^[a-z]+-[0-9]+-?", "", slug, flags=re.IGNORECASE)
    # Clean up
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug if slug else "work-in-progress"


def detect_repo_name(git_root: str) -> str:
    """Detect a short category name from the repo root path."""
    if not git_root:
        return "unknown"
    name = Path(git_root).name
    known = {
        "script_drop": "scriptdrop",
        "dotfiles": "dotfiles",
    }
    return known.get(name, name.lower())


def find_worktree_alias(path: str) -> str:
    """Check if CWD is inside a worktree alias under ~/Documents/code/worktrees/."""
    wt_dir = Path.home() / "Documents" / "code" / "worktrees"
    if not wt_dir.exists():
        return ""
    p = Path(path).resolve()
    for child in wt_dir.iterdir():
        if child.is_symlink() or child.is_dir():
            try:
                target = child.resolve()
                if target == p or str(p).startswith(str(target) + "/"):
                    return str(child)
            except (OSError, RuntimeError):
                continue
    # Also check .treehouse directories
    for child in wt_dir.iterdir():
        if child.name.startswith("."):
            continue
        try:
            target = child.resolve()
            if str(p).startswith(str(target) + "/"):
                return str(child)
        except (OSError, RuntimeError):
            continue
    return ""


def find_existing_plans(
    branch: str, jira_key: str, git_root: str, obsidian_root: str
) -> list[dict]:
    """Search Obsidian Engineering Plans for an existing plan matching context.

    Returns a list of dicts with 'path', 'dir_name', 'score' (higher = better match).
    """
    plans_dir = (
        Path(obsidian_root) / "30 Projects" / "Engineering Plans"
    )
    if not plans_dir.exists():
        return []

    matches = []
    year_dirs = sorted(plans_dir.iterdir())[-3:]  # current + past 2 years

    for year_dir in year_dirs:
        if not year_dir.is_dir():
            continue
        for plan_dir in year_dir.iterdir():
            if not plan_dir.is_dir():
                continue
            plan_file = plan_dir / "Plan.md"
            if not plan_file.exists():
                continue

            score = 0
            dir_name = plan_dir.name.lower()

            # Exact branch match in directory name
            branch_slug = branch.lower().replace("/", "-")
            if branch_slug and branch_slug in dir_name:
                score += 10

            # Jira key match
            if jira_key and jira_key.lower() in dir_name:
                score += 8

            # Git root in plan content (check frontmatter)
            if git_root:
                try:
                    content = plan_file.read_text(encoding="utf-8", errors="replace")
                    if git_root in content:
                        score += 5
                    # Check for repo name in frontmatter
                    if f"repository: {git_root}" in content:
                        score += 3
                except (OSError, PermissionError):
                    pass

            if score > 0:
                matches.append({
                    "path": str(plan_file),
                    "dir_name": plan_dir.name,
                    "score": score,
                })

    # Sort by score descending
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


def generate_plan_path(
    branch: str,
    jira_key: str,
    repo_name: str,
    git_root: str,
    obsidian_root: str,
) -> dict:
    """Generate the path for a new plan using existing conventions.

    Returns dict with 'plan_path', 'category', 'slug', and 'dir_name'.
    """
    today = date.today()
    year = str(today.year)
    date_prefix = today.isoformat()

    # Determine category
    if jira_key:
        category = repo_name  # e.g., scriptdrop
    elif repo_name == "codex" or (git_root and ".codex" in str(git_root)):
        category = "codex"
    else:
        category = repo_name

    # Determine slug
    branch_desc = extract_branch_description(branch)
    if jira_key:
        slug = f"{jira_key.lower()}-{branch_desc}" if branch_desc else jira_key.lower()
    elif branch_desc:
        slug = branch_desc
    else:
        slug = "work-in-progress"

    dir_name = f"{date_prefix}_{category}_{slug}"
    plan_path = (
        Path(obsidian_root)
        / "30 Projects" / "Engineering Plans"
        / year / dir_name / "Plan.md"
    )

    return {
        "plan_path": str(plan_path),
        "category": category,
        "slug": slug,
        "dir_name": dir_name,
    }


# ── main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Capture deterministic session state for save-progress skill."
    )
    parser.add_argument(
        "--repo",
        default=os.getcwd(),
        help="Git repo path (default: CWD)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--obsidian-root",
        default=os.path.expanduser("~/obsidian/work-brain"),
        help="Obsidian vault root (default: ~/obsidian/work-brain)",
    )
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    obsidian_root = os.path.expanduser(args.obsidian_root)

    state = {
        "timestamp": None,
        "error": None,
        "git_root": "",
        "is_git_repo": False,
        "branch": "",
        "head_hash": "",
        "head_subject": "",
        "recent_commits": [],
        "staged_count": 0,
        "unstaged_count": 0,
        "untracked_count": 0,
        "modified_files": [],
        "diff_stat": [],
        "jira_key": "",
        "repo_name": "unknown",
        "worktree_alias": "",
        "existing_plans": [],
        "new_plan": None,
        "plan_found": False,
    }

    # Timestamp
    from datetime import datetime

    state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Git detection
    if not is_git_repo(repo_path):
        # Try walking up
        for parent in Path(repo_path).parents:
            if is_git_repo(str(parent)):
                repo_path = str(parent)
                break

    state["is_git_repo"] = is_git_repo(repo_path)

    if state["is_git_repo"]:
        state["git_root"] = get_git_root(repo_path)
        state["branch"] = get_branch(repo_path)
        state["head_hash"] = get_head_hash(repo_path)
        state["head_subject"] = get_head_subject(repo_path)
        state["recent_commits"] = get_recent_commits(repo_path)
        counts = get_status_counts(repo_path)
        state["staged_count"] = counts["staged"]
        state["unstaged_count"] = counts["unstaged"]
        state["untracked_count"] = counts["untracked"]
        state["modified_files"] = get_modified_files(repo_path)
        state["diff_stat"] = get_diff_stat(repo_path)
        state["jira_key"] = extract_jira_key(state["branch"])
        state["repo_name"] = detect_repo_name(state["git_root"])
        state["worktree_alias"] = find_worktree_alias(repo_path)

        # Search for existing plans
        state["existing_plans"] = find_existing_plans(
            branch=state["branch"],
            jira_key=state["jira_key"],
            git_root=state["git_root"],
            obsidian_root=obsidian_root,
        )
        state["plan_found"] = len(state["existing_plans"]) > 0

        # Generate new plan path candidate
        state["new_plan"] = generate_plan_path(
            branch=state["branch"],
            jira_key=state["jira_key"],
            repo_name=state["repo_name"],
            git_root=state["git_root"],
            obsidian_root=obsidian_root,
        )
    else:
        state["error"] = f"Not a git repository: {repo_path}"

    # Output
    if args.format == "text":
        print("=== Session State ===")
        print(f"Timestamp:      {state['timestamp']}")
        print(f"Git root:       {state['git_root'] or 'N/A'}")
        print(f"Branch:         {state['branch'] or 'N/A'}")
        print(f"Head:           {state['head_hash']} — {state['head_subject']}")
        print(f"Jira key:       {state['jira_key'] or 'N/A'}")
        print(f"Repo name:      {state['repo_name']}")
        print(f"Worktree alias: {state['worktree_alias'] or 'N/A'}")
        print(f"Status:         {state['staged_count']} staged, "
              f"{state['unstaged_count']} unstaged, "
              f"{state['untracked_count']} untracked")
        if state["modified_files"]:
            print(f"Modified files:")
            for f in state["modified_files"][:15]:
                print(f"  - {f}")
            if len(state["modified_files"]) > 15:
                print(f"  ... and {len(state['modified_files']) - 15} more")
        if state["recent_commits"]:
            print(f"\nRecent commits:")
            for c in state["recent_commits"]:
                print(f"  {c['hash']} ({c['relative_date']}) {c['subject']}")
        if state["existing_plans"]:
            print(f"\nExisting plans found:")
            for p in state["existing_plans"][:3]:
                print(f"  [{p['score']}] {p['path']}")
            print(f"  (best match: {state['existing_plans'][0]['path']})")
        else:
            print(f"\nNo existing plans found.")
        if state["new_plan"]:
            print(f"\nNew plan path (candidate):")
            print(f"  {state['new_plan']['plan_path']}")
        if state["error"]:
            print(f"\nError: {state['error']}")
    else:
        print(json.dumps(state, indent=2, default=str))


if __name__ == "__main__":
    main()
