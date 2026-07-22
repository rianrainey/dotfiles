#!/usr/bin/env python3
"""Shared utilities for Treehouse worktree operations."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, capture_output=True, check=False,
    )


def git_status_clean(worktree: Path) -> tuple[bool, str]:
    status = run_git(worktree, "status", "--porcelain=v1", "--untracked-files=all")
    if status.returncode != 0:
        msg = status.stderr.strip() or status.stdout.strip() or "git status failed"
        return False, msg
    if status.stdout:
        return False, "worktree has tracked or untracked changes"
    return True, ""


def treehouse_return(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["treehouse", "return", str(path), "--force"],
            text=True, capture_output=True, check=False,
        )
    except FileNotFoundError:
        print("treehouse command not found", file=sys.stderr)
        return False
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "treehouse return failed"
        print(msg, file=sys.stderr)
        return False
    return True


def lexical_alias_target(alias_path: Path) -> Path:
    target = alias_path.readlink()
    if not target.is_absolute():
        target = alias_path.parent / target
    return Path(os.path.abspath(target))
