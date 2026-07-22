---
name: release-log-create
description: Create an external-facing stakeholder release digest for the script_drop repo over the past x weeks. Use when the user wants a changelog, release log, stakeholder update, weekly or multi-week release summary, or app-by-app digest for non-technical readers. Optimized for Slack or email, grouped by umbrella app, using local git history first with optional PR or Jira enrichment.
---

# Release Log Create

Use this skill to turn recent `script_drop` work into a stakeholder-friendly release digest.

## Inputs

- A time window in weeks, such as `2`, `4`, or `6`.
- Optionally, a narrower audience or app focus, such as pharmacy-facing or patient-facing changes.
- Optionally, a request for PR or Jira links in the appendix.

Default to the current repo when the user is working inside `script_drop`.

## Output Goal

Produce a hybrid stakeholder digest in executive plain-English with:

- `Top Highlights`
- `Patient App`
- `Pharmacy Admin / Pharmacy API`
- `Core / Internal Ops`
- `Courier Tools`
- `Program Request APIs`
- `Shared Platform / Security / Reliability`
- `Appendix: PRs and tickets`

Write for Slack or email first. Keep bullets short, useful, and easy to scan.

## Workflow

1. Confirm the requested time window. If the user says `past x weeks`, pass that integer to the script.
2. Run the bundled script to gather candidate changes:
   ```bash
   python3 scripts/build_release_log.py --repo /path/to/script_drop --weeks 4 --format json
   ```
3. Review the grouped output and discard low-signal items that are clearly internal-only noise.
4. Enrich high-value items with PR or Jira context when it materially improves clarity.
   - Use local commit subjects first.
   - Add PR numbers or Jira keys when already present in the subject or easy to retrieve.
   - Do not block on enrichment.
5. Rewrite each retained item into stakeholder-safe language:
   - what changed
   - who it affects
   - why it matters
6. Emit the final digest using the required section order.
7. Add a short appendix with PR and ticket references for traceability.

## Deterministic Support

Use the bundled script for commit collection and path-based grouping. It:

- reads git history for the requested week window
- groups commits by umbrella app section
- extracts PR numbers and Jira keys from commit subjects
- tags each item with a lightweight category such as feature, fix, security, ops, or notable change
- filters out obvious docs-only, test-only, and dev-only work unless the subject indicates stakeholder impact

If the user asks for a narrower scope, filter the script output to the relevant sections before drafting.

## Writing Rules

- Prefer business impact over implementation detail.
- Use light markers only when they help scanning: `✨`, `🛠`, `🔒`, `📈`, `⚠️`.
- Keep most bullets to one sentence.
- Avoid jargon unless the stakeholder audience clearly expects it.
- Do not expose internal-only cleanup unless it affected reliability, security, or operations.
- Merge repetitive technical commits into one stakeholder bullet when they represent the same outcome.

## Filtering Rules

Usually exclude:

- test-only changes
- docs-only changes
- devcontainer or local setup changes
- refactors with no visible stakeholder impact

Usually include:

- user-facing features
- workflow changes for pharmacy, courier, or internal ops users
- security fixes
- reliability or performance improvements
- API or integration changes that affect partner operations

## References

- For section mapping, read `references/app-mapping.md`.
- For tone and bullet shape, read `references/style-guide.md`.

## Example Invocation

`Use $release-log-create to draft a stakeholder release digest for the last 4 weeks in the script_drop repo.`
