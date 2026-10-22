# career-platform

My resume site at **https://brandondong.me**: a FastAPI app with Jinja templates that reads my profile, experience, projects, skills and credentials from a database.

It ran first on an Azure VM (Sept 29 – Oct 12, 2026) and now runs on Railway with PostgreSQL. Email for the domain runs on Zoho Mail, and Google Analytics 4 counts page views and outbound clicks after a visitor accepts.

- Submission index with links to all evidence: [docs/project-1-submission.md](docs/project-1-submission.md)
- Original spec and plans: [docs/superpowers/specs/](docs/superpowers/specs/) and [docs/superpowers/plans/](docs/superpowers/plans/)

> **Status on 2026-10-21:** Railway has paused all builds platform-wide during a security incident, so commit `7c4fce6` (database failure handling, below) is committed and tested but **not yet deployed**. The live site runs `ddf2f03`. Details: [docs/railway-migration-results.md](docs/railway-migration-results.md#database-failure-handling-commit-7c4fce6-2026-10-21).

## How it runs now (Railway)

| Piece | Where |
|---|---|
| Web service | Railway service `career-platform` in project `resilient-endurance`, built from GitHub `main` by Railpack (uv, Python 3.12) |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` (service Settings → Deploy) |
| Database | Railway PostgreSQL service `Postgres` (`postgres-ssl:18` image), reached over Railway's private network via `DATABASE_URL=${{Postgres.DATABASE_URL}}` |
| Other variables | `ADMIN_USERNAME`, `ADMIN_PASSWORD` (set on the service, never in Git) |
| Domain | `brandondong.me` → Cloudflare CNAME (DNS only) → Railway. `www` is a proxied Cloudflare record that redirects to the root |
| Certificates | Railway issues and renews the root's (Let's Encrypt, valid to 2027-01-10); Cloudflare covers `www`. Details and how to check: [docs/evidence/dns-final.md](docs/evidence/dns-final.md#certificates) |
| Health | `GET /healthz` returns 200 only when a profile can be read, 503 otherwise |

The app sits behind Railway's HTTPS proxy, so it trusts `X-Forwarded-Proto` (`app/main.py`). Without that, stylesheet links come out as `http://` and the page loads unstyled.

**When the database fails** (commit `7c4fce6`): every page returns HTTP 503, the last profile read successfully stays visible, and sections say "temporarily unavailable" instead of claiming they're empty. An empty table still returns 200 with "No projects listed yet." After the database recovers, the next request shows real data again without a restart, because every request opens a new database session.

### Update path

Commit and push to `main`. Railway builds that commit and swaps it in once it starts. Check it with `railway deployment list` and `railway logs`, or in the dashboard. On Azure the same update was SSH, `git pull`, `uv sync` and a service restart.

### Local development

Local development stays on SQLite: `uv sync`, then `uv run uvicorn app.main:app --reload`. Tests: `uv run pytest` (on this laptop, `.venv/Scripts/python.exe -m pytest`, because Windows blocks the `pytest.exe` launcher). The Postgres-only tests run when `TEST_POSTGRES_URL` points at a local throwaway database (see the Railway plan).

### Setting it up from scratch

1. Railway project with a PostgreSQL service and a web service connected to this repo, branch `main`.
2. Web service variables: `DATABASE_URL=${{Postgres.DATABASE_URL}}`, `ADMIN_USERNAME`, and a new random `ADMIN_PASSWORD`.
3. Start command as above, health check path `/healthz`, restart policy On Failure.
4. Load data: `scripts/copy_to_postgres.py` through a temporary Postgres TCP proxy, then remove the proxy.
5. Custom domain in Railway; in Cloudflare, `@` CNAME to Railway's target (DNS only) plus the `_railway-verify` TXT record.

Full steps with checks: [Railway plan, Section R](docs/superpowers/plans/2026-10-08-railway-migration.md#section-r-railway-setup-and-cutover-dashboard-done-by-hand).

## Architecture

- Web request on Railway and on Azure, with ports, protocols and where TLS ends: [docs/diagrams/request-path.md](docs/diagrams/request-path.md)
- Email (incoming, outgoing, SPF/DKIM/DMARC checks) and analytics: [docs/diagrams/email-and-analytics.md](docs/diagrams/email-and-analytics.md)

## Rollback

*Written 2026-10-21.*

**Code.** Revert the bad commit and push: `git revert <sha>`, then `git push origin main`. Railway builds the revert like any other commit. For a faster rollback without a build, open the service's Deployments tab in Railway, pick the last good deployment and choose Rollback (the undo step in the Railway plan, R7). Check afterward: `railway deployment list` shows the expected commit, `curl https://brandondong.me/healthz` returns `{"status":"ok"}`, and the page shows the expected content. Both paths need Railway's deploy system; during an outage like 2026-10-21's, neither works and the last successful deployment keeps serving.

**Data.** Railway's PostgreSQL is the only copy of the current data. Railway calls its Postgres unmanaged, so backups are my job, and **no backup has been taken yet** (see Limitations). The procedure:

1. Before any manual data change, take a dump: open a temporary TCP proxy on the Postgres service, run `pg_dump` against `DATABASE_PUBLIC_URL`, save the file outside this repository, then remove the proxy.
2. To undo a change, restore the affected rows from that dump, or for a full restore, drop the tables and load the dump with `psql`.
3. Check with the same table-by-table comparison used in the migration (row counts and content hashes), then load the pages.

**Writes after cutover.** The app has no routes that write to the database, so the only writes since the move are ones I made by hand (the "Cloudflare DNS" skill, id 10, on 2026-10-12). A rollback to an older dump would lose any such edits, so list them before restoring and re-apply them afterward.

**Schema.** Tables come from the SQLAlchemy models through `create_all`, which only creates missing tables and never changes existing ones. Rolling back code that changed a model doesn't change the table back; that would need a hand-written `ALTER TABLE` until the project adopts a migration tool.

**Hosting.** There's no second host to fall back to. The Azure VM and its SQLite copy were deleted on 2026-10-16, so DNS can't be pointed back at it.

## Who owns what

Railway now owns the host, the OS, routing, TLS certificates and their renewal. I still own the code, runtime versions, settings and secrets, the data and schema, DNS, testing, and recovery. Railway hosts PostgreSQL but calls it unmanaged, so backups and restores are mine too.

Compared with Tuesday's Azure setup, the firewall rule, nginx `server_name`, Certbot, Let's Encrypt domain validation and the renewal timer all moved to Railway. Getting HTTPS took one custom hostname and two DNS records. What I still had to do myself was DNS, the start command, secrets, and moving the data.

| Layer | Azure VM | Railway |
|---|---|---|
| Operating system and patches | Me (Ubuntu 24.04) | Railway |
| Runtime | Me: Python 3.12 and packages via `uv` on the VM | Shared: I pin Python and packages in Git; Railpack installs them |
| Web entry point | Me: Azure NSG rules and Nginx | Railway's edge |
| TLS certificate and renewal | Me: Certbot and its systemd timer | Railway (root); Cloudflare (`www`) |
| Application code | Me | Me |
| Configuration and secrets | Me: `.env` on the VM | Me, stored in Railway variables. Railway holds them, and the 2026-10-21 incident shows that's a risk I still have to respond to by rotating them |
| Database software | Me: SQLite library on the VM | Railway runs the Postgres container; version and settings are still my choice |
| Data and backups | Me | Me (unmanaged Postgres) |
| DNS | Me (Cloudflare) | Me (Cloudflare) |
| Keeping the app running | Me: systemd `Restart=always`, Nginx restart drop-in | Railway's restart policy and health check |
| Deploying | Me: SSH, `git pull`, restart | Railway builds each push, when its build system is up |

## How the migration kept my data

I took an online SQLite backup on the VM and checked that it reads. Then I copied it into Railway Postgres with `scripts/copy_to_postgres.py`, which runs in one transaction and resets the id sequences. Finally I compared the two databases table by table: row counts, rows matched by id, and content hashes all matched. Details, what Git moved versus what needed another method, and two checks that weren't done: [docs/railway-migration-results.md](docs/railway-migration-results.md). Plan: [docs/superpowers/plans/2026-10-08-railway-migration.md](docs/superpowers/plans/2026-10-08-railway-migration.md). There's no separate Railway spec: the plan quotes my request as its spec.

## Decisions

### Should a three-developer startup move from an Azure VM to Railway?

> **DRAFT, written by Claude from this migration's evidence. Brandon: edit this into your own argument before submitting.**

**Recommendation: move, but keep the exit open.**

- **Cost:** Railway used about $0.17 in four days for a small web service plus Postgres. A small Azure VM costs a fixed monthly amount whether it's busy or idle. At this size Railway is cheaper in money. The bigger saving is time.
- **Our hours:** the Azure path took two sessions of firewall rules, nginx, systemd, Certbot and renewal timers. On Railway the same result took one domain and two DNS records, and each update is now a `git push`. For three developers, those hours belong on the product.
- **Control:** we give up the OS, the proxy configuration and the TLS details. In return Railway's choices become our constraints: a deprecated config-as-code format, one custom domain on the trial, and egress billing on the database proxy.
- **Reliability:** Railway restarts failed deploys, keeps the old deploy serving while a new one builds, and refuses a deploy whose health check fails. The VM had one process supervisor and one machine. But Postgres on Railway is unmanaged, so backups are still on us.
- **What would change my answer:** data-residency or compliance rules that need our own network, steady high traffic where usage pricing beats nothing, or a need for anything Railway doesn't run, like custom kernels or GPUs. A second region on a paid plan would also change the cost picture.

### Managed email (Zoho) or running my own mail server?

> **TO WRITE (Brandon), in your own words.** The requirements count the version you wrote in class. Cover the alternatives you considered (for example running a mail server on the VM, or using another provider), what you chose, and why.

## Failures I investigated

*Summaries written afterward (2026-10-21); the linked records are the originals.*

**1. Application and database: the site would have served an empty database (Azure migration, 2026-09-29).** Record: [docs/evidence/ex03.md](docs/evidence/ex03.md) §3 and the [Azure plan's corrections](docs/superpowers/plans/2026-09-24-azure-vm-migration.md#corrections-to-the-spec-read-first). Real, not a lab exercise.
- **Symptom:** the migration plan's inspection found the site would load with the fallback banner instead of my profile.
- **Check:** `data/career_platform.db` was 0 bytes with no tables, and nothing in the code created them.
- **Diagnosis:** the database had never been filled; the app wasn't broken.
- **Repair:** loaded my resume's data into the database on the laptop, then copied the file to the VM.
- **Repeated check:** the laptop and VM copies had matching SHA-256 hashes, `integrity_check` returned `ok`, and the page showed my headline with no fallback banner (plan Verify results, 2026-09-29).

**2. DNS and TLS: wrong certificate after the Railway cutover (2026-10-12).** Record: [docs/evidence/ex05.md](docs/evidence/ex05.md). Real, not a lab exercise.
- **Symptom:** `https://brandondong.me` failed with a certificate name mismatch after `@` was pointed at Railway.
- **Checks:** both public resolvers returned Railway's address and the right TXT token; `openssl s_client` showed Railway's generic `*.up.railway.app` certificate; `curl -k` reached Railway's 404 instead of my app; CAA and DNSSEC were ruled out.
- **Diagnosis:** Railway hadn't finished verifying the domain, which gates both the certificate and the routing.
- **Repair:** Railway staff re-triggered verification after a support request; no DNS change.
- **Repeated check:** at 2026-10-13 02:57 UTC the same commands showed `CN=brandondong.me` and HTTP 200 from my app.

Also recorded: the Railway migration plan's 11 compatibility findings and how each was fixed ([plan](docs/superpowers/plans/2026-10-08-railway-migration.md#what-the-inspection-found-read-first)), the GA4 consent bug ([ex06.md](docs/evidence/ex06.md) §3, commit `48f342a`), and the blocked deploy of 2026-10-21 ([results](docs/railway-migration-results.md#database-failure-handling-commit-7c4fce6-2026-10-21)).

## Limitations

- **No database backup.** Railway's Postgres is the only copy of the current data, and no dump has been taken.
- **No fallback host.** The Azure VM was deleted on 2026-10-16.
- **Railway builds were paused on 2026-10-21.** The database failure handling in `7c4fce6` isn't live yet, and Railway advised rotating all secrets. `ADMIN_PASSWORD` and the Postgres password still need rotating once builds resume.
- **One profile copy per process.** The remembered profile lives in each app process, so a process that starts during an outage shows "Profile temporarily unavailable".
- **No IPv6 at the root.** `brandondong.me` has no AAAA record, so an IPv6-only visitor can't reach it ([dns-final.md](docs/evidence/dns-final.md)).
- **New messages from my domain land in Junk** at my LMU mailbox, even though SPF, DKIM and DMARC pass. Cause unverified ([zoho-header-check.md](docs/evidence/zoho-header-check.md)).
- **DMARC is `p=none`**, so it only monitors; spoofed mail isn't rejected yet.
- **Unverified Azure evidence:** no controlled VM restart was recorded, and the VM's private IP and the 443 NSG rule listing were never saved ([operate-the-vm plan](docs/superpowers/plans/2026-10-01-operate-the-vm.md#verify-results)).
- **Not done:** a message sent before the MX records existed ([ex06.md](docs/evidence/ex06.md)), a deliberate change to the source data before the migration, and a side-by-side comparison of the rendered pages ([results](docs/railway-migration-results.md)).
- **Schema changes** have no migration tool; `create_all` never alters existing tables.

## Costs, expiration dates and cleanup

| Service | What it is | Kind | Cost so far | Ends or renews | Cleanup plan |
|---|---|---|---|---|---|
| Railway web service | App container | Compute | Trial credit: $0.59 of $5 used as of 2026-10-22 00:18 UTC (`railway usage`) | Trial ends around **2026-11-07** (dashboard on 2026-10-12: 26 days left), or at $5 | Move to AWS after the midterm, before the trial ends; then delete the Railway project |
| Railway Postgres | Database container plus its volume (`/var/lib/postgresql/data`) | Compute + retained storage | Included above | Same trial | Take a `pg_dump` before deleting; the volume is deleted with the project |
| Domain `brandondong.me` | Registration at Namecheap | Other | Not recorded here; check the Namecheap order | Expires **2027-10-01** (WHOIS) | Decide on renewal before then |
| Cloudflare | DNS, `www` redirect | Other | $0, free plan | n/a | Keep while the domain is in use |
| Zoho Mail | Mailbox for my domain | SaaS | $0 (plan not recorded; check Zoho's admin console) | n/a | Keep; remove MX records first if ever cancelled |
| Google Analytics 4 | Analytics | SaaS | $0 | n/a | Remove the tag (`GA_MEASUREMENT_ID=""`) if no longer wanted |
| Azure VM, disk, static IP | Previous host | Compute + retained storage | About $6/month for the IP and disk while deallocated, before deletion | Deleted 2026-10-16 | Done. Only `NetworkWatcher_northcentralus` remains, which doesn't bill |

After the trial, Railway's Free plan allows no custom domain, so the site needs a paid plan or another host before about 2026-11-07.

## Reflection

> **TO WRITE (Brandon), in your own words:** what you understand better now, and what you would change.

## History: Azure VM (Sept–Oct 2026)

The site first ran on an Azure VM (`vm-career-platform`, Ubuntu 24.04, North Central US) as uvicorn with 2 workers behind Nginx under systemd, with SQLite and a Let's Encrypt certificate from Certbot. SSH was key-only and allowed only from my laptop's public IP; the app listened on `127.0.0.1:8000`, and only Nginx on ports 80 and 443 was public. The VM was deleted on 2026-10-16, with the instructor's verbal approval (given in person, about 2026-10-13).

**What had to be configured to survive a restart** *(written afterward, 2026-10-21)*: the app's systemd unit with `systemctl enable` (start at boot) and `Restart=always`; Nginx enabled at boot (the Ubuntu default) plus a drop-in with `Restart=on-failure`; and an absolute `DATABASE_URL`, so the app opened the real SQLite file no matter which directory systemd started it in. A controlled restart test was never recorded, so this is unverified.

- [Azure VM migration plan](docs/superpowers/plans/2026-09-24-azure-vm-migration.md)
- [Operate the VM (Nginx, systemd)](docs/superpowers/plans/2026-10-01-operate-the-vm.md)
- [How the site was secured on the VM](docs/how-this-site-is-secured.md) (Exercise 04, my HTTPS explanation)
- [Exercise 03: the VM, SSH rule and build issues](docs/evidence/ex03.md)
