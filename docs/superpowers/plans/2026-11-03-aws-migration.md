# AWS Migration (EC2 + RDS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve `brandondong.me` from one EC2 instance with a private Single-AZ RDS PostgreSQL database, with the data intact, before the Railway trial ends.

**Architecture:** Cloudflare DNS (DNS only) points at an Elastic IP. Nginx ends HTTPS on the instance and forwards to uvicorn on `127.0.0.1:8000`. uvicorn reaches RDS over SSL inside the default VPC. Railway keeps serving the domain until Task 10.

```
Browser ──HTTPS :443──► Elastic IP ──► Nginx (TLS ends, Let's Encrypt)
                                         └─HTTP 127.0.0.1:8000──► uvicorn (systemd)
                                                                    └─SSL :5432──► RDS, private
Laptop ──SSH :22 (my IP only)──► instance ──pg_dump──► laptop ──► Google Drive
```

**Tech Stack:** Ubuntu Server 26.04 LTS, t3.micro, RDS PostgreSQL 18.6, Nginx, certbot, systemd, uv, Python 3.12, FastAPI, AWS CLI, Cloudflare CLI (`cf`).

**Spec:** `guides/aws-migration.md` sections 6–12 (course repo) and `docs/aws-migration-notes.md`, which records the decisions.

**Status: carried out 2026-11-03 to 2026-11-05.** This is the plan as approved, so its checkboxes stay unticked. Results and every deviation are in `docs/aws-migration-notes.md`.

## Schedule

The Railway dashboard showed 4 days left on 2026-11-03. After the trial, the Free plan allows no custom domain.

| Target | Work |
|---|---|
| Nov 3–4 | Cost estimate, Tasks 1–7 |
| Nov 5 | Tasks 8–9 |
| Nov 5–6, quiet hour | Task 10, cutover |
| Nov 6–7 | Spare time for problems, Task 11 |

## What the inspection found

| # | Finding | Where | Handled in |
|---|---|---|---|
| 1 | Missing `ADMIN_*` falls back to `admin` / `career-platform`, public in this repo. Missing `DATABASE_URL` falls back to SQLite | `app/config.py:9-11` | Tasks 7, 9 |
| 2 | Only three custom variables exist on Railway: `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`. The rest use code defaults | `railway variables` | Task 7 |
| 3 | `ProxyHeadersMiddleware` has `trusted_hosts='*'`. Safe only if uvicorn listens on loopback and Nginx sets the headers itself | `app/main.py:26` | Task 7 |
| 4 | The site has no write routes, so Railway and AWS can't drift apart unless the database is edited by hand | `app/routes/admin.py`, `app/main.py` | Task 6 |
| 5 | The app only reads, so it doesn't need the RDS admin account | same | Task 6 |
| 6 | Footer and privacy page name Railway, and tests pin both | `templates/base.html:47`, `templates/privacy.html:26`, `tests/test_layout.py:45`, `tests/test_analytics.py:35` | Task 1 |
| 7 | No migration tool. The schema comes from the dump | repo | Task 6 |
| 8 | The manifest doesn't record the query behind its row hashes | `~/backups/career-platform/` | Task 6 |
| 9 | Start command and restart policy lived in Railway's dashboard, not Git | `docs/railway-migration-results.md:41` | Task 7 |
| 10 | The policy has no S3, `iam:PassRole` or `ec2:ModifyInstanceAttribute`, so no instance role, and resizing likely means relaunching | course policy JSON | Tasks 4, 11 |

## Global Constraints

- All work stays on branch `aws-migration`. Don't merge to `main` until Task 11, because Railway redeploys from `main`.
- Every AWS command uses `--profile isba-4775 --region us-east-1`. Stop if `get-caller-identity` ends in `:root`.
- In Git Bash, set `MSYS_NO_PATHCONV=1` for any command with a `/aws/...` path, or Bash rewrites the path.
- Don't use AdministratorAccess. If a request is denied, decode the message and read the rule that fired.
- Secrets live in `~/secrets/career-platform/` on the laptop, never in Git or chat, and are never printed. Passwords come from `openssl rand -hex 24`, so they need no URL encoding.
- No S3, per the decision record.
- Don't run `scripts/copy_to_postgres.py` on AWS. Don't edit Railway's database until Task 10 is finished.
- Don't change any Cloudflare record except the ones each task names. Zoho's MX, SPF, DKIM and DMARC records stay as they are.
- Log every deviation in `docs/aws-migration-notes.md`.

