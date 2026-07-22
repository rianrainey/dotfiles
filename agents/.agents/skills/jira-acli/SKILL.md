---
name: jira-acli
description: Shared ACLI authentication and Jira retrieval reference for Jira-related skills. Use when any skill needs to authenticate with acli, fetch a Jira issue, or retrieve comments/links. This is a utility skill — load it alongside other Jira skills rather than on its own.
---

# Jira ACLI Reference

## ACLI Authentication

Requires `acli` installed and available in `PATH`. Default Jira site is `goodrx-dev.atlassian.net`.

- Install: `https://developer.atlassian.com/cloud/acli/guides/install-acli/`
- Set site: `export JIRA_SITE="${JIRA_SITE:-goodrx-dev.atlassian.net}"`
- OAuth (interactive): `acli jira auth login --web`
- API token (non-interactive):
  - Create token: `https://id.atlassian.com/manage-profile/security/api-tokens`
  - Set env: `export JIRA_EMAIL="you@goodrx.com"` and `export JIRA_API_TOKEN="<token>"`
  - Login: `echo "$JIRA_API_TOKEN" | acli jira auth login --site "$JIRA_SITE" --email "$JIRA_EMAIL" --token`
- Verify: `acli jira auth status`
- Re-auth after errors: re-run the login command for the chosen auth method.

## Jira Retrieval Notes

- Prefer `acli jira workitem view <KEY> --json` over search once the issue key is known.
- Fetch comments and links separately via `acli jira workitem comment list --key <KEY> --json` and `acli jira workitem link list --key <KEY> --json`.
- Always use `--json` for structured parsing.
- Jira instances vary. If acceptance criteria is not a standard field, inspect the returned JSON for a likely custom field by name and include it in the plan summary.
- If linked issues or subtasks are present but only partially populated, summarize what is available rather than making extra speculative assumptions.
- MCP fallback: use `getJiraIssue` with `fields: ["*all"]` to mirror the data acli would return.
