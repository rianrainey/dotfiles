---
name: codex-efficiency-coach
description: Analyze local Codex usage for weekly reviews, token and concurrency trends, workflow efficiency, prompt rewrites, token waste audits, model/tool audits, practical coaching, and suggested AGENTS.md edits. Use when the user wants a Codex weekly review, efficiency audit, usage report with charts, or coaching on lower-token and higher-leverage Codex habits.
---

# Codex Efficiency Coach

Use this skill to review local Codex activity without dumping full transcripts into context. It supports two related workflows: a weekly metrics report with charts, and a broader efficiency coaching audit.

## Choose The Workflow

- For a weekly usage review, trend charts, top sessions, or concurrency analysis, run `scripts/weekly_review.py`.
- For a broader coaching audit, token waste analysis, prompt rewrites, model/tool audit, or AGENTS.md edit ideas, run `scripts/analyze_codex_efficiency.py`.
- Use both scripts when the user asks for a weekly review plus coaching recommendations.

Resolve script and reference paths relative to this skill directory.

## Inputs To Confirm

- Weekly review: default to `--lookback-days 7` unless the user provides explicit dates.
- Efficiency audit: default to `--days 30`.
- Ask before analyzing more than 30 days with the efficiency audit. After approval, pass `--confirm-over-30`.
- Ask whether the user wants Markdown or JSON only for the efficiency audit. Default to Markdown.
- Offer a small dry run when the user seems unsure: `--max-threads 8 --sample 4`.

## Data Sources

The scripts read local Codex data only and should not modify history:

- `history.jsonl`
- `session_index.jsonl`
- `state_*.sqlite`
- `logs_*.sqlite`
- `sessions/**/rollout-*.jsonl`
- `archived_sessions/*.jsonl`
- `attachments/` metadata only, unless the user explicitly asks for safe attachment inspection

Thread markdown files are optional context only. They are not the source of truth for token metrics.

## Safety Rules

- Prefer SQLite metadata, prompt history, previews, metrics, and sampled excerpts over full transcripts.
- Never paste whole conversations into the reply.
- Never modify or delete Codex history.
- Redact likely secrets, URLs, emails, sensitive local paths, patient identifiers, and credentials.
- Avoid network access unless the user explicitly asks for it.
- Keep evidence snippets short and scrubbed.
- Exclude internal reviewer/system threads unless the user explicitly asks for that noise.

## Weekly Review Workflow

Run:

```bash
python3 scripts/weekly_review.py --lookback-days 7
```

Useful flags:

- `--week-start YYYY-MM-DD`
- `--lookback-days 7`
- `--scope global|repo|hybrid`
- `--repo-root /abs/path`
- `--output-dir /abs/path`

Defaults:

- Use `--scope global` unless the user asks for repo-only analysis.
- For repo-only analysis, pass `--scope repo --repo-root "$(pwd)"`.
- The default output is under the Codex home reports directory when this skill is installed in `CODEX_HOME/skills`.
- Pass `--output-dir "$(pwd)/.codex/reports/codex-weekly"` when the user wants repo-local report artifacts.

After the script finishes, summarize:

- weekly token totals and prior-period deltas
- daily token and concurrency trends
- peak concurrency, parallelism ratio, and serial ratio
- highest-cost sessions
- coaching takeaways and next experiments

Mention that charts are SVG in this environment because no local PNG renderer is available.

## Efficiency Audit Workflow

Start small when practical:

```bash
python3 scripts/analyze_codex_efficiency.py --days 30 --max-threads 8 --sample 4 --format markdown
```

If the dry run is useful, widen the cap:

```bash
python3 scripts/analyze_codex_efficiency.py --days 30 --max-threads 40 --sample 6 --format markdown
```

For JSON output, pass `--format json`.

Summarize the report instead of pasting the whole output unless the user asks for raw output.

## Efficiency Audit Sections

Include these sections in the final response when using the broader audit:

- scorecard
- ranked recommendations
- prompt rewrites
- token waste audit
- model and tool audit
- suggested `AGENTS.md` edits
- weekly trend
- snippets and templates
- next 3 habits

## Output Guidance

- Use Markdown by default for human review.
- Use JSON when the user wants structured output or post-processing.
- Quote only short, redacted evidence snippets.
- Turn recommendations into concrete next actions, not generic advice.
- If the sample is too thin, say so and recommend widening `--max-threads` or the lookback window.
- Link or name generated report artifacts when the weekly script writes files.

## Improvement Feedback Loop

When an audit or coaching conversation reveals a reusable inefficiency, include one brief `Next time` suggestion in the final response.

- If the same inefficiency appears repeatedly, or if the user says `codify this`, propose a specific `AGENTS.md` or personal skill edit.
- Prefer `AGENTS.md` for always-on behavior such as terse request expansion, automatic decomposition, dry-run habits, or failed-command loops.
- Prefer a skill update only when the behavior belongs to a specialized reusable workflow with clear triggers.
- Do not modify global instructions or skills without explicit user approval.
- Keep proposed edits small, practical, and tied to observed behavior.

## Notes

- Token usage is computed from incremental changes in rollout `token_count` events, not from prompt text.
- Parallelism is computed from overlapping session activity windows.
- Coaching should be practical rather than judgmental.
- For metric definitions and heuristics, read `references/metrics.md` only when the user asks for metric details or you need to explain methodology.
- The efficiency analyzer streams JSONL incrementally and should not load whole transcripts into memory.
- If SQLite metadata is missing, fall back to JSONL sources and state that confidence is lower.