**Names:** security groups `career-web-sg` and `career-db-sg`; key pair `career-platform-aws`; instance tag `career-platform`; RDS `career-platform-db`, database `career_platform`, admin `career_admin`, app role `career_app`; config at `/etc/career-platform/env`.

## Review Focus

1. **A variable is missing from the server's env file.** Expect the default admin login to be refused and `/healthz` to be 200. Task 9.
2. **The instance reboots.** Expect the app and Nginx back with no manual steps. Task 9.
3. **RDS is unreachable.** Expect `/healthz` 503 and pages that fail within seconds rather than hang, then recovery on their own. Task 9.
4. **A request arrives by raw IP or an unknown hostname.** Expect the connection closed, not the site. Task 9.
5. **Mail after the DNS change.** Expect the MX, SPF, DKIM and DMARC records unchanged, and a test message delivered. Task 10.

---

### Task 1: Update the site text for AWS

**Files:**
- Modify: `templates/base.html:47`, `templates/privacy.html:26`, `app/main.py:24-25`, `database.py:10`
- Test: `tests/test_layout.py:45`, `tests/test_analytics.py:35`

**Interfaces:** Produces site text that Task 7 deploys. No code interfaces change.

- [ ] **Step 1: Change the tests.** `tests/test_layout.py:45` asserts `'Hosted on AWS' in footer`. In `tests/test_analytics.py:35`, replace `'Railway'` with `'Amazon Web Services'`.
- [ ] **Step 2: Run them.** `uv run pytest tests/test_layout.py tests/test_analytics.py -v`. Expected: FAIL on those two assertions.
- [ ] **Step 3: Change the templates.** Footer: `Hosted on AWS`. Privacy list item: **Amazon Web Services** hosts the site and its database. My web server receives every request your browser makes and keeps access logs that include your IP address for about 14 days.
- [ ] **Step 4: Update two comments.** `app/main.py:24-25`: Nginx ends HTTPS on the instance and forwards plain HTTP over localhost. `database.py:10`: replace "Railway's network" with "the network".
- [ ] **Step 5: Run everything.** `uv run pytest`. Expected: PASS.
- [ ] **Step 6: Commit** on `aws-migration`: `feat: name AWS as the host in the footer and privacy page`.

### Task 2: SSH key and security groups (guide section 7)

**Interfaces:** Produces `career-web-sg`, `career-db-sg`, key pair `career-platform-aws`.

- [ ] **Step 1: Make a new key, with Brandon typing the passphrase.** `ssh-keygen -t ed25519 -f ~/.ssh/isba4775_aws`. Don't reuse `isba4775_azure`, which has no passphrase.
- [ ] **Step 2: Import the public half.** `aws ec2 import-key-pair`. The private key never leaves the laptop.
- [ ] **Step 3: Create both groups in the default VPC** (`vpc-0b4618d7dfbd70463`).
  - `career-web-sg`: 22 from `<my IP>/32` (from `https://checkip.amazonaws.com`), 80 and 443 from `0.0.0.0/0`.
  - `career-db-sg`: 5432 from `career-web-sg` only, with no CIDR rule.
- [ ] **Step 4: Verify.** `describe-security-groups` shows exactly those rules.

### Task 3: Create the RDS database (guide section 7)

**Interfaces:** Consumes `career-db-sg`. Produces the RDS endpoint and `~/secrets/career-platform/rds-admin-password`.

- [ ] **Step 1: Generate the password to the secrets folder** without printing it. Pass it through `--cli-input-json file://...`, so it stays out of the command line and shell history, and delete that JSON file afterward.
- [ ] **Step 2: Create the database once.** Values: `postgres` 18.6, `db.t4g.micro`, 20 GB `gp3`, encrypted, no storage autoscaling, Single-AZ, not publicly accessible, `career-db-sg`, backup retention 7 days, deletion protection on, database `career_platform`, admin `career_admin`, and the Availability Zone chosen for the instance.
- [ ] **Step 3: Move on to Task 4.** Don't wait for the 5–10 minutes this takes.
- [ ] **Step 4: Brandon checks the RDS console.** Publicly accessible is No, the class and zone match, and encryption is on.

### Task 4: Launch the EC2 instance (guide section 8)

**Interfaces:** Consumes `career-web-sg`, `career-platform-aws`. Produces the instance ID and Elastic IP.

