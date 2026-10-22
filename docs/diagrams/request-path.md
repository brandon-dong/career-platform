# What happens when you enter brandondong.me

Railway is the current host. Azure is the earlier host, described after it. Values marked **unknown** aren't recorded in this repository. Each one names the check that would fill it in.

**Assumptions:** a new HTTPS connection over TCP, no cached DNS answer, and `brandondong.me` typed with no scheme.

## 1. Physical path and addresses

The DNS lookup and the web request both cross this hardware. They are separate exchanges.

```mermaid
flowchart LR
    subgraph home["Home network (private addresses)"]
        laptop["Laptop<br/>Wi-Fi NIC<br/>private IP: unknown<br/>(ipconfig /all)"]
        box["Spectrum home box<br/>access point + switch + router + NAT + firewall<br/>gateway: unknown private IP<br/>modem built in? unknown"]
    end
    isp["Spectrum ISP<br/>my public IP: unknown<br/>(the client address Railway's logs see)"]
    net["Internet routers<br/>(provider-managed, unknown)"]
    subgraph rw["Railway (provider-managed)"]
        edge["Railway edge<br/>69.46.46.57 :80 / :443<br/>public"]
        app["Web service container<br/>uvicorn app.main:app<br/>0.0.0.0:$PORT, private"]
        pg[("PostgreSQL service<br/>postgres.railway.internal<br/>private network")]
    end
    resolver["Recursive DNS resolver<br/>handed out by DHCP: unknown<br/>(ipconfig /all, 'DNS Servers')"]
    cf["Cloudflare authoritative DNS<br/>holds brandondong.me records<br/>@ is DNS only (grey cloud)"]

    laptop -- "Wi-Fi" --- box
    box -- "NAT: private → public" --- isp
    isp --- net
    net --- edge
    edge --- app
    app --- pg
    net -.- resolver
    resolver -.- cf
```

DHCP on the home box gives the laptop four settings: its private IP, the subnet mask, the default gateway, and the DNS server. The box rewrites the laptop's private source address to its public one (NAT) and remembers the flow, so it can map Railway's reply back to the laptop. Its firewall is stateful: it lets the reply in because it saw the request go out.

## 2. Request sequence on Railway

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser (laptop)
    participant R as Recursive resolver
    participant N as Root, then .me servers
    participant C as Cloudflare authoritative
    participant E as Railway edge 69.46.46.57
    participant A as App (uvicorn, $PORT)
    participant P as PostgreSQL (private)

    Note over B: Typed brandondong.me. Browser supplies http:// and extracts the hostname
    rect rgba(128,128,128,0.12)
    Note over B,C: DNS lookup: a separate exchange over UDP/53. The web request never passes through these servers
    B->>R: A record for brandondong.me?
    R->>N: Who serves .me, then brandondong.me?
    N-->>R: Referral to Cloudflare's name servers
    R->>C: A record for brandondong.me?
    C-->>R: 69.46.46.57 (CNAME to gvb8rrd4.up.railway.app, flattened at the root)
    R-->>B: 69.46.46.57
    end

    B->>E: TCP to :80, GET http://brandondong.me/
    E-->>B: 301 Location: https://brandondong.me/

    B->>E: New TCP connection to :443
    E-->>B: TLS certificate CN=brandondong.me, Let's Encrypt YE2
    Note over B: Browser checks hostname, dates (to 2027-01-10) and chain, then the two sides agree on keys
    Note over E: TLS ends here
    B->>E: GET / (encrypted)
    E->>A: GET / as plain HTTP, X-Forwarded-Proto: https
    A->>P: SELECT profile, experiences (SQL over the private network)
    P-->>A: Rows
    A-->>E: 200 HTML
    E-->>B: 200 HTML (encrypted)

    B->>E: GET /static/css/styles.css (separate HTTP request)
    E->>A: Forwarded
    A-->>B: 200 CSS, via the edge
    Note over B: GA4 loads only after the visitor clicks Accept. That's a separate DNS lookup and HTTPS connection to Google, not to Railway
