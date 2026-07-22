# ScriptDrop Container Reuse

Before Docker or test work, inspect the active worktree stack:

```bash
docker compose ps
```

If `elixir` is already running, reuse it. `./script/dev-up` can recreate
services after Compose/environment changes, and `./script/dev-test` can trigger
first-run dependency installation, asset builds, and compilation. Do not use
either solely to run a focused test, inspect local seed data, or capture a UI
screenshot.

When the development and test databases are already prepared, execute a
focused test in the existing container:

```bash
docker compose exec elixir bash -lc 'cd /workspace && MIX_ENV=test mix test <test-path>'
```

Use `./script/dev-setup` or `./script/dev-test` only when provisioning is
actually required. If that is unclear, report the likely setup cost before
starting it.

## UI screenshots

Use the host `playwright` skill and the application's mapped host port, such as
`http://localhost:21000`, after confirming the stack is running. Do not install
the `playwright` package or its browsers in the `elixir` container: those files
are not part of the image and are lost when the container is recreated. The
host Playwright wrapper uses persistent browser state and, on macOS, defaults
to installed Chrome.