- [ ] **Step 1: Look up the image at launch** from `/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id`. Confirm owner `099720109477` and a name with `server`, not `pro-server`.
- [ ] **Step 2: Launch once.** `t3.micro`, `CpuCredits=standard`, `HttpTokens=required`, 20 GB encrypted `gp3`, a default subnet in the same zone as RDS, public IPv4, `career-web-sg`, key `career-platform-aws`, tag `Name=career-platform`.
- [ ] **Step 3: Allocate and associate the Elastic IP.**
- [ ] **Step 4: Verify the SSH host key** by comparing the fingerprint from `aws ec2 get-console-output` with the one SSH offers, before accepting it.
- [ ] **Step 5: Brandon checks the EC2 console** against the guide's table.

### Task 5: Prepare the server

**Interfaces:** Produces a patched server with `/home/ubuntu/career-platform` on branch `aws-migration`.

- [ ] **Step 1: Update packages and install** `nginx`, `certbot`, `python3-certbot-nginx`, `postgresql-client-18`, `unattended-upgrades`, and `uv`.
- [ ] **Step 2: Add a 1 GiB swap file** that survives reboots.
- [ ] **Step 3: Download the RDS CA bundle** from `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` to `/etc/ssl/rds/global-bundle.pem`.
- [ ] **Step 4: Push the branch and clone it.** `git push -u origin aws-migration`, then clone with `--branch aws-migration`. Run `uv sync --locked --no-dev`.
- [ ] **Step 5: Verify.** `pg_restore --version` shows 18.x, `free -h` shows swap, `systemctl is-enabled unattended-upgrades` shows enabled, and Railway still serves the unchanged site from `main`.

### Task 6: Restore the data (guide section 9)

**Interfaces:** Consumes the endpoint and `railway-20261103T205200Z.dump`. Produces restored data and `~/secrets/career-platform/rds-app-password`.

- [ ] **Step 1: Confirm nobody edited Railway since the backup.** If anyone did, take a new backup first, as in section 2 of the notes.
- [ ] **Step 2: Check the dump** with `sha256sum -c`, then `scp` it to the instance. Run a `psql` connection test to RDS with `sslmode=verify-full`.
- [ ] **Step 3: Restore into the empty database** with `pg_restore --no-owner --no-privileges --exit-on-error`, as `career_admin`. Expected: exit 0.
- [ ] **Step 4: Compare.** The manifest doesn't record its hash query, so run one row-hash query per table against both RDS and a fresh local `postgres:18.6` restore of the same dump. Expected: all 7 tables match, and counts match the manifest (1, 3, 1, 10, 6, 0, 0).
- [ ] **Step 5: Check sequences** match the restore in the notes: `skills_id_seq` = 10, `credentials_id_seq` = 6.
- [ ] **Step 6: Create the read-only role.** `career_app` gets LOGIN, CONNECT, schema USAGE, and SELECT on all tables and sequences. This goes beyond the guide, because it limits what someone who gets into the VM can do.
- [ ] **Step 7: Delete the dump from the instance,** and record the results in the notes.

### Task 7: Run the app under systemd and Nginx (guide section 9)

**Files:**
- Create: `deploy/career-platform.service`, `deploy/nginx-career-platform.conf`

**Interfaces:** Consumes the app password and endpoint. Produces the app answering on port 80 for `aws.brandondong.me`.

- [ ] **Step 1: Write the unit file.** `User=ubuntu`, `WorkingDirectory=/home/ubuntu/career-platform`, `EnvironmentFile=/etc/career-platform/env`, `ExecStart=/home/ubuntu/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`, `Restart=always`, `RestartSec=3`, enabled for `multi-user.target`.
- [ ] **Step 2: Write the Nginx config.** A `default_server` block that returns 444, and a block for `aws.brandondong.me` that proxies to `127.0.0.1:8000` and sets `Host $host`, `X-Real-IP $remote_addr`, `X-Forwarded-For $remote_addr`, `X-Forwarded-Proto $scheme`. Overwriting `X-Forwarded-For` matters because of finding 3.
- [ ] **Step 3: Commit and push** `deploy/`: `feat: add systemd and Nginx config for EC2`. Pull on the server.
- [ ] **Step 4: Write `/etc/career-platform/env`** with mode 640, `root:ubuntu`, holding the three variables. Read the admin values from Railway without printing them. Quote the URL:
  `DATABASE_URL="postgresql://career_app:<password>@<endpoint>:5432/career_platform?sslmode=verify-full&sslrootcert=/etc/ssl/rds/global-bundle.pem"`
- [ ] **Step 5: Install and start both,** then run `nginx -t`.
- [ ] **Step 6: Verify on the server.** `curl -s 127.0.0.1:8000/healthz` returns `{"status":"ok"}`, `ss -tlnp` shows uvicorn on `127.0.0.1` only, and `pg_stat_ssl` shows the app's connection using SSL.

