# Final DNS and HTTPS check: brandondong.me

**Taken:** 2026-10-21 23:45 UTC, from my laptop on my home network. Records listed with the Cloudflare CLI; HTTPS checked with `curl` and `openssl`. Cloudflare is the authoritative DNS provider and manages the NS records itself, so the API doesn't list them.

Earlier states: [dns-before-zoho.md](dns-before-zoho.md) (2026-10-13, before mail) and the cutover in [ex05.md](ex05.md) (2026-10-12).

## Records

```text
$ cf dns records list -z brandondong.me --per-page 100 --order type
```

10 records. TTL `Auto` is 300 s.

| Type | Name | Content | Proxied | Created (UTC) | Purpose |
|---|---|---|---|---|---|
| CNAME | `@` | `gvb8rrd4.up.railway.app` | no (DNS only) | modified 2026-10-12 21:48 | The site. Cloudflare flattens it at the root, so lookups return Railway's edge address `69.46.46.57`. DNS only, so HTTPS goes straight to Railway |
| A | `www` | `192.0.2.1` | **yes** | modified 2026-10-16 22:11 | Placeholder that exists only so Cloudflare's edge can answer the "Redirect from WWW to root" rule (301). `192.0.2.1` is a reserved address that never receives traffic |
| TXT | `_railway-verify` | `railway-verify=8340fab8…3031e` | no | 2026-10-12 21:48 | Proves to Railway that I control the domain, which gates Railway's certificate and routing ([ex05.md](ex05.md)) |
| MX | `@` | `mx.zoho.com`, priority 10 | no | 2026-10-13 21:36:29 | Incoming mail goes to Zoho. Lowest priority number is tried first |
| MX | `@` | `mx2.zoho.com`, priority 20 | no | 2026-10-13 21:36:47 | Zoho backup |
| MX | `@` | `mx3.zoho.com`, priority 50 | no | 2026-10-13 21:37:04 | Zoho second backup |
| TXT | `@` | `v=spf1 include:zohomail.com ~all` | no | 2026-10-13 21:42 | SPF: Zoho's servers may send for the domain; anything else is a soft fail |
| TXT | `zmail._domainkey` | `v=DKIM1; k=rsa; p=MIGfMA0G…IDAQAB` | no | not shown in the output | DKIM public key for selector `zmail`. Receivers use it to check Zoho's signature on my outgoing mail |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:bdong@brandondong.me` | no | 2026-10-13 22:01 | DMARC: asks receivers to check that SPF or DKIM aligns with the From domain. `p=none` means monitor only, no quarantine or reject; aggregate reports go to my address |
| TXT | `@` | `zoho-verification=zb84169548.zmverify.zoho.com` | no | 2026-10-13 21:08 | Proved domain ownership to Zoho during setup |

The first MX record was created at **2026-10-13 21:36:29 UTC**. Any message sent before that moment had no mail record to follow.

## HTTPS verification

```text
$ curl -s -o /dev/null -L -w '%{http_code} final=%{url_effective} redirects=%{num_redirects} ssl_verify=%{ssl_verify_result}\n' <url>
https://brandondong.me/        200 final=https://brandondong.me/ redirects=0 ssl_verify=0
http://brandondong.me/         200 final=https://brandondong.me/ redirects=1 ssl_verify=0
http://www.brandondong.me/     200 final=https://brandondong.me/ redirects=1 ssl_verify=0
https://www.brandondong.me/    000 final=https://www.brandondong.me/ redirects=0 ssl_verify=0   (first try, see below)

$ curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' http://www.brandondong.me/
301 -> https://brandondong.me/
```

**`https://www` failed once, then passed.** The first request returned `000` (no response). A verbose rerun at 23:45:26 returned `301 Location: https://brandondong.me/` from Cloudflare. Ten repeats at 23:45:38 all returned `200` after one redirect, and so did five IPv4-only repeats. I didn't find the cause of the single failure. The verbose run shows Cloudflare asking Windows' TLS library (schannel) to renegotiate, which is one possibility, but I haven't confirmed it.

**No IPv6 at the root.** Forcing IPv6 (`curl -6`) gets the `301` from Cloudflare, then stops, because `brandondong.me` has no AAAA record (`nslookup -type=AAAA brandondong.me 1.1.1.1` returns no address, and neither does Railway's target). A visitor with IPv6 only couldn't reach the site. Normal dual-stack visitors fall back to IPv4.

## Certificates

```text
$ openssl s_client -connect <host>:443 -servername <host> -verify_hostname <host> | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

| Host | Served by | Subject / SAN | Issuer | Valid | Verify |
|---|---|---|---|---|---|
| `brandondong.me` | Railway edge (`69.46.46.57`) | `CN=brandondong.me` / `brandondong.me` | Let's Encrypt YE2 | 2026-10-12 23:33 → 2027-01-10 23:33 UTC | `0 (ok)` |
| `www.brandondong.me` | Cloudflare edge (proxied) | `CN=brandondong.me` / `*.brandondong.me`, `brandondong.me` | Let's Encrypt YE1 | 2026-10-01 21:01 → 2026-12-30 21:01 UTC | `0 (ok)` |

**Renewal.** Both certificates last 90 days and both renewals are automatic and handled by the provider, so I don't run anything myself:

- **Root:** Railway issues and renews the certificate for the custom domain. Renewal depends on `@` still pointing at Railway and `_railway-verify` staying in place. Check: run the `openssl` command above after early December 2026 and confirm `notBefore` moved forward.
- **`www`:** Cloudflare's Universal SSL covers the proxied name and renews at the edge.

On Azure, renewal was mine: Certbot's systemd timer ([how-this-site-is-secured.md](../how-this-site-is-secured.md)).
