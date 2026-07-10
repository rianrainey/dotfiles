#!/usr/bin/env python3
"""Create a git worktree and branch from a Jira issue key and title."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

PORT_KEYS = [
    "CORE_WEB_PORT",
    "PATIENT_APP_PORT",
    "COURIER_ADMIN_WEB_PORT",
    "PHARMACY_ADMIN_WEB_PORT",
    "KATHY_BOT_PORT",
    "COURIER_LEGACY_WEB_PORT",
    "PHARMACY_API_WEB_PORT",
    "PROGRAM_REQUEST_API_WEB_PORT",
    "LIVERELOAD_PORT",
    "ERL_DIST_PORT",
    "CLOUDBEAVER_PORT",
    "POSTGRES_PORT",
]

REDIRECT_KEYS = {
    "CORE_WEB_PHARMACY_ADMIN_REDIRECT_URL": "PHARMACY_ADMIN_WEB_PORT",
    "CORE_WEB_COURIER_ADMIN_REDIRECT_URL": "COURIER_ADMIN_WEB_PORT",
    "CORE_WEB_COURIER_APP_REDIRECT_URL": "COURIER_LEGACY_WEB_PORT",
}

PORT_BLOCK_START = 35000
PORT_BLOCK_SIZE = 20
PORT_BLOCK_COUNT = 250


def slugify(issue_key: str, title: str) -> str:
    normalized_title = re.sub(r"[^a-z0-9]+", "-", title.lower())
    normalized_title = re.sub(r"-{2,}", "-", normalized_title).strip("-")
    issue = issue_key.lower()
    return f"{issue}-{normalized_title}" if normalized_title else issue


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def is_port_available(port: int) -> bool:
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                if sock.connect_ex((host, port)) == 0:
                    return False
            except OSError:
                continue
    return True


def build_port_block(slug: str) -> dict[str, int]:
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()
    first_block = int(digest[:8], 16) % PORT_BLOCK_COUNT

    for offset in range(PORT_BLOCK_COUNT):
        block = (first_block + offset) % PORT_BLOCK_COUNT
        first_port = PORT_BLOCK_START + (block * PORT_BLOCK_SIZE)
        ports = {key: first_port + index for index, key in enumerate(PORT_KEYS)}
        if all(is_port_available(port) for port in ports.values()):
            return ports

    raise RuntimeError("No available local ScriptDrop port block found.")


def upsert_env_file(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    seen: set[str] = set()
    next_lines: list[str] = []
    pattern = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=")

    for line in lines:
        match = pattern.match(line)
        key = match.group(1) if match else None
        if key in values:
            if key not in seen:
                next_lines.append(f"{key}={values[key]}")
                seen.add(key)
            continue
        next_lines.append(line)

    missing = [key for key in values if key not in seen]
    if missing:
        if next_lines and next_lines[-1] != "":
            next_lines.append("")
        next_lines.append("# Local worktree port overrides")
        next_lines.extend(f"{key}={values[key]}" for key in missing)

    path.write_text("\n".join(next_lines) + "\n")


def bootstrap_ports(worktree_path: Path, slug: str) -> dict[str, int]:
    ports = build_port_block(slug)
    env_path = worktree_path / ".env"
    example_path = worktree_path / ".env.example"

    if not env_path.exists() and example_path.exists():
        shutil.copyfile(example_path, env_path)

    upsert_env_file(env_path, {key: str(value) for key, value in ports.items()})

    envs_dir = worktree_path / "envs"
    if envs_dir.exists():
        redirects = {
            key: f"http://localhost:{ports[port_key]}"
            for key, port_key in REDIRECT_KEYS.items()
        }
        upsert_env_file(envs_dir / "dev.local.env", redirects)

    return ports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-key", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--worktree-root", required=True)
    parser.add_argument("--base-branch", default="master")
    parser.add_argument(
        "--skip-port-bootstrap",
        action="store_true",
        help="Create only the git worktree; do not write ScriptDrop local port overrides.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    worktree_root = Path(args.worktree_root).expanduser().resolve()

    if not repo.exists():
        print(f"Repo path does not exist: {repo}", file=sys.stderr)
        return 1

    slug = slugify(args.issue_key, args.title)
    branch = slug
    worktree_path = worktree_root / slug

    if worktree_path.exists():
        print(f"Worktree path already exists: {worktree_path}", file=sys.stderr)
        return 2

    branch_check = run_git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    if branch_check.returncode == 0:
        print(f"Branch already exists: {branch}", file=sys.stderr)
        return 3

    base_check = run_git(repo, "rev-parse", "--verify", args.base_branch)
    if base_check.returncode != 0:
        print(f"Base branch not found: {args.base_branch}", file=sys.stderr)
        return 4

    worktree_root.mkdir(parents=True, exist_ok=True)
    create = run_git(
        repo,
        "worktree",
        "add",
        "-b",
        branch,
        str(worktree_path),
        args.base_branch,
    )
    if create.returncode != 0:
        message = create.stderr.strip() or create.stdout.strip() or "git worktree add failed"
        print(message, file=sys.stderr)
        return create.returncode

    print(f"branch={branch}")
    print(f"worktree={worktree_path}")

    if not args.skip_port_bootstrap:
        try:
            ports = bootstrap_ports(worktree_path, slug)
        except Exception as exc:
            print(f"Port bootstrap failed: {exc}", file=sys.stderr)
            return 5
        for key, value in ports.items():
            print(f"port_{key}={value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
