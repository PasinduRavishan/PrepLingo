# SPEC 16 — Personal .me Domain & Multi-Project Live Links

Status: Reference guide
Date: 2026-03-18
Goal: Purchase a personal `.me` domain, manage DNS via Cloudflare, and host multiple deployed projects as clean subdomains (e.g. `preplingo.yourname.me`, `project2.yourname.me`)

---

## Why a .me Domain

`.me` is the standard TLD for personal developer portfolios and project showcases. It reads naturally as a personal brand (`ravishan.me`), is widely recognised, and subdomains make clean per-project URLs without needing separate domains for every project.

**Example end result:**
```
ravishan.me                  → your portfolio / landing page
preplingo.ravishan.me        → PrepLingo deployed on GCP
project2.ravishan.me         → another project on any server
api.ravishan.me              → a backend API
```

---

## Part 1 — Purchase the Domain

### Option A — Porkbun (Recommended)

**Website:** porkbun.com

**Why:** Cheapest `.me` pricing (around $5-8/year first year, ~$12-15/year renewal), free WHOIS privacy included by default (most registrars charge extra), clean interface, and free SSL via Let's Encrypt integrated.

**Steps:**
1. Go to porkbun.com
2. Search `yourname.me` in the search bar
3. Add to cart → Checkout
4. Create an account with your email
5. Pay (credit card, PayPal, or crypto)
6. Your domain is registered — you'll receive a confirmation email

**Cost:** ~$5-8 first year (look for first-year promo), ~$12-15/year renewal

---

### Option B — Namecheap

**Website:** namecheap.com

**Why:** Very reliable, long-standing registrar, good dashboard, competitive pricing, includes free WHOIS privacy (WhoisGuard).

**Steps:**
1. Go to namecheap.com
2. Search your domain name
3. Add to cart → select 1-year or 2-year registration
4. Use the coupon section (Namecheap frequently has promo codes — search "Namecheap coupon" before checkout)
5. Create account → checkout

**Cost:** ~$3-6 first year with promo, ~$14-18/year renewal

---

### Option C — Squarespace Domains (formerly Google Domains)

**Website:** domains.squarespace.com

**Why:** Simple, clean interface, Google-quality infrastructure. Slightly more expensive but very reliable.

**Cost:** ~$20/year flat (no first-year discount, no surprises)

---

### Pricing Comparison

| Registrar | First Year | Renewal/year | WHOIS Privacy | Notes |
|-----------|-----------|--------------|---------------|-------|
| **Porkbun** | ~$5-8 | ~$12-15 | Free | Best deal overall |
| **Namecheap** | ~$3-6 | ~$14-18 | Free | Most popular choice |
| Squarespace | ~$20 | ~$20 | Free | Premium, no deals |
| GoDaddy | ~$2-5 | ~$20-25 | Paid extra | Avoid renewal shock |

> ⚠️ Avoid GoDaddy for renewals — first year is cheap, renewal is expensive and they upsell aggressively.

---

## Part 2 — Move DNS to Cloudflare (Free)

After purchasing, move DNS management to **Cloudflare**. Cloudflare is the industry standard for DNS management and gives you:
- Fastest DNS in the world (1.1.1.1 network)
- Free SSL/HTTPS for all subdomains
- DDoS protection
- Simple dashboard to add/edit DNS records
- Free tier is more than enough for personal projects

**Website:** cloudflare.com

### Steps

**1. Create a free Cloudflare account**
- Go to cloudflare.com → Sign up
- Enter your email and create a password

**2. Add your domain to Cloudflare**
- Dashboard → Add a Site → enter `yourname.me`
- Select the **Free** plan → Continue

**3. Cloudflare scans your existing DNS records**
- It will show any existing records (usually just a default A record from your registrar)
- Click Continue

**4. Cloudflare gives you two nameservers**
- They look like: `alice.ns.cloudflare.com` and `bob.ns.cloudflare.com`
- Copy both of them

**5. Update nameservers at your registrar**

Go back to wherever you bought the domain:

*Porkbun:* Account → Domain Management → click your domain → Authoritative Nameservers → change to Cloudflare's nameservers

*Namecheap:* Dashboard → click your domain → Nameservers → select "Custom DNS" → enter Cloudflare's nameservers

*Squarespace:* Domains → your domain → DNS → Nameservers → enter Cloudflare's nameservers

**6. Wait for propagation**
- Cloudflare verifies the nameserver change
- Takes 5 minutes to 48 hours (usually under 30 minutes)
- Cloudflare emails you when it's active

**All DNS management now happens in Cloudflare's dashboard.**

---

## Part 3 — Point the Root Domain Somewhere

Before adding project subdomains, decide what `yourname.me` itself shows.

**Option A — GitHub Pages portfolio** (free, simple)

Host a simple HTML portfolio on GitHub Pages:
1. Create a GitHub repo named `yourname.me` or `portfolio`
2. Enable GitHub Pages (Settings → Pages → Source: main branch)
3. In Cloudflare DNS → Add record:
   ```
   Type: CNAME
   Name: @   (or yourname.me)
   Target: yourgithubusername.github.io
   Proxy: ON (orange cloud)
   ```

**Option B — Coming soon / redirect to LinkedIn**
```
Type: CNAME
Name: @
Target: yourlinkedin.com/in/yourhandle  (or any redirect)
```

**Option C — Leave it for now, just use subdomains**
- Add `A` records only for subdomains
- Root domain can return nothing or a simple holding page

---

## Part 4 — Add Project Subdomains in Cloudflare

For each deployed project, add a DNS record in Cloudflare pointing the subdomain to the server IP.

### Adding a subdomain → GCP VM (PrepLingo)

In Cloudflare Dashboard → your domain → DNS → Add record:

