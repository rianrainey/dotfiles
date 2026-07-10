#!/usr/bin/env python3
"""Generate a weekly Codex usage review from local session artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "codex-weekly"
UTC = timezone.utc
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
SESSION_FILE_RE = re.compile(
    r"rollout-.*-(?P<session_id>[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\.jsonl$"
)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_mapping(cls, data: dict[str, int] | None) -> "TokenUsage":
        data = data or {}
        return cls(**{field: int(data.get(field, 0) or 0) for field in TOKEN_FIELDS})

    def to_dict(self) -> dict[str, int]:
        return {field: getattr(self, field) for field in TOKEN_FIELDS}

    def add(self, other: "TokenUsage") -> None:
        for field in TOKEN_FIELDS:
            setattr(self, field, getattr(self, field) + getattr(other, field))

    def delta_from(self, prior: "TokenUsage") -> "TokenUsage":
        values = {}
        for field in TOKEN_FIELDS:
            current = getattr(self, field)
            previous = getattr(prior, field)
            values[field] = current - previous if current >= previous else current
        return TokenUsage(**values)


@dataclass
class HistoryInfo:
    first_user_ts: datetime | None = None
    last_user_ts: datetime | None = None
    prompt_count: int = 0
    first_prompt: str = ""
    skill_invocations: int = 0


@dataclass
class SessionInfo:
    session_id: str
    source_path: Path
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    first_token_ts: datetime | None = None
    thread_name: str = ""
    repo_path: str = ""
    token_totals: TokenUsage = field(default_factory=TokenUsage)
    token_events: list[tuple[datetime, TokenUsage]] = field(default_factory=list)
    daily_deltas: dict[date, TokenUsage] = field(default_factory=lambda: defaultdict(TokenUsage))
    history: HistoryInfo = field(default_factory=HistoryInfo)

    @property
    def duration(self) -> timedelta:
        if not self.first_ts or not self.last_ts:
            return timedelta()
        return max(self.last_ts - self.first_ts, timedelta())

    @property
    def feedback_loop(self) -> timedelta | None:
        if not self.history.first_user_ts or not self.first_token_ts:
            return None
        return self.first_token_ts - self.history.first_user_ts

    @property
    def active(self) -> bool:
        return self.first_ts is not None and self.last_ts is not None

    @property
    def focus_session(self) -> bool:
        return self.duration <= timedelta(minutes=90) and self.token_totals.total_tokens <= 120_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-start", help="Inclusive UTC week start in YYYY-MM-DD format.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--scope", choices=("global", "repo", "hybrid"), default="global")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        if "." in normalized:
            main, frac = normalized.split(".", 1)
            suffix = ""
            if "+" in frac:
                frac, suffix = frac.split("+", 1)
                suffix = "+" + suffix
            elif "-" in frac[1:]:
                frac, suffix = frac.rsplit("-", 1)
                suffix = "-" + suffix
            frac = (frac + "000000")[:6]
            parsed = datetime.fromisoformat(f"{main}.{frac}{suffix}")
        else:
            raise
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def start_end_from_args(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.week_start:
        start = datetime.combine(date.fromisoformat(args.week_start), time.min, tzinfo=UTC)
        end = start + timedelta(days=7)
        return start, end
    end = datetime.now(UTC)
    start = end - timedelta(days=max(args.lookback_days, 1))
    return start, end


def load_session_index(path: Path) -> dict[str, str]:
    names: dict[str, tuple[datetime, str]] = {}
    if not path.exists():
        return {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        updated = parse_ts(record.get("updated_at")) or datetime.fromtimestamp(0, UTC)
        session_id = record.get("id")
        thread_name = record.get("thread_name", "")
        prior = names.get(session_id)
        if prior is None or updated >= prior[0]:
            names[session_id] = (updated, thread_name)
    return {session_id: name for session_id, (_, name) in names.items()}


def load_history(path: Path) -> dict[str, HistoryInfo]:
    result: dict[str, HistoryInfo] = defaultdict(HistoryInfo)
    if not path.exists():
        return {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        session_id = record.get("session_id")
        text = (record.get("text") or "").strip()
        ts = datetime.fromtimestamp(int(record.get("ts", 0)), UTC)
        info = result[session_id]
        info.prompt_count += 1
        if info.first_user_ts is None or ts < info.first_user_ts:
            info.first_user_ts = ts
            info.first_prompt = text
        if info.last_user_ts is None or ts > info.last_user_ts:
            info.last_user_ts = ts
        if "$" in text or "/spawn" in text:
            info.skill_invocations += 1
    return result


def rollout_paths(root: Path) -> list[Path]:
    live = sorted(root.glob("sessions/**/rollout-*.jsonl"))
    archived = sorted(root.glob("archived_sessions/rollout-*.jsonl"))
    return live + archived


def extract_workdir(payload: dict) -> str | None:
    if payload.get("type") != "function_call":
        return None
    arguments = payload.get("arguments")
    if not isinstance(arguments, str):
        return None
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        return None
    workdir = parsed.get("workdir")
    return str(workdir) if workdir else None


def parse_rollout(path: Path, session_names: dict[str, str], histories: dict[str, HistoryInfo]) -> SessionInfo | None:
    match = SESSION_FILE_RE.search(path.name)
    if not match:
        return None
    session_id = match.group("session_id")
    session = SessionInfo(
        session_id=session_id,
        source_path=path,
        thread_name=session_names.get(session_id, ""),
        history=histories.get(session_id, HistoryInfo()),
    )
    prior_total = TokenUsage()
    workdirs: Counter[str] = Counter()

    with path.open() as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            record = json.loads(raw_line)
            ts = parse_ts(record.get("timestamp"))
            if ts:
                if session.first_ts is None or ts < session.first_ts:
                    session.first_ts = ts
                if session.last_ts is None or ts > session.last_ts:
                    session.last_ts = ts

            payload = record.get("payload", {})
            workdir = extract_workdir(payload)
            if workdir:
                workdirs[workdir] += 1

            if record.get("type") != "event_msg" or payload.get("type") != "token_count":
                continue

            info = payload.get("info") or {}
            totals = TokenUsage.from_mapping(info.get("total_token_usage"))
            delta = totals.delta_from(prior_total)
            prior_total = totals
            if delta.total_tokens <= 0:
                continue

            if session.first_token_ts is None and ts is not None:
                session.first_token_ts = ts
            session.token_totals.add(delta)
            if ts is not None:
                session.token_events.append((ts, delta))
                day_bucket = ts.date()
                session.daily_deltas[day_bucket].add(delta)

    if workdirs:
        session.repo_path = workdirs.most_common(1)[0][0]
    return session if session.active else None


def filter_sessions(
    sessions: Iterable[SessionInfo],
    start: datetime,
    end: datetime,
    scope: str,
    repo_root: Path,
) -> tuple[list[SessionInfo], list[SessionInfo]]:
    all_sessions = []
    repo_sessions = []
    repo_root = repo_root.resolve()
    for session in sessions:
        if session.last_ts is None or session.first_ts is None:
            continue
        if session.last_ts < start or session.first_ts >= end:
            continue
        all_sessions.append(session)
        if session.repo_path:
            try:
                current = Path(session.repo_path).expanduser().resolve()
            except FileNotFoundError:
                current = Path(session.repo_path).expanduser()
            if str(current).startswith(str(repo_root)):
                repo_sessions.append(session)
    if scope == "global":
        return all_sessions, repo_sessions
    if scope == "repo":
        return repo_sessions, repo_sessions
    return all_sessions, repo_sessions


def daterange(start_day: date, end_day: date) -> list[date]:
    days = []
    current = start_day
    while current < end_day:
        days.append(current)
        current += timedelta(days=1)
    return days


def compute_daily_totals(sessions: Iterable[SessionInfo], days: list[date]) -> dict[date, TokenUsage]:
    totals = {day: TokenUsage() for day in days}
    for session in sessions:
        for ts, usage in session.token_events:
            if ts.date() in totals:
                totals[ts.date()].add(usage)
    return totals


def clip_interval(session: SessionInfo, start: datetime, end: datetime) -> tuple[datetime, datetime] | None:
    if session.first_ts is None or session.last_ts is None:
        return None
    clipped_start = max(session.first_ts, start)
    clipped_end = min(session.last_ts, end)
    if clipped_end <= clipped_start:
        return None
    return clipped_start, clipped_end


def concurrency_summary(sessions: Iterable[SessionInfo], start: datetime, end: datetime) -> dict[str, float]:
    events = []
    for session in sessions:
        interval = clip_interval(session, start, end)
        if interval is None:
            continue
        interval_start, interval_end = interval
        events.append((interval_start, 1))
        events.append((interval_end, -1))
    if not events:
        return {"active_hours": 0.0, "parallel_hours": 0.0, "parallelism_ratio": 0.0, "series_ratio": 0.0, "peak_concurrency": 0}
    events.sort(key=lambda item: (item[0], item[1]))
    active = 0
    peak = 0
    previous = events[0][0]
    active_seconds = 0.0
    parallel_seconds = 0.0
    for ts, delta in events:
        span = (ts - previous).total_seconds()
        if active > 0 and span > 0:
            active_seconds += span
            if active > 1:
                parallel_seconds += span
        active += delta
        peak = max(peak, active)
        previous = ts
    ratio = parallel_seconds / active_seconds if active_seconds else 0.0
    return {
        "active_hours": active_seconds / 3600.0,
        "parallel_hours": parallel_seconds / 3600.0,
        "parallelism_ratio": ratio,
        "series_ratio": 1.0 - ratio if active_seconds else 0.0,
        "peak_concurrency": peak,
    }


def concurrency_by_day(sessions: Iterable[SessionInfo], days: list[date]) -> dict[date, dict[str, float]]:
    result = {}
    for day in days:
        day_start = datetime.combine(day, time.min, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        result[day] = concurrency_summary(sessions, day_start, day_end)
    return result


def hourly_concurrency(sessions: Iterable[SessionInfo], start: datetime, end: datetime) -> list[tuple[datetime, float]]:
    buckets = []
    current = start.replace(minute=0, second=0, microsecond=0)
    while current < end:
        bucket_end = min(current + timedelta(hours=1), end)
        total_seconds = (bucket_end - current).total_seconds() or 1.0
        overlap_seconds = 0.0
        for session in sessions:
            interval = clip_interval(session, current, bucket_end)
            if interval is None:
                continue
            interval_start, interval_end = interval
            overlap_seconds += (interval_end - interval_start).total_seconds()
        buckets.append((current, overlap_seconds / total_seconds))
        current = bucket_end
    return buckets


def daily_session_counts(sessions: Iterable[SessionInfo], days: list[date]) -> dict[date, int]:
    counts = {day: 0 for day in days}
    for session in sessions:
        if session.first_ts and session.first_ts.date() in counts:
            counts[session.first_ts.date()] += 1
    return counts


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def week_totals(daily: dict[date, TokenUsage]) -> TokenUsage:
    total = TokenUsage()
    for usage in daily.values():
        total.add(usage)
    return total


def session_usage_in_window(session: SessionInfo, start: datetime, end: datetime) -> TokenUsage:
    total = TokenUsage()
    for ts, usage in session.token_events:
        if start <= ts < end:
            total.add(usage)
    return total


def previous_period_sessions(sessions: Iterable[SessionInfo], start: datetime, end: datetime) -> list[SessionInfo]:
    return [session for session in sessions if session.first_ts and session.last_ts and session.last_ts >= start and session.first_ts < end]


def score_from_ratio(ratio: float, thresholds: tuple[float, float, float]) -> int:
    low, mid, high = thresholds
    if ratio >= high:
        return 90
    if ratio >= mid:
        return 75
    if ratio >= low:
        return 60
    return 40


def compute_coaching(
    sessions: list[SessionInfo],
    weekly: TokenUsage,
    concurrency: dict[str, float],
    session_window_totals: dict[str, TokenUsage],
) -> list[dict[str, str]]:
    feedback_minutes = [session.feedback_loop.total_seconds() / 60.0 for session in sessions if session.feedback_loop]
    median_feedback = median(feedback_minutes)
    cache_ratio = (
        weekly.cached_input_tokens / weekly.input_tokens if weekly.input_tokens else 0.0
    )
    focus_ratio = (
        sum(
            1
            for session in sessions
            if session.duration <= timedelta(minutes=90)
            and session_window_totals[session.session_id].total_tokens <= 120_000
        )
        / len(sessions)
        if sessions
        else 0.0
    )
    skill_count = sum(session.history.skill_invocations for session in sessions)
    sessions_per_day = Counter(session.first_ts.date() for session in sessions if session.first_ts)
    bursty_days = sum(1 for count in sessions_per_day.values() if count >= 3)

    cards = [
        {
            "label": "Token efficiency",
            "score": str(int((score_from_ratio(cache_ratio, (0.1, 0.2, 0.35)) + score_from_ratio(focus_ratio, (0.25, 0.45, 0.6))) / 2)),
            "summary": f"Cached-input ratio is {cache_ratio:.0%}; focus-session ratio is {focus_ratio:.0%}.",
            "next_step": "Split long sessions earlier and keep related work in the same thread when cache reuse is paying off.",
        },
        {
            "label": "Parallel work",
            "score": str(int((score_from_ratio(concurrency['parallelism_ratio'], (0.1, 0.2, 0.35)) + min(concurrency["peak_concurrency"] * 20, 100)) / 2)),
            "summary": f"Parallelism ratio is {concurrency['parallelism_ratio']:.0%} with peak concurrency {concurrency['peak_concurrency']}.",
            "next_step": "When you see three independent asks, start separate threads quickly instead of stacking them into one long serial session.",
        },
        {
            "label": "Delegation leverage",
            "score": str(min(40 + bursty_days * 15, 95)),
            "summary": f"{bursty_days} active day(s) launched at least 3 sessions, a rough proxy for decomposed workstreams.",
            "next_step": "Turn repeatable multi-step reviews into background threads or reusable skills instead of keeping them in the foreground thread.",
        },
        {
            "label": "Feedback speed",
            "score": str(90 if 0 < median_feedback <= 2 else 75 if median_feedback <= 5 else 55 if median_feedback <= 10 else 35),
            "summary": f"Median time to first token activity is {median_feedback:.1f} minutes.",
            "next_step": "Bias toward earlier tool calls, small validation checks, and shorter planning loops before diving deep.",
        },
        {
            "label": "Reuse",
            "score": str(min(35 + skill_count * 10, 95)),
            "summary": f"Detected {skill_count} skill-style or structured workflow invocations in the selected sessions.",
            "next_step": "Promote any recurring workflow with stable inputs into a dedicated skill or script so future weeks cost fewer tokens.",
        },
    ]
    return cards


def chart_palette() -> dict[str, str]:
    return {
        "ink": "#153243",
        "accent": "#2f6690",
        "accent_2": "#3a7ca5",
        "accent_3": "#81c3d7",
        "accent_4": "#d9dcd6",
        "grid": "#d6dde3",
        "bg": "#f8fafb",
        "text": "#0b1f2a",
        "good": "#3d9970",
        "warn": "#e69500",
    }


def svg_wrap(width: int, height: int, body: str, title: str) -> str:
    colors = chart_palette()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="{width}" height="{height}" fill="{colors['bg']}"/>
<text x="28" y="34" font-size="20" font-family="Helvetica, Arial, sans-serif" fill="{colors['text']}" font-weight="700">{title}</text>
{body}
</svg>
"""


