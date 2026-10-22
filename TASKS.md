# Project 1 gaps

Audit against the Project 1 requirements, 2026-10-20, updated 2026-10-21. Each line names the file or check that closes it.

**Due:** Thursday, October 22, 2026, 1:45 PM, through Brightspace.

**Rules for every task below** (from the requirements):

- Date each observation and record the command with its actual result.
- If a check wasn't run or can't be rerun, mark it **unverified**. Don't fill in the expected result.
- Label anything written now about earlier work as *written afterward (2026-10-21)*. Don't present it as a plan made before the work.
- Keep passwords, keys, `.env` files, database exports and private message contents out of Git. Redact email and analytics evidence.
- Link to existing files instead of copying them. Don't replace the Ex04 explanation (`docs/how-this-site-is-secured.md`) with an agent-written one.

## 1. Profile and project data (15 pts)

- [x] Pages return HTTP 503 when the database fails: `app/main.py` `render_page`, with a test in `tests/test_pages.py` — done: commit `7c4fce6`; Railway deploy blocked by Railway's 2026-10-21 outage (see `docs/railway-migration-results.md`)
- [x] Real profile stays visible on database failure instead of the invented fallback profile: `app/services/fallback_service.py`, `app/main.py` — done: commit `7c4fce6`
- [x] Database failure shows "Projects temporarily unavailable", distinct from the empty-table message: `templates/projects.html` — done: commit `7c4fce6`
- [x] Record a database-down → recovered-without-restart check, with date and result: new section in `docs/railway-migration-results.md` — done: local check 2026-10-21 in `docs/railway-migration-results.md`; Railway check still to do (below)
- [ ] Add a clearly labeled "this website, in progress" project entry: Railway Postgres `projects` table

## 2. Azure deployment (20 pts)

- [x] Record the instructor's approval and date for decommissioning the VM: `docs/railway-migration-results.md` "Azure VM decommissioned" and `README.md` — done: verbal, about 2026-10-13, recorded in both files
- [x] Mark the controlled VM restart test as unverified (never run, VM now decommissioned): `docs/superpowers/plans/2026-10-01-operate-the-vm.md` Verify results — done: operate-the-vm Verify results
- [x] Explain which parts needed configuration to survive a restart (`systemctl enable`, `Restart=always`, nginx enabled plus its restart drop-in, absolute `DATABASE_URL`), labeled written afterward: `README.md` Azure section — done: README Azure history
- [x] Record the VM's private IP, or mark it unverified: `docs/evidence/ex03.md` §1 — done: marked unverified in operate-the-vm Verify results
- [x] Mark the port 443 NSG rule as unverified (no command output recorded): `docs/how-this-site-is-secured.md` Open ports — done: marked unverified in operate-the-vm Verify results (Ex04 file left unchanged)

## 3. Domain and HTTPS (15 pts)

- [x] Final DNS record list after Zoho (web, `www` redirect, MX, SPF, DKIM, DMARC, verification TXT), each with its purpose and the date: `cf dns records list`, saved to `docs/evidence/dns-final.md` — done: `docs/evidence/dns-final.md`, 2026-10-21
- [x] Re-verify final HTTPS for `https://brandondong.me`, `http://www` and `https://www` today (status, certificate name, dates): `docs/evidence/dns-final.md` — done: `docs/evidence/dns-final.md`, 2026-10-21
- [x] Explain the Railway certificate's hostname, validity and renewal, and how to check it: `README.md` — done: `docs/evidence/dns-final.md` Certificates; still to link from README

## 4. Railway / PostgreSQL migration (25 pts)

- [x] Say that no separate Railway spec exists and that the plan quotes the request as its spec, or link the spec if it does exist: `README.md`, `docs/project-1-submission.md` — done: README and index
- [x] State what Git moves (code, lock file, `.python-version`) and what needs another method (secrets in Railway variables, data through the copy script), labeled written afterward: `docs/railway-migration-results.md` — done: railway-migration-results.md
- [x] Document that no real change was made to the source data before the copy, or show one that exists only in the live data: `docs/railway-migration-results.md` — done: railway-migration-results.md, marked not done
- [x] Compare the rendered page on source vs target, or mark it unverified: `docs/railway-migration-results.md` — done: marked not done in railway-migration-results.md
- [x] Fill in or link the empty plan Results table: `docs/superpowers/plans/2026-10-08-railway-migration.md` §Results — done: filled 2026-10-21
- [x] Data rollback procedure, including writes after cutover (the app has no write routes; manual database edits are the only writes): `README.md` Rollback section — done: README Rollback
- [x] Responsibility comparison across OS, runtime, web entry, TLS, code, config, DB software, data and DNS, Azure vs Railway: table in `README.md` "Who owns what" — done: README Who owns what

## 5. Reviewed change through Railway (5 pts)

- [x] Record the diff review and local check for `a81cd86`, or mark it unverified: `docs/railway-migration-results.md` Verification — done: local tests verified from the 10-12 transcript; human diff review unverified
- [x] Rollback section covering code and database changes: `README.md` — done: README Rollback
- [x] Confirm no credentials are in Git history: `git log -p | grep -iE 'password=|postgresql://[^u]|secret'`, result noted in `docs/project-1-submission.md` — done: clean 2026-10-21 23:45 UTC; note still to add to the index

