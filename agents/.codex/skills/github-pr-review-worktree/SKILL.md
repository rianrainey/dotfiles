---
name: github-pr-review-worktree
description: Review a GitHub pull request from either a GitHub PR URL or a Jira issue URL by resolving the associated PR, creating an isolated git worktree, inspecting the diff against the base branch, and producing a code review with an executive summary plus prioritized findings from high severity to low severity. Use when the user wants a pull request reviewed from a URL, especially in `~/Documents/code/script_drop`, and when the review should emphasize expert Elixir, Phoenix, Ecto, and OTP judgment.
---

# GitHub PR Review Worktree

## Overview

Create a fresh review worktree for a GitHub pull request. The input may be either a GitHub pull request URL or a Jira issue URL that points to a ticket associated with a GitHub PR. Resolve the final PR URL first, inspect the PR in isolation, and deliver a severity-ordered review. Use an Elixir-first lens for BEAM, Phoenix, Ecto, and deployment safety concerns when the changed code touches those areas.

## Inputs

- A GitHub pull request URL, or
- A Jira issue URL that is associated with a GitHub pull request.

## Fixed Defaults

- Repo path: `~/Documents/code/script_drop`
- Worktree root: `~/Documents/code/worktree_sd`

## Workflow

1. Normalize the review target into a GitHub pull request URL.
   - If the input is already a GitHub pull request URL, use it as-is.
   - If the input is a Jira issue URL, extract the issue key and use the Atlassian MCP to resolve the associated GitHub pull request URL before doing any GitHub work.
   - Prefer this Jira resolution order:
     - `getAccessibleAtlassianResources` if needed to determine the Jira `cloudId`
     - `getJiraIssue` to load the issue summary, description, and link context
     - `getJiraIssueRemoteIssueLinks` to inspect remote links for GitHub pull request URLs
   - When inspecting Jira data, prefer URLs that clearly match GitHub pull request patterns like `/pull/<number>`.
   - If remote issue links are empty, also inspect the Jira description, comments, and linked issue context already returned by Atlassian for a GitHub PR URL.
   - If multiple GitHub pull request URLs are present, prefer the one that appears most directly tied to the ticket. If the right choice is ambiguous, stop and ask.
   - If no GitHub pull request URL can be found from Jira, stop and report that blocker clearly.
2. Verify GitHub API authentication before doing PR lookup. Prefer `gh auth status`, but if the sandbox cannot read the local keychain, fall back to `GH_TOKEN`, `GITHUB_TOKEN`, or a 1Password-backed token exposed through `GITHUB_PR_REVIEW_OP_SECRET_REF` or `GITHUB_PR_REVIEW_OP_ITEM_ID`.
3. Prepare the review worktree with a reuse-first strategy.
   - First check whether the expected review branch and worktree already exist for this PR.
   - If they exist and clearly correspond to the same PR, prefer reusing them instead of creating a fresh worktree.
   - If they do not exist, run `scripts/prepare_pr_worktree.py <pr-url>` from the skill directory, not the repo root, to create the review branch and worktree. The script:
   - parses the PR number from the URL
   - fetches PR metadata with `gh pr view`
   - creates a safe local review branch named `pr-<number>-<normalized-title>`
   - creates the worktree at `~/Documents/code/worktree_sd/<same-slug>`
4. Reuse safely.
   - Do not overwrite or repurpose an existing branch or worktree that appears to belong to a different PR or different review target.
   - If an existing branch or worktree is ambiguous, stop and ask.
   - If it is an exact match for the same PR, reuse it and continue.
5. Work inside the new worktree for all subsequent inspection. Do not switch the active session automatically unless the user asks.
6. Gather review context in two passes:
   - First pass, always collect:
     - `gh pr view <url> --json title,body,author,baseRefName,headRefName,commits`
     - `git diff --stat origin/<base-branch>...HEAD`
     - `git diff --name-only origin/<base-branch>...HEAD`
   - Second pass, inspect only the highest-signal files and diffs deeply unless the PR is small enough that reviewing the whole diff is clearly cheap.
   - Prioritize files with:
     - Elixir, Phoenix, Ecto, OTP, migrations, background jobs, config, auth, concurrency, or production workflow impact
     - schema or data-shape changes
     - low test coverage or risky control flow
     - surprising file size or high churn
   - Use targeted `git diff origin/<base-branch>...HEAD -- <path>` for those files.
