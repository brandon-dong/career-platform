# Azure VM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the career-platform FastAPI app on the Azure VM `vm-career-platform`, serving the same SQLite data the laptop has.

**Architecture:** Code comes from GitHub, dependencies come from a committed `uv.lock`, and the database file is copied from the laptop with `scp`. Uvicorn listens only on the VM's `127.0.0.1:8000`. We check the site from the VM with `curl` and from the laptop through an SSH tunnel, so the only inbound port we open is 22, and only for the laptop's IP address.

**Tech Stack:** Ubuntu Server 24.04 LTS, git, sqlite3, uv, Python 3.12, FastAPI 0.115, Uvicorn 0.30, SQLAlchemy 2.0, SQLite.

**Spec:** Brandon's migration plan (chat, 2026-09-24), reproduced here:

```
Server     Azure VM, already created, reached over SSH
Packages   apt-get: git, sqlite3
Code       git clone from GitHub
Python     uv, then uv sync from the lock file
Config     copy .env from .env.example
Data       scp my SQLite .db file from my laptop
Processes  start uvicorn
Verify     the site answers on the VM and shows my data
```

## Corrections to the spec (read first)

1. **VM IP.** The request gave the laptop's public IPv4 address as the VM's IP. This plan connects to the VM's public IP (`<VM_IP>`) and uses the laptop's IP (`<LAPTOP_IP>`) only as the allowed source in the firewall rule.
2. **No lock file exists yet.** The repo has `requirements.txt` but no `pyproject.toml` or `uv.lock`, so `uv sync` has nothing to install from. Python step Py2 creates both on the laptop and pushes them to GitHub.
3. **The laptop database is empty.** `data/career_platform.db` is 0 bytes and the code never calls `create_all`. As things stand, the site would load with the "fallback mode" banner, and the Verify section would fail. Data step D1 is a hard gate: don't continue until it passes.
4. **Port 22 is closed.** The VM was created with no public inbound ports. Server step S1 opens 22 to the laptop's IP only.

## Global Constraints

- Resource group: `rg-career-platform`. VM: `vm-career-platform`. Region: North Central US. Network security group (NSG): `vm-career-platformNSG`.
- VM public IP: `<VM_IP>` (Portal: VM → Overview → Public IP address). Laptop public IP: `<LAPTOP_IP>` (`curl -4 -s https://api.ipify.org`). Real values are kept out of this public file.
- SSH user: `azureuser`. SSH key: `~/.ssh/isba4775_azure`. Always use both. Never use password login.
- Inbound rules: TCP 22 from `<LAPTOP_IP>/32` only. Don't open 8000, 80 or 443 in this plan.
- App directory on the VM: `/home/azureuser/career-platform`. Database: `/home/azureuser/career-platform/data/career_platform.db`.
- Python 3.12 (`requires-python >=3.12`), matching the laptop (3.12.10) and Ubuntu 24.04 (3.12.x).
- The VM shuts down automatically at 7:00 PM Pacific. After that it is deallocated, and uvicorn isn't running.
- **Laptop shell:** Git Bash, except where a step says PowerShell. `az` isn't on the Git Bash PATH. Run `az` commands in PowerShell after this line:
  `Set-Alias az 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'`

## Review Focus

These failure modes are the most likely to cause trouble, and each one looks like success unless someone checks for it:

1. **Empty or missing database.** If the database is empty or missing, `/` still returns HTTP 200, but it shows the fallback profile and a "Profile view is in fallback mode" banner. D1 (gate) and V1 (banner must be absent) catch this.
2. **Relative `DATABASE_URL` combined with the wrong working directory.** SQLAlchemy quietly creates a new empty `career_platform.db` wherever uvicorn was started. That leads straight to the fallback page. Cf2 uses an absolute path, and V1 checks that no stray `.db` file appeared.
3. **Laptop IP changes** (different Wi-Fi, campus vs. home). `ssh` then hangs until it times out. To fix it, update the S1 rule's source IP (see S1 Undo/Update).
4. **Auto-shutdown at 7 PM.** The VM is deallocated and uvicorn is gone, and `ssh` times out. Run S2 (start the VM) and then Pr1 again.
5. **Default admin password copied from `.env.example`.** The password `career-platform` is public on GitHub. Cf2 replaces it, and V3 confirms the old password is rejected.

