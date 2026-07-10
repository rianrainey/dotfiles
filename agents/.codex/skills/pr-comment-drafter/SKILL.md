---
name: pr-comment-drafter
description: Draft GitHub pull request review comments in Rian's preferred humble junior-engineer style. Use when Rian asks to write, rewrite, soften, tighten, or post a PR comment; when a finding needs to become an inline review comment; or when Rian asks for language that is curious, concrete, evidence-backed, and not overly senior-sounding.
---

# PR Comment Drafter

## Goal

Turn a review concern into a clear PR comment that sounds like a thoughtful engineer asking a grounded question, not a verdict from a judge. Keep the comment humble without weakening the technical point.

## Voice

- Write like a junior-to-mid engineer who did the homework.
- Use "I might be misunderstanding..." when there is real ambiguity.
- Prefer "I think..." and "Would it be safer..." over blunt certainty.
- Stay concrete: name the input, code path, rollback, response, missing check, or failing test.
- Keep the ask specific and actionable.
- Avoid sounding performatively apologetic. One humility marker is usually enough.
- Avoid praise padding unless Rian asks for it.
- Avoid dramatic words like "broken", "dangerous", "obviously", or "just".

## Drafting Workflow

1. Identify the best line for the comment.
2. Explain the concern in one plain sentence.
3. Give the concrete example or failing case.
4. Explain the consequence in user/business terms.
5. Ask for a specific safer alternative.
6. Include a small test example only when it makes the point easier to verify.

## Default Comment Shape

```md
I might be misunderstanding [the intended behavior / this flow], but I think [specific concern].

Right now [what the code checks or does]. That handles [valid case], but it also seems to allow [edge case].

In that case, [concrete consequence: rollback, wrong response, extra query, missing authorization, etc.].

Would it be safer to [specific recommendation]? That would still [preserve intended behavior], but avoid [bug/regression].
```

## With A Failing Test

Use this when Rian asks for proof or a test case:

````md
I might be misunderstanding the intended behavior, but I think this case would still fail under the current logic:

```elixir
[small focused example]
```

I would expect this to return [expected result], because [reason]. Right now it looks like it returns [actual result], which means [business consequence].

Would it be safer to [specific fix]?
````

## Style Example

Good:

```md
I might be misunderstanding the intended idempotency case, but I think this still allows one false-positive case.

Right now this checks that all nested `order_delivery_attempts` have the same `order_id`. That catches a real duplicate submit, but it also catches a request like `"order_ids" => [order.id, order.id]`.

In that case, the request itself is trying to insert two `order_delivery_attempts` for the same order. The unique constraint would make the transaction roll back, but we would still return `:delivery_attempt_exists`, which the courier controllers treat as success.

Would it be safer to only map this to `:delivery_attempt_exists` when there is exactly one nested `order_delivery_attempt` with the unique constraint error? That would still handle the duplicate-submit race, but avoid treating duplicate IDs inside the same request as a successful/idempotent delivery.
```

Avoid:

```md
This is wrong. You need to check the length here or this will silently drop deliveries.
```

The direct version may be technically accurate, but it is harsher than Rian's preferred PR style.

## Posting Comments

If Rian asks to post the comment, confirm the file, side, line, commit SHA, and PR number from GitHub or the local diff. Then use the GitHub CLI or available GitHub tool to post exactly the drafted comment. After posting, return the comment URL.