7. Keep the review triage-driven.
   - Prefer a small number of high-confidence, meaningful findings over exhaustive commentary on every file.
   - If the diff is broad but low-risk, summarize the low-risk areas instead of deeply reviewing all of them.
   - If the diff is narrow or clearly high-risk, review more comprehensively.
8. If the PR touches Elixir or Phoenix code, read [references/elixir_review_heuristics.md](references/elixir_review_heuristics.md) before forming conclusions.
9. Review with a code-review mindset, not an implementation mindset:
   - prioritize correctness, security, deploy safety, data integrity, concurrency, and production risk
   - prefer concrete findings with evidence over speculative style notes
   - keep praise brief and specific
10. Write the review to a markdown file inside the review worktree before returning the final answer.
   - Default filename: `pr-<number>-review.md`
   - Default location: the root of the newly created or reused review worktree
   - The markdown review must begin near the top of the document with a Markdown link to the original PR URL
   - Use Markdown headings and concise sections so the review is easy to skim in an editor
11. Always include paste-ready suggested PR comments.
   - Keep this section even in faster reviews.
   - Write comments so they can be copied directly into GitHub review comments with minimal or no editing.
   - For normal-sized PRs, include at least 3 suggested PR comments.
   - For very small PRs with only one or two meaningful discussion points, fewer comments are acceptable.
   - Spread the comments across the most important issues, subtle implementation details, or teaching moments rather than clustering them all on one tiny nit.
   - For each suggested PR comment, specify the best file and line to attach it to in GitHub review UI.
   - If an exact line is unclear, give the nearest useful line or code block and say why that placement makes sense.
12. Produce the markdown review in this order:
   - `Pull Request`: a link to the source PR URL
   - `Executive Summary`: what changed and the overall risk profile
   - `Top Findings`: ordered from high severity to low severity, each with file references and reasoning
   - `Suggested PR Comments`: copy-paste-ready review comments written in a warm, empathetic, coaching-oriented tone that still communicates strong engineering judgment
   - `Expert Recommendations`: Elixir, Phoenix, Ecto, or OTP guidance in the spirit of senior community maintainers
   - `Teachable Moments`: short explanations of Elixir or Phoenix concepts that appear in the review and may be unfamiliar to a Rails-oriented engineer
   - `Testing Gaps`: missing or weak coverage that limits confidence
   - `Lower-Risk Areas Reviewed`: optional short summary when the PR is large and some areas were triaged rather than deeply analyzed
13. Keep the terminal response shorter than the markdown review.
   - In chat, report the review worktree path, local review branch, markdown review file path, a short executive summary, and the top findings only.
   - Put the full polished review and all paste-ready comments in the markdown file.
14. If no material issues are found, say so explicitly and still mention residual risks or areas you could not verify.

## Review Standards

- Treat severity as:
  - High: correctness, security, data loss, authorization, deploy breakage, concurrency hazards
  - Medium: likely bugs, hidden maintenance traps, missing error handling, significant performance regressions
  - Low: clarity, consistency, minor design drift, non-blocking cleanup
- Anchor findings to the diff and surrounding code, not only to the PR description.
- Prefer identifying a small number of meaningful issues over a long list of low-signal nits.
- When referencing files, include the full GitHub branch URL for the PR head branch when possible so the user can jump directly from the review into GitHub.
- Write the markdown review for a strong working engineer, not for an academic audience.
  - Prefer plain language over theory-heavy wording.
  - Explain the practical risk first, then the technical nuance.
  - Keep findings readable in one pass by someone skimming during review.
- Assume the reader benefits from language that is a little simpler than standard senior-engineer review prose.
  - Prefer concrete examples over abstract categories.
  - Lead with examples like `429`, `503`, timeout, or dropped warning log rather than phrases like “non-200 branch” when possible.
  - Avoid piling multiple layers of jargon into one sentence.
