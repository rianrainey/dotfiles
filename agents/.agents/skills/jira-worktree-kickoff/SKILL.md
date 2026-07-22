---
name: jira-worktree-kickoff
description: Use when the user wants to start implementation from a Jira issue URL, including terse requests such as "work this ticket", "start this", or "fix this ticket". This skill fetches the Jira ticket via acli, gathers planning context, acquires a leased Treehouse worktree, creates a Jira-named branch and workspace alias, then hands off ScriptDrop setup and validation to repo wrappers (./script/dev-*).
---

# Jira Worktree Kickoff

Use this skill when the user provides a Jira issue URL and wants an implementation-ready ScriptDrop workspace plus a plan.

## Inputs

- A Jira issue URL.

## Terse Request Handling

Do not require the user to provide a structured prompt. When the user gives a short request with a Jira issue URL, infer the internal brief from the ticket and local repo context:

- Goal: derive from the issue summary, description, and acceptance criteria.
- Context: collect the issue key, repo, base branch, linked issues, subtasks, comments, and likely affected areas.
- Constraints: preserve unrelated edits, follow repo conventions, protect secrets, and call out high-risk areas.
- Verify: propose the smallest useful check based on the issue's risk and affected system.
- Deliver: report the Obsidian plan path, branch name, workspace alias path, Treehouse path, open questions, and next step.

Ask only when missing information would materially change the plan or implementation path.

## Fixed Defaults

- Repo path: resolve the current ScriptDrop git root
- Workspace alias root: `~/Documents/code/worktrees`
- Treehouse pool: `~/.treehouse` by default; a repository `treehouse.toml` may override the pool `root`
- Base branch: `master`
- Obsidian plan root: `~/obsidian/work-brain/30 Projects/Engineering Plans`

## Workflow

1. Parse the Jira URL and extract the issue key. Look for an uppercase key matching `[A-Z][A-Z0-9]+-[0-9]+`.
2. Assign the ticket to Rian Rainey (`rian.rainey@goodrx.com`) and transition it to "In Dev":
   - `acli jira workitem assign <KEY> --assignee "rian.rainey@goodrx.com"`
   - `acli jira workitem transition <KEY> --step "In Dev"`
3. Fetch the Jira issue:
   a. Ensure acli is authenticated (load `jira-acli` skill for auth reference).
   b. `acli jira workitem view <KEY> --json` — summary, description, status, priority, and all standard fields.
   c. `acli jira workitem comment list --key <KEY> --json` — comments.
   d. `acli jira workitem link list --key <KEY> --json` — linked issues and subtasks.
   e. If acli is unavailable or auth fails, fall back to Atlassian MCP (`getAccessibleAtlassianResources` → `getJiraIssue` with fields `["*all"]`).
4. Gather implementation context from the issue:
   - summary/title
   - description
   - acceptance criteria or similarly named custom fields if present
   - comments
   - linked issues
   - subtasks
5. Create the single shared plan before changing code at `~/obsidian/work-brain/30 Projects/Engineering Plans/YYYY/YYYY-MM-DD_scriptdrop_<issue-key-lowercase>-<normalized-title>/Plan.md`. Use the global `AGENTS.md` plan format and cover:
   - intended behavior
   - affected systems or files if inferable
   - dependencies or blockers
   - smallest useful verification path
   - open questions from the ticket context
   Do not create a duplicate repo-local `.codex/sessions/threads`, claude, or opencode equivalent plan. Use `Context.md` beside the plan only when the gathered ticket context would make `Plan.md` unwieldy. Never write secrets, raw credentials, auth headers, `.env` values, customer data, or large logs into either note.
6. Run `todowrite` with 3-6 items (e.g. research, plan, implement, verify, ship). Keep one item `in_progress` at a time. This prevents session drift.
7. Build the branch slug as `<issue-key-lowercase>-<normalized-title>`.
8. Before leasing, check for reusable worktrees: `treehouse status`. If an existing leased worktree already has the right branch or a usable state, reuse it (`git switch <branch>`) instead of acquiring a new lease.
9. Run `.agents/skills/jira-worktree-kickoff/scripts/create_worktree.py` with the issue key, title, repo path, workspace alias root, and base branch. It fetches the exact `origin/<base-branch>` tip before acquiring a durable Treehouse lease, creates the Jira-named branch from that fetched commit, and creates a ticket-named alias at `~/Documents/code/worktrees/<slug>`.
10. Update the plan front matter with the branch and alias path, then continue every implementation command from the printed alias path, never from the main checkout.
11. Run all ScriptDrop setup, tests, formatting, and servers from the worktree alias using these wrappers:
    - `./script/dev-setup` — install dependencies inside the container
    - `./script/dev-up` — start Docker services (this owns all env/port setup; do not write `.env` files)
    - `./script/dev-test` — run tests
    - `./script/dev-ci` — full CI check
    - `./script/dev-server` — start dev server
     Before invoking a wrapper that can provision or recreate containers, run `docker compose ps`. Reuse a running stack for focused commands and screenshots; do not run `./script/dev-up`, `./script/dev-setup`, or `./script/dev-test` merely to take a screenshot. See `references/scriptdrop-container-reuse.md` for the focused-test and screenshot workflow. Keep the stack warm by default. Run `./script/dev-down` only when Docker resources need to be reclaimed.
12. Report the Obsidian plan path, branch name, alias path, Treehouse path, open questions, and the next ScriptDrop wrapper command.

## Slug Rules

- Lowercase the issue key and title.
- Convert any run of non-alphanumeric characters to `-`.
- Collapse repeated dashes.
- Trim leading and trailing dashes.
- Final format must be safe for both a git branch and directory name.

## Worktree Rules

- Actually acquire the Treehouse lease and create the workspace alias. Do not only print commands.
- Treehouse pool directories are intentionally reusable and numeric. The ticket-named alias and branch are the human-facing identifiers.
- Fail safely if the target alias path or branch already exists. Do not overwrite or reuse either without explicit user approval.
- Create the branch with the exact same `<slug>`.
- Create the branch from the exact `origin/<base-branch>` commit fetched before lease acquisition, never from the reusable Treehouse slot's prior `HEAD`.
- At completion, run `scripts/return_worktree.py --worktree <alias-path>` after committing or otherwise preserving the work. This removes the alias only after Treehouse has returned the lease.
- For any later ScriptDrop tests, setup, servers, or validation, run repo wrappers from the created worktree, never from the main checkout:
  - `./script/dev-setup`, `./script/dev-up`, `./script/dev-test`, `./script/dev-ci`, `./script/dev-server`
  - `./script/dev-down` only when reclaiming Docker resources

## Treehouse CLI Reference

- `treehouse status` — show all worktrees in the pool, their lease state, and current branch.
- `treehouse get --lease --lease-holder <slug>` — acquire a durable lease. Prints the worktree absolute path to stdout (banners go to stderr). The worktree is reserved until returned.
- `treehouse return <path> --force` — release a lease (cleans, resets, returns worktree to the pool). Refuses if the worktree has uncommitted changes.
- `treehouse destroy <path> --include-leased --yes` — forcibly remove a leased worktree (data loss risk).
- **Reusing an existing lease:** If `treehouse status` shows a leased worktree from a prior session, you can reuse it rather than acquiring a new one. Switch branches inside it with `git switch <branch>` — it is a standard git worktree once leased.
- **Why Treehouse:** ScriptDrop runs in Docker containers; treehouse provides pre-warmed, reusable git worktrees so agents avoid `npm install` overhead and can start coding immediately.
