---
name: scriptdrop-dev-ops
description: ScriptDrop Docker troubleshooting, database setup, port reference, and dev server debugging. Use when development containers have OOM kills, the dev server won't start, CSS/JS assets return 404, the database doesn't exist, or any ScriptDrop Docker/infrastructure issue arises during implementation.
---

# ScriptDrop Dev Ops

ScriptDrop runs many Docker containers from different worktree sessions. This skill covers common issues and their fixes.

## OOM Kills During Compilation (`mix deps.compile` killed by signal 9)

**Symptoms:** `bash: line X: YYYY Killed mix phx.server` or beam.smp process killed during compilation.

**Root cause:** Multiple stale worktree Docker containers consumed all available memory. Each worktree session spawns 6 containers (elixir, postgres, pubsub, hooknt, pdf_utils, pupperteer) consuming ~1–2 GiB. With 5+ stale sessions, memory is exhausted.

**Fix:**
1. Check memory inside the container: `docker exec <container> free -h`
2. If `available` is under 2 GiB, stop stale containers from other sessions:
   ```bash
   # List all containers
   docker ps --format "{{.Names}}" | sort

   # Identify which containers belong to your session (e.g., script_drop_2_<hash>-*)
   # Stop ALL containers from OTHER sessions:
   docker stop <container-name-1> <container-name-2> ...
   ```
3. After freeing memory, restart the server.

**Prevention:** Run `./script/dev-down` after finishing a session to reclaim resources.

## Dev Server Won't Start (Port Not Listening)

**Symptoms:** `curl http://localhost:21000` returns `connection refused` even though `mix phx.server` appears to be running.

**Troubleshooting steps:**

1. **Check if the endpoint bound:** Inside the container, `ss -tlnp | grep 4000`. The app binds to port 4000 (not 21000 — Docker maps 21000→4000 via `CORE_WEB_PORT` in `.env`).

2. **Check for zombie processes:** `ps aux | grep beam | grep -v grep`. Defunct (zombie) beam processes mean the parent shell was killed without reaping children. Kill them: `kill -9 <pid>` for every zombie.

3. **Check for stuck prompt:** `grep -i "yes/no\|install" /tmp/phx_server.log`. If Phoenix is prompting to install webpack-cli or similar, install it: `npm install -g webpack-cli`.

4. **Clear and restart:**
   ```bash
   docker exec <container> bash -c 'pkill -9 -f beam.smp; sleep 3'
   docker exec -d -w /workspace <container> bash -c 'mix phx.server > /tmp/phx_server.log 2>&1'
   ```
   Wait 5–15 seconds, then check `ss -tlnp | grep 4000`.

## CSS/JS 404 (Assets Not Compiled)

**Symptoms:** Browser console shows 404 for `/css/core_web.css` or `/js/core_web.js`.

**Fix:** Compile webpack assets before starting the server:
```bash
docker exec -w /workspace/apps/core_web/assets <container> bash -c 'pnpm install && pnpm run compile'
```

This must be done before or while the phx.server runs. The webpack watcher (started by phx.server in dev mode) will also compile, but initial compilation is lazy — explicitly pre-compile to avoid 404s on first load.

## Database Doesn't Exist

**Symptoms:** `FATAL 3D000 (invalid_catalog_name) database "core_dev" does not exist`

**Fix:**
```bash
docker exec -e MIX_ENV=dev -w /workspace <container> mix ecto.create
docker exec -e MIX_ENV=dev -w /workspace <container> mix ecto.migrate
```

## Running the Seeds

The seeds create pharmacies, users, and scheduled delivery rules needed for most development:
```bash
docker exec -e MIX_ENV=dev -w /workspace <container> mix run apps/core/priv/repo/seeds.exs
```

This also runs the scheduled-delivery seeds which create "High Volume Pharmacy" (ID 539) and "Next Day Pharmacy" (ID 540) with `scheduled_service_level: true` and operating ranges where `cutoff_time = pickup_start = 09:00:00` — the exact overlap scenario used for testing the service rules timeline.

## Seeded Test Users

| User | Password | Type | Access |
|---|---|---|---|
| `superuser@example.com` | `supersecret` | superuser | Ops portal (`/pharmacies/:id`, `/dashboard`, etc.) |
| `scheduled-pharmacy@example.com` | `supersecret` | pharmacy_admin | Pharmacy admin portal only |
| `frayt@example.com` | `supersecret` | courier | Courier portal only |

**Always use `superuser@example.com` for ops portal screenshots.** Pharmacy admins cannot access the pharmacy show page.

## Port Reference

| Service | Port (Host) | Port (Container) | Config Var |
|---|---|---|---|
| Core Web (ops portal) | 21000 | 4000 | `CORE_WEB_PORT` |
| Patient App | 4200 | 4200 | `PATIENT_APP_PORT` |
| Courier Admin | 4300 | 4300 | `COURIER_ADMIN_WEB_PORT` |
| Pharmacy Admin | 4500 | 4500 | `PHARMACY_ADMIN_WEB_PORT` |

When accessing from the host, use the host port (e.g., `http://localhost:21000`). When accessing from inside the container, use the container port (e.g., `http://localhost:4000`).
