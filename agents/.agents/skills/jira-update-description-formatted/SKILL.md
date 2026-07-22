---
name: jira-update-description-formatted
description: Update Jira issue descriptions with rendered formatting through Atlassian CLI. Use when Codex needs to create or edit a Jira ticket description/body/comment-like rich text using acli and the result must render headings, bullet lists, links, inline code, or other Jira editor styling instead of storing Markdown shortcuts literally.
---

# Jira Update Description Formatted

## Core rule

Use Atlassian Document Format (ADF) JSON for styled Jira descriptions.

Do not rely on Markdown shortcuts such as `### Heading`, `- item`, or backtick inline code when sending text through `acli jira workitem edit --description` or `--description-file`. The Jira web editor converts those shortcuts interactively before saving, but `acli` can store them as literal plain text.

## Workflow

1. Read the Jira issue first:

```bash
acli jira workitem view KEY-123 --fields summary,status,description --json
```

2. Draft the description in simple Markdown shorthand if that is faster.

Supported by the helper script:

- `### H3 heading`
- `- bullet item`
- `[link text](https://example.com)`
- inline code with backticks, such as `` `Core.State.abbreviations()` ``
- blank lines between sections

3. Convert the Markdown shorthand to ADF JSON:

```bash
python3 /path/to/skill/scripts/markdown_to_adf.py description.md description.adf.json
```

4. Validate that the output is JSON and has structured ADF nodes:

```bash
jq '.content | map({type, level: .attrs.level?})' description.adf.json
```

5. Update the Jira issue with the ADF file:

```bash
acli jira workitem edit --key KEY-123 --description-file description.adf.json --yes --json
```

6. Verify the stored description is structured, not one plain paragraph:

```bash
acli jira workitem view KEY-123 --fields description --json |
  jq '.fields.description.content | map({type, level: .attrs.level?})'
```

Expect `heading` nodes for rendered headings, `bulletList` nodes for rendered bullets, and `code` marks inside text nodes for inline code.

## Writing guidance

- Prefer `heading` level `3` for Jira ticket sections unless the user asks for a different hierarchy.
- Use inline `code` marks for constants, functions, field names, file paths, issue keys only when useful, and short command fragments.
- Use links as ADF `link` marks rather than bare URLs when a descriptive label is available.
- Keep descriptions scannable: context, decision, implementation notes, acceptance criteria, and caveats are usually enough.
- Preserve source links, ticket keys, owners, and facts from the source material.

## Direct ADF pattern

For small edits, it is also fine to write ADF directly. Minimal H3:

```json
{
  "type": "heading",
  "attrs": { "level": 3 },
  "content": [{ "type": "text", "text": "Acceptance criteria" }]
}
```

Minimal inline code:

```json
{
  "type": "text",
  "text": "Core.State.abbreviations()",
  "marks": [{ "type": "code" }]
}
```

Minimal link:

```json
{
  "type": "text",
  "text": "Slack thread",
  "marks": [{ "type": "link", "attrs": { "href": "https://example.com" } }]
}
```

## Notes

- `acli jira workitem edit --description-file` accepts plain text or ADF. Use ADF whenever styling matters.
- Jira Cloud issue descriptions are stored as ADF documents with top-level `version`, `type: "doc"`, and `content`.
- If the rendered ticket still looks wrong, read the issue back and inspect `.fields.description`; the node structure tells the truth.