def render_grouped_bar_chart(title: str, labels: list[str], series: list[tuple[str, list[float], str]], width: int = 1000, height: int = 420) -> str:
    colors = chart_palette()
    left = 60
    top = 70
    chart_width = width - left - 30
    chart_height = height - top - 70
    max_value = max((max(values) for _, values, _ in series if values), default=1.0)
    if max_value <= 0:
        max_value = 1.0
    group_width = chart_width / max(len(labels), 1)
    bar_width = group_width / max(len(series) + 1, 2)
    body = []
    for grid_idx in range(5):
        y = top + chart_height * grid_idx / 4
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{colors["grid"]}" stroke-width="1"/>')
        value = max_value * (1 - grid_idx / 4)
        body.append(f'<text x="14" y="{y + 4:.1f}" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{value/1000:.0f}k</text>')
    for idx, label in enumerate(labels):
        x_center = left + group_width * idx + group_width / 2
        body.append(f'<text x="{x_center:.1f}" y="{height - 26}" text-anchor="middle" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{label}</text>')
        for series_idx, (_, values, color) in enumerate(series):
            value = values[idx] if idx < len(values) else 0.0
            bar_height = chart_height * (value / max_value)
            x = left + group_width * idx + bar_width * (series_idx + 0.4)
            y = top + chart_height - bar_height
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width * 0.7:.1f}" height="{bar_height:.1f}" rx="4" fill="{color}"/>')
    legend_x = width - 250
    for idx, (name, _, color) in enumerate(series):
        y = 22 + idx * 20
        body.append(f'<rect x="{legend_x}" y="{y}" width="12" height="12" rx="2" fill="{color}"/>')
        body.append(f'<text x="{legend_x + 18}" y="{y + 10}" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{name}</text>')
    return svg_wrap(width, height, "\n".join(body), title)


