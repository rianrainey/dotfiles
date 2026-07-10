---
name: jira-worktree-kickoff
description: Use when the user wants to start implementation from a Jira issue URL, including terse requests such as "work this ticket", "start this", or "fix this ticket". This skill fetches the Jira ticket with the Atlassian MCP, gathers description, acceptance criteria, comments, linked issues, and subtasks, creates a short implementation plan, creates a git worktree and branch named from the Jira key and title, and prepares ScriptDrop local port overrides to avoid Docker container port conflicts.
---

# Jira Worktree Kickoff

Use this skill when the user provides a Jira issue URL and wants an implementation-ready worktree plus a plan.

## Inputs

- A Jira issue URL.

## Terse Request Handling

Do not require the user to provide a structured prompt. When the user gives a short request with a Jira issue URL, infer the internal brief from the ticket and local repo context:

- Goal: derive from the issue summary, description, and acceptance criteria.
- Context: collect the issue key, repo, base branch, linked issues, subtasks, comments, and likely affected areas.
- Constraints: preserve unrelated edits, follow repo conventions, protect secrets, and call out high-risk areas.
- Verify: propose the smallest useful check based on the issue's risk and affected system.
- Deliver: report the plan, branch name, worktree path, assigned local ports, open questions, and next step.

Ask only when missing information would materially change the plan or implementation path.

## Fixed Defaults

- Repo path: `~/Documents/code/script_drop`
- Worktree root: `~/Documents/code/worktree_sd`
- Base branch: `master`

## Workflow

1. Parse the Jira URL and extract the issue key. Look for an uppercase key matching `[A-Z][A-Z0-9]+-[0-9]+`.
2. Use the Atlassian MCP to fetch the Jira issue. If needed, call `getAccessibleAtlassianResources` first to determine the Jira `cloudId`, then call `getJiraIssue`.
3. Gather implementation context from the issue:
   - summary/title
   - description
   - acceptance criteria or similarly named custom fields if present
   - comments
   - linked issues
   - subtasks
4. Create a concise plan before changing code. Cover:
   - intended behavior
   - affected systems or files if inferable
   - dependencies or blockers
   - smallest useful verification path
   - open questions from the ticket context
5. Build the branch slug as `<issue-key-lowercase>-<normalized-title>`.
6. Run `scripts/create_worktree.py` with the issue key, title, repo path, worktree root, and base branch.
7. Use the script's printed `port_<KEY>=<value>` lines as the assigned ScriptDrop host-port block. If port bootstrapping fails, report the failure and do not run container commands until it is fixed.
8. Report the plan, branch name, worktree path, assigned local ports, and the next ScriptDrop wrapper command to run from the worktree. Do not automatically switch the active session into the new worktree.

## Slug Rules

- Lowercase the issue key and title.
- Convert any run of non-alphanumeric characters to `-`.
- Collapse repeated dashes.
- Trim leading and trailing dashes.
- Final format must be safe for both a git branch and directory name.

## Jira Retrieval Notes

- Prefer `getJiraIssue` over search once the issue key is known.
- Request fields needed for planning, including comments, subtasks, issue links, summary, and description.
- Jira instances vary. If acceptance criteria is not a standard field, inspect returned fields for a likely custom field by name and include it in the plan summary.
- If linked issues or subtasks are present but only partially populated, summarize what is available rather than making extra speculative assumptions.

## Worktree Rules

- Actually create the worktree. Do not only print commands.
- Fail safely if the target worktree path already exists.
- Fail safely if the target branch already exists.
- Do not overwrite or reuse either without explicit user approval.
- Create the worktree from repo `~/Documents/code/script_drop` and base branch `master`.
- Create the worktree under `~/Documents/code/worktree_sd/<slug>`.
- Create the branch with the exact same `<slug>`.
- By default, `scripts/create_worktree.py` also creates or updates the new worktree's `.env` with a deterministic, currently available port block starting near `35000`.
- The port bootstrap preserves existing `.env` lines and only upserts these keys: `CORE_WEB_PORT`, `PATIENT_APP_PORT`, `COURIER_ADMIN_WEB_PORT`, `PHARMACY_ADMIN_WEB_PORT`, `KATHY_BOT_PORT`, `COURIER_LEGACY_WEB_PORT`, `PHARMACY_API_WEB_PORT`, `PROGRAM_REQUEST_API_WEB_PORT`, `LIVERELOAD_PORT`, `ERL_DIST_PORT`, `CLOUDBEAVER_PORT`, and `POSTGRES_PORT`.
- When the worktree has an `envs/` directory, the script also upserts common cross-app redirect URLs in `envs/dev.local.env` so local redirects point at this worktree's assigned ports.
- Use `--skip-port-bootstrap` only when the user explicitly wants a plain git worktree without ScriptDrop local port preparation.
- For any later ScriptDrop tests, setup, servers, or validation, follow `ScriptDrop Container Workflow`: run repo wrappers such as `./script/dev-up`, `./script/dev-setup`, `./script/dev-test`, `./script/dev-ci`, and `./script/dev-server` from the created worktree, never from the main checkout.
- If `./script/dev-up` still reports a collision, update only this worktree's `.env` port values or rerun `./script/dev-down` from this worktree before retrying; do not use raw `docker compose down` as the normal recovery path.

## Invocation

Example request:

`Use $jira-worktree-kickoff for https://your-company.atlassian.net/browse/SDRP-170`
