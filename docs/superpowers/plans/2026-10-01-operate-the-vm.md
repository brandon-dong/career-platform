# Operate the VM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## The VM (read-only check, 2026-10-01)

| Field | Value |
|---|---|
| Name | `vm-career-platform` |
| Resource group / region | `RG-CAREER-PLATFORM` / North Central US |
| Size / image | `Standard_B2ats_v2` (2 vCPU, 1 GiB) / Ubuntu Server 24.04 LTS |
| State | VM running |
| Public IP | `20.80.7.163` (no DNS name) |
| SSH | `ssh career-vm` (= `ssh -i ~/.ssh/isba4775_azure azureuser@20.80.7.163`); key-only, passwords off |
| NSG `vm-career-platformNSG` | `Allow-SSH-Laptop` 22 from the laptop's IP/32 (prio 300); **`Allow-HTTP-80` 80 from `*` (prio 310) — already exists** |
| App | `/home/azureuser/career-platform`, venv `.venv`, DB `data/career_platform.db`, `.env` with absolute `DATABASE_URL` |
| Today | Uvicorn started by hand with `nohup` on `127.0.0.1:8000` (migration plan step Pr1) |

> **Heads-up on the port 80 rule.** You planned to add `Allow-HTTP-80` at priority 320. A rule with that exact name is already there at priority 310, and Azure won't accept two rules with the same name in one NSG. Nothing needs adding: Task 4 just confirms the existing rule. If you want it at 320 anyway, edit the existing rule's priority instead of adding a new one.

**Goal:** Visitors reach the site at `http://20.80.7.163` (no port). It starts on boot, restarts after a crash, and survives one worker crashing, while port 8000 stays private and the app runs as `azureuser`.

**Architecture:**

```
Internet ──► Azure NSG (port 80 open) ──► nginx :80 (0.0.0.0) ──► uvicorn :8000 (127.0.0.1 only)
                                          systemd: nginx          systemd: career-platform
                                                                  user azureuser, 1 manager + 2 workers
```