def render_line_chart(title: str, labels: list[str], values: list[float], width: int = 1000, height: int = 420) -> str:
    colors = chart_palette()
    left = 60
    top = 70
    chart_width = width - left - 30
    chart_height = height - top - 70
    max_value = max(values, default=1.0)
    if max_value <= 0:
        max_value = 1.0
    body = []
    for grid_idx in range(5):
        y = top + chart_height * grid_idx / 4
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{colors["grid"]}" stroke-width="1"/>')
        value = max_value * (1 - grid_idx / 4)
        body.append(f'<text x="14" y="{y + 4:.1f}" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{value:.1f}</text>')
    if labels:
        step = chart_width / max(len(labels) - 1, 1)
        points = []
        for idx, value in enumerate(values):
            x = left + step * idx
            y = top + chart_height - chart_height * (value / max_value)
            points.append((x, y))
            if idx % max(1, math.ceil(len(labels) / 12)) == 0:
                body.append(f'<text x="{x:.1f}" y="{height - 26}" text-anchor="middle" font-size="11" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{labels[idx]}</text>')
        path = " ".join(f"L {x:.1f} {y:.1f}" if idx else f"M {x:.1f} {y:.1f}" for idx, (x, y) in enumerate(points))
        body.append(f'<path d="{path}" fill="none" stroke="{colors["accent"]}" stroke-width="3"/>')
        for x, y in points:
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{colors["accent_3"]}" stroke="{colors["accent"]}" stroke-width="1.5"/>')
    return svg_wrap(width, height, "\n".join(body), title)