---

## Section 1: Server

- [x] **S1. Allow SSH from the laptop only**
  - **Where:** Laptop (PowerShell). Portal alternative: VM → Networking → Add inbound port rule.
  - **Run:**
    ```powershell
    az network nsg rule create -g rg-career-platform --nsg-name vm-career-platformNSG `
      -n AllowSSHFromLaptop --priority 1000 --direction Inbound --access Allow `
      --protocol Tcp --source-address-prefixes <LAPTOP_IP>/32 --destination-port-ranges 22
    ```
  - **Why:** The VM has no inbound ports open, so SSH and `scp` can't reach it. Limiting the rule to `/32` means only this laptop's current IP can even try to connect.
  - **Check:**
    ```powershell
    az network nsg rule list -g rg-career-platform --nsg-name vm-career-platformNSG `
      --query "[].{name:name,src:sourceAddressPrefix,port:destinationPortRange,access:access}" -o table
    ```
    Expected: a single row, `AllowSSHFromLaptop  <LAPTOP_IP>/32  22  Allow`.
  - **Undo:** `az network nsg rule delete -g rg-career-platform --nsg-name vm-career-platformNSG -n AllowSSHFromLaptop`
  - **Update if the laptop IP changes:** `az network nsg rule update -g rg-career-platform --nsg-name vm-career-platformNSG -n AllowSSHFromLaptop --source-address-prefixes <new-ip>/32` (get the new IP with `curl -4 -s https://api.ipify.org`).

- [x] **S2. Make sure the VM is running**
  - **Where:** Laptop (PowerShell). Portal alternative: VM → Overview → Start.
  - **Run:** `az vm start -g rg-career-platform -n vm-career-platform`
  - **Why:** The 7 PM auto-shutdown deallocates the VM. If it's stopped, SSH can't connect.
  - **Check:** `az vm get-instance-view -g rg-career-platform -n vm-career-platform --query "instanceView.statuses[1].displayStatus" -o tsv`. Expected: `VM running`.
  - **Undo:** `az vm deallocate -g rg-career-platform -n vm-career-platform`. This stops compute billing. Don't use `az vm stop`, which keeps billing.

- [x] **S3. Add an SSH alias so the right user and key are always used**
  - **Where:** Laptop (Git Bash).
  - **Run:**
    ```bash
    cat >> ~/.ssh/config <<'EOF'

    Host career-vm
        HostName <VM_IP>
        User azureuser
        IdentityFile ~/.ssh/isba4775_azure
        IdentitiesOnly yes
    EOF
    ```
  - **Why:** Every later step uses `career-vm`, so no command can accidentally use the wrong IP, user or key. `IdentitiesOnly` stops SSH from trying other keys first.
  - **Check:** `ssh -G career-vm | grep -E '^(hostname|user|identityfile) '`. Expected: `hostname <VM_IP>`, `user azureuser`, `identityfile ~/.ssh/isba4775_azure`.
  - **Undo:** Delete the `Host career-vm` block from `~/.ssh/config`.

- [x] **S4. First SSH login**
  - **Where:** Laptop (Git Bash).
  - **Run:** `ssh career-vm 'hostname; lsb_release -ds; whoami'`. Answer `yes` to the host-key prompt the first time.
  - **Why:** Proves that the network rule, key and user all work before anything else depends on them. It also records the VM's host key in `~/.ssh/known_hosts`.
  - **Check:** Expected output: `vm-career-platform`, `Ubuntu 24.04.x LTS`, `azureuser`, with no password prompt.
  - **Undo:** `ssh-keygen -R <VM_IP>` removes the saved host key.