- **nginx** is a *reverse proxy*. It holds public port 80 and hands each request to the app on `127.0.0.1:8000`. Ports below 1024 need special rights, and nginx is designed for that: its master process starts as root only to open port 80, and the processes that actually handle requests run as the low-privilege `www-data` user. So the app itself never needs root.
- **systemd** is Ubuntu's process supervisor. A small *unit file* tells it how to start the app, which user to run it as, to start it at boot (`enable`), and to start it again if it dies (`Restart=always`).
- **`--workers 2`** makes uvicorn run one manager process and two worker processes. If one worker crashes, the other keeps serving and the manager starts a replacement (uvicorn 0.30's multiprocess manager). If the manager itself dies, systemd restarts all of it.

**Tech Stack:** Ubuntu 24.04, systemd, nginx (from apt), uvicorn 0.30.6 (already in `.venv`), FastAPI, SQLite.

**Spec:** Brandon's request (chat, 2026-10-01): reachable at `http://PUBLIC-IP` with no port; starts on boot, comes back after a crash, one crash doesn't take the site down; port 8000 closed to the Internet; not root; service named `career-platform`; run as `azureuser`; use the existing code, venv and DB in `~/career-platform`; don't change repo files or add tests; no crash/restart tests in this plan.

## Global Constraints

- Service name: `career-platform`. Unit file: `/etc/systemd/system/career-platform.service`.
- Run as `User=azureuser`, `Group=azureuser`. Never run uvicorn with `sudo`.
- `WorkingDirectory=/home/azureuser/career-platform`, because `app/main.py` opens `static/` and `templates/` by relative path.
- Uvicorn binds `127.0.0.1:8000` only. No NSG rule for 8000 may exist.
- Use `/home/azureuser/career-platform/.venv/bin/uvicorn`. Don't run `uv sync` or change `pyproject.toml`/`uv.lock`.
- No changes to files in the git repo. Everything this plan creates is under `/etc` on the VM.
- Azure changes only in the portal, and only by you (Task 4 is read-only).
- Laptop shell: Git Bash. VM shell: `ssh career-vm`. Every command block below says which one.
- No crash, kill or reboot tests in this plan. You'll run those yourself.

## Review Focus

Things most likely to go wrong, and which check catches each:

1. **The old hand-started uvicorn is still on port 8000.** The new service then fails with `address already in use` and keeps restarting. Task 1 stops it, and Task 2's check shows a running service.
2. **nginx's default "Welcome to nginx!" page answers instead of the site.** Still HTTP 200, so a status code alone doesn't prove anything. Task 3 removes the default site and compares the page on port 80 with the page on port 8000.
3. **The service starts in the wrong folder.** The app crashes with `Directory 'static' does not exist`, or loads the fallback profile. `WorkingDirectory` prevents it, and the checks look for the fallback banner, which must be absent.
4. **Duplicate `Allow-HTTP-80` rule.** See the heads-up at the top. Task 4 lists the rules.
5. **The 7 PM auto-shutdown still applies.** "Starts on boot" means the site comes back by itself *when the VM is started*. It doesn't keep the VM on. Between 7 PM and the next start, `http://20.80.7.163` won't load. That's expected, not a bug in this plan.

---

### Task 1: Stop the hand-started app (≈2 min)

**Where:** VM (`ssh career-vm`).

**Why:** Only one program can listen on `127.0.0.1:8000`. From now on systemd owns that port, so the `nohup` copy has to go.

- [ ] **Step 1: Stop it**

```bash
pkill -u azureuser -f '[u]vicorn app.main:app' ; rm -f ~/uvicorn.pid
```

(The `[u]` matters when this runs as `ssh career-vm "…"`: without it, `pkill -f` also matches the remote shell running the command and kills the SSH session.)

- [ ] **Step 2: Check**

```bash
ss -ltn | grep ':8000' || echo "8000 is free"
```

Expected: `8000 is free`. (If the VM was restarted since the migration, uvicorn was already gone and this is still the expected result.)

---

### Task 2: Run the app as a systemd service (≈6 min)

**Where:** VM.

**Why:** This is the core of the change. Each line of the unit file meets one requirement:

| Line | Requirement it meets |
|---|---|
| `User=azureuser` / `Group=azureuser` | Not root |
| `WorkingDirectory=…` | Finds `static/`, `templates/` |
| `--host 127.0.0.1 --port 8000` | 8000 isn't reachable from outside the VM |
| `--workers 2` | One worker crash doesn't take the site down |
| `Restart=always` + `RestartSec=3` | Comes back after a crash (3 s pause so a crash loop doesn't trip systemd's "too many restarts" limit of 5 in 10 s) |
| `WantedBy=multi-user.target` + `enable` | Starts at boot |

Two workers fit easily in 1 GiB (about 70 MB each). The app's `.env` is still read by `app/config.py`, so the unit needs no environment settings.

- [ ] **Step 1: Write the unit file**

```bash
sudo tee /etc/systemd/system/career-platform.service > /dev/null <<'EOF'
[Unit]
Description=Career Platform (FastAPI on uvicorn)
After=network.target

[Service]
User=azureuser
Group=azureuser
WorkingDirectory=/home/azureuser/career-platform
ExecStart=/home/azureuser/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

- [ ] **Step 2: Check the file before using it**

```bash
sudo systemd-analyze verify /etc/systemd/system/career-platform.service && echo "unit OK"
```

Expected: `unit OK` and no warnings about `career-platform.service`.

- [ ] **Step 3: Load it, enable it at boot, and start it now**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now career-platform
```

- [ ] **Step 4: Check that it's running, enabled, and not root**

```bash
systemctl is-enabled career-platform     # expect: enabled
systemctl is-active career-platform      # expect: active
ps -o user=,pid=,ppid=,args= -p "$(paste -sd, /sys/fs/cgroup/system.slice/career-platform.service/cgroup.procs)"
ss -ltn | grep ':8000'
```

The `ps` line lists every process systemd started for this service (its *cgroup*), so nothing can hide from the check.

Expected:
- `enabled` and `active`.
- One manager line (`…/uvicorn app.main:app …`) and two worker lines (`…python… multiprocessing.spawn …`). Uvicorn starts workers as fresh Python processes, so their command line doesn't mention uvicorn. There may also be one `resource_tracker` helper line. **Every line is owned by `azureuser`, none by `root`.**
- `127.0.0.1:8000` only (not `0.0.0.0:8000` or `*:8000`).

If anything is off, read the log: `journalctl -u career-platform -n 50 --no-pager`.

- [ ] **Step 5: Check that it serves real data**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/ | grep -c 'fallback mode'
```

Expected: `200`, then `0` (no fallback banner, so the database is being read).

---

### Task 3: Put nginx in front on port 80 (≈7 min)

**Where:** VM.

**Why:** nginx takes requests on public port 80 and forwards them to `127.0.0.1:8000`. The `proxy_set_header` lines pass the visitor's real address and the original host name along, so the app's logs show the visitor instead of `127.0.0.1`. Ubuntu's nginx package is already set to start at boot. The small *drop-in* file adds `Restart=on-failure`, so nginx also comes back if it crashes; otherwise the app would be up but unreachable.

- [ ] **Step 1: Install nginx**

```bash
sudo apt-get update && sudo apt-get install -y nginx
```

- [ ] **Step 2: Write the site config and turn off the default site**

```bash
sudo tee /etc/nginx/sites-available/career-platform > /dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
sudo rm -f /etc/nginx/sites-enabled/default
```

(`sites-enabled/default` is only a link, so removing it doesn't delete anything. The original stays in `sites-available/`.)

- [ ] **Step 3: Make nginx restart after a crash**

```bash
sudo mkdir -p /etc/systemd/system/nginx.service.d
printf '[Service]\nRestart=on-failure\nRestartSec=3\n' | sudo tee /etc/systemd/system/nginx.service.d/restart.conf > /dev/null
sudo systemctl daemon-reload
```

- [ ] **Step 4: Test the config, then reload**

```bash
sudo nginx -t && sudo systemctl reload nginx && sleep 2
```

Expected: `syntax is ok` and `test is successful`. If the test fails, nginx keeps running the old config. Fix the file and run this step again. The `sleep 2` matters: `reload` returns as soon as it signals nginx, and for a moment the old worker processes, still serving the welcome page, keep answering.

- [ ] **Step 5: Check**

```bash
systemctl is-enabled nginx                     # expect: enabled
systemctl show nginx -p Restart                # expect: Restart=on-failure
ss -ltn | grep ':80 '                          # expect: 0.0.0.0:80 (and [::]:80)
diff -I 'rel="stylesheet"' <(curl -s http://127.0.0.1:8000/) <(curl -s http://127.0.0.1/) && echo "port 80 = app"
```

Expected: as commented, ending with `port 80 = app`. That means port 80 returns the same page as the app, not nginx's welcome page. The stylesheet line is skipped on purpose: the app builds that link from each request's `Host`, so it reads `http://127.0.0.1:8000/static/…` on one side and `http://127.0.0.1/static/…` on the other. The second form shows nginx is forwarding `Host` correctly.

---

### Task 4: Check from the outside (≈3 min)

**Where:** Laptop (Git Bash), then a browser. The Azure command is read-only (PowerShell).

**Why:** Everything so far was checked from inside the VM. This task checks what a visitor actually sees, and confirms 8000 is closed at the network edge.

- [ ] **Step 1: Confirm the NSG rules (read-only)**

```powershell
& 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' network nsg rule list -g RG-CAREER-PLATFORM --nsg-name vm-career-platformNSG `
  --query "[].{name:name,prio:priority,port:destinationPortRange,src:sourceAddressPrefix,access:access}" -o table
```

Expected: `Allow-SSH-Laptop` (22) and **one** `Allow-HTTP-80` (80, `*`). No row for 8000.

- [ ] **Step 2: The site answers on port 80 with real data**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://20.80.7.163/
curl -s http://20.80.7.163/ | grep -c 'fallback mode'
curl -s -o /dev/null -w '%{http_code}\n' http://20.80.7.163/static/css/styles.css
```

Expected: `200`, `0`, `200`.

- [ ] **Step 3: Port 8000 is closed from the Internet**

```bash
curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://20.80.7.163:8000/
```

Expected: `000` after about 5 seconds, meaning no connection. It's closed twice over: no NSG rule, and uvicorn listens only on `127.0.0.1`.

- [ ] **Step 4: Browser**

Open `http://20.80.7.163` (type `http://`; the site has no HTTPS). Expected: your name and headline, no fallback banner, CSS applied, and every nav page loads.

---

## Undo (in this order)

```bash
# VM
sudo rm /etc/nginx/sites-enabled/career-platform /etc/nginx/sites-available/career-platform
sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
sudo rm -r /etc/systemd/system/nginx.service.d
sudo apt-get remove -y nginx            # optional
sudo systemctl disable --now career-platform
sudo rm /etc/systemd/system/career-platform.service
sudo systemctl daemon-reload
```

Then start it by hand again with migration plan step Pr1 if needed. In the portal, delete `Allow-HTTP-80` to close port 80 again.

## Verify results

| Check | Where | Expected | Result | Date |
|---|---|---|---|---|
| Task 1 port free | VM | `8000 is free` | `8000 is free` (VM had rebooted; nothing to stop) | 2026-10-01 |
| Task 2 service | VM | enabled, active, manager + 2 workers all `azureuser`, `127.0.0.1:8000` | enabled, active; manager + 2 workers + `resource_tracker`, all `azureuser`; `127.0.0.1:8000` | 2026-10-01 |
| Task 2 real data | VM | `200`, 0 fallback | `200`, 0 | 2026-10-01 |
| Task 3 nginx | VM | enabled, `Restart=on-failure`, `0.0.0.0:80`, `port 80 = app` | All four (after the `sleep 2` and stylesheet-line fixes) | 2026-10-01 |
| Task 4 NSG | Laptop | one `Allow-HTTP-80`, no 8000 | `Allow-SSH-Laptop` 22, `Allow-HTTP-80` 80 (prio 310); no 8000 | 2026-10-01 |
| Task 4 public site | Laptop | `200`, 0 fallback, CSS `200` | `200`, 0, CSS `200`; all 7 pages `200` | 2026-10-01 |
| Task 4 8000 closed | Laptop | `000` | `000` | 2026-10-01 |
| Task 4 browser | Laptop | real profile, no banner | Pending (owner) | |

## Run log (2026-10-01)

| Step | What happened | What we did |
|---|---|---|
| Task 1 | `pkill -f 'uvicorn app.main:app'` run over `ssh "…"` killed its own SSH shell (exit 255) | Pattern changed to `'[u]vicorn …'` |
| Task 3 | First `diff` still saw "Welcome to nginx!" | `reload` is asynchronous; old workers answered. Added `sleep 2` |
| Task 3 | `diff` then differed only on the stylesheet `<link>` | The app builds that URL from `Host`; the check now skips that one line |
