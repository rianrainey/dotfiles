---
name: session-efficiency
description: Workflow-level guidance for efficient opencode sessions. Use when starting a new Jira ticket, when a session feels slow or unfocused, or when the user asks to "work smarter", "improve efficiency", or "fix my opencode workflow". Covers session structure, tool discipline, model fallback, before/after verification, and DB seeding.
---

# Session Efficiency

## Goal

Eliminate common inefficiencies: excessive bash calls, low edit-to-message ratios, unfocused back-and-forth, and model quota failures. Priority order: finish faster with fewer tokens.

---

## 1. Session Structure

### Before starting

- Run `todowrite` with 2-6 items before the first implementation step. Break the ticket into: research, plan, implement, verify, ship.
- Keep one item `in_progress` at a time. No parallel. This prevents the agent from drifting.

### Planning (skip for trivial fixes)

- Scan the ticket summary, description, and comments before touching code.
- Identify the files likely to change. Use `grep` and `glob` to confirm they exist.
- Open the 2-4 most relevant files in parallel with a single `read` call.
- State the expected before/after behavior aloud (to yourself) before writing code.

---

## 2. Tool Discipline (biggest wins)

### Bash overuse is the #1 efficiency killer

Reserve bash for: git operations, running tests/servers, Docker/container commands, and one-shot file reads only when `read` is unavailable.

| Instead of bash... | Use tool |
|---|---|
| `cat`, `head`, `tail`, `less` | `read` |
| `grep`, `rg`, `ack`, `ag` | `grep` |
| `find`, `fd`, `ls` | `glob` |
| `sed -i`, `awk` | `edit` |
| `echo > file`, `cat << EOF` | `write` |

### Edit over write

- Prefer `edit` (targeted replacement) over `write` (full file rewrite).
- `write` erases the file and replaces it entirely — risky and wasteful for small changes.
- Target 80%+ edits.

### Read efficiently

- Batch reads: read 3-5 files in one tool call.
- Read at least 80 lines to understand context. Avoid repeated tiny 20-line reads.
- Read a file once and reference the output; do not re-read the same file in consecutive turns.

---

## 3. Model & Provider Strategy

- Default to `deepseek-v4-flash-free` unless a task specifically needs OpenAI.
- If a task needs OpenAI and quota is hit, switch to the fallback model immediately. Do not retry 3+ times.

---

## 4. Before / After Verification

Screenshots are not the best default. Use the approach that matches the change type:

| Change type | Before | After |
|---|---|---|
| API/logic change | Trace the existing code path (find example input) | Run the same path with same input, diff output |
| UI/frontend change | Screenshot (use `playwright` or `screenshot` skill) | Screenshot after change |
| DB migration | `SELECT * FROM <table>` before | Same query after |
| JSON/API response change | Capture current response | Diff against new response |
| Test change | Note which tests exist and pass | Run tests, report pass/fail diff |

If unsure, ask the user what "before" looks like. Do not screenshot without asking.

---

## 5. Local DB Seeding

For changes that need test data (new columns, new tables, new states):

- Look for existing seed files or factories in the repo:
  - `grep -r "seed" --include "*.exs" --include "*.rb" --include "*.py"`
  - Check `priv/repo/seeds.exs`, `db/seeds/`, `test/factories/`, `spec/factories/`
  - Check `./script/dev-*` wrappers for reset/seed commands
- Use the repo's existing factory approach (ExMachina, FactoryBot, etc.) to insert records.
- If no factory exists and the change is small, write an ad-hoc insert in the `iex` or `rails console` to produce the needed state.
- Never commit seeds unless the repo has a dedicated seed file convention.

---

## 6. Caching & Context

- Keep related context in the same turn (batch reads, batch tool calls).
- Use `grep` to find a symbol, then immediately `read` the file in the same turn. Do not split across turns.

---

## 7. Guardrails

- If a session has run 50+ messages with fewer than 10 edits, pause and reassess. The agent is probably talking too much and outputting too many bash commands.
- If bash usage exceeds 25% of all tool calls in a session, switch to dedicated tools.
- If OpenAI returns a quota error on the first call, switch models immediately. Do not retry.
- If the same file is read more than 3 times in one session, the agent missed context the first time — consolidate all needed reads into one batch.

---

## 8. Commit, Push, Draft PR

- `git add -A && git commit --no-verify -m "<message>"` (skip lefthook hooks)
- `git push -u origin HEAD`
- `gh pr create --draft --base master --title "<title>" --body-file <body_path>`
- Let CI surface issues; do not run a full local CI check unless the change is risky.

---

## 9. Treehouse Reuse

- Before leasing a new worktree, run `treehouse status` to check if an existing leased worktree already has the right branch or a usable state.
- If reusing: `git switch <branch>` inside the existing worktree. No new lease needed.
- If a prior session's worktree is stale but has no uncommitted changes, `git fetch origin && git rebase origin/master` to refresh.
