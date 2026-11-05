# DNS before the AWS migration: brandondong.me

**Taken:** 2026-11-04, with the Cloudflare CLI (`cf` 1.0.0-beta.16), before any DNS change for AWS. This is the rollback reference for the cutover.

```text
$ cf dns records list -z brandondong.me --per-page 100 --order type

A      www.brandondong.me                 proxied  ttl=auto 192.0.2.1
CNAME  brandondong.me                     dns-only ttl=auto gvb8rrd4.up.railway.app
MX     brandondong.me                     dns-only ttl=auto mx3.zoho.com
MX     brandondong.me                     dns-only ttl=auto mx2.zoho.com
MX     brandondong.me                     dns-only ttl=auto mx.zoho.com
TXT    brandondong.me                     dns-only ttl=auto "v=spf1 include:zohomail.com ~all"
TXT    brandondong.me                     dns-only ttl=600 "zoho-verification=zb84169548.zmverify.zoho.com"
TXT    _dmarc.brandondong.me              dns-only ttl=auto "v=DMARC1; p=none; rua=mailto:bdong@brandondong.me"
TXT    _railway-verify.brandondong.me     dns-only ttl=auto "railway-verify=8340fab8a02168b5f72f5acc3306468cb5e1efa70aac868392d18cf90ba3031e"
TXT    zmail._domainkey.brandondong.me    dns-only ttl=auto "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDaDUp9fx+bXXCqrBX+qsvFNX9gN/sYNkuiEhEVvUl7/s6ItYc42D3JgglmmGC11EyijGaxOUjCQjSxkR3m9ZY957uLoiYx4Vf3NU7ZZWaIdVz03FaL4/MOv98vwbMXag+5reP0dkv+gp22szupNwwhHOFOjVmjZcLITrhFvPydQQIDAQAB"
```

**Rollback while the Railway trial lasts:** replace the root record with `CNAME gvb8rrd4.up.railway.app`, DNS only.
