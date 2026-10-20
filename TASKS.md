# Project 1 gaps

Audit against the Project 1 requirements, 2026-10-20. Each line names the file or check that closes it.

## 1. Profile and project data

- [ ] Pages return HTTP 503 when the database fails: `app/main.py` `render_page`, with a test in `tests/test_pages.py`
- [ ] Real profile stays visible on database failure instead of the invented fallback profile: `app/services/fallback_service.py`, `app/main.py`
- [ ] Database failure shows "Projects temporarily unavailable", distinct from the empty-table message: `templates/projects.html`
- [ ] Record a database-down → recovered-without-restart check with date and result: new section in `docs/railway-migration-results.md`
- [ ] Add a clearly labeled "this website, in progress" project entry: Railway Postgres `projects` table

## 2. Azure deployment

- [ ] Mark the controlled VM restart test as unverified (never run, VM now decommissioned): `docs/superpowers/plans/2026-10-01-operate-the-vm.md` Verify results
- [ ] Record the VM's private IP, or mark it unverified: `docs/evidence/ex03.md` §1
- [ ] Mark the port 443 NSG rule as unverified (no command output recorded): `docs/how-this-site-is-secured.md` Open ports
- [ ] Record the instructor's approval and date for decommissioning the VM: `docs/railway-migration-results.md` "Azure VM decommissioned" and `README.md`

## 3. Domain and HTTPS

- [ ] Final DNS record list after Zoho, with each record's purpose: `cf dns records list`, saved to `docs/evidence/`
- [ ] Explain Railway certificate renewal and how to check it: `README.md`

## 4. Railway / PostgreSQL migration

- [ ] Document that no real source-data change was made before the copy, or show one that exists only in the live data: `docs/railway-migration-results.md`
- [ ] State what Git moves and what needs another method (secrets, data): `docs/superpowers/plans/2026-10-08-railway-migration.md`, or a retrospective note in `docs/railway-migration-results.md`
- [ ] Fill in or link the empty plan Results table: `docs/superpowers/plans/2026-10-08-railway-migration.md` §Results
- [ ] Compare the rendered page on source vs target, or mark it unverified: `docs/railway-migration-results.md`
- [ ] Data rollback procedure, including writes after cutover: `README.md` Rollback section
- [ ] Responsibility comparison across OS, runtime, web entry, TLS, code, config, DB software, data and DNS: table in `README.md` "Who owns what"

## 5. Reviewed change through Railway

- [ ] Record the diff review and local check for `a81cd86`: `docs/railway-migration-results.md` Verification
- [ ] Rollback section covering code and database changes: `README.md`

## 6. Zoho email

- [ ] Create the header analysis: `docs/evidence/zoho-header-check.md`
- [ ] Add the before-MX message line and what happened to it: `docs/evidence/ex06.md` §1
- [ ] Record and explain the MX, SPF, DKIM and DMARC values, including DMARC policy: `docs/evidence/ex06.md` §2
- [ ] Link ex06 and the header check: `README.md`, `docs/project-1-submission.md`

## 7. GA4

- [ ] Explain why the outbound click event is useful: `docs/evidence/ex06.md` §3
- [ ] Explain the collection path, browser → gtag.js → collect → Realtime: `docs/evidence/ex06.md` §3

## 8. Engineering record

- [ ] Azure and Railway diagrams with ports, protocols, and the email and analytics paths: `README.md`
- [ ] Rewrite the Claude-drafted Railway decision in your own words: `README.md` Decision
- [ ] Add the managed vs self-hosted email decision: `README.md`
- [ ] Failures section linking `docs/evidence/ex03.md` and `docs/evidence/ex05.md`: `README.md`
- [ ] Restructure ex03's failure as symptom, checks, diagnosis, repair, repeated check: `docs/evidence/ex03.md` §3
- [ ] Reflection section: `README.md`
- [ ] Remaining limitations, costs and cleanup plan in one place: `README.md`
- [ ] Link the original spec and plans: `README.md`, `docs/project-1-submission.md`
- [ ] Repo URL, live HTTPS URL and final commit SHA: `docs/project-1-submission.md`
- [ ] Links for diagrams, reviewed commit and deploy, failures, decisions, reflection and costs: `docs/project-1-submission.md`