def render_horizontal_bar_chart(title: str, labels: list[str], values: list[float], width: int = 1000, height: int = 460) -> str:
    colors = chart_palette()
    left = 260
    top = 70
    chart_width = width - left - 40
    row_height = 34
    chart_height = max(len(labels), 1) * row_height
    max_value = max(values, default=1.0)
    if max_value <= 0:
        max_value = 1.0
    body = []
    for idx, label in enumerate(labels):
        y = top + idx * row_height
        body.append(f'<text x="{left - 12}" y="{y + 18}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{label}</text>')
        bar_width = chart_width * ((values[idx] if idx < len(values) else 0.0) / max_value)
        body.append(f'<rect x="{left}" y="{y + 6}" width="{bar_width:.1f}" height="18" rx="6" fill="{colors["accent_2"]}"/>')
        body.append(f'<text x="{left + bar_width + 8:.1f}" y="{y + 20}" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="{colors["text"]}">{int(values[idx]):,}</text>')
    return svg_wrap(width, max(height, top + chart_height + 40), "\n".join(body), title)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percent(value: float) -> str:
    return f"{value:.0%}"


def minutes_str(delta: timedelta | None) -> str:
    if delta is None:
        return "n/a"
    return f"{delta.total_seconds() / 60.0:.1f} min"