```
Type:    A
Name:    preplingo
Value:   34.55.196.147     ← your GCP VM external IP
TTL:     Auto
Proxy:   ON (orange cloud) ← enables Cloudflare SSL + DDoS protection
```

This creates `preplingo.yourname.me` → your GCP VM.

**Important:** With Cloudflare proxy ON (orange cloud), Cloudflare provides free HTTPS at `https://preplingo.yourname.me` automatically — no Certbot needed on the server side.

### Adding more projects

Each project deployed on a different server gets its own A record:

```
Type:    A
Name:    project2
Value:   IP_OF_PROJECT2_SERVER
TTL:     Auto
Proxy:   ON
```

```
Type:    A
Name:    api
Value:   IP_OF_API_SERVER
TTL:     Auto
Proxy:   ON
```

You can have unlimited subdomains on the free Cloudflare plan.

---

## Part 5 — Configure Nginx on Each Server for the Subdomain

When a request hits `preplingo.yourname.me`, it routes to your GCP VM. Nginx needs to know the domain name to accept it.

Update `nginx/nginx.conf` on the GCP VM:

```nginx
server {
    listen 80;
    server_name preplingo.yourname.me;   # ← add your domain

    # ... rest of config stays the same
}
```

Then restart nginx:
```bash
docker compose restart nginx
```

Since Cloudflare proxy is ON, Cloudflare handles HTTPS → your server only needs HTTP on port 80. Cloudflare terminates SSL and forwards to your server as HTTP. This is called **Cloudflare Flexible SSL** and requires zero server-side certificate setup.

> If you want end-to-end encryption (Cloudflare → your server also HTTPS), set Cloudflare SSL/TLS mode to **Full** and add a Let's Encrypt cert to your server (see Part 5 of deployment guide).

---

## Part 6 — DNS Record Types Reference

| Type | Use case | Example |
|------|----------|---------|
| `A` | Point domain/subdomain to an IPv4 address | `preplingo → 34.55.196.147` |
| `AAAA` | Point to IPv6 address | (same as A but for IPv6) |
| `CNAME` | Point subdomain to another hostname | `www → yourname.me` |
| `MX` | Email routing | (for custom email) |
| `TXT` | Domain verification, SPF records | (for Google verification etc.) |

For project hosting, you will almost always use `A` records.

---

## Part 7 — Useful Tools and Websites

### Domain Registration
| Tool | URL | Use |
|------|-----|-----|
| **Porkbun** | porkbun.com | Buy domain (recommended) |
| **Namecheap** | namecheap.com | Buy domain (alternative) |
| **TLD List** | tld-list.com | Compare prices across all registrars for any TLD |
| **Instant Domain Search** | instantdomainsearch.com | Check availability fast |

### DNS Management
| Tool | URL | Use |
|------|-----|-----|
| **Cloudflare** | cloudflare.com | DNS management, free SSL, DDoS protection (use this) |
| **DNS Checker** | dnschecker.org | Verify DNS propagation across the world |
| **MX Toolbox** | mxtoolbox.com | DNS lookup and debugging |
| **WhatsMyDNS** | whatsmydns.net | Check if your DNS has propagated globally |

### SSL Certificates (if not using Cloudflare proxy)
| Tool | URL | Use |
|------|-----|-----|
| **Let's Encrypt** | letsencrypt.org | Free SSL certs (via Certbot) |
| **Certbot** | certbot.eff.org | Tool to get and renew Let's Encrypt certs |
| **SSL Labs** | ssllabs.com/ssltest | Test your HTTPS configuration quality |

### Hosting / Deployment (for future projects)
| Platform | URL | Best for |
|----------|-----|----------|
| **GCP Compute Engine** | cloud.google.com | Full VMs, Docker, any stack |
| **Railway** | railway.app | Fast deploy, persistent disk, generous free tier |
| **Render** | render.com | Easy deploy from GitHub, good free tier |
| **Fly.io** | fly.io | Containers globally, good free tier |
| **Vercel** | vercel.com | Frontend / Next.js (free, instant) |
| **Netlify** | netlify.com | Static sites and JAMstack (free) |

---

## Part 8 — Step-by-Step Summary

```
1. Buy yourname.me at Porkbun or Namecheap (~$5-15/year)

2. Create free Cloudflare account → Add your domain → Get nameservers

3. Update nameservers at registrar to Cloudflare's nameservers

4. Wait for propagation (5 min - 2 hours)

5. In Cloudflare DNS:
   Add A record: preplingo → 34.55.196.147 (proxy ON)
   Add A record: project2  → OTHER_IP        (proxy ON)
   Add CNAME:   www        → yourname.me     (proxy ON)

6. Update nginx.conf on each server:
   server_name preplingo.yourname.me;

7. Restart nginx:
   docker compose restart nginx

8. Visit https://preplingo.ravishan.me — works with free HTTPS via Cloudflare
```

---

## Part 9 — Auto-Renewal Reminder

Domains expire annually. Enable auto-renewal at your registrar to avoid losing the domain:

- **Porkbun:** Account → Domain Management → Auto-renew toggle → ON
- **Namecheap:** Dashboard → domain → Auto-Renew → ON

Set a calendar reminder 30 days before expiry as a backup. If a domain expires and someone else registers it, you lose it permanently.

---

## Part 10 — What Your Portfolio URLs Could Look Like

Once set up:

| URL | Project |
|-----|---------|
| `yourname.me` | Portfolio / landing page |
| `preplingo.yourname.me` | PrepLingo AI Interview Trainer |
| `api.yourname.me` | Any backend API |
| `project2.yourname.me` | Next project |
| `blog.yourname.me` | Optional blog (Ghost, Hashnode, etc.) |

All served over HTTPS, all from one domain, all free to add via Cloudflare.
