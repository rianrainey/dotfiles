---
name: save-progress
description: Save the current opencode session state to Obsidian as a structured progress checkpoint. Use when the user says "save progress", "checkpoint", "record session", "save state", "handoff", "create handoff", or at the end of a session. Finds or creates an Engineering Plan in `~/obsidian/work-brain/30 Projects/Engineering Plans/`, appends a timestamped session log with git state, changes, blockers, and next steps so the next agent can pick up where this one left off.
metadata:
  short-description: Session checkpoint for Obsidian work-brain
---

# Save Progress

## Goal

Turn the current opencode session into a self-contained Obsidian note that a new agent can read and continue from with minimal context loss. Every save creates a permanent record of what was accomplished, what is in progress, what is blocked, and what should happen next.

## Inputs

- A trigger phrase from the user: "save progress", "checkpoint", "record session", "save state", "handoff", or similar.
- Optionally, the user may provide a free-form summary to include.

## Fixed Defaults

- Obsidian vault: `~/obsidian/work-brain`
- Plan root: `~/obsidian/work-brain/30 Projects/Engineering Plans/<YYYY>/`
- Plan file: `<date>_<category>_<slug>/Plan.md`
- Template: `~/obsidian/work-brain/_System/Templates/Engineering Plan.md`
- Jira key detection: branch name pattern `[A-Z][A-Z0-9]+-[0-9]+`

## Workflow

### 1. Detect session context

Run the companion script to gather deterministic state:

```bash
python3 scripts/capture_session_state.py --repo "$PWD" --format json
```

If the script is run from the worktree or repo root it will detect everything automatically. Pass `--format text` for a human-readable debug view.

The script returns: git root, branch, recent commits (hash + subject + relative date), staged/unstaged file counts, diff stat summary, worktree alias path (if applicable), Jira key extracted from branch name, and the repo folder name.

If the script fails (e.g., not in a git repo), fall back to manual detection:
- `git rev-parse --show-toplevel 2>/dev/null` for repo root
- `git rev-parse --abbrev-ref HEAD` for branch
- Check `$TREEHOUSE_WORKTREE` or `~/Documents/code/worktrees/` for an alias

### 2. Find or create the Plan.md

**To find an existing plan:**

Look in `~/obsidian/work-brain/30 Projects/Engineering Plans/<YYYY>/` (check current year and past year). Search for:
- A directory matching the current branch name
- A directory matching the Jira key
- A directory matching today's date that contains the branch name or Jira key
- A `Plan.md` whose frontmatter contains `branch: <current-branch>` or `workspace: <current-worktree>`

Search with `glob` and `grep` across the Engineering Plans tree:

```bash
# Find by branch name in folder name
ls ~/obsidian/work-brain/30\ Projects/Engineering\ Plans/2026/ | grep -i "<branch-slug>"

# Find by branch in frontmatter
grep -rl "branch: <current-branch>" ~/obsidian/work-brain/30\ Projects/Engineering\ Plans/2026/*/Plan.md
```

Use `glob("~/obsidian/work-brain/30 Projects/Engineering Plans/**/Plan.md")` to find all plan files, then `grep` each one for the branch or Jira key.

**If found:** Read the full Plan.md to understand current state, task list progress, and any prior session logs.

**If not found:** Create a new plan using the template:

- Category detection (first match wins):
  - Repo folder is `script_drop` or similar → `scriptdrop`
  - Repo folder is `dotfiles` → `dotfiles`
  - Branch starts with `sdrp-`, `pr-`, or has a Jira key → `scriptdrop`
  - Branch has a Jira key from another project → lowercase project key
  - Otherwise → the repo folder name
- Path: `~/obsidian/work-brain/30 Projects/Engineering Plans/<YYYY>/<date>_<category>_<slug>/Plan.md`
- Slug from branch name: lowercase, replace non-alphanumeric with `-`, collapse dashes, trim edges. Jira `SDRP-123` becomes `sdrp-123`.
- Copy the template content, fill in frontmatter (date, project, repository, branch, worktree)
- Use `cp` the template then `edit` to fill in frontmatter

### 3. Gather session state from the user

Before writing, ask the user (no more than 3-4 questions together):

1. **What was accomplished?** A quick bullet list. If the user has nothing to add, leave it to the git log.
2. **Are there any blockers?** What is preventing progress right now.
3. **What should the next agent do next?** The top 1-3 concrete next steps.
4. **Session status?** Is this a mid-work checkpoint ("in-progress"), a completion handoff ("ready-for-review"), or abandoning the branch ("stalled")?

Present inferred context as confirmation rather than asking questions the data already answers:
- "I see you're on branch `sdrp-123-foo-bar` in `script_drop` with 3 uncommitted files. Shall I save as a mid-session checkpoint?"

### 4. Compose the session entry

Append a new section to Plan.md named `## Session <N> — <YYYY-MM-DD>` (incrementing the session number from existing entries).

