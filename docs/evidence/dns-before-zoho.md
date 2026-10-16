# DNS snapshot before the Zoho Mail setup: brandondong.me

**Taken:** 2026-10-13 21:11:11 UTC, with the Cloudflare CLI (`cf` 1.0.0-beta.16).

```text
$ cf dns records list -z brandondong.me --per-page 100 --order type
```

The zone has 4 records. That is fewer than the page size of 100, so this is the full list. Cloudflare manages the zone's NS records itself, so the API does not list them. TTL `1` means "Auto" (300 s).

| Type | Name | Content | Proxied | TTL | Created (UTC) | Comment |
|---|---|---|---|---|---|---|
| A | `www` | `20.80.7.163` | no | Auto | 2026-10-01 21:41 | Azure VM, left in place after the Railway cutover |
| CNAME | `@` | `gvb8rrd4.up.railway.app` | no | Auto | 2026-10-01 21:41 (modified 2026-10-12 21:48) | Railway web service (was A 20.80.7.163, Azure VM) |
| TXT | `@` | `"zoho-verification=zb84169548.zmverify.zoho.com"` | no | 600 | **2026-10-13 21:08:55** | none |
| TXT | `_railway-verify` | `"railway-verify=8340fab8…3031e"` | no | Auto | 2026-10-12 21:48 | Railway custom domain verification |

## Notes

- **There was already one Zoho record.** The `zoho-verification` TXT record was created at 21:08:55 UTC, 2 minutes 16 seconds before this snapshot. The true state before Zoho is the other three rows. To roll back to it, delete that TXT record.
- **No mail records yet.** There are no MX records, no SPF (`v=spf1`) TXT, no DKIM, and no DMARC (`_dmarc`). Today the domain cannot receive mail, and it publishes no sending policy.
- **The apex is a CNAME.** Cloudflare's CNAME flattening lets MX and TXT records sit next to the `@` CNAME. Without it, that combination would break the DNS rule that a CNAME can't share a name with other records (RFC 1034).

<details>
<summary>Raw CLI output</summary>

```json
[
  {
    "id": "543cb4bf68a5ee13e26150cc3fdf61f2",
    "name": "www.brandondong.me",
    "type": "A",
    "content": "20.80.7.163",
    "proxiable": true,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-01T21:41:13.492485Z",
    "modified_on": "2026-10-01T21:41:13.492485Z"
  },
  {
    "id": "4d330b20c8adf5497fb3c110a026f970",
    "name": "brandondong.me",
    "type": "CNAME",
    "content": "gvb8rrd4.up.railway.app",
    "proxiable": true,
    "proxied": false,
    "ttl": 1,
    "settings": {
      "flatten_cname": false
    },
    "meta": {},
    "comment": "Railway web service (was A 20.80.7.163, Azure VM)",
    "tags": [],
    "created_on": "2026-10-01T21:41:39.055945Z",
    "modified_on": "2026-10-12T21:48:41.398448Z",
    "comment_modified_on": "2026-10-12T21:48:41.398448Z"
  },
  {
    "id": "7be8a69409b196ce9110e96eab094304",
    "name": "brandondong.me",
    "type": "TXT",
    "content": "\"zoho-verification=zb84169548.zmverify.zoho.com\"",
    "proxiable": false,
    "proxied": false,
    "ttl": 600,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-13T21:08:55.030851Z",
    "modified_on": "2026-10-13T21:08:55.030851Z"
  },
  {
    "id": "af92302c96ef2455b6ad92a316db7170",
    "name": "_railway-verify.brandondong.me",
    "type": "TXT",
    "content": "\"railway-verify=8340fab8a02168b5f72f5acc3306468cb5e1efa70aac868392d18cf90ba3031e\"",
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": "Railway custom domain verification",
    "tags": [],
    "created_on": "2026-10-12T21:48:48.283182Z",
    "modified_on": "2026-10-12T21:48:48.283182Z",
    "comment_modified_on": "2026-10-12T21:48:48.283182Z"
  }
]
```

</details>
