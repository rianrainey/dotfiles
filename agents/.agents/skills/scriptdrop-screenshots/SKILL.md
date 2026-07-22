---
name: scriptdrop-screenshots
description: Playwright screenshot workflow for ScriptDrop UI changes. Use when implementing a UI/frontend change that needs visual verification in the ScriptDrop ops portal, patient app, courier admin, or pharmacy admin. Covers Docker-based Playwright setup, superuser login, and screenshot capture.
---

# ScriptDrop Screenshots

Use this skill when a ScriptDrop UI change needs visual verification. It covers setting up and running Playwright inside the ScriptDrop Docker container to capture screenshots.

## Workflow

1. **Save the screenshot script** — Copy the template from `scripts/screenshot.js` to `./tmp/screenshot.js` inside the worktree directory. Customize the navigation URL and selectors for your specific page.

2. **Use the seeded superuser** — Never create a custom test user. The seeded superuser credentials are:
   - **Username:** `superuser@example.com`
   - **Password:** `supersecret`
   - This user has access to `/pharmacies/:id` (ops portal). Do NOT use the pharmacy admin users (`scheduled-pharmacy@example.com`) — they cannot access the ops portal pharmacy pages, which require the `:superusers_only` pipeline.

3. **Run Playwright inside the Docker container** — Do not run it from the host. The container has Chromium installed via `npx playwright install chromium`:
   ```bash
   # Copy script into container
   docker cp <worktree>/tmp/screenshot.js <container-name>:/tmp/screenshot.js

   # Install playwright if not already present
   docker exec -w /tmp <container-name> bash -c 'npm init -y > /dev/null 2>&1 && npm install playwright > /dev/null 2>&1'

   # Run script
   docker exec -w /tmp <container-name> node /tmp/screenshot.js

   # Copy screenshots back
   docker cp <container-name>:/tmp/<screenshot>.png <worktree>/tmp/
   ```

4. **Screenshots go to `./tmp/`** — Save them in the worktree's `./tmp/` directory (e.g., `~/Documents/code/worktrees/<slug>/tmp/`). The worktree already has a `.gitignore` that excludes `tmp/`.

5. **Server port mapping** — The app listens on port 4000 inside the container. Docker maps it to the port defined by `CORE_WEB_PORT` in `.env` (default 21000 on localhost). From inside the container, always use `http://localhost:4000`.

6. **Pharmacy show page URL** — `http://localhost:21000/pharmacies/<id>` (or `http://localhost:4000/pharmacies/<id>` from inside the container). Requires superuser login.

## Script Template

See `scripts/screenshot.js` for the base Playwright script. Customize the target URL and page interactions for your specific test case.
