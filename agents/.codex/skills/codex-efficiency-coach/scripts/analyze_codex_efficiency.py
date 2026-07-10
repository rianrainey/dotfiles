#!/usr/bin/env python3
"""Analyze Codex usage patterns and produce an efficiency coaching report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SECRET_PATTERNS = [
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
]
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
URL_PATTERN = re.compile(r"https?://[^\s)>\"]+", re.I)
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DOB_PATTERN = re.compile(r"(?i)\b(?:dob|date of birth)\b\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")
PATIENT_ID_PATTERN = re.compile(
    r"""
    \b
    (?:
        mrn(?:[\s_-]*(?:id|number|no))?
        |
        (?:patient|member|rx)(?:[\s_-]*)?(?:id|identifier|number|no)
        |
        (?:patient|member|mrn)(?:[\s_-]*)identifier
    )
    \b
    \s*[:=]?\s*
    [A-Za-z0-9]+(?:[A-Za-z0-9_-]*[A-Za-z0-9])?
    """,
    re.I | re.X,
)
HOME_PATH_PATTERN = re.compile(re.escape(str(Path.home())))
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass
class ThreadMeta:
    thread_id: str
    title: str
    updated_at: dt.datetime
    created_at: dt.datetime | None
    tokens_used: int
    cwd: str
    approval_mode: str
    model_provider: str
    model: str | None
    thread_source: str | None
    agent_role: str | None
    first_user_message: str
    preview: str
    rollout_path: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", help="Override CODEX_HOME")
    parser.add_argument("--days", type=int, default=30, help="Look back this many days")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Report output format",
    )
    parser.add_argument(
        "--max-threads",
        type=int,
        default=40,
        help="Maximum recent threads to inspect in detail",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=6,
        help="Maximum evidence snippets and rewrite candidates to keep",
    )
    parser.add_argument(
        "--confirm-over-30",
        action="store_true",
        help="Required when --days is greater than 30 to confirm the wider scan",
    )
    parser.add_argument(
        "--include-internal",
        action="store_true",
        help="Include internal reviewer/system threads that are excluded by default",
    )
    parser.add_argument(
        "--self-check-redaction",
        action="store_true",
        help="Run a small local check for patient-identifier redaction coverage",
    )
    args = parser.parse_args()
    if args.days > 30 and not args.confirm_over_30:
        parser.error("--days greater than 30 requires --confirm-over-30 after user approval")
    return args


def resolve_codex_home(override: str | None) -> Path:
    raw = override or os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(raw).expanduser().resolve()


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def to_datetime(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            value /= 1000.0
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return to_datetime(int(text))
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    return None


def redact_text(text: str, limit: int = 280) -> str:
    if not text:
        return ""
    value = HOME_PATH_PATTERN.sub("~", text)
    value = URL_PATTERN.sub("[redacted-url]", value)
    value = EMAIL_PATTERN.sub("[redacted-email]", value)
    value = SSN_PATTERN.sub("[redacted-ssn]", value)
    value = DOB_PATTERN.sub("[redacted-dob]", value)
    value = PATIENT_ID_PATTERN.sub("[redacted-patient-id]", value)
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[redacted-secret]", value)
    value = WHITESPACE_PATTERN.sub(" ", value).strip()
    if len(value) > limit:
        value = value[: limit - 3] + "..."
    return value


def normalize_prompt(text: str) -> str:
    lowered = redact_text(text, limit=800).lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = WHITESPACE_PATTERN.sub(" ", lowered).strip()
    return lowered


def run_redaction_self_check() -> int:
    samples = [
        "patient id: ABCD1234",
        "patient identifier ABCD1234",
        "patient_id=ABCD1234",
        "patient-id ABCD1234",
        "patientnumber: ABCD1234",
        "member id ABCD1234",
        "member identifier ABCD1234",
        "member no ABCD1234",
        "mrn: ABCD1234",
        "mrn no ABCD1234",
        "mrn identifier ABCD1234",
        "rx id: ABCD1234",
        "rx identifier ABCD1234",
    ]
    failures = [sample for sample in samples if "[redacted-patient-id]" not in redact_text(sample, limit=200)]
    if failures:
        for sample in failures:
            print(f"FAILED: {sample}")
        return 1
    print("Redaction self-check passed.")
    return 0


def incremental_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return


def find_latest_sqlite(codex_home: Path, prefix: str) -> Path | None:
    candidates = list(codex_home.glob(f"{prefix}_*.sqlite"))
    sqlite_dir = codex_home / "sqlite"
    if sqlite_dir.exists():
        candidates.extend(sqlite_dir.glob(f"{prefix}_*.sqlite"))
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    return sorted(existing, key=lambda path: (path.stat().st_mtime, str(path)))[-1]


def sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def resolve_rollout_path(codex_home: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    rollout_path = Path(raw_path).expanduser()
    if not rollout_path.is_absolute():
        rollout_path = codex_home / rollout_path
    if rollout_path.exists():
        return rollout_path
    archived = codex_home / "archived_sessions" / rollout_path.name
    if archived.exists():
        return archived
    return None


def parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            loaded = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    return {}


def command_name(command: str) -> str:
    command = command.strip()
    if not command:
        return ""
    match = re.match(r"(?:[A-Z_][A-Z0-9_]*=\S+\s+)*(?:\./)?([A-Za-z0-9_.:/-]+)", command)
    if not match:
        return ""
    return Path(match.group(1)).name


def classify_command(command: str) -> set[str]:
    lowered = command.lower()
    classes: set[str] = set()
    if re.search(r"\brg\b|\bgrep\b|\bfind\b|\bls\b|\bsed\b", lowered):
        classes.add("local_inspection")
    if re.search(r"\bgit\b|\bgh\b", lowered):
        classes.add("git")
    if re.search(r"\b(pytest|mix test|npm test|cargo test|go test|rspec|quick_validate|smoke)\b", lowered):
        classes.add("verification")
    if re.search(r"(^|[\s/])scripts?/|(^|\s)\./script/", lowered):
        classes.add("local_script")
    if re.search(r"\bcurl\b|\bwget\b|\bnpm install\b|\bpip install\b", lowered):
        classes.add("network_or_install")
    return classes


def is_internal_thread(thread: ThreadMeta) -> bool:
    markers = [
        thread.model or "",
        thread.model_provider or "",
        thread.thread_source or "",
        thread.agent_role or "",
        thread.title or "",
        thread.first_user_message or "",
        thread.preview or "",
    ]
    joined = " ".join(markers).lower()
    internal_phrases = (
        "codex-auto-review",
        "approvals_reviewer",
        "request action you are assessing",
        "transcript start",
        "treat the transcript",
    )
    return any(phrase in joined for phrase in internal_phrases)


def load_recent_threads(
    codex_home: Path, cutoff: dt.datetime, max_threads: int, include_internal: bool
) -> tuple[list[ThreadMeta], dict[str, int]]:
    state_db = find_latest_sqlite(codex_home, "state")
    threads: list[ThreadMeta] = []
    spawn_counts: dict[str, int] = defaultdict(int)
    if state_db and state_db.exists():
        try:
            conn = sqlite3.connect(state_db)
            conn.row_factory = sqlite3.Row
            if sqlite_table_exists(conn, "threads"):
                rows = conn.execute(
                    """
                    SELECT id, title, updated_at, updated_at_ms, created_at, created_at_ms,
                           tokens_used, cwd, approval_mode, model_provider, model,
                           thread_source, agent_role, first_user_message, preview, rollout_path
                    FROM threads
                    ORDER BY COALESCE(updated_at_ms, updated_at * 1000) DESC
                    LIMIT ?
                    """,
                    (max_threads * 5,),
                ).fetchall()
                for row in rows:
                    updated_at = to_datetime(row["updated_at_ms"] or row["updated_at"])
                    if not updated_at or updated_at < cutoff:
                        continue
                    created_at = to_datetime(row["created_at_ms"] or row["created_at"])
                    thread = ThreadMeta(
                        thread_id=row["id"],
                        title=redact_text(row["title"] or ""),
                        updated_at=updated_at,
                        created_at=created_at,
                        tokens_used=int(row["tokens_used"] or 0),
                        cwd=redact_text(row["cwd"] or "", limit=140),
                        approval_mode=row["approval_mode"] or "unknown",
                        model_provider=row["model_provider"] or "unknown",
                        model=row["model"],
                        thread_source=row["thread_source"],
                        agent_role=row["agent_role"],
                        first_user_message=redact_text(row["first_user_message"] or ""),
                        preview=redact_text(row["preview"] or ""),
                        rollout_path=row["rollout_path"],
                    )
                    if not include_internal and is_internal_thread(thread):
                        continue
                    threads.append(thread)
                    if len(threads) >= max_threads:
                        break
            if sqlite_table_exists(conn, "thread_spawn_edges"):
                edge_rows = conn.execute(
                    """
                    SELECT parent_thread_id, COUNT(*) AS child_count
                    FROM thread_spawn_edges
                    GROUP BY parent_thread_id
                    """
                ).fetchall()
                for row in edge_rows:
                    spawn_counts[row["parent_thread_id"]] = int(row["child_count"] or 0)
        except sqlite3.Error:
            threads = []
            spawn_counts = defaultdict(int)
        finally:
            try:
                conn.close()
            except UnboundLocalError:
                pass
    if threads:
        return threads, spawn_counts

    session_index = codex_home / "session_index.jsonl"
    for item in incremental_jsonl(session_index):
        updated_at = to_datetime(item.get("updated_at"))
        if not updated_at or updated_at < cutoff:
            continue
        thread = ThreadMeta(
            thread_id=item.get("id", ""),
            title=redact_text(item.get("thread_name", "")),
            updated_at=updated_at,
            created_at=None,
            tokens_used=0,
            cwd="",
            approval_mode="unknown",
            model_provider="unknown",
            model=None,
            thread_source=None,
            agent_role=None,
            first_user_message="",
            preview="",
            rollout_path=None,
        )
        if not include_internal and is_internal_thread(thread):
            continue
        threads.append(thread)
        if len(threads) >= max_threads:
            break
    return threads, spawn_counts


def load_history_metrics(
    codex_home: Path, thread_ids: set[str], cutoff: dt.datetime, sample: int
) -> dict[str, Any]:
    history_path = codex_home / "history.jsonl"
    prompt_counts: Counter[str] = Counter()
    session_messages: Counter[str] = Counter()
    evidence: list[dict[str, str]] = []
    cutoff_ts = int(cutoff.timestamp())
    for item in incremental_jsonl(history_path):
        session_id = item.get("session_id")
        ts = int(item.get("ts", 0) or 0)
        if session_id not in thread_ids or ts < cutoff_ts:
            continue
        text = redact_text(item.get("text", ""))
        if not text:
            continue
        session_messages[session_id] += 1
        prompt_counts[normalize_prompt(text)] += 1
        if len(evidence) < sample and len(text) >= 30:
            evidence.append({"thread_id": session_id, "text": text})
    duplicates = [
        {"prompt_key": key, "count": count}
        for key, count in prompt_counts.most_common(sample)
        if key and count > 1
    ]
    return {
        "session_messages": session_messages,
        "duplicate_prompts": duplicates,
        "history_evidence": evidence,
    }


def load_rollout_metrics(codex_home: Path, threads: list[ThreadMeta], sample: int) -> dict[str, Any]:
    tool_names: Counter[str] = Counter()
    payload_type_counts: Counter[str] = Counter()
    command_names: Counter[str] = Counter()
    command_classes: Counter[str] = Counter()
    failed_commands: Counter[str] = Counter()
    thread_tool_counts: dict[str, int] = defaultdict(int)
    evidence_snippets: list[dict[str, str]] = []
    failed_evidence: list[dict[str, str]] = []
    for thread in threads:
        rollout_path = resolve_rollout_path(codex_home, thread.rollout_path)
        if not rollout_path:
            continue
        snippet_budget = sample
        pending_calls: dict[str, dict[str, str]] = {}
        for item in incremental_jsonl(rollout_path):
            item_type = item.get("type")
            payload = item.get("payload") or {}
            if item_type == "response_item":
                payload_type = payload.get("type", "unknown")
                payload_type_counts[payload_type] += 1
                if payload_type in {"function_call", "custom_tool_call", "tool_search_call"}:
                    name = payload.get("name", payload_type)
                    tool_names[name] += 1
                    thread_tool_counts[thread.thread_id] += 1
                    call_id = payload.get("call_id", "")
                    parsed_args = parse_tool_arguments(payload.get("arguments"))
                    command = str(parsed_args.get("cmd", "")) if name == "exec_command" else ""
                    cmd_name = command_name(command)
                    if cmd_name:
                        command_names[cmd_name] += 1
                    for class_name in classify_command(command):
                        command_classes[class_name] += 1
                    if call_id:
                        pending_calls[call_id] = {
                            "tool": name,
                            "command": redact_text(command, limit=180),
                            "command_name": cmd_name,
                            "title": thread.title or thread.preview or thread.thread_id,
                        }
                    if snippet_budget > 0:
                        evidence_snippets.append(
                            {
                                "thread_id": thread.thread_id,
                                "tool": name,
                                "title": thread.title or thread.preview or thread.thread_id,
                                "command": redact_text(command, limit=120),
                            }
                        )
                        snippet_budget -= 1
                elif payload_type in {"function_call_output", "custom_tool_call_output"}:
                    call = pending_calls.get(payload.get("call_id", ""))
                    if not call:
                        continue
                    output = str(payload.get("output", ""))
                    exit_match = re.search(r"Process exited with code\s+(-?\d+)", output)
                    if exit_match and int(exit_match.group(1)) != 0:
                        failed_key = call["command_name"] or call["tool"]
                        failed_commands[failed_key] += 1
                        if len(failed_evidence) < sample:
                            failed_evidence.append(
                                {
                                    "thread_id": thread.thread_id,
                                    "tool": call["tool"],
                                    "command": call["command"],
                                    "title": call["title"],
                                }
                            )
    return {
        "tool_names": tool_names,
        "payload_type_counts": payload_type_counts,
        "command_names": command_names,
        "command_classes": command_classes,
        "failed_commands": failed_commands,
        "thread_tool_counts": thread_tool_counts,
        "tool_evidence": evidence_snippets[:sample],
        "failed_evidence": failed_evidence,
    }


def load_log_metrics(codex_home: Path, cutoff: dt.datetime) -> dict[str, Any]:
    logs_db = find_latest_sqlite(codex_home, "logs")
    if not logs_db:
        return {"warn_count": 0, "error_count": 0, "top_log_targets": []}
    try:
        conn = sqlite3.connect(logs_db)
        conn.row_factory = sqlite3.Row
        if not sqlite_table_exists(conn, "logs"):
            return {"warn_count": 0, "error_count": 0, "top_log_targets": []}
        rows = conn.execute(
            """
            SELECT level, target, COUNT(*) AS count
            FROM logs
            WHERE ts >= ?
            GROUP BY level, target
            ORDER BY count DESC
            LIMIT 25
            """,
            (int(cutoff.timestamp()),),
        ).fetchall()
    except sqlite3.Error:
        return {"warn_count": 0, "error_count": 0, "top_log_targets": []}
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass
    warn_count = 0
    error_count = 0
    top_targets: list[dict[str, Any]] = []
    for row in rows:
        level = row["level"] or ""
        count = int(row["count"] or 0)
        if level.upper().startswith("WARN"):
            warn_count += count
        if level.upper().startswith("ERROR"):
            error_count += count
        if len(top_targets) < 5:
            top_targets.append(
                {"level": level, "target": redact_text(row["target"] or "", limit=80), "count": count}
            )
    return {"warn_count": warn_count, "error_count": error_count, "top_log_targets": top_targets}


def load_attachment_metrics(codex_home: Path, cutoff: dt.datetime) -> dict[str, int]:
    attachment_dir = codex_home / "attachments"
    if not attachment_dir.exists():
        return {"recent_attachments": 0}
    count = 0
    for path in attachment_dir.rglob("*"):
        if not path.is_file():
            continue
        modified = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
        if modified >= cutoff:
            count += 1
    return {"recent_attachments": count}


def compute_scorecard(
    threads: list[ThreadMeta],
    spawn_counts: dict[str, int],
    history_metrics: dict[str, Any],
    rollout_metrics: dict[str, Any],
    log_metrics: dict[str, Any],
) -> dict[str, Any]:
    tokens = [thread.tokens_used for thread in threads if thread.tokens_used > 0]
    avg_tokens = round(statistics.mean(tokens), 1) if tokens else 0.0
    prompt_lengths = [len(thread.first_user_message) for thread in threads if thread.first_user_message]
    long_prompt_ratio = (
        sum(1 for length in prompt_lengths if length > 220) / len(prompt_lengths)
        if prompt_lengths
        else 0.0
    )
    avg_tools = (
        statistics.mean(rollout_metrics["thread_tool_counts"].values())
        if rollout_metrics["thread_tool_counts"]
        else 0.0
    )
    subagent_ratio = sum(1 for thread in threads if spawn_counts.get(thread.thread_id, 0) > 0) / max(
        len(threads), 1
    )
    duplication_penalty = min(
        sum(item["count"] - 1 for item in history_metrics["duplicate_prompts"]),
        10,
    )
    issue_penalty = min(log_metrics["warn_count"] + (log_metrics["error_count"] * 2), 10)
    context_hygiene = max(1, round(5 - (long_prompt_ratio * 4) - (duplication_penalty / 8)))
    tool_leverage = max(1, min(5, round(2 + min(avg_tools, 6) / 2)))
    delegation = max(1, min(5, round(3 + subagent_ratio * 2)))
    validation = max(1, round(4 - (issue_penalty / 8)))
    spend = max(1, round(5 - min(avg_tokens / 120000, 4)))
    overall = round(((context_hygiene + tool_leverage + delegation + validation + spend) / 25) * 100)
    return {
        "overall": overall,
        "categories": {
            "context_hygiene": context_hygiene,
            "tool_leverage": tool_leverage,
            "delegation": delegation,
            "validation": validation,
            "token_spend": spend,
        },
        "headline_metrics": {
            "threads": len(threads),
            "avg_tokens_per_thread": avg_tokens,
            "long_prompt_ratio": round(long_prompt_ratio, 2),
            "avg_tool_calls_per_thread": round(avg_tools, 1),
            "subagent_thread_ratio": round(subagent_ratio, 2),
        },
    }


def build_recommendations(
    threads: list[ThreadMeta],
    scorecard: dict[str, Any],
    spawn_counts: dict[str, int],
    history_metrics: dict[str, Any],
    rollout_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    prompt_lengths = [len(thread.first_user_message) for thread in threads if thread.first_user_message]
    long_prompt_ratio = (
        sum(1 for length in prompt_lengths if length > 220) / len(prompt_lengths)
        if prompt_lengths
        else 0.0
    )
    models = Counter((thread.model or thread.model_provider or "unknown") for thread in threads)
    total_threads = max(len(threads), 1)
    frontier_threads = sum(
        count
        for model, count in models.items()
        if any(marker in model.lower() for marker in ("gpt-5.5", "gpt-5.4", "frontier", "xhigh"))
    )
    high_cost_without_subagent = [
        thread
        for thread in threads
        if thread.tokens_used >= 80_000 and spawn_counts.get(thread.thread_id, 0) == 0
    ]
    connector_tools = [
        name
        for name in rollout_metrics["tool_names"]
        if any(marker in name.lower() for marker in ("mcp", "gmail", "google", "slack", "github", "browser"))
    ]
    recommendations: list[dict[str, Any]] = []
    if long_prompt_ratio >= 0.25:
        examples = [thread.first_user_message for thread in threads if len(thread.first_user_message) > 220][:2]
        recommendations.append(
            {
                "priority": 1,
                "title": "Front-load outcome and constraints, not narrative",
                "impact": "High",
                "why": f"{round(long_prompt_ratio * 100)}% of sampled kickoff prompts were longer than 220 characters.",
                "evidence": [redact_text(item) for item in examples],
            }
        )
    if frontier_threads / total_threads >= 0.6 and any(thread.tokens_used < 40_000 for thread in threads):
        recommendations.append(
            {
                "priority": 2,
                "title": "Use a cheaper/faster model for small searches, rewrites, and single-file edits",
                "impact": "High",
                "why": f"{frontier_threads} of {len(threads)} sampled threads used high-end models, including low-token tasks.",
                "evidence": [
                    f"{thread.title or thread.thread_id}: {thread.model or thread.model_provider}, {thread.tokens_used} tokens"
                    for thread in threads
                    if thread.tokens_used < 40_000
                ][:2],
            }
        )
    if history_metrics["duplicate_prompts"]:
        recommendations.append(
            {
                "priority": 2,
                "title": "Promote repeated requests into reusable skills or templates",
                "impact": "High",
                "why": "Repeated prompt shapes appeared in recent history.",
                "evidence": [
                    f"{item['count']}x: {item['prompt_key'][:100]}"
                    for item in history_metrics["duplicate_prompts"][:2]
                ],
            }
        )
    if high_cost_without_subagent:
        recommendations.append(
            {
                "priority": 3,
                "title": "Delegate isolated exploration or QA when a thread crosses 80k tokens",
                "impact": "High",
                "why": "High-token threads without child agents are good candidates for Explorer, Coder, or QA isolation.",
                "evidence": [
                    f"{thread.title or thread.thread_id}: {thread.tokens_used} tokens"
                    for thread in high_cost_without_subagent[:2]
                ],
            }
        )
    top_tool = rollout_metrics["tool_names"].most_common(1)
    if top_tool and top_tool[0][0] == "exec_command":
        recommendations.append(
            {
                "priority": 3,
                "title": "Convert repeated shell inspection into tiny helper scripts or parallel reads",
                "impact": "Medium",
                "why": f"`exec_command` dominated observed tool use ({top_tool[0][1]} calls).",
                "evidence": [
                    f"{item['title']} -> {item['tool']}"
                    for item in rollout_metrics["tool_evidence"][:2]
                ],
            }
        )
    if connector_tools and rollout_metrics["command_classes"].get("local_inspection", 0) < len(connector_tools):
        recommendations.append(
            {
                "priority": 4,
                "title": "Use CLI instead of MCP here when the data is already local",
                "impact": "Medium",
                "why": "Connector/browser tools appeared while local inspection command usage was comparatively low.",
                "evidence": connector_tools[:2],
            }
        )
    if rollout_metrics["command_classes"].get("verification", 0) == 0 and threads:
        recommendations.append(
            {
                "priority": 5,
                "title": "End coding threads with an explicit test or smoke command",
                "impact": "High",
                "why": "No verification-class commands were detected in the sampled rollouts.",
                "evidence": ["Look for `pytest`, `npm test`, `mix test`, `cargo test`, `go test`, `quick_validate`, or a named smoke check."],
            }
        )
    if rollout_metrics["failed_commands"]:
        failed_name, failed_count = rollout_metrics["failed_commands"].most_common(1)[0]
        if failed_count >= 2:
            recommendations.append(
                {
                    "priority": 6,
                    "title": "Stop after two identical command failures and inspect the environment",
                    "impact": "Medium",
                    "why": f"`{failed_name}` failed {failed_count} times in sampled rollouts.",
                    "evidence": [
                        f"{item['title']} -> {item['command'] or item['tool']}"
                        for item in rollout_metrics["failed_evidence"][:2]
                    ],
                }
            )
    if sum(spawn_counts.get(thread.thread_id, 0) for thread in threads) > len(threads):
        recommendations.append(
            {
                "priority": 4,
                "title": "Use delegation selectively, then close subthreads quickly",
                "impact": "Medium",
                "why": "Subagent usage is frequent enough that closure discipline affects context costs.",
                "evidence": [
                    f"{thread.title or thread.thread_id}: {spawn_counts.get(thread.thread_id, 0)} child threads"
                    for thread in threads
                    if spawn_counts.get(thread.thread_id, 0) > 0
                ][:2],
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "title": "Keep the current workflow, but add a standard dry-run habit",
                "impact": "Medium",
                "why": f"Overall efficiency score is {scorecard['overall']}, so the next gains come from faster feedback loops.",
                "evidence": ["Run small `--max-threads` and `--sample` checks before deeper audits."],
            }
        )
    for index, item in enumerate(recommendations, start=1):
        item["priority"] = index
    return recommendations


def build_prompt_rewrites(threads: list[ThreadMeta], sample: int) -> list[dict[str, str]]:
    candidates = sorted(
        [thread for thread in threads if thread.first_user_message],
        key=lambda thread: (len(thread.first_user_message), thread.tokens_used),
        reverse=True,
    )[:sample]
    rewrites = []
    for thread in candidates:
        original = redact_text(thread.first_user_message, limit=220)
        concise_goal = thread.title or thread.preview or "Complete the task"
        concise_goal = redact_text(concise_goal, limit=90)
        rewrite = (
            f"Goal: {concise_goal}. "
            f"Context: work in `{thread.cwd or '~'}`. "
            "Constraints: preserve unrelated edits, keep evidence concise, and avoid broad transcript dumps. "
            "Verify with one small smoke test and return changed files plus remaining risk."
        )
        rewrites.append({"original": original, "rewrite": redact_text(rewrite, limit=240)})
    return rewrites


def build_token_waste_audit(
    threads: list[ThreadMeta],
    history_metrics: dict[str, Any],
    rollout_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    high_cost_threads = sorted(threads, key=lambda thread: thread.tokens_used, reverse=True)[:5]
    audit = []
    for thread in high_cost_threads:
        drivers = []
        if len(thread.first_user_message) > 220:
            drivers.append("long kickoff prompt")
        if history_metrics["session_messages"].get(thread.thread_id, 0) > 4:
            drivers.append("many follow-up user messages")
        if rollout_metrics["thread_tool_counts"].get(thread.thread_id, 0) > 12:
            drivers.append("heavy tool orchestration")
        if not drivers:
            drivers.append("high total token spend")
        audit.append(
            {
                "thread": thread.title or thread.thread_id,
                "tokens_used": thread.tokens_used,
                "waste_drivers": drivers,
            }
        )
    return audit


def build_model_tool_audit(
    threads: list[ThreadMeta], rollout_metrics: dict[str, Any], log_metrics: dict[str, Any]
) -> dict[str, Any]:
    models = Counter((thread.model or thread.model_provider or "unknown") for thread in threads)
    approval_modes = Counter(thread.approval_mode or "unknown" for thread in threads)
    return {
        "models": [{"name": name, "count": count} for name, count in models.most_common(5)],
        "approval_modes": [{"name": name, "count": count} for name, count in approval_modes.most_common()],
        "tools": [{"name": name, "count": count} for name, count in rollout_metrics["tool_names"].most_common(8)],
        "commands": [
            {"name": name, "count": count}
            for name, count in rollout_metrics["command_names"].most_common(8)
        ],
        "command_classes": [
            {"name": name, "count": count}
            for name, count in rollout_metrics["command_classes"].most_common()
        ],
        "failed_commands": [
            {"name": name, "count": count}
            for name, count in rollout_metrics["failed_commands"].most_common(5)
        ],
        "payload_types": [
            {"name": name, "count": count}
            for name, count in rollout_metrics["payload_type_counts"].most_common(8)
        ],
        "log_signals": log_metrics,
    }


def build_agents_md_edits(
    recommendations: list[dict[str, Any]], rollout_metrics: dict[str, Any]
) -> list[str]:
    edits = []
    if any("cheaper/faster model" in item["title"] for item in recommendations):
        edits.append(
            "Add a `Model Choice` rule: use cheaper/faster models for simple rewrites, searches, formatting, and single-file edits."
        )
    if any("reusable skills or templates" in item["title"] for item in recommendations):
        edits.append(
            "Add a short `Reusable Prompts` section with standard kickoff templates for audits, reviews, and staged skill work."
        )
    if rollout_metrics["tool_names"].get("exec_command", 0) >= 10:
        edits.append(
            "Add a `Fast Inspection` rule that prefers parallel `rg`, `sed`, and `ls` reads before bespoke shell exploration."
        )
    edits.append(
        "Add a `Dry Run First` rule for analytics scripts: require an example smoke-test command using small limits."
    )
    if rollout_metrics["failed_commands"]:
        edits.append(
            "Add a `Failed Command Loop` rule: after two identical failures, inspect versions, paths, env vars, and sandbox limits before retrying."
        )
    return edits[:4]


def build_weekly_trend(
    threads: list[ThreadMeta], rollout_metrics: dict[str, Any]
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"threads": 0, "tokens": 0, "tool_calls": 0})
    for thread in threads:
        week_start = (thread.updated_at - dt.timedelta(days=thread.updated_at.weekday())).date().isoformat()
        entry = grouped[week_start]
        entry["threads"] += 1
        entry["tokens"] += thread.tokens_used
        entry["tool_calls"] += rollout_metrics["thread_tool_counts"].get(thread.thread_id, 0)
    trend = []
    for week_start, entry in sorted(grouped.items()):
        threads_count = entry["threads"]
        trend.append(
            {
                "week_start": week_start,
                "threads": threads_count,
                "tokens": entry["tokens"],
                "avg_tokens": round(entry["tokens"] / threads_count, 1) if threads_count else 0,
                "avg_tool_calls": round(entry["tool_calls"] / threads_count, 1) if threads_count else 0,
            }
        )
    return trend


def build_snippets_templates(recommendations: list[dict[str, Any]]) -> list[dict[str, str]]:
    headline = recommendations[0]["title"] if recommendations else "Keep requests crisp"
    return [
        {
            "name": "Task kickoff",
            "template": "Goal: <outcome>. Constraints: <paths/rules>. Verify with: <small command>. Deliver: <what changed + risk>.",
        },
        {
            "name": "Dry-run analytics",
            "template": "Run the smallest safe sample first, confirm output shape, then widen the lookback only if the summary is useful.",
        },
        {
            "name": "Delegation handoff",
            "template": f"Context file + plan step + exact write scope. Primary coaching target: {headline.lower()}.",
        },
    ]


def build_next_habits(recommendations: list[dict[str, Any]]) -> list[str]:
    habits = []
    for item in recommendations[:3]:
        habits.append(item["title"])
    while len(habits) < 3:
        habits.append("End each task with one concrete verification command")
    return habits[:3]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    codex_home = resolve_codex_home(args.codex_home)
    cutoff = utc_now() - dt.timedelta(days=args.days)
    threads, spawn_counts = load_recent_threads(
        codex_home, cutoff, args.max_threads, args.include_internal
    )
    thread_ids = {thread.thread_id for thread in threads}
    history_metrics = load_history_metrics(codex_home, thread_ids, cutoff, args.sample)
    rollout_metrics = load_rollout_metrics(codex_home, threads, args.sample)
    log_metrics = load_log_metrics(codex_home, cutoff)
    attachment_metrics = load_attachment_metrics(codex_home, cutoff)
    scorecard = compute_scorecard(threads, spawn_counts, history_metrics, rollout_metrics, log_metrics)
    recommendations = build_recommendations(
        threads, scorecard, spawn_counts, history_metrics, rollout_metrics
    )
    return {
        "codex_home": str(codex_home),
        "lookback_days": args.days,
        "generated_at": utc_now().isoformat(),
        "scope": {
            "threads_analyzed": len(threads),
            "max_threads": args.max_threads,
            "sample": args.sample,
            "recent_attachments": attachment_metrics["recent_attachments"],
            "include_internal": args.include_internal,
        },
        "scorecard": scorecard,
        "ranked_recommendations": recommendations,
        "prompt_rewrites": build_prompt_rewrites(threads, args.sample),
        "token_waste_audit": build_token_waste_audit(threads, history_metrics, rollout_metrics),
        "model_tool_audit": build_model_tool_audit(threads, rollout_metrics, log_metrics),
        "agents_md_edits": build_agents_md_edits(recommendations, rollout_metrics),
        "weekly_trend": build_weekly_trend(threads, rollout_metrics),
        "snippets_templates": build_snippets_templates(recommendations),
        "next_3_habits": build_next_habits(recommendations),
        "evidence_snippets": {
            "history": history_metrics["history_evidence"],
            "tools": rollout_metrics["tool_evidence"],
        },
        "privacy": {
            "redaction": "Likely secrets, URLs, emails, home paths, and common patient identifiers are redacted. Attachments are counted by metadata only.",
            "transcript_policy": "JSONL is streamed incrementally and full transcripts are not loaded into memory.",
        },
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Codex Efficiency Report",
        "",
        f"- Codex home: `{report['codex_home']}`",
        f"- Lookback: `{report['lookback_days']}` days",
        f"- Threads analyzed: `{report['scope']['threads_analyzed']}`",
        f"- Dry-run limits: `--max-threads {report['scope']['max_threads']} --sample {report['scope']['sample']}`",
        "",
        "## Scorecard",
        f"- Overall: **{report['scorecard']['overall']} / 100**",
    ]
    for name, value in report["scorecard"]["categories"].items():
        lines.append(f"- {name.replace('_', ' ').title()}: {value}/5")
    lines.extend(
        [
            "",
            "## Ranked Recommendations",
        ]
    )
    for item in report["ranked_recommendations"]:
        lines.append(f"{item['priority']}. **{item['title']}** ({item['impact']})")
        lines.append(f"   {item['why']}")
        for evidence in item["evidence"][:2]:
            lines.append(f"   Evidence: `{redact_text(str(evidence), limit=140)}`")
    lines.extend(["", "## Prompt Rewrites"])
    for item in report["prompt_rewrites"]:
        lines.append(f"- Original: `{item['original']}`")
        lines.append(f"- Rewrite: `{item['rewrite']}`")
    lines.extend(["", "## Token Waste Audit"])
    for item in report["token_waste_audit"]:
        lines.append(
            f"- `{redact_text(item['thread'], limit=80)}` used `{item['tokens_used']}` tokens; drivers: {', '.join(item['waste_drivers'])}"
        )
    lines.extend(["", "## Model And Tool Audit"])
    lines.append(
        "- Models: "
        + ", ".join(f"{item['name']} ({item['count']})" for item in report["model_tool_audit"]["models"])
    )
    lines.append(
        "- Tools: "
        + ", ".join(f"{item['name']} ({item['count']})" for item in report["model_tool_audit"]["tools"])
    )
    if report["model_tool_audit"]["commands"]:
        lines.append(
            "- Commands: "
            + ", ".join(
                f"{item['name']} ({item['count']})" for item in report["model_tool_audit"]["commands"]
            )
        )
    if report["model_tool_audit"]["command_classes"]:
        lines.append(
            "- Command classes: "
            + ", ".join(
                f"{item['name']} ({item['count']})"
                for item in report["model_tool_audit"]["command_classes"]
            )
        )
    if report["model_tool_audit"]["failed_commands"]:
        lines.append(
            "- Failed commands: "
            + ", ".join(
                f"{item['name']} ({item['count']})"
                for item in report["model_tool_audit"]["failed_commands"]
            )
        )
    lines.append(
        "- Approval modes: "
        + ", ".join(
            f"{item['name']} ({item['count']})" for item in report["model_tool_audit"]["approval_modes"]
        )
    )
    lines.extend(["", "## AGENTS.md Edits"])
    for item in report["agents_md_edits"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Weekly Trend"])
    for item in report["weekly_trend"]:
        lines.append(
            f"- Week of `{item['week_start']}`: {item['threads']} threads, {item['tokens']} tokens, "
            f"{item['avg_tokens']} avg tokens, {item['avg_tool_calls']} avg tool calls"
        )
    lines.extend(["", "## Snippets And Templates"])
    for item in report["snippets_templates"]:
        lines.append(f"- **{item['name']}**: `{item['template']}`")
    lines.extend(["", "## Next 3 Habits"])
    for item in report["next_3_habits"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Notes"])
    lines.append(f"- {report['privacy']['redaction']}")
    lines.append(f"- {report['privacy']['transcript_policy']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if args.self_check_redaction:
        return run_redaction_self_check()
    report = build_report(args)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
