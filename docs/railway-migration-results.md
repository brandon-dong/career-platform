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
- `www` left as `A 20.80.7.163` (the Railway trial allows one custom domain).

Certificate status: **issued.** Railway staff re-triggered verification after a support request, and on 2026-10-13 02:57 UTC `https://brandondong.me` served `CN=brandondong.me` (Let's Encrypt YE2) with HTTP 200. Before that it was pending. Railway reported "Waiting for DNS update" on the TXT record while public resolvers already returned the correct value. The zone's negative-cache TTL is 30 minutes. Investigation: [evidence/ex05.md](evidence/ex05.md).

## Rollback

- **Code:** revert the commit and push. Railway redeploys `main` on every push.
- **DNS:** delete the `@` CNAME and recreate `A @ 20.80.7.163`, DNS only. The VM is still running with its own SQLite copy.
- **Data:** once Railway takes writes, pointing DNS back at the VM loses them. The VM's data is a snapshot from 2026-10-08. Before rolling back, pause writes and compare both databases (the comparison above is the method), then copy any new rows back.

## Cost notes

- Railway trial: 30 days or $5.00 of usage, whichever comes first. On 2026-10-12 the dashboard showed **26 days or $4.83 left**, so about $0.17 was used in 4 days. The trial ends around **2026-11-07**. The Free plan after it allows no custom domain.
- Public traffic through the Postgres TCP proxy is billed as egress, so the proxy is removed after the migration.
- Azure VM (`Standard_B2ats_v2`) keeps running as the fallback until the instructor says it can stop. Its cost is in Azure Cost Management.
