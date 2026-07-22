# Metrics

## Token Metrics

- `session_total_tokens`: Sum of positive deltas between successive rollout `total_token_usage` snapshots for a session.
- `daily_total_tokens`: Sum of session token deltas whose event timestamps fall on that UTC day.
- `cached_input_ratio`: `cached_input_tokens / input_tokens`, guarded for divide-by-zero.

## Parallelism Metrics

- `active_time`: Total time with at least one active session in the selected window.
- `parallel_time`: Total time with two or more active sessions.
- `parallelism_ratio`: `parallel_time / active_time`
- `series_ratio`: `1 - parallelism_ratio`
- `peak_concurrency`: Maximum number of simultaneously active sessions.

## Session Metrics

- `session_duration`: `last_event_ts - first_event_ts`
- `feedback_loop_minutes`: time from first recorded user turn to first token event for the same session, when both are present
- `focus_session`: A session lasting at most 90 minutes and using at most 120000 tokens

## Coaching Heuristics

- `token_efficiency`: favors higher cached-input ratio and lower median session cost
- `parallel_work`: favors higher parallelism ratio and peak concurrency above 1
- `delegation_leverage`: favors bursty starts of distinct sessions within short windows
- `feedback_speed`: favors lower median time to first token activity
- `reuse`: favors explicit skill-style prompts and repeated use of structured workflows