def report_path(base_dir: Path, start: datetime, end: datetime, scope: str) -> Path:
    stamp = f"{start.date().isoformat()}_to_{end.date().isoformat()}_{scope}"
    return base_dir / stamp


def format_session_name(session: SessionInfo) -> str:
    name = session.thread_name or session.history.first_prompt or session.session_id
    name = " ".join(name.split())
    return name[:52] + "..." if len(name) > 55 else name


def build_report(
    start: datetime,
    end: datetime,
    scope: str,
    sessions: list[SessionInfo],
    repo_sessions: list[SessionInfo],
    daily: dict[date, TokenUsage],
    previous_daily: dict[date, TokenUsage],
    daily_concurrency: dict[date, dict[str, float]],
    hourly: list[tuple[datetime, float]],
    output_dir: Path,
) -> str:
    weekly = week_totals(daily)
    previous_weekly = week_totals(previous_daily)
    concurrency = concurrency_summary(sessions, start, end)
    session_window_totals = {
        session.session_id: session_usage_in_window(session, start, end) for session in sessions
    }
    coaching = compute_coaching(sessions, weekly, concurrency, session_window_totals)
    day_labels = [day.strftime("%m-%d") for day in daily]
    top_sessions = sorted(
        sessions,
        key=lambda item: session_window_totals[item.session_id].total_tokens,
        reverse=True,
    )[:8]
    skill_count = sum(session.history.skill_invocations for session in sessions)
    median_feedback = median([
        session.feedback_loop.total_seconds() / 60.0
        for session in sessions
        if session.feedback_loop is not None
    ])
    focus_ratio = (
        sum(
            1
            for session in sessions
            if session.duration <= timedelta(minutes=90)
            and session_window_totals[session.session_id].total_tokens <= 120_000
        )
        / len(sessions)
        if sessions
        else 0.0
    )

    tokens_chart = output_dir / "daily_tokens.svg"
    tokens_chart.write_text(
        render_grouped_bar_chart(
            "Daily Token Trends",
            day_labels,
            [
                ("Input", [daily[day].input_tokens for day in daily], chart_palette()["accent"]),
                ("Cached input", [daily[day].cached_input_tokens for day in daily], chart_palette()["accent_3"]),
                ("Output", [daily[day].output_tokens for day in daily], chart_palette()["good"]),
            ],
        )
    )

    session_chart = output_dir / "daily_sessions.svg"
    session_chart.write_text(
        render_grouped_bar_chart(
            "Daily Session Starts and Peak Concurrency",
            day_labels,
            [
                ("Session starts", [daily_session_counts(sessions, list(daily.keys()))[day] for day in daily], chart_palette()["accent_2"]),
                ("Peak concurrency", [daily_concurrency[day]["peak_concurrency"] for day in daily], chart_palette()["warn"]),
            ],
        )
    )

    hourly_chart = output_dir / "hourly_parallelism.svg"
    hourly_chart.write_text(
        render_line_chart(
            "Hourly Average Active Threads",
            [bucket.strftime("%m-%d %H:%M") for bucket, _ in hourly],
            [value for _, value in hourly],
        )
    )

    top_chart = output_dir / "top_sessions.svg"
    top_chart.write_text(
        render_horizontal_bar_chart(
            "Top Sessions by Total Tokens",
            [format_session_name(session) for session in top_sessions],
            [session_window_totals[session.session_id].total_tokens for session in top_sessions],
        )
    )

    previous_delta = weekly.total_tokens - previous_weekly.total_tokens
    chart_note = (
        "PNG charts were requested, but this environment does not have a local PNG renderer "
        "available (`PIL`, `cairosvg`, `matplotlib`, and `plotly` are absent). The analyzer "
        "writes install-free SVG charts instead."
    )

    report = f"""# Codex Weekly Review

Selected window: `{start.isoformat()}` to `{end.isoformat()}`

Scope: `{scope}`

## Weekly Summary

- Total tokens: **{weekly.total_tokens:,}** ({previous_delta:+,} vs prior period)
- Input tokens: **{weekly.input_tokens:,}**
- Cached input tokens: **{weekly.cached_input_tokens:,}**
- Output tokens: **{weekly.output_tokens:,}**
- Active sessions: **{len(sessions)}**
- Repo-matching sessions: **{len(repo_sessions)}**
- Peak concurrency: **{concurrency['peak_concurrency']}**
- Parallelism ratio: **{percent(concurrency['parallelism_ratio'])}**
- Serial ratio: **{percent(concurrency['series_ratio'])}**
- Focus-session ratio: **{percent(focus_ratio)}**
- Median time to first token activity: **{median_feedback:.1f} min**
- Structured workflow invocations: **{skill_count}**

## Charts

{chart_note}

![Daily token trends]({tokens_chart.name})

![Daily session starts and peak concurrency]({session_chart.name})

![Hourly average active threads]({hourly_chart.name})

![Top sessions by total tokens]({top_chart.name})

## Top Sessions

"""
    for session in top_sessions:
        report += (
            f"- **{format_session_name(session)}**: {session_window_totals[session.session_id].total_tokens:,} total tokens, "
            f"{session.duration.total_seconds() / 3600.0:.1f}h duration, feedback {minutes_str(session.feedback_loop)}\n"
        )

    report += "\n## Coaching\n\n"
    for card in coaching:
        report += (
            f"- **{card['label']}**: score {card['score']}/100. {card['summary']} "
            f"Next move: {card['next_step']}\n"
        )

    report += """

## 10x Developer Traits To Optimize

- **Parallel work orchestration**: keep independent workstreams moving in parallel instead of waiting for one long foreground session to finish.
- **Task decomposition**: split broad asks into smaller named threads sooner so context stays tight and reusable.
- **Context efficiency**: maximize cache reuse and avoid re-explaining the same setup across sprawling sessions.
- **Feedback loop speed**: get to the first tool call, validation step, or measurable artifact quickly.
- **Workflow reuse**: convert repeated patterns into skills, scripts, and templates.
- **Verification discipline**: close loops with tests, checks, or explicit QA instead of relying on intuition.
- **Outcome density**: favor more focused sessions that reach a concrete artifact quickly.
- **Naming clarity**: thread names should be strong enough to read as a work log after the fact.
- **Background execution**: when work can proceed independently, let background threads keep momentum while you handle the next decision.
- **Reviewable artifacts**: reports, plans, and scripts create leverage for your future self and teammates.
"""
    return report


