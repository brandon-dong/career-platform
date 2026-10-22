# Email and analytics paths

These paths are the same on Azure and Railway. Mail never touches the web host, and analytics events go from the visitor's browser straight to Google. Web request path: [request-path.md](request-path.md).

## Incoming mail

```mermaid
flowchart LR
    S["Sender's mail server<br/>e.g. LMU (Microsoft 365)"]
    D[("DNS: MX brandondong.me<br/>mx.zoho.com (10)<br/>mx2 (20), mx3 (50)")]
    Z["Zoho mail servers<br/>mx.zoho.com"]
    M["My Zoho mailbox"]
    B["Me, in Zoho webmail"]

    S -->|"1. which server takes mail for brandondong.me? (DNS, UDP 53)"| D
    S -->|"2. SMTP, TCP 25"| Z
    Z --> M
    B -->|"3. HTTPS 443"| M
```

Before the MX records existed (before 2026-10-13 21:36:29 UTC), step 1 had no answer, so sending servers had nowhere to deliver.

## Outgoing mail and how the receiver checks it

```mermaid
flowchart LR
    B["Me, in Zoho webmail"]
    Z["Zoho sending server<br/>sender5-of-o52.zoho.com<br/>165.173.182.52"]
    R["Recipient's mail server<br/>e.g. Microsoft 365"]
    subgraph dns["DNS records the receiver looks up"]
        SPF["TXT @<br/>v=spf1 include:zohomail.com ~all"]
        DKIM["TXT zmail._domainkey<br/>public key"]
        DMARC["TXT _dmarc<br/>p=none"]
    end
    I["Recipient's inbox or Junk"]

    B -->|"HTTPS 443"| Z
    Z -->|"SMTP, TCP 25<br/>message signed with DKIM"| R
    R -.->|"SPF: may this IP send for the envelope sender?"| SPF
    R -.->|"DKIM: does the signature verify?"| DKIM
    R -.->|"DMARC: does a pass match the From domain?"| DMARC
    R --> I
```

The SMTP port between mail servers (25) is the standard one. I didn't capture it myself. The receiver's verdicts are in [zoho-header-check.md](../evidence/zoho-header-check.md).

## Analytics

```mermaid
sequenceDiagram
    participant V as Visitor's browser
    participant W as brandondong.me (Railway)
    participant G as Google (googletagmanager.com, GA4 collection)
    participant R as GA4 Realtime (me)

    V->>W: GET page (HTTPS 443)
    W-->>V: HTML with a held-back GA tag and consent banner
    Note over V: Nothing goes to Google yet
    V->>V: Visitor clicks Accept (static/js/consent.js)
    V->>G: Load gtag.js (HTTPS 443)
    V->>G: page_view event, analytics consent granted (gcs=G101)
    V->>G: click event with link_url, link_domain, outbound=true
    G-->>R: Events appear in Realtime within seconds
```

If the visitor clicks Decline or makes no choice, the browser never loads `gtag.js` and sends nothing. Evidence: [ex06.md](../evidence/ex06.md) §3.
