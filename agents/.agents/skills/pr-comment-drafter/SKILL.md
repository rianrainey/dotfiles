---
name: pr-comment-drafter
description: Draft GitHub pull request review comments in Rian's preferred humble junior-engineer style. Use when Rian asks to write, rewrite, soften, tighten, or post a PR comment; when a finding needs to become an inline review comment; or when Rian asks for plain, curious, evidence-backed language with links to relevant source code.
---

# PR Comment Drafter

## Goal

Turn a review concern into a short, clear PR comment that sounds like a thoughtful junior engineer asking a grounded question, not a verdict from a judge. Keep the comment humble without weakening the technical point.

## Voice

- Write like a junior engineer who did the homework and wants to check their understanding.
- Use "I might be misunderstanding..." when there is real ambiguity.
- Prefer "I think..." and "Would it be safer..." over blunt certainty.
- Use short sentences and everyday words. Explain framework behavior only when it is needed to understand the concern.
- Stay concrete: name the input, code path, response, missing check, or failing test.
- Keep the ask specific and actionable.
- Link to the relevant source code when it supports the concern, especially when the evidence is in an unchanged file outside the PR diff. Use a GitHub blob URL pinned to the PR head branch and line range.
- Link to external documentation only when it directly explains a library or framework behavior central to the concern.
- Avoid sounding performatively apologetic. One humility marker is usually enough.
- Avoid praise padding unless Rian asks for it.
- Avoid dramatic words like "broken", "dangerous", "obviously", or "just".

## Drafting Workflow

1. Identify the best line for the comment.
2. If the evidence is elsewhere, collect a direct GitHub link to the relevant file and lines. Do not claim that an unchanged file is part of the PR.
3. Explain the concern in one plain sentence.
4. Give one concrete example or failing case.
5. Explain the consequence in user or API terms.
6. Ask for one specific safer alternative.
7. Suggest a focused test when it would protect the intended behavior.

## Default Comment Shape

```md
I may be missing some context, but I wanted to check [specific concern].

Right now [what the code checks or does]. [Link to the relevant code or documentation when it supports this claim.] That handles [valid case], but [plain-language edge case].

In that case, [concrete consequence: rollback, wrong response, extra query, missing authorization, etc.].

Could we [specific recommendation]? Could we also add [focused test] so we are confident about this behavior later?
```

## With A Failing Test

Use this when Rian asks for proof or a test case:

````md
I may be missing some context, but I think this case could still fail:

```elixir
[small focused example]
```

I would expect [expected result], because [reason]. Right now it looks like [actual result], which means [business consequence].

Could we [specific fix] and add this as a regression test?
````

## Style Example

Good:

```md
I may be missing some context, but I wanted to check this idempotency case.

Right now this checks whether every nested `order_delivery_attempt` has the same `order_id`. That catches a real duplicate submit, but it also treats `"order_ids" => [order.id, order.id]` the same way.

In that case, one request is trying to create two records for the same order. The database rolls the request back, but we still return `:delivery_attempt_exists`, which the courier controllers treat as success.

Could we return `:delivery_attempt_exists` only when there is one nested `order_delivery_attempt` with the unique-constraint error? That would still handle duplicate submits, but not treat duplicate IDs in one request as success. A test with the same order ID twice would help protect this.
```

Avoid:

```md
This is wrong. You need to check the length here or this will silently drop deliveries.
```

The direct version may be technically accurate, but it is harsher than Rian's preferred PR style.

## Posting Comments

If Rian asks to post the comment, confirm the file, side, line, commit SHA, and PR number from GitHub or the local diff. Verify that inline comments target changed lines; if supporting evidence is in unchanged code, link to it in a comment attached to the nearest changed call site. Then use the GitHub CLI or available GitHub tool to post exactly the drafted comment. After posting, return the comment URL.