If this is a **new plan** (no prior sessions), first populate it:
- Set the title: `# Engineering Plan: <description>`
- Add the `## Goal` section with what the ticket/branch is about
- Add `## Task List` with initial checklist items
- Add `## Log` section

Every session entry should follow this structure:

```markdown
## Session <N> — YYYY-MM-DD

### What was accomplished

- Commit `abc1234` — subject line from git log
- [User-provided accomplishment]
- [Another accomplishment]

### In progress / changed files

- `path/to/file.ex` — what is being changed here (from git status + user context)

### Blocked / open questions

- [User-provided blocker or N/A]

### Next steps

1. [First concrete step]
2. [Second concrete step]
3. [Third concrete step]

### Git state

- **Branch:** `<branch-name>`
- **Head:** `<abbreviated-hash>` — `<subject>`
- **Worktree:** `<worktree-path>` (if applicable)
- **Uncommitted:** `<N>` staged, `<N>` unstaged
- **Modified files:** `<file1>`, `<file2>`, ...
```

### 5. Update frontmatter

Refresh the Plan.md frontmatter to reflect current state:

| Field | Source |
|---|---|
| `status` | User-provided or inferred: `in-progress`, `ready-for-review`, `stalled`, `complete` |
| `branch` | Detected branch name |
| `worktree` / `workspace` | Detected worktree alias |
| `pull_request` / `pr` | If a draft PR exists (`gh pr view --json url`), add it |
| `jira` / `issue` | Extracted Jira key |
| `repository` | Detected repo root |

If the plan used the template's `type: engineering-plan` frontmatter (long-form) vs the abbreviated `issue:` style, stick with whatever already exists. For new plans, use the template form.

### 6. Update Task List

If there is a `## Task List` section, update checkboxes to reflect actual progress:
- Mark completed items `[x]` where the session log confirms they are done
- Add new items the session revealed as necessary
- Reorder if priorities shifted

### 7. Report

Tell the user:

```
✅ Progress saved to: `~/obsidian/work-brain/30 Projects/Engineering Plans/2026/2026-07-22_scriptdrop_sdrp-123-foo-bar/Plan.md`

Session 3 checkpoint written.
Branch: sdrp-123-foo-bar
Status: in-progress
Next: 1. Run tests  2. Fix the edge case  3. Push and PR
```

## Companion Script

The `scripts/capture_session_state.py` script handles all deterministic state gathering. Run it early in the workflow to populate the session context. It accepts:

- `--repo <path>` — git repo root, defaults to CWD
- `--format json` (default) or `--format text` for debug output
- `--obsidian-root <path>` — override default Obsidian vault path

The script does not modify any files. It is a read-only context gatherer.

## Plan Creation Rules

- Follow the existing naming convention exactly: `YYYY-MM-DD_<category>_<slug>/Plan.md`
- Use underscore `_` between date and category, category and slug
- Use the variant pattern that matches the category:
  - `scriptdrop_sdrp-<num>-<description>` — Jira ticket work
  - `codex_<description>` — OpenCode/Codex work
  - `dotfiles_<description>` — dotfiles repo work
  - `<repo>_<description>` — any other repo
  - `pr-<num>_<description>` — PR review work
- Never write secrets, credentials, auth tokens, or `.env` values into the plan
- Never write large logs or dumps of data
- Use `edit` to update existing plans (target specific sections), not `write` to replace the whole file
- Read the full plan before editing to avoid losing content

## Examples

**User says:** "save progress"
```
Agent detects: branch sdrp-680-tweak-service-rules, repo script_drop, 2 uncommitted files
Agent finds: existing Plan.md at .../2026-07-21_scriptdrop_sdrp-680-tweak-service-rules-on-pharmacy-show-page/Plan.md
Agent: "I see session 1 already has Docker setup and before-screenshots. You have 2 uncommitted files
  and your head commit is 'fix: adjust cutoff label positioning for overlap'. What did you get done
  this session, and what should the next agent tackle?"
User: [answers]
Agent: appends Session 2 entry, updates status, updates task list
Agent: reports save path and next steps
```

**User says:** "handoff, I'm done for today"
```
Agent finds no existing plan → creates new plan from template with date, branch, repo
Agent captures git state, asks what was done and what's next
Agent populates Goal, Task List, Log, and the session entry
Agent: reports the new plan path
```

## See Also

- `~/obsidian/work-brain/_System/Templates/Engineering Plan.md` — the canonical template
- `jira-worktree-kickoff` — creates plans when starting Jira work

## Invocation

Load with: `Use $save-progress`

The skill activates on any of these user phrases:
- "save progress"
- "checkpoint"
- "record session"
- "save state"
- "handoff"
- "create handoff"
- "save what I've done"
- "prepare handoff"
- "next agent" (context-dependent)

Do not wait for the exact phrase — if the user clearly wants to persist session state for continuity, use this skill proactively.
