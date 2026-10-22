# Railway migration: results

Migration of the career site from the Azure VM (SQLite) to Railway (web service + PostgreSQL), October 8–12, 2026. Plan: [2026-10-08-railway-migration.md](superpowers/plans/2026-10-08-railway-migration.md).

Connection strings, passwords and keys are left out of this file on purpose.

## Data transfer and comparison

Source: an online `.backup` of the VM database (`~/backups/career_platform-20261008T214850Z.db` on the VM). Its `PRAGMA integrity_check` returned `ok`, and its SQL dump matched the live file. The backup was copied into Railway Postgres by `scripts/copy_to_postgres.py` in one transaction, over TLS, through Railway's temporary public TCP proxy.

Comparison, VM backup vs Railway, read back independently. Rows were matched by `id`, and JSON, boolean and timestamp values were normalized before comparing:

| Table | VM rows | Railway rows | Columns | Rows matched | Content hash | Result |
|---|---|---|---|---|---|---|
| profiles | 1 | 1 | same | 1/1 | `46921beef069` both | ✅ |
| experiences | 3 | 3 | same | 3/3 | `3d2f7c511a06` both | ✅ |
| projects | 1 | 1 | same | 1/1 | `1d6920ed85bf` both | ✅ |
| skills | 9 | 9 | same | 9/9 | `999a19e1c8f1` both | ✅ |
| credentials | 6 | 6 | same | 6/6 | `dea2482951e8` both | ✅ |
| content_pieces | 0 | 0 | same | 0/0 | empty | ✅ |
| contact_submissions | 0 | 0 | same | 0/0 | empty | ✅ |

Both sides had the same seven tables. The VM's live database still hashed the same as the backup after the transfer, so nothing changed on the VM during the move.

## Verification

| Check | Result |
|---|---|
| Railway URL `/healthz` | `{"status":"ok"}` |
| Fallback banner on `/` | absent |
| Stylesheet link behind Railway's proxy | `https://…/static/css/styles.css`, loads (200) |
| Experience order | Western Express → LMU Ice Hockey → Tutor |
| `/admin` with the published default password | 401 |
| Write test: skill added through the Railway CLI (`railway run -s Postgres`) | "Cloudflare DNS" inserted as id 10 and shown on `/skills` |
| Update test: commit `a81cd86` ("Hosted on Railway" footer) pushed | Railway deployment `74e886c2` built that SHA, SUCCESS, footer live ~50 s after the push |
| Custom domain `brandondong.me` | HTTPS 200 with a certificate for `brandondong.me` (2026-10-13 02:57 UTC); see below |

### Custom domain

DNS was changed at 21:48 UTC on 2026-10-12 with the Cloudflare CLI (`cf`):

