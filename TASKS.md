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
- [ ] Mark the controlled VM restart test as unverified (never run, VM now decommissioned): `docs/superpowers/plans/2026-10-01-operate-the-vm.md` Verify results
- [ ] Explain which parts needed configuration to survive a restart (`systemctl enable`, `Restart=always`, nginx enabled plus its restart drop-in, absolute `DATABASE_URL`), labeled written afterward: `README.md` Azure section
- [ ] Record the VM's private IP, or mark it unverified: `docs/evidence/ex03.md` §1
- [ ] Mark the port 443 NSG rule as unverified (no command output recorded): `docs/how-this-site-is-secured.md` Open ports

## 3. Domain and HTTPS (15 pts)

- [x] Final DNS record list after Zoho (web, `www` redirect, MX, SPF, DKIM, DMARC, verification TXT), each with its purpose and the date: `cf dns records list`, saved to `docs/evidence/dns-final.md` — done: `docs/evidence/dns-final.md`, 2026-10-21
- [x] Re-verify final HTTPS for `https://brandondong.me`, `http://www` and `https://www` today (status, certificate name, dates): `docs/evidence/dns-final.md` — done: `docs/evidence/dns-final.md`, 2026-10-21
- [x] Explain the Railway certificate's hostname, validity and renewal, and how to check it: `README.md` — done: `docs/evidence/dns-final.md` Certificates; still to link from README

## 4. Railway / PostgreSQL migration (25 pts)

- [ ] Say that no separate Railway spec exists and that the plan quotes the request as its spec, or link the spec if it does exist: `README.md`, `docs/project-1-submission.md`
- [ ] State what Git moves (code, lock file, `.python-version`) and what needs another method (secrets in Railway variables, data through the copy script), labeled written afterward: `docs/railway-migration-results.md`
- [ ] Document that no real change was made to the source data before the copy, or show one that exists only in the live data: `docs/railway-migration-results.md`
- [ ] Compare the rendered page on source vs target, or mark it unverified: `docs/railway-migration-results.md`
- [ ] Fill in or link the empty plan Results table: `docs/superpowers/plans/2026-10-08-railway-migration.md` §Results
- [ ] Data rollback procedure, including writes after cutover (the app has no write routes; manual database edits are the only writes): `README.md` Rollback section
- [ ] Responsibility comparison across OS, runtime, web entry, TLS, code, config, DB software, data and DNS, Azure vs Railway: table in `README.md` "Who owns what"

## 5. Reviewed change through Railway (5 pts)

- [ ] Record the diff review and local check for `a81cd86`, or mark it unverified: `docs/railway-migration-results.md` Verification
- [ ] Rollback section covering code and database changes: `README.md`
- [x] Confirm no credentials are in Git history: `git log -p | grep -iE 'password=|postgresql://[^u]|secret'`, result noted in `docs/project-1-submission.md` — done: clean 2026-10-21 23:45 UTC; note still to add to the index

## 6. Zoho email (15 pts)

- [ ] Create the header analysis the Zoho guide asks for: `docs/evidence/zoho-header-check.md`
- [ ] Add the before-MX message line and what happened to it. If none was sent before the first MX record (2026-10-13 21:36:29 UTC), say so and mark it not done: `docs/evidence/ex06.md` §1
- [ ] Record and explain the MX, SPF, DKIM and DMARC values, including the DMARC policy: `docs/evidence/ex06.md` §2
- [ ] Link ex06 and the header check: `README.md`, `docs/project-1-submission.md`

## 7. GA4 (10 pts)

- [ ] Explain why the outbound click event is useful: `docs/evidence/ex06.md` §3
- [ ] Explain the collection path, browser → consent → gtag.js → `/g/collect` → Realtime, and what the checks prove: `docs/evidence/ex06.md` §3

## 8. Engineering record (20 pts)

README (`README.md`):

- [ ] Commit `docs/diagrams/request-path.md` and link it from the README
- [ ] Add the email path (sender → MX → Zoho; Zoho → recipient with SPF/DKIM/DMARC) and the analytics path (browser → Google) to the diagrams: `docs/diagrams/`
- [ ] Rewrite the Claude-drafted Railway decision in your own words: `README.md` Decision
- [ ] Add the managed vs self-hosted email decision with the alternatives and reasons: `README.md`
- [ ] Failures section linking `docs/evidence/ex03.md` (app/database: empty database) and `docs/evidence/ex05.md` (DNS/TLS): `README.md`
- [ ] Restructure ex03's failure as symptom, checks, diagnosis, repair, repeated check: `docs/evidence/ex03.md` §3
- [ ] Reflection: what you understand better, what you'd change: `README.md`
- [ ] Remaining limitations in one place (no fallback host, unmanaged Postgres backups, Junk filtering, unverified Azure checks): `README.md`
- [ ] Service inventory: compute vs retained storage vs other billables, with renewal or expiry dates and cleanup plans (Railway web + Postgres volume, domain at Namecheap, registered 2026-10-01, expires 2027-10-01, Cloudflare, Zoho Free, GA4, Azure deleted 2026-10-16): `README.md` Costs
- [ ] Re-check Railway's remaining credit and days, and record the date: `README.md` Costs
- [ ] Link the original spec and plans (`docs/superpowers/specs/`, `docs/superpowers/plans/`): `README.md`

Submission index (`docs/project-1-submission.md`), in the order the requirements list:

- [ ] Repo URL, live HTTPS URL and final commit SHA at the top
- [ ] 1. README, the original application spec and plans
- [ ] 2. Azure and Railway diagrams, including email and analytics data flow
- [ ] 3. Migration plans, source/target data comparison, cutover results, rollback
- [ ] 4. Azure HTTP/restart evidence (restart marked unverified) and final DNS/HTTPS verification
- [ ] 5. Reviewed commit `a81cd86`, Railway deployment `74e886c2`, live-change verification
- [ ] 6. Zoho sending, receiving, replying, and DNS authentication evidence (ex06, zoho-header-check)
- [ ] 7. GA4 page-view and interaction evidence, with the explanation
- [ ] 8. README sections or records for failures, decisions, reflection, costs and limitations

## Blocked by Railway's outage (from 2026-10-21 07:24 UTC)

- [ ] When builds resume for Trial plans, confirm Railway deploys `7c4fce6` or later: `railway deployment list`
- [ ] Rerun the database outage check on Railway and record it: `docs/railway-migration-results.md`
- [ ] Rotate `ADMIN_PASSWORD` and the Postgres password (variable and database role together), then redeploy: Railway service variables
- [ ] If builds aren't back by submission, say in the index that the live site runs `ddf2f03`, not the submitted SHA: `docs/project-1-submission.md`
- [ ] Consider a short note to the instructor before 1:45 PM naming the commit and the incident link

## Submit

- [ ] Final commit pushed, Railway deploy healthy (`/healthz` 200 on `https://brandondong.me`)
- [ ] Put the final SHA in the submission index, then push. The SHA of the commit that adds it can't appear inside itself, so name the commit before it, or state that the final SHA is the one entered in Brightspace
- [ ] Submit repo URL, live HTTPS URL and final commit SHA in Brightspace before 2026-10-22 1:45 PM
- [ ] Keep the site up through the midterm interview (Oct 26–28). Railway trial ends around 2026-11-07