## Section 2: Packages

- [x] **P1. Record what's already installed**
  - **Where:** VM (`ssh career-vm`).
  - **Run:** `dpkg-query -W -f='${Package} ${Status}\n' git sqlite3 2>&1 | tee ~/preinstalled-packages.txt`
  - **Why:** Ubuntu's cloud image usually includes `git`. Recording this means Undo removes only what we added.
  - **Check:** `cat ~/preinstalled-packages.txt` has one line per package. `git` probably says `install ok installed`, and `sqlite3` probably says it isn't installed.
  - **Undo:** `rm ~/preinstalled-packages.txt`

- [x] **P2. Install git and sqlite3**
  - **Where:** VM.
  - **Run:** `sudo apt-get update && sudo apt-get install -y git sqlite3`
  - **Why:** `git` clones the code. `sqlite3` lets us inspect the copied database on the VM (D4 and V1). The app itself uses Python's built-in `sqlite3` module and doesn't need this CLI.
  - **Check:** `git --version && sqlite3 --version`. Both print a version and the exit code is 0.
  - **Undo:** `sudo apt-get remove -y sqlite3` (add `git` only if P1 showed it wasn't installed before), then `sudo apt-get autoremove -y`.

## Section 3: Code

- [x] **C1. Clone the repository**
  - **Where:** VM.
  - **Run:** `git clone https://github.com/brandon-dong/career-platform.git ~/career-platform`
  - **Why:** GitHub is the source of truth for the code. The repo is public, so no credentials are needed on the VM.
  - **Check:** `git -C ~/career-platform log --oneline -1` matches `git log --oneline -1` on the laptop (right now that's `cb05308`; after Py2 it becomes the lock-file commit, and Py4 pulls it).
  - **Undo:** `rm -rf ~/career-platform`

## Section 4: Python

- [x] **Py1. Install uv on the laptop**
  - **Where:** Laptop (PowerShell).
  - **Run:** `winget install --id astral-sh.uv -e`, then open a new terminal.
  - **Why:** The lock file has to be created from the laptop's working copy and committed. uv isn't installed on the laptop yet.
  - **Check:** `uv --version` prints `uv 0.x.y`.
  - **Undo:** `winget uninstall --id astral-sh.uv`

- [x] **Py2. Create `pyproject.toml` and `uv.lock` from `requirements.txt`**
  - **Where:** Laptop (Git Bash, in the repo root).
  - **Run:**
    ```bash
    uv init --bare --python 3.12
    uv add fastapi==0.115.0 uvicorn==0.30.6 jinja2==3.1.4 python-dotenv==1.0.1 sqlalchemy==2.0.35 aiosqlite==0.20.0
    uv add --dev pytest==8.3.3 httpx==0.27.2
    uv run pytest
    ```
  - **Why:** `uv sync` installs from `uv.lock`, and the repo doesn't have one. The versions are copied exactly from `requirements.txt`, so the VM gets the same versions as the laptop. `pytest` and `httpx` are test-only tools, so they go in the dev group and the VM can leave them out.
  - **Check:** `uv run pytest` gives the same result as `python -m pytest` did before this change. `git status --short` shows exactly `?? pyproject.toml` and `?? uv.lock`. `git check-ignore uv.lock` prints nothing, meaning it isn't ignored.
  - **Undo:** `rm pyproject.toml uv.lock && rm -rf .venv`

- [x] **Py3. Commit and push the lock file**
  - **Where:** Laptop (Git Bash).
  - **Run:**
    ```bash
    git add pyproject.toml uv.lock
    git commit -m "build: add pyproject and uv lock file for deployment"
    git push origin main
    ```
  - **Why:** The VM gets its code from GitHub, so the lock file has to be on GitHub. **This push is public** (the repo is public). Confirm before running it.
  - **Check:** `git ls-remote origin refs/heads/main` prints the same SHA as `git rev-parse HEAD`.
  - **Undo:** `git revert HEAD && git push origin main`

- [x] **Py4. Install uv on the VM and sync dependencies**
  - **Where:** VM.
  - **Run:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.local/bin/env
    cd ~/career-platform && git pull --ff-only
    uv sync --locked --no-dev
    ```
  - **Why:** `--locked` makes the command fail if `uv.lock` doesn't match `pyproject.toml`, instead of quietly re-resolving versions. `--no-dev` leaves out pytest and httpx on the server.
  - **Check:** `uv --version` prints a version. Then run `uv run --no-dev python -c "import fastapi, uvicorn, sqlalchemy, jinja2, dotenv; print(fastapi.__version__, uvicorn.__version__)"`. Expected: `0.115.0 0.30.6`.
  - **Undo:** `rm -rf ~/career-platform/.venv`. To remove uv itself: `rm ~/.local/bin/uv ~/.local/bin/uvx && rm -rf ~/.cache/uv ~/.local/share/uv`

## Section 5: Config

- [x] **Cf1. Create `.env` from the example**
  - **Where:** VM.
  - **Run:** `cd ~/career-platform && cp .env.example .env && chmod 600 .env`
  - **Why:** `app/config.py` loads `.env` from the repo root. `.env` is gitignored, so it isn't in the clone. `chmod 600` makes it readable only by `azureuser`, because it will hold the admin password.
  - **Check:** `ls -l .env` shows `-rw-------`.
  - **Undo:** `rm ~/career-platform/.env`

- [x] **Cf2. Set an absolute database path and a new admin password**
  - **Where:** VM.
  - **Run:**
    ```bash
    cd ~/career-platform
    NEWPW=$(openssl rand -base64 18)
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=sqlite:////home/azureuser/career-platform/data/career_platform.db|" .env
    sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$NEWPW|" .env
    echo "Admin password: $NEWPW"
    ```
    Save the printed password in your password manager.
  - **Why:** The example uses `sqlite:///./career_platform.db`, which is relative to wherever uvicorn is started and points at the repo root, not `data/`. A wrong path doesn't cause an error. SQLAlchemy just creates a new empty database. Four slashes make the path absolute. The example password is published on GitHub.
  - **Check:** `uv run --no-dev python -c "from app.config import DATABASE_URL, ADMIN_PASSWORD; print(DATABASE_URL); print(ADMIN_PASSWORD != 'career-platform')"`. Expected: the absolute URL, then `True`.
  - **Undo:** `cp .env.example .env && chmod 600 .env`

## Section 6: Data

- [x] **D1. GATE: confirm the laptop database actually has data**
  - **Where:** Laptop (Git Bash, repo root).
  - **Run:**
    ```bash
    ls -l data/career_platform.db
    python -c "import sqlite3; c=sqlite3.connect('data/career_platform.db'); print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")]); print('profiles:', c.execute('select count(*) from profiles').fetchone()[0])"
    ```
  - **Why:** "Shows my data" can only pass if there is data. **As of 2026-09-24 this file is 0 bytes**, so the second command fails with `no such table: profiles`.
  - **Check:** The file size is greater than 0, the table list includes `profiles` and `experiences`, and `profiles: 1` or more. **If this fails, stop here.** Either point the plan at the real `.db` file (and update the path in D2), or fill in the laptop database first.
  - **Undo:** None needed (read-only).

- [x] **D2. Take a consistent snapshot on the laptop**
  - **Where:** Laptop (Git Bash, repo root).
  - **Run:** `python -c "import sqlite3; s=sqlite3.connect('data/career_platform.db'); d=sqlite3.connect('career_platform.snapshot.db'); s.backup(d); d.close(); s.close()"`
  - **Why:** If the laptop app is running, copying the live file can capture a write halfway through. SQLite's backup API produces a consistent copy. The snapshot filename matches the `career_platform.db` pattern in `.gitignore`, so git won't pick it up.
  - **Check:** `python -c "import sqlite3; print(sqlite3.connect('career_platform.snapshot.db').execute('pragma integrity_check').fetchone()[0])"`. Expected: `ok`.
  - **Undo:** `rm career_platform.snapshot.db`

- [x] **D3. Copy the snapshot to the VM**
  - **Where:** Laptop (Git Bash, repo root).
  - **Run:**
    ```bash
    ssh career-vm 'mkdir -p ~/career-platform/data'
    scp career_platform.snapshot.db career-vm:career-platform/data/career_platform.db
    ssh career-vm 'chmod 600 ~/career-platform/data/career_platform.db'
    ```
  - **Why:** This puts the data at the exact path Cf2 set in `DATABASE_URL`.
  - **Check:** The hashes match:
    ```bash
    sha256sum career_platform.snapshot.db
    ssh career-vm 'sha256sum ~/career-platform/data/career_platform.db'
    ```
  - **Undo:** `ssh career-vm 'rm ~/career-platform/data/career_platform.db'`

- [x] **D4. Check the database on the VM**
  - **Where:** VM.
  - **Run:** `sqlite3 ~/career-platform/data/career_platform.db "pragma integrity_check; select count(*) from profiles; select headline from profiles limit 1;"`
  - **Why:** Confirms the file arrived intact and can be read on Linux, before the app depends on it.
  - **Check:** `ok`, then the same profile count as D1, then your headline.
  - **Undo:** Same as D3.

## Section 7: Processes

- [x] **Pr1. Start uvicorn in the background, listening on localhost only**
  - **Where:** VM.
  - **Run:**
    ```bash
    cd ~/career-platform
    nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 &
    echo $! > ~/uvicorn.pid
    ```
  - **Why:** It has to run from `~/career-platform`, because `app/main.py` mounts `static/` and `templates/` by relative path. `nohup` keeps it running after you log out of SSH. Listening on `127.0.0.1` means it can't be reached from the internet. The NSG blocks 8000 anyway, and making the site public is a separate decision. Calling `.venv/bin/uvicorn` directly (not through `uv run`) makes the PID in `~/uvicorn.pid` belong to uvicorn itself.
  - **Check:** `grep "Application startup complete" ~/uvicorn.log` and `ss -ltn | grep 127.0.0.1:8000` both return a line.
  - **Undo:** `kill $(cat ~/uvicorn.pid) && rm ~/uvicorn.pid`
  - **Note:** The process doesn't survive the 7 PM auto-shutdown or a reboot. After S2 starts the VM again, run Pr1 again. Running it under systemd is out of scope for this plan.

## Section 8: Verify

- [x] **V1. The site answers on the VM and shows the real profile**
  - **Where:** VM.
  - **Run:**
    ```bash
    cd ~/career-platform
    for p in / /about /experience /projects /skills /contact /static/css/styles.css; do
      printf '%-24s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000$p)"
    done
    HEADLINE=$(sqlite3 data/career_platform.db "select headline from profiles limit 1")
    curl -s http://127.0.0.1:8000/ | grep -cF "$HEADLINE"
    curl -s http://127.0.0.1:8000/ | grep -c "fallback mode"
    ls career_platform.db 2>&1
    ```
  - **Why:** An HTTP 200 alone doesn't prove anything, because the fallback page also returns 200. The headline has to come from the database, the banner must be absent, and there must be no stray empty database at the repo root.
  - **Check:** All seven paths return `200`. The headline count is `1` or more. The `fallback mode` count is `0`. `ls` prints `No such file or directory`.
  - **Undo:** None (read-only).

- [x] **V2. Your browser shows the site through an SSH tunnel**
  - **Where:** Laptop (Git Bash), then a browser.
  - **Run:** `ssh -N -L 8000:127.0.0.1:8000 career-vm`, leave it running, and open http://localhost:8000
  - **Why:** You see the real rendered page from the VM without opening port 8000 to the internet. Stop any local copy of the app first, since it would also want laptop port 8000.
  - **Check:** The home page shows your name, headline and experience, with no fallback banner. The other nav pages load, and CSS is applied.
  - **Undo:** Press Ctrl+C in the tunnel terminal.

- [x] **V3. Admin uses the new password**
  - **Where:** VM.
  - **Run:**
    ```bash
    cd ~/career-platform
    PW=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
    curl -s -o /dev/null -w 'new: %{http_code}\n' -u "admin:$PW" http://127.0.0.1:8000/admin/
    curl -s -o /dev/null -w 'old: %{http_code}\n' -u admin:career-platform http://127.0.0.1:8000/admin/
    ```
  - **Why:** Confirms that Cf2 took effect and the password published on GitHub no longer works.
  - **Check:** `new: 200`, `old: 401`.
  - **Undo:** None (read-only).

---

## Full rollback (VM stays; migration removed)

Run in this order, each step's Undo: Pr1 → D3 → Cf1 → Py4 → C1 → P2 → P1 → S4 → S3 → S1. Py3 (the pushed commit) and Py1 (uv on the laptop) are harmless to keep. Undo them separately if you want. To stop all charges, delete the whole `rg-career-platform` resource group.

---

## Run log (2026-09-29)

All 21 steps ran. Where the run differed from the plan:

| Step | What happened | What we did |
|---|---|---|
| S1 | An SSH rule `Allow-SSH-Laptop` (same source IP, port 22) already existed | Deleted the duplicate `AllowSSHFromLaptop`; kept `Allow-SSH-Laptop` |
| S4 | The host-key prompt can't be answered in a non-interactive shell | Used `StrictHostKeyChecking=accept-new` (still rejects a changed key) |
| Py2 | No "before" test run was possible: system Python lacked FastAPI/SQLAlchemy | Gate became "all tests pass under uv": 5 passed |
| Py3 | Plan doc was also uncommitted | Committed it with `pyproject.toml` and `uv.lock` (owner approved) |
| Cf2 | Plan said to print the new admin password | Not printed, to keep it out of the chat log; read it from `.env` over SSH |
| D1 | **Gate failed:** `data/career_platform.db` was 0 bytes with no tables | Created tables and loaded the owner's resume data with a local, git-excluded seed script; gate then passed |
| D2 | `career_platform.snapshot.db` is not matched by `.gitignore` as the plan claimed | Added it to `.git/info/exclude` |
| V1 | Headline check found 0 matches | The page escapes `&` as `&amp;`; the rendered `<h1>` did show the database headline |

Found later (2026-09-30): after moving networks, the laptop's public IP changed and SSH was blocked until S1's rule was updated to the new IP.

## Verify results

| Check | Where | Expected | Result | Date |
|---|---|---|---|---|
| D3 copy matches | Laptop + VM | Same SHA-256 on both | Match | 2026-09-29 |
| D4 database readable on VM | VM | `integrity_check` ok; 1 profile | ok; 1 profile; headline correct | 2026-09-29 |
| Pr1 app started | VM | Startup complete; listening on 127.0.0.1:8000 | Both | 2026-09-29 |
| V1 all pages answer | VM | 7 paths return 200 | 7/7 200 (/, /about, /experience, /projects, /skills, /contact, CSS) | 2026-09-29 |
| V1 real data, not fallback | VM | Headline present; 0 fallback banners; no stray root `.db` | Headline in `<h1>`; 0 banners; no stray file | 2026-09-29 |
| V2 browser via SSH tunnel | Laptop | Profile visible, no banner | Confirmed by owner ("Looks good") | 2026-09-29 |
| V3 admin password replaced | VM | New password 200; default 401 | 200 / 401 | 2026-09-29 |