def main() -> int:
    args = parse_args()
    start, end = start_end_from_args(args)
    repo_root = Path(args.repo_root).expanduser().resolve()
    output_root = Path(args.output_dir).expanduser().resolve()
    output_dir = report_path(output_root, start, end, args.scope)
    ensure_dir(output_dir)

    session_names = load_session_index(ROOT / "session_index.jsonl")
    histories = load_history(ROOT / "history.jsonl")
    parsed_sessions = [
        session
        for path in rollout_paths(ROOT)
        if (session := parse_rollout(path, session_names, histories)) is not None
    ]

    selected_sessions, repo_sessions = filter_sessions(parsed_sessions, start, end, args.scope, repo_root)
    selected_sessions.sort(key=lambda item: item.first_ts or datetime.fromtimestamp(0, UTC))
    previous_start = start - (end - start)
    previous_end = start
    previous_sessions, _ = filter_sessions(parsed_sessions, previous_start, previous_end, args.scope, repo_root)

    days = daterange(start.date(), end.date() + timedelta(days=1))
    previous_days = daterange(previous_start.date(), previous_end.date() + timedelta(days=1))
    daily = compute_daily_totals(selected_sessions, days)
    previous_daily = compute_daily_totals(previous_sessions, previous_days)
    daily_concurrency = concurrency_by_day(selected_sessions, days)
    hourly = hourly_concurrency(selected_sessions, start, end)

    report_text = build_report(
        start,
        end,
        args.scope,
        selected_sessions,
        repo_sessions,
        daily,
        previous_daily,
        daily_concurrency,
        hourly,
        output_dir,
    )
    (output_dir / "report.md").write_text(report_text)

    daily_rows = []
    for day, usage in daily.items():
        daily_rows.append(
            {
                "day": day.isoformat(),
                **usage.to_dict(),
                "peak_concurrency": int(daily_concurrency[day]["peak_concurrency"]),
                "parallelism_ratio": round(daily_concurrency[day]["parallelism_ratio"], 4),
            }
        )
    write_csv(
        output_dir / "daily_metrics.csv",
        daily_rows,
        ["day", *TOKEN_FIELDS, "peak_concurrency", "parallelism_ratio"],
    )

    session_rows = []
    for session in selected_sessions:
        session_rows.append(
            {
                "session_id": session.session_id,
                "thread_name": format_session_name(session),
                "repo_path": session.repo_path,
                "first_ts": session.first_ts.isoformat() if session.first_ts else "",
                "last_ts": session.last_ts.isoformat() if session.last_ts else "",
                "duration_minutes": round(session.duration.total_seconds() / 60.0, 2),
                "feedback_loop_minutes": round(session.feedback_loop.total_seconds() / 60.0, 2)
                if session.feedback_loop
                else "",
                **session_usage_in_window(session, start, end).to_dict(),
            }
        )
    write_csv(
        output_dir / "session_metrics.csv",
        session_rows,
        [
            "session_id",
            "thread_name",
            "repo_path",
            "first_ts",
            "last_ts",
            "duration_minutes",
            "feedback_loop_minutes",
            *TOKEN_FIELDS,
        ],
    )

    print(f"report={output_dir / 'report.md'}")
    print(f"charts={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
