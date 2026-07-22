# Elixir PR Review Heuristics

Use this reference when the pull request touches Elixir, Phoenix, Ecto, Oban, Broadway, or OTP-heavy code.

## Priorities

1. Protect correctness and operational safety first.
2. Prefer clear data flow and explicit boundaries over clever abstractions.
3. Keep modules small, cohesive, and honest about side effects.
4. Preserve Elixir and Phoenix conventions unless the codebase already established a stronger local pattern.

## High-severity smells

- Silent behavior changes in `with`, pattern matches, or function heads that broaden accepted inputs or swallow failures.
- Process, task, or supervision changes that can leak work, crash unexpectedly, or lose retries.
- Ecto queries or preload changes that create authorization gaps, multi-tenant leakage, or incorrect row selection.
- Migrations or schema changes that are not deploy-safe.
- Conversions to atoms from untrusted input.
- N+1 queries or expensive per-row work on hot paths.

## Review questions

### Module design

- Does each module own one clear responsibility?
- Are public functions small, intention-revealing, and easy to compose?
- Did the PR add indirection without removing real complexity?

### Error handling

- Are success and failure shapes consistent?
- Are exceptions used only for exceptional cases?
- Does logging preserve useful context without leaking secrets?

### Concurrency and OTP

- Does a new `Task`, `GenServer`, or async flow have supervision, timeout, and backpressure considered?
- Could message ordering or retries create duplicated side effects?
- Would a crash leave partial state or stuck work behind?

### Ecto and data boundaries

- Are changesets still the place where validation and casting happen?
- Are repo calls located in boundary modules rather than scattered through controllers or views?
- Does the query match the business rule exactly, including tenant and status scoping?

### Phoenix and web flows

- Are controllers and LiveViews thin?
- Are assigns and params normalized before business logic uses them?
- Does the change preserve authorization, CSRF, caching, and idempotency expectations?

### Tests

- Do tests cover the changed branch behavior and failure paths?
- Are tests asserting outcomes instead of implementation details?
- Is there enough regression coverage for bugs that would matter in production?

## Tone for recommendations

- Write findings in a direct, technical voice.
- Favor concrete alternatives over vague style advice.
- Call out when something is idiomatic and solid, not only when it is wrong.