- Assume the reader is strong in Rails-style application development but new to Elixir and Phoenix.
  - Briefly decode unfamiliar Elixir notation when it appears in findings or recommendations.
  - If using syntax like `assert_log/2`, explain that `/2` means “a function with arity 2,” similar to naming a method by the number of arguments it accepts.
  - If using tuples like `{:error, {:ok, %HTTPoison.Response{...}}}`, explain what the tuple shape represents in plain language before recommending test cases around it.
  - When a BEAM, Phoenix, Ecto, or OTP idea differs from common Rails instincts, add a short comparison that helps bridge the mental model.
- Prefer clearer wording for potentially unfamiliar review terms.
  - If using a word like `transient`, immediately explain it in plain language, for example: “temporary failures like timeout, rate limit `429`, or Slack `503`.”
  - If using a response-class phrase like `non-200`, prefer the concrete statuses first, then optionally explain the broader category.
- For each suggested PR comment, make it sound like a thoughtful staff engineer:
  - warm and respectful
  - clear about risk and intent
  - helpful in explaining why the change matters
  - comfortable teaching or clarifying esoteric code paths without sounding condescending
- When a tricky concept, invariant, concurrency edge case, or framework-specific nuance is involved, include at least one suggested comment that explains the subtlety in plain language so it can help the PR author and future readers.
- Preserve concrete, evidence-backed findings in the style of:
  - clear severity label
  - direct explanation of the real risk
  - specific file reference
  - concise recommendation
  - optional supporting source or framework citation when it materially strengthens the point
- Optimize for signal density.
  - Avoid spending time on low-risk files if they do not materially affect the review outcome.
  - Spend depth where the risk is concentrated, not where churn is merely visible.
- Keep the teaching lightweight and practical.
  - Do not turn the review into a tutorial.
  - Add short “what this means” explanations only where they help the user understand or act on the review.
  - Prefer one or two sentences of explanation over jargon-heavy deep dives unless the user asks for more.
  - In `Teachable Moments`, assume the reader may be a true beginner for the Elixir concept being referenced, even if they are a strong application engineer overall.
  - Prefer tiny runnable code snippets over abstract explanations when teaching Elixir behavior.
  - When a concept is easy to misunderstand, include a `Bad`, `Good`, `Great` progression with short code samples.
  - Use snippets to answer the exact confusion, for example showing that `Map.put/3` on a struct keeps the struct type when the key already exists.
  - Keep teachable examples short enough to skim in under a minute.
  - If a teachable moment feels dense, rewrite it in plainer language first, then add one concrete example instead of adding more theory.
- In suggested PR comments, optimize for language the user can confidently post.
  - Keep the wording smart but natural.
  - Avoid phrases the user would struggle to defend or explain if the author asks a follow-up question.
  - Favor direct, concrete wording over abstract or overly polished language.

## Notes

- GitHub SSH auth and GitHub API auth are separate. An SSH key alone is enough for `git fetch`, but `gh pr view` still needs API auth.
- For 1Password users, prefer storing a GitHub token in 1Password and exposing it through one of:
  - `GITHUB_PR_REVIEW_OP_SECRET_REF=op://Vault/Item/token`
  - `GITHUB_PR_REVIEW_OP_ITEM_ID=<item-id>` with an item field like `token`
- If the PR cannot be fetched because the sandbox cannot access the macOS keychain, the 1Password fallback lets the skill work without manual per-run token export.
- Keep the review read-only unless the user explicitly asks for fixes.
- If the Jira issue cannot be resolved to a GitHub PR URL, say that clearly and stop after reporting the blocker.
- If the PR cannot be fetched because of GitHub auth or network restrictions, say that clearly and stop after reporting the blocker.
- Report the review worktree path, local review branch, and markdown review file path before presenting findings so the user can jump into the same environment.
- In the markdown review file, make suggested PR comments easy to copy by putting each one in its own fenced Markdown block under a short heading that names the target file or issue.
- For each suggested PR comment block, include:
  - target file
  - suggested GitHub line number or nearest anchor line
  - a one-line note on why that placement is the best spot
- Do not duplicate the full markdown review in the terminal response unless the user asks for it there too.
- When possible, include teachable moments near the relevant finding instead of only as a separate section, so the explanation is attached to the concrete code concern.
