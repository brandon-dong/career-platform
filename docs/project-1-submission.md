# Project 1 submission: links

| | |
|---|---|
| Repository | https://github.com/brandon-dong/career-platform |
| Live site | https://brandondong.me |
| Final commit | The SHA entered in Brightspace. A commit can't contain its own SHA, so it isn't repeated here |
| Live deployment | Railway deployment of `ddf2f03`. Railway paused all builds on 2026-10-21, so later commits, including the database failure fix `7c4fce6`, aren't deployed yet ([details](railway-migration-results.md#database-failure-handling-commit-7c4fce6-2026-10-21)) |

Items marked **unverified** or **not done** in the linked files were checked and are stated as they are.

## 1. README, original spec and plans

- [README](../README.md)
- Spec: [career platform design](superpowers/specs/2026-09-15-career-platform-design.md), [site layout design](superpowers/specs/2026-09-29-site-layout-design.md)
- Plans: [career platform](superpowers/plans/2026-09-15-career-platform.md), [Azure VM migration](superpowers/plans/2026-09-24-azure-vm-migration.md), [site layout](superpowers/plans/2026-09-29-site-layout.md), [operate the VM](superpowers/plans/2026-10-01-operate-the-vm.md), [Railway migration](superpowers/plans/2026-10-08-railway-migration.md). There's no separate Railway spec: the plan quotes the request as its spec

## 2. Diagrams

- [Web request on Railway and Azure](diagrams/request-path.md): hardware, DNS, ports, protocols, where TLS ends
- [Email and analytics](diagrams/email-and-analytics.md): MX delivery, SPF/DKIM/DMARC checks, GA4 events

## 3. Migration, data comparison, cutover, rollback

- [Railway migration plan](superpowers/plans/2026-10-08-railway-migration.md): dependency inventory and compatibility findings, written 2026-10-08 before the cutover (commit `25133e4`)
- [Migration results](railway-migration-results.md): table-by-table comparison, what Git moved versus other methods, verification, DNS cutover, VM decommission
- [README: Rollback](../README.md#rollback) and [README: Who owns what](../README.md#who-owns-what)

## 4. Azure HTTP and restart evidence, final DNS and HTTPS

- [Operate the VM: Verify results](superpowers/plans/2026-10-01-operate-the-vm.md#verify-results): Nginx, systemd, 2 workers, NSG, port 8000 closed (2026-10-01). Controlled restart: **unverified**
- [Azure VM migration: Verify results](superpowers/plans/2026-09-24-azure-vm-migration.md#verify-results) and [Exercise 03](evidence/ex03.md): VM, SSH rule, database copy
- [How the site was secured on the VM](how-this-site-is-secured.md): my Exercise 04 HTTPS explanation, certificate, renewal dry run, open ports
- [Final DNS and HTTPS check](evidence/dns-final.md): all records with their purpose, `http`/`https` and `www` redirects, both certificates (2026-10-21)
- [Exercise 05](evidence/ex05.md): the Railway cutover's DNS and TLS investigation

## 5. Reviewed change, Railway deployment, live verification

- Commit [`a81cd86`](https://github.com/brandon-dong/career-platform/commit/a81cd86) ("Hosted on Railway" footer) → Railway deployment `74e886c2`, footer live about 50 s after the push ([results, Verification](railway-migration-results.md#verification))
- [What the 2026-10-12 transcript shows about its review](railway-migration-results.md#review-of-the-update-test-a81cd86): local tests verified, human diff review **unverified**
- [README: Rollback](../README.md#rollback)

## 6. Zoho email

- [Exercise 06 results sheet](evidence/ex06.md): received, replied, new outgoing message, Junk-folder issue; before-MX message **not done**
- [Zoho header check](evidence/zoho-header-check.md): SPF, DKIM and DMARC verdicts and alignment
- [DNS records with their purpose](evidence/dns-final.md#records)

## 7. GA4

- [Exercise 06 §3](evidence/ex06.md#3-google-analytics): `page_view` and outbound `click` in Realtime, with screenshots, and the consent bug fixed in `48f342a`
- [How events reach GA4](diagrams/email-and-analytics.md#analytics)

## 8. Failures, decisions, reflection, costs, limitations

- [Failures I investigated](../README.md#failures-i-investigated): empty database ([ex03](evidence/ex03.md)) and wrong certificate after cutover ([ex05](evidence/ex05.md))
- [Decisions](../README.md#decisions)
- [Reflection](../README.md#reflection)
- [Costs, expiration dates and cleanup](../README.md#costs-expiration-dates-and-cleanup)
- [Limitations](../README.md#limitations)
- Secrets: a scan of the full Git history on 2026-10-21 found no real credentials and no committed `.env`, database or key files
