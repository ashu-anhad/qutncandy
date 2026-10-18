# Deployment plan

Status: **in progress** — production files ready (`docker-compose.prod.yml`, `deploy/`, `deploy.sh`); Azure VM not yet
created (2026-10-19).
Constraint: **trial project, ₹0 running cost.** Domain **qutncandy.com** (and qutncandy.in) owned at GoDaddy.
Hosting: **Microsoft Azure**, free account.

## Setup

```
Customers ──HTTPS──▶ qutncandy.com / www   (DNS at GoDaddy: A record → VM public IP)
                        │
                        ▼
              Azure VM  Standard_B1s (1 vCPU, 1 GB RAM + 2 GB swap), Ubuntu 24.04, Central India
              Docker Compose (docker-compose.prod.yml):
                caddy     – free HTTPS (Let's Encrypt), security headers, www → apex redirect
                frontend  – nginx serving the React build
                backend   – FastAPI (1 process)
                worker    – cancels unpaid orders every 5 min
                db        – PostgreSQL 18 (Docker volume)
                backup    – nightly DB dump + images archive in /opt/qutncandy/backups (7 days)
```

| Need | Choice | Cost |
|---|---|---|
| Server | Azure free account: B1s Linux VM, 750 h/month | Free for 12 months, then ~₹700–900/month |
| Disk | 64 GB Premium SSD (P6) | Free for 12 months (2 × P6 included) |
| Public IP | Standard static IPv4 | Free for 12 months (1,500 h/month included) |
| Bandwidth | Outbound data | 15 GB/month free (100 GB after upgrading) |
| DNS | GoDaddy (unchanged provider) | ₹0 |
| HTTPS | Caddy + Let's Encrypt | ₹0 |
| Database / images | On the VM, in Docker volumes, backed up nightly | ₹0 |
| Email | Gmail SMTP + app password | ₹0 |
| Payments | Razorpay test mode | ₹0 |

**Azure free-account rules to know:** signup needs a card (or use "Azure for Students" without one). The $200 credit
lasts 30 days; after that Azure asks you to **upgrade to pay-as-you-go** to keep the 12-month free services — they
stay free within the limits above, anything beyond is billed. A **budget alert** (step 3) warns before any charge.

## Steps

### You — Azure portal (portal.azure.com)

1. **Account**: azure.microsoft.com/free → Start free → sign in with a Microsoft account → card verification.
2. **Create the VM**: Virtual machines → Create → Azure virtual machine.
   - Resource group: **Create new** → `qutncandy-rg`; VM name `qutncandy-vm`; Region **(Asia Pacific) Central India**.
   - Image **Ubuntu Server 24.04 LTS – x64 Gen2**; Size **Standard_B1s** (marked "Free services eligible"; use "See all sizes").
   - Authentication **SSH public key**, username **azureuser**, **Generate new key pair**, key name `qutncandy-key`.
   - Public inbound ports: **Allow selected** → **SSH (22), HTTP (80), HTTPS (443)**.
   - Disks: OS disk **Premium SSD**, size **64 GiB (P6)** (matches the free allowance); tick "Delete with VM".
   - Networking: defaults (new virtual network, new public IP); tick "Delete public IP and NIC when VM is deleted".
   - Review + create → **Create** → **Download private key and create resource** (saves `qutncandy-key.pem`).
   - When deployed: open the VM → copy **Public IP address**.
3. **Budget alert**: Cost Management → Budgets → Add → ₹100/month, alert at 50% to your email.
4. **Key on the Mac**: `mv ~/Downloads/qutncandy-key.pem ~/.ssh/ && chmod 600 ~/.ssh/qutncandy-key.pem`
5. **GoDaddy DNS** (qutncandy.com → DNS): `A` `@` → VM public IP (remove other `@` A records / parking);
   `CNAME` `www` → `@`; turn off GoDaddy website/forwarding for this domain.
   Optional: qutncandy.in → GoDaddy Forwarding → `https://qutncandy.com` (301).
6. **Google Cloud**: add `https://qutncandy.com` to the OAuth client's authorised JavaScript origins.
7. Optional now or later: Razorpay test keys, Gmail app password → into `backend/.env.production`.

### Me — from this Mac (you approve each command)

1. `deploy/.env.server`: `SERVER=azureuser@<ip>`, `SSH_KEY=~/.ssh/qutncandy-key.pem`.
2. `./deploy.sh setup` — installs Docker, firewall rules, 2 GB swap, unattended security updates.
3. `./deploy.sh` — creates `backend/.env.production` with fresh secrets, copies the code, builds, starts; Caddy
   fetches the HTTPS certificate once DNS points at the VM.
4. `./deploy.sh admin <email> "<name>"` (you type the password) and `./deploy.sh seed` for sample products.
5. Verify `https://qutncandy.com`, `https://www.qutncandy.com` → redirect, `/api/health`.

### Together — go-live checks

Sign up, Google login, browse, cart, checkout (Razorpay test UPI `success@razorpay` once keys are set), admin ships,
customer sees tracking, emails arrive. Point the Razorpay webhook at `https://qutncandy.com/api/webhooks/razorpay`.

## Day-to-day

| Task | Command |
|---|---|
| Deploy latest code | `./deploy.sh` |
| Roll back | `git checkout <commit> && ./deploy.sh` (then `git checkout main`) |
| What's running | `./deploy.sh status` |
| Logs | `./deploy.sh logs` or `./deploy.sh logs backend` |
| Download backups | `./deploy.sh backups` (do this regularly — backups otherwise live on the VM) |

## Limits (fine for a trial)

- 1 GB RAM: one API process; builds run on the VM using swap (first build takes several minutes).
- Single machine; recovery = new VM + `./deploy.sh` + restore the latest backup.
- Free for 12 months only; set a reminder before the anniversary.

## When it becomes a real store

Bigger VM (B2s), Azure Database for PostgreSQL (managed backups), Azure Blob Storage + CDN for images, a transactional
email provider on your domain, Razorpay live keys. The Docker setup carries over; storage, database URL and DNS change.