```

### Client and server on each connection

| Connection | Client | Server | Protocol and port | Public or private |
|---|---|---|---|---|
| DNS query | Laptop | Recursive resolver | UDP 53 | Crosses the internet unless the resolver is the home box |
| Recursive lookups | Resolver | Root, `.me`, Cloudflare name servers | UDP 53 | Public |
| Redirect | Browser | Railway edge | TCP 80, HTTP | Public |
| Web request | Browser | Railway edge | TCP 443, HTTPS (TLS) | Public |
| Edge to app | Railway edge | uvicorn | HTTP on `$PORT` | Private, inside Railway |
| Database | App (SQLAlchemy) | PostgreSQL | TCP, port from `DATABASE_URL` | Private, `postgres.railway.internal` |

**Why the app trusts `X-Forwarded-Proto`:** TLS ends at the edge, so the app receives plain HTTP. Without that header it builds `http://` stylesheet links, which browsers block on an HTTPS page (`app/main.py`).

**Why UDP for DNS and TCP for the site:** a DNS question and answer each fit in one small packet, and the client can just ask again if one is lost. A web page is a long, ordered byte stream that needs delivery guarantees, and TLS needs TCP underneath it.

**With a cached answer:** if the browser, the OS, or the resolver still holds `69.46.46.57` within its TTL, steps 1–6 are skipped or shortened. Everything from the TCP connection onward stays the same.

## 3. What changes on Azure (Sept 29 – Oct 16, 2026; decommissioned)

```mermaid
flowchart LR
    B["Browser"] -- "DNS: A @ → 20.80.7.163 (DNS only)" --> D[("Cloudflare")]
    B -- "TCP 80 / 443" --> NSG
    subgraph az["Azure, vm-career-platform (Ubuntu 24.04)"]
        NSG["Network security group<br/>22 from laptop IP /32 only<br/>80 from any<br/>443 from any (no rule output recorded)"]
        NG["Nginx :80 → 301 to https<br/>Nginx :443, TLS ends here<br/>Let's Encrypt via Certbot"]
        UV["uvicorn, 2 workers<br/>127.0.0.1:8000 (loopback)<br/>systemd, Restart=always"]
        DB[("SQLite file<br/>~/career-platform/data/career_platform.db")]
        NSG --> NG -- "plain HTTP" --> UV -- "file read, no network" --> DB
    end
```

| Part | Railway | Azure |
|---|---|---|
| DNS answer for `@` | CNAME to Railway, flattened to `69.46.46.57` | A record `20.80.7.163` |
| Network filter | Railway's edge (provider) | Azure NSG rules I wrote |
| Where TLS ends | Railway edge, certificate renewed by Railway | Nginx on the VM, Certbot timer renews |
| App listener | `0.0.0.0:$PORT` inside the container | `127.0.0.1:8000`, reachable only from the VM itself |
| Database | PostgreSQL service over the private network | SQLite file on the same disk, no network hop |
| Keeping it running | Railway restart policy and health check (`/healthz`) | systemd `enable` + `Restart=always` |
| VM private IP | n/a | Unknown, never recorded |

**Localhost means different things on each host:** on Azure, `127.0.0.1:8000` is loopback on the VM, so only Nginx on that VM can reach uvicorn. On Railway, the app binds `0.0.0.0` so Railway's edge can reach the container from outside it.

## Sources

- Railway edge IP, DNS and certificate: [evidence/ex05.md](../evidence/ex05.md)
- DNS records and grey cloud: [evidence/dns-before-zoho.md](../evidence/dns-before-zoho.md)
- Railway service layout: [plans/2026-10-08-railway-migration.md](../superpowers/plans/2026-10-08-railway-migration.md)
- Azure Nginx, systemd and NSG: [plans/2026-10-01-operate-the-vm.md](../superpowers/plans/2026-10-01-operate-the-vm.md), [how-this-site-is-secured.md](../how-this-site-is-secured.md)
- Decommission: [railway-migration-results.md](../railway-migration-results.md)
