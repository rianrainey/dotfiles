# Style Guide

Use this guidance when turning raw commits into stakeholder release bullets.

## Audience

Assume non-technical stakeholders reading in Slack or email.

## Bullet shape

Default shape:

`<emoji> <what changed> for <who it affects>, <why it matters>.`

Examples:

- `✨ Improved pharmacy association workflows for internal pharmacy teams, reducing manual setup work.`
- `🔒 Hardened export and file upload flows for pharmacy operations users, lowering security risk.`
- `🛠 Fixed shipping and tracking edge cases for internal ops teams, reducing avoidable follow-up work.`

## Category markers

- `✨` feature or enhancement
- `🛠` fix
- `🔒` security
- `📈` operations or workflow improvement
- `⚠️` notable change or migration with stakeholder awareness value

## Rewrite rules

- Lead with the outcome, not the implementation.
- Mention the affected audience whenever it is clear.
- Keep most bullets to one sentence.
- Merge related technical commits into one stakeholder bullet when they represent the same visible outcome.
- Avoid internal jargon, table names, controller names, and implementation artifacts unless the audience needs them.
- Preserve security context, but do not sensationalize it.

## Exclusions

Do not surface work that is only:

- tests
- documentation
- local setup
- CI cleanup
- internal refactors with no stakeholder impact
