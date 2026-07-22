---
name: jira-ready-for-review
description: Use when the user wants all Jira tickets currently in a board's Ready for Review column. Default to `https://goodrx-dev.atlassian.net/jira/software/c/projects/SDRP/boards/6010` when no board URL is provided. This skill uses the Atlassian MCP to identify the Jira site and project, query the matching Ready for Review status, and summarize the tickets with links, assignees, and updated dates.
---

# Jira Ready For Review

Use this skill when the user wants the current set of tickets in a Jira board's `Ready for Review` column.

## Fixed Default

- Default board URL: `https://goodrx-dev.atlassian.net/jira/software/c/projects/SDRP/boards/6010`
- Default project key: `SDRP`
- Default status: `Ready for review`

## Inputs

- A Jira board URL, ideally in the form `https://<site>.atlassian.net/jira/software/c/projects/<PROJECT>/boards/<BOARD_ID>`.
- If no board URL is provided, always use `https://goodrx-dev.atlassian.net/jira/software/c/projects/SDRP/boards/6010`.
- Optionally, a custom column name if the user is not asking for `Ready for Review`.

## Workflow

1. Resolve the board URL.
   - If the user provided a board URL, use it.
   - If the user did not provide one, always use `https://goodrx-dev.atlassian.net/jira/software/c/projects/SDRP/boards/6010`.
2. Parse the board URL and extract the site hostname, project key, and board ID when they are present.
   - If parsing fails but the default board URL is in use, continue with `goodrx-dev.atlassian.net`, project `SDRP`, and board `6010`.
3. Use the Atlassian MCP to determine the Jira `cloudId`. Prefer the site that matches the board URL.
4. Confirm the project exists with `getVisibleJiraProjects`.
5. Query Jira issues with JQL using the project key and the matching status name. For the standard case, use:
   `project = <PROJECT_KEY> AND status = "Ready for review" ORDER BY updated DESC`
6. Treat the board column as a Jira status match unless the MCP exposes board-column details directly in the future.
   - For the default workflow, assume the board's `Ready for Review` column maps to Jira status `Ready for review`.
   - Keep the answer concise and do not include the assumption sentence unless the user asked for extra detail or the mapping looks uncertain.
7. Summarize the results in this compact format:
   - First line: `I found <count> ticket:` or `I found <count> tickets:`
   - Then one flat bullet per issue in descending `updated` order
   - issue key with link
   - summary
   - assignee if present
   - updated date
8. Format each issue exactly like this shape:
   - `- SDRP-191 (https://goodrx-dev.atlassian.net/browse/SDRP-191) - [Sentry] Slack alert notification failure`
   - `  Assignee: Caleb Long`
   - `  Updated: March 19, 2026`
9. If no issues match, say so plainly and include the exact JQL used.

## Jira Retrieval Notes

- Prefer `searchJiraIssuesUsingJql` for the final ticket list because the user is asking for a filtered set, not one specific issue.
- Use `getAccessibleAtlassianResources` first when the `cloudId` is unknown.
- Use `getVisibleJiraProjects` to verify the project key before assuming the board URL is valid.
- Jira status names are case-insensitive in practice, but keep the displayed status text aligned with the user's wording when reporting results.
- If the board column name and Jira status name might differ, say that you are using the Jira status that best matches the column name exposed by the board URL context.

## Response Shape

Prefer this structure by default:

1. `I found <count> ticket:` or `I found <count> tickets:`
2. A flat list of matching issues in descending `updated` order.
3. Omit extra explanation unless needed.
4. Include the exact JQL only when there are no matches or when the user asks for it.

## Example Default Invocation

`Use $jira-ready-for-review`

## Example Invocation

`Use $jira-ready-for-review to pull all tickets in Ready for Review from https://goodrx-dev.atlassian.net/jira/software/c/projects/SDRP/boards/6010`
