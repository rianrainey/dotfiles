#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SECTION_ORDER = [
    "Patient App",
    "Pharmacy Admin / Pharmacy API",
    "Core / Internal Ops",
    "Courier Tools",
    "Program Request APIs",
    "Shared Platform / Security / Reliability",
]

APP_SECTION_MAP = {
    "apps/patient_app": "Patient App",
    "apps/pharmacy_admin_web": "Pharmacy Admin / Pharmacy API",
    "apps/pharmacy_api": "Pharmacy Admin / Pharmacy API",
    "apps/pharmacy_api_web": "Pharmacy Admin / Pharmacy API",
    "apps/core": "Core / Internal Ops",
    "apps/core_web": "Core / Internal Ops",
    "apps/update_comms": "Core / Internal Ops",
    "apps/update_comms_email": "Core / Internal Ops",
    "apps/surveys": "Core / Internal Ops",
    "apps/courier_admin_web": "Courier Tools",
    "apps/courier_legacy_web": "Courier Tools",
    "apps/program_request_api": "Program Request APIs",
    "apps/program_request_api_web": "Program Request APIs",
    "apps/event_bus": "Shared Platform / Security / Reliability",
    "apps/d0_receiver": "Shared Platform / Security / Reliability",
    "apps/kathy_bot": "Shared Platform / Security / Reliability",
    "apps/prometheus_metrics": "Shared Platform / Security / Reliability",
    "apps/telcom_parser": "Shared Platform / Security / Reliability",
    "apps/xml": "Shared Platform / Security / Reliability",
}

IGNORE_PREFIXES = (
    ".github/",
    "docs/",
    ".devcontainer/",
    "test/",
    "apps/test_support/",
)

ALWAYS_INCLUDE_PATTERNS = (
    "security",
    "vulnerability",
    "xss",
    "idor",
    "csrf",
    "fix",
    "bug",
    "outage",
    "incident",
    "migration",
)

CATEGORY_RULES = [
    ("🔒", "security", re.compile(r"\b(security|vulnerability|xss|idor|csrf|auth)\b", re.I)),
    ("✨", "feature", re.compile(r"\b(add|support|implement|feature|association|ui|launch|enable)\b", re.I)),
    ("📈", "ops", re.compile(r"\b(logging|workflow|performance|reliability|normalize|migration|tracking)\b", re.I)),
    ("🛠", "fix", re.compile(r"\b(fix|bug|error|handle|prevent|suppress|cleanup)\b", re.I)),
]

PR_RE = re.compile(r"\(#(\d+)\)")
JIRA_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def run_git_log(repo: Path, weeks: int) -> str:
    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        f"--since={weeks} weeks ago",
        "--date=short",
        "--pretty=format:__COMMIT__%n%ad%n%H%n%s",
        "--name-only",
        "--",
        "apps",
        ".github",
        "docs",
        ".devcontainer",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def parse_commits(raw: str):
    commits = []
    for block in raw.split("__COMMIT__\n"):
        block = block.strip()
        if not block:
            continue
        lines = list(block.splitlines())
        if len(lines) < 3:
            continue
        date, commit_hash, subject = lines[:3]
        paths = [line.strip() for line in lines[3:] if line.strip()]
        commits.append(
            {
                "date": date,
                "hash": commit_hash,
                "short_hash": commit_hash[:8],
                "subject": subject,
                "paths": paths,
            }
        )
    return commits


def is_noise(commit):
    if not commit["paths"]:
        return True
    subject = commit["subject"].lower()
    if any(pattern in subject for pattern in ALWAYS_INCLUDE_PATTERNS):
        return False
    visible_paths = []
    for path in commit["paths"]:
        if any(part in path for part in ("/test/", "/tests/", "_test.", "/fixtures/")):
            continue
        if any(path.startswith(prefix) for prefix in IGNORE_PREFIXES):
            continue
        visible_paths.append(path)
    return not visible_paths


def matched_sections(paths):
    sections = []
    for path in paths:
        normalized = path.rstrip("/")
        matched = None
        for prefix, section in APP_SECTION_MAP.items():
            if normalized == prefix or normalized.startswith(prefix + "/"):
                matched = section
                break
        if matched:
            sections.append(matched)
    return sorted(set(sections))


def choose_section(commit):
    sections = matched_sections(commit["paths"])
    if not sections:
        return "Shared Platform / Security / Reliability"
    if len(sections) == 1:
        return sections[0]
    non_shared = [section for section in sections if section != "Shared Platform / Security / Reliability"]
    if len(non_shared) == 1:
        return non_shared[0]
    return "Shared Platform / Security / Reliability"


def classify(subject):
    for emoji, category, pattern in CATEGORY_RULES:
        if pattern.search(subject):
            return emoji, category
    return "⚠️", "notable"


def to_record(commit):
    emoji, category = classify(commit["subject"])
    return {
        "date": commit["date"],
        "hash": commit["hash"],
        "short_hash": commit["short_hash"],
        "subject": commit["subject"],
        "section": choose_section(commit),
        "sections_touched": matched_sections(commit["paths"]),
        "paths": commit["paths"],
        "category": category,
        "emoji": emoji,
        "pr_numbers": PR_RE.findall(commit["subject"]),
        "jira_keys": JIRA_RE.findall(commit["subject"]),
    }


def build_payload(repo: Path, weeks: int):
    raw = run_git_log(repo, weeks)
    commits = [to_record(commit) for commit in parse_commits(raw) if not is_noise(commit)]
    grouped = defaultdict(list)
    for commit in commits:
        grouped[commit["section"]].append(commit)
    for section in SECTION_ORDER:
        grouped[section].sort(key=lambda item: (item["date"], item["hash"]), reverse=True)
    highlights = sorted(
        commits,
        key=lambda item: (
            item["category"] not in {"security", "feature", "ops"},
            item["date"],
            item["hash"],
        ),
        reverse=True,
    )[:5]
    return {
        "repo": str(repo),
        "weeks": weeks,
        "highlights": highlights,
        "sections": {section: grouped.get(section, []) for section in SECTION_ORDER},
    }


def render_markdown(payload):
    lines = [f"# Release log candidates for the last {payload['weeks']} week(s)", "", "## Top Highlights", ""]
    if payload["highlights"]:
        for item in payload["highlights"]:
            refs = item["jira_keys"] + [f"#{number}" for number in item["pr_numbers"]]
            ref_suffix = f" ({', '.join(refs)})" if refs else ""
            lines.append(f"- {item['emoji']} {item['subject']}{ref_suffix}")
    else:
        lines.append("- No stakeholder-relevant commits found in this window.")
    for section in SECTION_ORDER:
        lines.extend(["", f"## {section}", ""])
        items = payload["sections"].get(section) or []
        if not items:
            lines.append("- No noteworthy items detected.")
            continue
        for item in items:
            refs = item["jira_keys"] + [f"#{number}" for number in item["pr_numbers"]]
            ref_suffix = f" ({', '.join(refs)})" if refs else ""
            lines.append(f"- {item['emoji']} {item['subject']}{ref_suffix}")
            lines.append(f"  Date: {item['date']} | Commit: {item['short_hash']}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Build grouped release-log candidates from git history.")
    parser.add_argument("--repo", default=".", help="Path to the git repo. Defaults to cwd.")
    parser.add_argument("--weeks", type=int, required=True, help="How many weeks back to inspect.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    payload = build_payload(repo, args.weeks)

    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(payload))


if __name__ == "__main__":
    main()
