# Zoho header check: brandondong.me

Header analysis for mail sent from my Zoho address, following the course guide *Domain email with Zoho*. The message body is left out. Results sheet: [ex06.md](ex06.md).

*Assembled 2026-10-21 from the header saved in ex06 on 2026-10-13. No prediction was written down before I opened the header, so this file doesn't include one.*

## 1. Public DNS matches what Zoho expects

Zoho's admin console showed the domain and DKIM as verified on 2026-10-13. Checked again from outside Zoho, against Google's public resolver (8.8.8.8), on 2026-10-22 00:19 UTC:

```text
$ curl -s -H 'accept: application/dns-json' 'https://dns.google/resolve?name=<name>&type=<type>'
MX  brandondong.me                   10 mx.zoho.com.  20 mx2.zoho.com.  50 mx3.zoho.com.
TXT brandondong.me                   v=spf1 include:zohomail.com ~all
TXT zmail._domainkey.brandondong.me  v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDaDUp9…
TXT _dmarc.brandondong.me            v=DMARC1; p=none; rua=mailto:bdong@brandondong.me
```

All four match the records in Cloudflare ([dns-final.md](dns-final.md)) and the values Zoho gave for the account. `p=none` means DMARC only monitors for now. Tools such as MXToolbox flag "DMARC Policy Not Enabled" for it, which is expected at this stage.

## 2. What the receiving server decided

**Message:** "Test 03: Outbound with DKIM", sent from my `brandondong.me` address in Zoho webmail to my LMU (Microsoft 365) mailbox on 2026-10-13 at 22:08:54 UTC. Header read in Outlook on the web: three dots → View → View message details.

```text
Authentication-Results: mx.microsoft.com 1; spf=pass (sender IP is
 165.173.182.52) smtp.mailfrom=brandondong.me; dkim=pass (signature was
 verified) header.d=brandondong.me;dmarc=pass action=none
 header.from=brandondong.me;compauth=pass reason=100
Received-SPF: Pass (protection.outlook.com: domain of brandondong.me
 designates 165.173.182.52 as permitted sender)
 receiver=protection.outlook.com; client-ip=165.173.182.52;
 helo=sender5-of-o52.zoho.com; pr=C
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/relaxed; s=zmail; d=brandondong.me; ...
```

Each check names a different part of the message:

| Check | Result | What it checked | Domain it names | Which DNS record it used |
|---|---|---|---|---|
| SPF | pass | Whether the sending server's IP (`165.173.182.52`, a Zoho server announcing itself as `sender5-of-o52.zoho.com`) may send for the **envelope sender** | `smtp.mailfrom=brandondong.me` | `TXT @`: `include:zohomail.com` |
| DKIM | pass | Whether the signature on the message verifies with the public key for selector `s=zmail` | `header.d=brandondong.me` | `TXT zmail._domainkey` |
| DMARC | pass, `action=none` | Whether SPF or DKIM passed **for the same domain as the visible From address** | `header.from=brandondong.me` | `TXT _dmarc`, `p=none` |

**Alignment:** SPF and DKIM both pass for `brandondong.me`, the same domain as the From header, so DMARC passes on both. DKIM is signed with my own domain's key (`d=brandondong.me`), not Zoho's. `compauth=pass` is Microsoft's overall verdict after combining the three checks.

## 3. What this doesn't explain

This message still went to Junk, even though all three checks passed (see [ex06.md](ex06.md)). Authentication shows the mail really came from my domain. Microsoft's junk filtering also weighs other things, such as the reputation of a domain created on 2026-10-01 with almost no sending history. The headers don't record why it was moved to Junk, so the cause is **unverified**.

## 4. If a reply landed in spam

Look at `Authentication-Results` first. If all three pass, as here, the DNS records are working and the issue is reputation or the recipient's own filtering. If SPF fails, check the `TXT @` record. If DKIM fails, check the `zmail._domainkey` record. If DMARC fails while SPF or DKIM passes, the domain that passed doesn't match the From address.