### Task 8: Test subdomain and HTTPS (guide section 10)

**Files:**
- Create: `docs/evidence/dns-before-aws.md`

- [ ] **Step 1: Save the DNS records first.** `cf dns records list -z brandondong.me --per-page 100 --order type`, into the evidence file. This is the rollback reference.
- [ ] **Step 2: Add `A aws` to the Elastic IP, DNS only.** Check `cf dns records --help` for the syntax. Change nothing else.
- [ ] **Step 3: Brandon checks** the grey cloud in the dashboard, and that `nslookup aws.brandondong.me` returns the Elastic IP.
- [ ] **Step 4: Run `sudo certbot --nginx -d aws.brandondong.me --redirect`.**
- [ ] **Step 5: Verify.** Padlock in the browser, HTTP redirects to HTTPS, and `sudo certbot renew --dry-run` passes.

### Task 9: Test the AWS copy (guide section 10)

**Files:**
- Modify: `docs/aws-migration-notes.md` (tests, evidence, anything unverified)

- [ ] **Step 1: Pages.** `/`, `/about`, `/experience`, `/projects`, `/skills`, `/credentials`, `/contact`, `/privacy` return 200 with real data. The stylesheet loads over `https://`. The footer says AWS.
- [ ] **Step 2: Admin.** `/admin` with `admin` / `career-platform` returns 401. No credentials returns 401. The real login works.
- [ ] **Step 3: Reboot.** `sudo reboot`, then `/healthz` returns 200 with no manual steps.
- [ ] **Step 4: Database failure.** Revoke the 5432 rule for about a minute. Expected: `/healthz` 503, pages respond within about 10 seconds. Restore the rule. Expected: `/healthz` 200 with no restart.
- [ ] **Step 5: Exposure.** From the laptop: port 8000 and the RDS endpoint on 5432 aren't reachable, and a request to the bare IP is closed.
- [ ] **Step 6: Logs.** `/etc/logrotate.d/nginx` keeps about 14 days, matching the privacy text. If not, change the config or the text.
- [ ] **Step 7: Test the backup path.** From the laptop, run `pg_dump -Fc` on the instance over SSH to a file, restore it into a local `postgres:18.6`, compare counts, and copy it to Drive.

**Gate:** don't start Task 10 until Tasks 8–9 pass and Brandon approves.

### Task 10: Cut over (guide section 11)

- [ ] **Step 1: Confirm** Railway is still up, and that the `@` record's TTL is short. If it isn't, lower it at least one old TTL ahead.
- [ ] **Step 2: Add `brandondong.me` to `server_name`** in the Nginx config. Commit, push, pull, reload.
- [ ] **Step 3: At a quiet hour, replace `@ CNAME gvb8rrd4.up.railway.app` with `@ A <Elastic IP>`,** DNS only. Change nothing else.
- [ ] **Step 4: Once `nslookup brandondong.me` returns the Elastic IP,** run `sudo certbot --nginx --expand -d aws.brandondong.me -d brandondong.me --redirect`. Visitors may see a certificate warning until this finishes.
- [ ] **Step 5: Verify.** Padlock on `https://brandondong.me`, all Task 9 pages pass, and `https://www.brandondong.me/skills?x=1` still ends at the root domain with 200.
- [ ] **Step 6: Verify mail.** Compare a new `cf dns records list` with `docs/evidence/dns-before-aws.md`: only `@` differs, plus `A aws`. Send a test message through Zoho.

**Rollback while the trial lasts:** put the `@` CNAME back. Data can't have diverged (finding 4). After the trial ends there's no Railway to return to, so problems get fixed forward on AWS.

### Task 11: Merge and record (guide sections 11–12)

**Files:**
- Modify: `README.md`, `docs/aws-migration-notes.md`, `TASKS.md`

- [ ] **Step 1: Merge `aws-migration` into `main`,** with Brandon's approval, and switch the server to `main`. Restart the app and check the site. Delete the branch.
- [ ] **Step 2: Update the README** with the guide's five items and a Mermaid diagram (see section 12). Include the backup and restore commands, and the rule that terminating is safe for data but deleting RDS is not.
- [ ] **Step 3: Note the leftovers.** Current cost, credits remaining, end-of-semester choice, and the ongoing weekly backup from the laptop. Remove the `aws` record if it's no longer wanted.
- [ ] **Step 4: Check the repo for secrets** before the final push.
