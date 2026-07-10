---
name: github-create-draft-pr
description: Create a GitHub draft pull request for the current branch using the repository's PR description or issue template, after first running a security-best-practices review. Use when the user asks to open, draft, prepare, or create a GitHub PR with gh CLI, especially when they want a simple business-first review document, the repo template followed, or a security pass before the PR is opened.
---

# GitHub Create Draft PR

Create a draft PR with `gh` only after doing a brief security-oriented review using `security-best-practices` for the languages and frameworks in scope.

When this skill creates a PR, it should also create a plain-language review document that is easy to scan and understand.

## Writing Style For The Review Doc

- Write at about an 8th grade reading level.
- Use short sentences, short paragraphs, and simple bullets.
- Put the business reason first. Explain why the change matters before the technical details.
- Avoid jargon when possible. If a technical term is needed, explain it in plain words.
- Prefer "this changes", "this fixes", "this means" over abstract engineering language.

## Review Doc Structure

Create a companion review document for the PR with this shape:

1. PR link near the top.
2. Business flow changes near the top, before the executive summary.
3. Short executive summary.
4. Main code or system changes.
5. Testing.
6. Risks, follow-ups, or open questions.

The business flow section should answer:

- What business process is changing?
- Who is affected?
- Why are we doing this now?
- What will feel different after this ships?

Save the review doc with a filename like:

- `pr-12345-[3-5-word-summary]-review.md`

Use a short lowercase hyphenated summary slug. Do not use a vague name like `review.md`.

## Workflow

1. Verify the repo and branch state.
   - Confirm the current directory is inside a git repository.
   - Determine the current branch and default base branch.
   - Check for an existing PR for the branch before creating a new one:
     - `gh pr view --json number,url,state,isDraft`
   - If a PR already exists, stop and tell the user instead of creating a duplicate.

2. Verify GitHub CLI authentication.
   - Run `gh auth status` with escalated permissions because `gh` requires network access.
   - If authentication is missing or insufficient, ask the user to complete `gh auth login` and then continue.

3. Run a focused security pass before drafting the PR.
   - Use the `security-best-practices` skill explicitly.
   - Keep this pass lightweight unless the user asked for a full security report.
   - Inspect the changed files and look for high-impact issues in the touched code only.
   - If you find critical or important security concerns, pause and tell the user before creating the PR.
   - If there are no blocking findings, continue and mention that the security pass was completed.

4. Gather the PR context from git.
   - Summarize the branch diff against the base branch.
   - Review recent commits:
     - `git log --oneline <base>..HEAD`
   - Review changed files:
     - `git diff --stat <base>...HEAD`
   - Use this context to write a concise title, fill the PR body, and draft the business-first review notes.

5. Find the repository's PR template.
   - Look for common GitHub PR template locations first:
     - `.github/pull_request_template.md`
     - `.github/PULL_REQUEST_TEMPLATE.md`
     - `.github/pull_request_template/*.md`
     - `docs/pull_request_template.md`
   - If the user specifically says "issue template", inspect `.github/ISSUE_TEMPLATE/` and use the closest matching structure only if the repo clearly uses it for PR descriptions.
   - Prefer a dedicated PR template over any issue template when both exist.
   - If multiple PR templates exist, choose the one that best matches the branch or changed area and explain the choice briefly.
   - If no template exists, create a short body with sections for summary, testing, security notes, and follow-ups.

6. Draft the PR content and review notes.
   - Write a clear title from the branch diff and commit history.
   - Fill the template with concrete details instead of leaving placeholders.
   - Keep unchecked checklist items only when they are still genuinely pending.
   - Include a short security note such as "Performed a focused security-best-practices review; no blocking findings" when applicable.
   - Include testing notes based on commands actually run. If nothing was run, say so plainly.
   - Save the generated body to a temporary markdown file in the repo, such as `.git/.codex-draft-pr.md`, before calling `gh`.
   - Also draft the companion review document content using the structure above.
   - The review doc should be plain-language and business-first, not just a technical summary.

7. Create the draft PR.
   - Use `gh pr create --draft --base <base> --title <title> --body-file <path>`.
   - If the repo prefers the web flow and the user asked for it, use `--web`; otherwise stay in CLI flow.
   - If `gh pr create` reports that the branch is not pushed, push with the least surprising safe option and retry:
     - `git push -u origin <branch>`
   - Do not merge, mark ready for review, or assign reviewers unless the user asked.
   - Capture the PR number and URL from the create result or a follow-up `gh pr view`.

8. Create or update the companion review document.
   - Save the review doc in the repo with the final PR number in the filename:
     - `pr-12345-[3-5-word-summary]-review.md`
   - Put the PR link near the top of the document.
   - Put "Business Flow Changes" before "Executive Summary".
   - Keep the tone simple enough for a non-expert engineer or business partner to follow.

9. Report back with the result.
   - Provide the PR URL.
   - Summarize the generated title and the main body sections.
   - Mention the review doc path.
   - Mention whether a repo template was found and which file was used.
   - Mention the outcome of the security pass and any non-blocking concerns.

## Guardrails

- Run all `gh` commands with escalated permissions because they require network access.
- Do not create a duplicate PR for a branch that already has one.
- Do not suppress meaningful security findings just to get the PR opened quickly.
- Do not invent test results, issue links, or rollout steps.
- Prefer concise PR bodies that match the repo's conventions over generic boilerplate.
- Do not write the review doc in dense technical prose when plain language would work better.
- Do not put the business impact after a long technical section.

## Useful Commands

```bash
gh auth status
gh pr view --json number,url,state,isDraft
gh pr view --json number,url,title
git remote show origin
git rev-parse --abbrev-ref HEAD
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
rg --files .github
gh pr create --draft --base main --title "..." --body-file .git/.codex-draft-pr.md
```

Adjust the base branch if the repository uses something other than `main`.
