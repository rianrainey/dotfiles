---
name: teach-me-this-pr
description: Explain a pull request, branch, diff, Jira-linked PR, or code review finding in a beginner-friendly way so Rian can switch context quickly. Use when Rian asks to understand a PR, be taught the business context, get a Ruby-developer-friendly explanation of Elixir or unfamiliar code, or asks phrases like "teach me this PR", "help me grok this", "explain this like I am junior", "walk me through this review", or "why does this matter?"
---

# Teach Me This PR

## Goal

Make the PR understandable before asking Rian to judge it. Start from the business workflow, then walk down to entrypoints, data flow, changed code, and review risk. Assume Rian is smart but may be brand new to the feature area or language.

## Voice

- Be warm, plainspoken, and concrete.
- Use "let's reset from zero" energy when the user is lost.
- Prefer short paragraphs and tiny examples over dense explanations.
- Translate Elixir/Phoenix/Ecto concepts into Ruby/Rails-ish equivalents when helpful.
- Do not make Rian feel behind. Normalize confusion when the domain or language is doing real work.
- Avoid vague claims. Point to files and line numbers when local code is available.

## Workflow

1. Resolve the PR, branch, diff, or ticket context before explaining.
2. Read the changed files and nearby callers, tests, schemas, and controllers enough to explain the behavior from source.
3. Start with the business object or user action in one sentence.
4. Define the main nouns in simple terms.
5. Describe the happy path in 3-5 steps.
6. Describe the edge case or review concern separately.
7. Tie every important claim to a file and line number.
8. End with a tiny mental model, failing example, or "why this matters" summary.

## Explanation Shape

Use this order by default:

```md
**Reset**
[One or two sentences describing the business workflow.]

**Main Nouns**
`ThingOne`: [plain-English meaning]
`ThingTwo`: [plain-English meaning]

**Happy Path**
1. [First thing the app does.]
2. [Next thing.]
3. [What gets saved or returned.]

**The Tricky Case**
[Explain the confusing case with a tiny concrete input.]

**Code Trail**
- `path/to/file.ex:12`: [what happens here]
- `path/to/other_file.ex:34`: [why it matters]

**Mental Model**
[One short takeaway Rian can reuse.]
```

Skip sections when the user asks a narrow follow-up. Keep answering the exact confusion they named.

## Ruby Translation

When explaining Elixir/Ecto to a Ruby developer:

- `Ecto.Multi` is like a transaction builder: several DB operations either all commit or all roll back.
- A changeset is like an ActiveRecord model plus validation/errors for a specific write.
- `cast_assoc` means nested association params are being turned into child records.
- `{:ok, value}` / `{:error, reason}` is a tagged return value instead of exceptions for expected outcomes.
- Pattern matching in function heads or `case` branches is routing based on shape.

Use Ruby-ish pseudocode sparingly when it clarifies the business behavior:

```ruby
DeliveryAttempt.transaction do
  delivery_attempt = DeliveryAttempt.create!(...)
  OrderDeliveryAttempt.create!(order_id: 123, delivery_attempt: delivery_attempt)
end
```

## Style Example

Good:

```md
Totally. Let's reset from zero.

A delivery attempt is the record that says:

`Courier tried to deliver this order.`

The database protects one rule: an order can only have one delivery-attempt link. So the question is whether the request failed because another request already saved that link, or because this request accidentally tried to create the same link twice.
```

Avoid:

```md
The changeset validates uniqueness via nested association casting and therefore the idempotency mapper is overly broad.
```

That may be true, but it skips the business story Rian needs first.
