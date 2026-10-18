# Deployment plan

Status: **in progress** — production files ready (`docker-compose.prod.yml`, `deploy/`, `deploy.sh`); server not yet created (2026-10-19).
Constraint: **trial project, ₹0 running cost.** The only paid item is the domain: **qutncandy.com**
(and qutncandy.in), already owned at GoDaddy. In the steps below, `<domain>` = `qutncandy.com`.

## Free setup (chosen)

```
Customers ──HTTPS──▶ <domain> / www.<domain>   (DNS stays at GoDaddy: A records → server IP)
                        │
                        ▼
              Oracle Cloud "Always Free" VM (Mumbai or Hyderabad, Ubuntu, ARM)
              Docker Compose:
                caddy     – free HTTPS certificates (Let's Encrypt), security headers, www → apex redirect
                frontend  – nginx serving the React build
                backend   – FastAPI
                worker    – cancels unpaid orders every 5 min
                db        – PostgreSQL 18 (data on a Docker volume)
                media     – product images on a Docker volume
                backup    – nightly pg_dump + media archive, last 7 kept on the server
```

| Need | Free choice | Notes |
|---|---|---|
| Server | Oracle Cloud Always Free (Ampere ARM VM) | Signup needs a card for identity verification; Always Free resources aren't charged. Free capacity is sometimes unavailable in a region (retry, or try the other Indian region). Instances left almost completely idle for a week may be reclaimed |
| DNS | GoDaddy (no change of provider) | Two records: `@` A → server IP, `www` CNAME → `@` |
| HTTPS | Caddy + Let's Encrypt | Automatic issue and renewal |
| Database | Postgres in Docker on the same VM | Backups are our job (nightly dump, see below) |
| Images | Docker volume on the VM | Included in the nightly backup |
| Code delivery | `./deploy.sh` copies the project over SSH (rsync) | No GitHub needed; git on the Mac keeps versions for rollback |
| Email | Gmail SMTP + app password | ~500/day; sender shows as your Gmail. Fine for a trial |
| Payments | Razorpay **test mode** | No KYC; live mode later needs KYC + policy pages |
| Google login | Existing OAuth client | Add `https://<domain>` and `https://www.<domain>` as authorised origins |
| Phone OTP | Disabled (`OTP_ENABLED=false`) | No free Indian SMS provider |
| Uptime check | UptimeRobot free | Alerts if the site goes down; its pings also keep the VM from looking idle |

**Free alternative without giving Oracle a card:** Cloudflare Pages (frontend) + Render free web service
(backend; sleeps when idle, ~1 min cold start) + Neon free Postgres + an image host (e.g. Cloudinary free), with
the expiry job triggered by a scheduled GitHub Action. More services and slower; only if the card is a deal-breaker.

## Steps

### You (all free)

1. **GitHub**: create a private repository; add me the remote URL (or I'll give you the push commands).
2. **Oracle Cloud**: sign up, choose **Mumbai** or **Hyderabad** as home region. Create a VM:
   Ubuntu 24.04, shape **VM.Standard.A1.Flex** (e.g. 2 OCPU / 12 GB, within Always Free), add your SSH public key.
   In the VM's network security list, allow inbound TCP **80** and **443** (22 is open by default).
   Note the public IP.
3. **GoDaddy DNS**: add `A` record `@` → VM public IP and `CNAME` `www` → `@` (remove the GoDaddy "parked" records).
4. **Gmail**: turn on 2-step verification, create an **app password** (Google Account → Security → App passwords).
5. **Razorpay**: generate **test** keys (Dashboard → Test Mode → API Keys).
6. **Google Cloud**: add `https://<domain>` and `https://www.<domain>` to the OAuth client's authorised origins.
7. Give me SSH access to the VM (or run the commands I provide yourself).

### Me (code + server setup)

1. **Git**: `git init`, check `.gitignore` (no `.env`, `media/`, `node_modules/`), first commit, push.
2. **`docker-compose.prod.yml`**: add Caddy (HTTPS for `<domain>`, `www` redirect, security headers, gzip),
   expose only 80/443, keep Postgres internal, ARM-compatible images, Docker log rotation.
3. **Production settings**: `backend/.env.production.example` with every variable explained; `COOKIE_SECURE=true`,
   `SITE_URL=https://<domain>`, `CORS_ORIGINS`, `OTP_ENABLED=false`, Gmail SMTP, generated strong `JWT_SECRET`
   and `POSTGRES_PASSWORD`; backend refuses to start in production with default secrets.
4. **Migrations as a deploy step** instead of on every start; `/api/health` also checks the database.
5. **`deploy.sh`**: one command from your Mac — SSH → `git pull` → build → migrate → restart; `./deploy.sh <commit>`
   rolls back. Plus a first-time `server-setup.sh` (install Docker, firewall 22/80/443, swap file).
6. **Backups**: nightly `pg_dump` + media archive kept for 7 days on the VM, and a `backup-download.sh` to copy the
   latest to your Mac; restore steps documented and tested once.
7. **Security basics**: rate limiting on login / forgot-password; change the weak admin password.
8. **Uptime**: set up the UptimeRobot check on `https://<domain>/api/health` (needs your free account, or you add it).

### Go-live (together)

1. Deploy, open `https://<domain>`, check the HTTPS padlock.
2. Create the admin on the server; test: sign up, Google login, browse, cart, pay with Razorpay test UPI
   (`success@razorpay`), admin ships, customer sees tracking, emails arrive in Gmail.
3. Point the Razorpay **webhook** at `https://<domain>/api/webhooks/razorpay`.
4. Replace the sample catalog with real products when ready.

## Limits of the free setup (fine for a trial)

- One machine: if it fails, restore from the latest backup onto a new VM (~30 min).
- Backups live on the same VM unless downloaded; download them regularly (`backup-download.sh`).
- Gmail sending limits and "via gmail.com" sender; no custom-domain email.
- Test-mode payments only (no real money) until Razorpay KYC.

## When it becomes a real store (paid, ~₹2,500/month)

Move to: DigitalOcean Bangalore droplet + Managed PostgreSQL (automatic backups, point-in-time restore),
Cloudflare DNS/CDN + R2 for images, a transactional email provider on your own domain, Razorpay live keys.
The Docker setup carries over; only storage, database URL and DNS change.

## Open questions

- ~~Domain name~~ → `qutncandy.com` (`qutncandy.in` can redirect to it: GoDaddy → Forwarding, 301)
- OK to sign up for Oracle Cloud with card verification? (If not, use the no-card alternative above.)
- SSH access for me, or will you run the server commands yourself?
