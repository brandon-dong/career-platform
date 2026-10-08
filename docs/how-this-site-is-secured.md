# How this site is secured

> **How do I know my data to your site is encrypted?**

I know my site is encrypted for a few reasons. First, the site uses HTTPS, which encrypts traffic with TLS. Second, when I open my site on Chrome, and click on the icon to the left of the URL (the one that would say site unsecure if it wasn't), I can click on the certificate, which proves that the server really is brandondong.me, so nobody can pretend to be the site. Moreover, any packets sent between the visitor's browser and the server are encrypted, so someone on the same network can't read or change them.

## The certificate

| Field | Value |
|---|---|
| Issued by | Let's Encrypt (intermediate `YE1`) |
| Covers | `brandondong.me` and `www.brandondong.me` |
| Valid from | Oct 6, 2026 21:04:13 GMT |
| Expires | Jan 4, 2027 21:04:12 GMT |
| Connection | TLS 1.3, cipher `TLS_AES_256_GCM_SHA384` |

Let's Encrypt is a free, trusted certificate authority, and it issued the certificate after checking that I am the one who controls the domain over port 80. YE1 is Let's Encrypt's intermediate certificate that signed my certificate, and YE1 is in turn signed by a Let's Encrypt root certificate that Chrome already trusts. Both names, brandondong.me and www.brandondong.me, are listed because they are different hostnames. A certificate only covering one would trigger a warning for the other. Finally, it's only valid for 90 days (until January 4th).

### Certificate details from `openssl`

Command: `openssl s_client -connect brandondong.me:443 -servername brandondong.me | openssl x509 -noout -subject -issuer -dates`

```text
subject=CN=brandondong.me
issuer=C=US, O=Let's Encrypt, CN=YE1
notBefore=Oct  6 21:04:13 2026 GMT
notAfter=Jan  4 21:04:12 2027 GMT
```

## Renewal

Let's Encrypt certificates last 90 days on purpose, as over time, the risk of a key being exposed/leaked gets higher, so that lifespan balances convenience with safety. Installing Certbot set up a systemd timer that runs `certbot renew` about twice a day, and it only renews when the certificate has 30 days or fewer left. After renewing, it reloads Nginx, so I don't have to do anything. This further reinforces the convenience and safety of Let's Encrypt.

When I installed Certbot on the VM on Oct 6, 2026 (`sudo apt-get install -y certbot python3-certbot-nginx`), the install enabled the renewal timer:

```text
Setting up certbot (2.9.0-1) ...
Created symlink /etc/systemd/system/timers.target.wants/certbot.timer → /usr/lib/systemd/system/certbot.timer.
```

Getting the certificate (`sudo certbot --nginx -d brandondong.me -d www.brandondong.me`) ended with:

```text
This certificate expires on 2027-01-04.
These files will be updated when the certificate renews.
Certbot has set up a scheduled task to automatically renew this certificate in the background.

Deploying certificate
Successfully deployed certificate for brandondong.me to /etc/nginx/sites-enabled/career-platform
Successfully deployed certificate for www.brandondong.me to /etc/nginx/sites-enabled/career-platform
Congratulations! You have successfully enabled HTTPS on https://brandondong.me and https://www.brandondong.me
```

I ran both checks on Oct 7, 2026 (Pacific time) through the Azure portal's **Run command** (VM → Operations → Run command → RunShellScript), because SSH only allows my usual IP and I was on a different network. Run command executes as root, so the commands didn't need `sudo`.

Renewal test (`certbot renew --dry-run`):

```text
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Processing /etc/letsencrypt/renewal/brandondong.me.conf
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Account registered.
Simulating renewal of an existing certificate for brandondong.me and www.brandondong.me

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Congratulations, all simulated renewals succeeded: 
  /etc/letsencrypt/live/brandondong.me/fullchain.pem (success)
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
```

Renewal timer (`systemctl list-timers | grep certbot`):

```text
Thu 2026-10-08 05:22:58 UTC 3h 49min Tue 2026-10-06 21:59:51 UTC            - certbot.timer                  certbot.service
```

The timer's next run was Thu Oct 8 at 05:22:58 UTC (3h 49min away when I checked), and its last run was Tue Oct 6 at 21:59:51 UTC. The dry run proves renewal works, and the timer proves that it will happen automatically.

## Open ports

| Port | Open to | Why |
|---|---|---|
| 443 (HTTPS) | Anyone | The only port that actually serves the site, over an encrypted connection |
| 80 (HTTP) | Anyone | Sends a 301 redirect to HTTPS for both names, so no page content is served over plain HTTP. It also has to stay open for Let's Encrypt's domain check at each renewal |
| 22 (SSH) | Only my laptop's public IP | SSH for me to manage the server. The Azure NSG rule AllowSSHFromLaptop restricts it to my laptop's IP, and login uses my SSH key, not a password. |
| 8000 (app) | Not open to the internet | Uvicorn app, bound to 127.0.0.1, so only programs on the VM (Nginx) can reach it. |

Only my laptop's current public IP gets through the NSG rule. Everyone else's connection just hangs. When my IP changes (coffee shop, home), I have to update the rule first. Even from the allowed IP, someone would still need my private SSH key.

## Where encryption starts and ends

```text
Browser ──HTTPS (encrypted)──► Nginx on the VM :443 ──HTTP (plain, inside the VM)──► uvicorn app 127.0.0.1:8000
```

Encryption starts in the visitor's browser and ends at Nginx on the VM. Nginx holds the private key and decrypts each request. Nginx forwards the request as plain HTTP, which is acceptable because it never leaves the VM, and port 8000 isn't reachable from the internet.

## Check it yourself in Chrome

1. In Chrome, type `http://brandondong.me` into the address bar. The site redirects to `https://brandondong.me`.
2. Click the icon to the left of the URL.
3. Click **Connection is secure**.
4. Click **Certificate is valid**.

This is what Chrome showed me. Chrome displays the dates in Pacific time, so 2:04:13 PM PDT and 1:04:12 PM PST are the same moments as 21:04:13 and 21:04:12 GMT in the table above.

```text
Issued To
Common Name (CN)          brandondong.me
Organization (O)          <Not Part Of Certificate>
Organizational Unit (OU)  <Not Part Of Certificate>

Issued By
Common Name (CN)          YE1
Organization (O)          Let's Encrypt
Organizational Unit (OU)  <Not Part Of Certificate>

Validity Period
Issued On                 Tuesday, October 6, 2026 at 2:04:13 PM
Expires On                Monday, January 4, 2027 at 1:04:12 PM

SHA-256 Fingerprints
Certificate               c8d1e7be95d54c8a87f962ecad755d9ed7710dfe6157c8d0dd74788648404dd7
Public Key                e9fd646f301421ef193b2e3d9f2dec723606733fa98aaa47bcbf4e60cdb2b179
```