## 6. Zoho email (15 pts)

- [x] Create the header analysis the Zoho guide asks for: `docs/evidence/zoho-header-check.md` — done: docs/evidence/zoho-header-check.md
- [x] Add the before-MX message line and what happened to it. If none was sent before the first MX record (2026-10-13 21:36:29 UTC), say so and mark it not done: `docs/evidence/ex06.md` §1 — done: recorded as not done
- [x] Record and explain the MX, SPF, DKIM and DMARC values, including the DMARC policy: `docs/evidence/ex06.md` §2 — done: dns-final.md and zoho-header-check.md (linked from ex06 via the index)
- [x] Link ex06 and the header check: `README.md`, `docs/project-1-submission.md` — done: README Limitations and index

## 7. GA4 (10 pts)

- [x] Explain why the outbound click event is useful: `docs/evidence/ex06.md` §3 — done: written by Brandon
- [x] Explain the collection path, browser → consent → gtag.js → `/g/collect` → Realtime, and what the checks prove: `docs/evidence/ex06.md` §3 — done: docs/diagrams/email-and-analytics.md

## 8. Engineering record (20 pts)

README (`README.md`):

- [x] Commit `docs/diagrams/request-path.md` and link it from the README — done: linked from README Architecture
- [x] Add the email path (sender → MX → Zoho; Zoho → recipient with SPF/DKIM/DMARC) and the analytics path (browser → Google) to the diagrams: `docs/diagrams/` — done: docs/diagrams/email-and-analytics.md
- [x] Rewrite the Claude-drafted Railway decision in your own words: `README.md` Decision — done: drafted by Claude, edited by Brandon (reliability point added)
- [x] Add the managed vs self-hosted email decision with the alternatives and reasons: `README.md` — done: written by Brandon
- [x] Failures section linking `docs/evidence/ex03.md` (app/database: empty database) and `docs/evidence/ex05.md` (DNS/TLS): `README.md` — done: README Failures I investigated
- [x] Restructure ex03's failure as symptom, checks, diagnosis, repair, repeated check: `docs/evidence/ex03.md` §3 — done: structured summary in README; ex03 itself left unchanged
- [x] Reflection: what you understand better, what you'd change: `README.md` — done: written by Brandon
- [x] Remaining limitations in one place (no fallback host, unmanaged Postgres backups, Junk filtering, unverified Azure checks): `README.md` — done: README Limitations
- [x] Service inventory: compute vs retained storage vs other billables, with renewal or expiry dates and cleanup plans (Railway web + Postgres volume, domain at Namecheap, registered 2026-10-01, expires 2027-10-01, Cloudflare, Zoho Free, GA4, Azure deleted 2026-10-16): `README.md` Costs — done: README Costs table
- [x] Re-check Railway's remaining credit and days, and record the date: `README.md` Costs — done: $0.59 used, 2026-10-22 00:18 UTC
- [x] Link the original spec and plans (`docs/superpowers/specs/`, `docs/superpowers/plans/`): `README.md` — done: README and index

Submission index (`docs/project-1-submission.md`), in the order the requirements list:

- [x] Repo URL, live HTTPS URL and final commit SHA at the top — done: index (final SHA points to Brightspace)
- [x] 1. README, the original application spec and plans
- [x] 2. Azure and Railway diagrams, including email and analytics data flow
- [x] 3. Migration plans, source/target data comparison, cutover results, rollback
- [x] 4. Azure HTTP/restart evidence (restart marked unverified) and final DNS/HTTPS verification
- [x] 5. Reviewed commit `a81cd86`, Railway deployment `74e886c2`, live-change verification
- [x] 6. Zoho sending, receiving, replying, and DNS authentication evidence (ex06, zoho-header-check)
- [x] 7. GA4 page-view and interaction evidence, with the explanation
- [x] 8. README sections or records for failures, decisions, reflection, costs and limitations

## Blocked by Railway's outage (from 2026-10-21 07:24 UTC)

- [ ] When builds resume for Trial plans, confirm Railway deploys `7c4fce6` or later: `railway deployment list`
- [ ] Rerun the database outage check on Railway and record it: `docs/railway-migration-results.md`
- [ ] Rotate `ADMIN_PASSWORD` and the Postgres password (variable and database role together), then redeploy: Railway service variables
- [x] If builds aren't back by submission, say in the index that the live site runs `ddf2f03`, not the submitted SHA: `docs/project-1-submission.md` — done: index Live deployment row
- [ ] Consider a short note to the instructor before 1:45 PM naming the commit and the incident link

## Submit

- [ ] Final commit pushed, Railway deploy healthy (`/healthz` 200 on `https://brandondong.me`)
- [x] Put the final SHA in the submission index, then push. The SHA of the commit that adds it can't appear inside itself, so name the commit before it, or state that the final SHA is the one entered in Brightspace — done: index points to the SHA entered in Brightspace
- [ ] Submit repo URL, live HTTPS URL and final commit SHA in Brightspace before 2026-10-22 1:45 PM
- [ ] Keep the site up through the midterm interview (Oct 26–28). Railway trial ends around 2026-11-07
