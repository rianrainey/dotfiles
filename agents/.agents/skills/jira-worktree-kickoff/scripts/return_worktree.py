#!/usr/bin/env python3
"""Return a leased Treehouse worktree and remove its ticket-named alias."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from treehouse_util import (
    git_status_clean,
    lexical_alias_target,
    treehouse_return,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True, help="Ticket-named workspace alias path.")
    args = parser.parse_args()

    alias_path = Path(args.worktree).expanduser()
    if not alias_path.is_symlink():
        print(f"Expected a workspace alias symlink: {alias_path}", file=sys.stderr)
        return 1

    treehouse_path = lexical_alias_target(alias_path)
    if not treehouse_path.is_dir():
        print(f"Workspace alias target does not exist: {alias_path}", file=sys.stderr)
        return 2

    clean, reason = git_status_clean(treehouse_path)
    if not clean:
        print(f"Refusing to return a worktree with tracked or untracked changes: {reason}", file=sys.stderr)
        print(f"retained_alias={alias_path}", file=sys.stderr)
        print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)
        return 4

    if not treehouse_return(treehouse_path):
        print(f"retained_alias={alias_path}", file=sys.stderr)
        print(f"retained_treehouse_worktree={treehouse_path}", file=sys.stderr)
        return 5

    try:
        alias_path.unlink()
    except OSError as exc:
        print(f"returned={treehouse_path}")
        print(f"alias_cleanup_error={exc}", file=sys.stderr)
        print(f"retained_alias={alias_path}", file=sys.stderr)
        return 7

    print(f"returned={treehouse_path}")
    print(f"removed_alias={alias_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