- `@` changed from `A 20.80.7.163` (Azure VM) to `CNAME gvb8rrd4.up.railway.app`, DNS only.
- Added `TXT _railway-verify` with Railway's verification value.
- `www` left as `A 20.80.7.163` (the Railway trial allows one custom domain). Changed on 2026-10-16; see [Azure VM decommissioned](#azure-vm-decommissioned).

Certificate status: **issued.** Railway staff re-triggered verification after a support request, and on 2026-10-13 02:57 UTC `https://brandondong.me` served `CN=brandondong.me` (Let's Encrypt YE2) with HTTP 200. Before that it was pending. Railway reported "Waiting for DNS update" on the TXT record while public resolvers already returned the correct value. The zone's negative-cache TTL is 30 minutes. Investigation: [evidence/ex05.md](evidence/ex05.md).

### Review of the update test (`a81cd86`)

*Written afterward (2026-10-21), from the Claude Code session transcript of 2026-10-12.* At 22:00:03–22:00:08 UTC the agent added `test_footer_says_where_the_site_is_hosted` and changed the footer in `templates/base.html`. At 22:00:10 it ran the full test suite on my laptop (`86 passed, 2 skipped`) and committed in the same command, then pushed. Railway started building `a81cd86` as deployment `74e886c2` at 22:00:30. **Local tests before the push: verified. A human review of the diff before committing: unverified**, because the test run and the commit happened in one step with no recorded review.

## Database failure handling (commit `7c4fce6`, 2026-10-21)

Commit `7c4fce6` makes every page return HTTP 503 when the database can't be reached, keeps the last profile read successfully visible, and shows "Projects temporarily unavailable" instead of the empty-table message. Before it, pages returned 200 with an invented fallback profile. Tests: `tests/test_degraded.py` (16 of its 18 tests failed before the change, all pass after; full suite 137 passed, 2 Postgres-only skipped).

**Local check, 2026-10-21.** uvicorn on my laptop against a copy of the SQLite database. To make the database unavailable, a second process held an exclusive SQLite lock, so the app's reads timed out; releasing the lock brought it back.

| Time (UTC) | State | `/` | `/projects` | `/healthz` |
|---|---|---|---|---|
| 23:26:37 | Healthy | 200, my profile | 200, Fintech project | 200 `ok` |
| 23:26:39 | Lock held by another process | 503, my profile still shown | 503, "Projects temporarily unavailable" | 503 `database unavailable` |
| 23:27:17 | Lock released, app **not** restarted | 200 | 200, Fintech project back | 200 `ok` |
| 23:28:22 | New app process started while locked (no remembered profile) | 503, "Profile temporarily unavailable", contact email shown | | |

An earlier attempt to simulate the outage by moving the database file failed because Windows keeps an open file locked; those results were discarded.

**Railway deploy: blocked, unverified.** I pushed `7c4fce6` at 2026-10-21 23:35 UTC. GitHub `main` shows it, but Railway started no deployment: `railway deployment list` at 23:47 UTC still showed the 2026-10-20 deployment of `ddf2f03` as the latest, and so did GitHub's deployment list. The service settings were unchanged (repo `brandon-dong/career-platform`, branch `main`).

The cause is on Railway's side. Railway's status page lists a platform-wide "Railway Platform Outage" from 2026-10-21 07:24 UTC, with builds and deployments paused for all customers and Free and Trial plans restored last ([incident](https://status.railway.com/incident/QH8L8B3E)). It is tied to a security incident in which environment variables may have been read ([Railway security disclosure](https://blog.railway.com/p/security-disclosure-wednesday-october-21st)).

Until builds resume, `https://brandondong.me` runs `ddf2f03`, the code from before this fix. The same database outage check has **not** been run on Railway. When builds resume: confirm the deployment's commit, rerun the check, and rotate `ADMIN_PASSWORD` and the Postgres password (the variable and the database role together), then redeploy. Rotating earlier would not take effect without a redeploy, and changing only the variable would cut the app off from its database.

Read-only log review, 2026-10-21 23:50 UTC: the web service's retained HTTP log showed no `/admin` requests, and the last 300 Postgres log lines showed no failed logins.

## Rollback

- **Code:** revert the commit and push. Railway redeploys `main` on every push.
- **Hosting:** there is no second host anymore. The Azure VM was deleted on 2026-10-16, so DNS can't be pointed back at it.
- **Data:** Railway Postgres is the only current copy. The VM and its SQLite copy (snapshot from 2026-10-08) were deleted with it. The `.db` files in this repo date from 2026-09-29 and are older than that snapshot.

## Azure VM decommissioned

On 2026-10-16 the VM was removed so nothing on Azure keeps billing. **The instructor approved this in person after class, on 2026-10-13 as best I remember.** The approval was verbal, so there is no written record of it in this repository. Before that, the VM was already deallocated, but its Standard static public IP and 30 GB StandardSSD OS disk still billed about $6/month.

1. **`www` moved off the VM's IP first (22:11:43 UTC).** The record was `A 20.80.7.163`, DNS only. That IP would be released with the resource group and could be assigned to another Azure customer, so `www` would have served their site. With the Cloudflare CLI, `www` became `A 192.0.2.1`, **proxied**. `192.0.2.1` is a reserved placeholder address that never receives traffic. Proxying lets the zone's existing redirect rule ("Redirect from WWW to root", 301, created 2026-10-13) run at Cloudflare's edge. It had never run before, because Cloudflare only applies redirect rules to proxied records.
2. **Checked:** `http://` and `https://www.brandondong.me/skills?x=1` both return `301` to `https://brandondong.me/skills?x=1`, which ends at HTTP 200. The edge certificate covers `brandondong.me` and `*.brandondong.me` (`Verify return code: 0 (ok)`). `cf dns records list --content 20.80.7.163` returned `[]`.
3. **Resource group deleted (22:12:19 → 22:15:14 UTC).** `az group delete --name rg-career-platform` removed the VM, OS disk, public IP, NIC, NSG, VNet and auto-shutdown schedule. `az group exists` then returned `false`. The only resource left in the subscription is `NetworkWatcher_northcentralus`, which Azure creates automatically and does not bill.

## Cost notes

- Railway trial: 30 days or $5.00 of usage, whichever comes first. On 2026-10-12 the dashboard showed **26 days or $4.83 left**, so about $0.17 was used in 4 days. The trial ends around **2026-11-07**. The Free plan after it allows no custom domain.
- Domain `brandondong.me`: registered at Namecheap on 2026-10-01, expires 2027-10-01 (`.me` WHOIS, checked 2026-10-21). DNS is on Cloudflare's free plan.
- Public traffic through the Postgres TCP proxy is billed as egress, so the proxy is removed after the migration.
- Azure VM (`Standard_B2ats_v2`): deleted on 2026-10-16 with its resource group (see above). Azure no longer bills for it. Cost Management may still show the last partial day, because usage data arrives about a day late.
