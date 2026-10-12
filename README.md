# career-platform

My resume site at **https://brandondong.me**: a FastAPI app with Jinja templates that reads my profile, experience, projects, skills and credentials from a database.

## How it runs now (Railway)

| Piece | Where |
|---|---|
| Web service | Railway service `career-platform` in project `resilient-endurance`, built from GitHub `main` by Railpack (uv, Python 3.12) |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` (service Settings → Deploy) |
| Database | Railway PostgreSQL service `Postgres`, reached over Railway's private network via `DATABASE_URL=${{Postgres.DATABASE_URL}}` |
| Other variables | `ADMIN_USERNAME`, `ADMIN_PASSWORD` (set on the service, never in Git) |
| Domain | `brandondong.me` → Cloudflare CNAME (DNS only) → Railway; Railway issues and renews the certificate |
| Health | `GET /healthz` returns 200 only when a profile can be read |

The app sits behind Railway's HTTPS proxy, so it trusts `X-Forwarded-Proto` (`app/main.py`). Without that, stylesheet links come out as `http://` and the page loads unstyled.

### Update path

Commit and push to `main`. Railway builds that commit and swaps it in once it starts. Check it with `railway deployment list` and `railway logs`, or in the dashboard. On Azure the same update was SSH, `git pull`, `uv sync` and a service restart.

### Local development

Local development stays on SQLite: `uv sync`, then `uv run uvicorn app.main:app --reload`. Tests: `uv run pytest`. The Postgres-only tests run when `TEST_POSTGRES_URL` points at a local throwaway database (see the plan).

## Who owns what

Railway now owns the host, the OS, routing, TLS certificates and their renewal. I still own the code, runtime versions, settings and secrets, the data and schema, DNS, testing, and recovery. Railway hosts PostgreSQL but calls it unmanaged, so backups and restores are mine too.

Compared with Tuesday's Azure setup, the firewall rule, nginx `server_name`, Certbot, Let's Encrypt domain validation and the renewal timer all moved to Railway. Getting HTTPS took one custom hostname and two DNS records. What I still had to do myself was DNS, the start command, secrets, and moving the data.

## How the migration kept my data

I took an online SQLite backup on the VM and checked that it reads. Then I copied it into Railway Postgres with `scripts/copy_to_postgres.py`, which runs in one transaction and resets the id sequences. Finally I compared the two databases table by table: row counts, rows matched by id, and content hashes all matched. Details, rollback and cost notes: [docs/railway-migration-results.md](docs/railway-migration-results.md). Plan: [docs/superpowers/plans/2026-10-08-railway-migration.md](docs/superpowers/plans/2026-10-08-railway-migration.md).

**Trial clock:** Railway's trial ends around **2026-11-07**, or at $5 of usage. The Free plan after that drops the custom domain, so the Azure VM stays running as the fallback.

## Decision: should a three-developer startup move from an Azure VM to Railway?

> **DRAFT, written by Claude from this migration's evidence. Brandon: edit this into your own argument before submitting.**

**Recommendation: move, but keep the exit open.**

- **Cost:** Railway used about $0.17 in four days for a small web service plus Postgres. A small Azure VM costs a fixed monthly amount whether it's busy or idle. At this size Railway is cheaper in money. The bigger saving is time.
- **Our hours:** the Azure path took two sessions of firewall rules, nginx, systemd, Certbot and renewal timers. On Railway the same result took one domain and two DNS records, and each update is now a `git push`. For three developers, those hours belong on the product.
- **Control:** we give up the OS, the proxy configuration and the TLS details. In return Railway's choices become our constraints: a deprecated config-as-code format, one custom domain on the trial, and egress billing on the database proxy.
- **Reliability:** Railway restarts failed deploys, keeps the old deploy serving while a new one builds, and refuses a deploy whose health check fails. The VM had one process supervisor and one machine. But Postgres on Railway is unmanaged, so backups are still on us.
- **What would change my answer:** data-residency or compliance rules that need our own network, steady high traffic where usage pricing beats nothing, or a need for anything Railway doesn't run, like custom kernels or GPUs. A second region on a paid plan would also change the cost picture.

## History: Azure VM (Sept–Oct 2026)

The site first ran on an Azure VM (`vm-career-platform`, Ubuntu 24.04) as uvicorn behind nginx under systemd, with SQLite and a Let's Encrypt certificate from Certbot. Plans and notes:

- [Azure VM migration](docs/superpowers/plans/2026-09-24-azure-vm-migration.md)
- [Operate the VM (nginx, systemd)](docs/superpowers/plans/2026-10-01-operate-the-vm.md)
- [How the site was secured on the VM](docs/how-this-site-is-secured.md)
- [Exercise 05: DNS/TLS failure during the cutover](docs/evidence/ex05.md)
