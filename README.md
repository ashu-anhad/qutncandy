# QutnCandy

Online store for handcrafted cotton chikankari clothing (qutncandy.com / qutncandy.in). Tagline: "Wear your confidence".
React (Vite) frontend · FastAPI backend · PostgreSQL. Architecture plan: one SPA, one stateless API, one database.

## Setup

PostgreSQL needs a database `cutencandy` owned by user `candy` (password `candy`), or change `DATABASE_URL` in `backend/.env`.

### Backend (http://localhost:8000, API docs at /docs)

    cd backend
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env              # then set JWT_SECRET
    alembic upgrade head              # create/upgrade tables
    python -m app.cli create-admin --email you@example.com --name "Your Name"
    python -m app.cli seed            # optional: sample categories and products
    uvicorn app.main:app --reload

### Frontend (http://localhost:5173)

    cd frontend
    npm install
    npm run dev

Vite proxies `/api` and `/media` (uploaded images) to the backend.

Open items and known gaps are tracked in [TODO.md](TODO.md); the deployment plan is in [DEPLOYMENT.md](DEPLOYMENT.md);
brand colours, fonts and logo rules are in [BRAND.md](BRAND.md).

## Development

- Tests: `cd backend && pytest` (runs in a throwaway `test` schema inside the dev database)
- After changing models: add the model import to `app/models.py`, then
  `alembic revision --autogenerate -m "describe change"` and `alembic upgrade head`

## Layout

    backend/app/
      core/        config, db, security (JWT + argon2), deps (current user / admin), errors
      auth/        users, signup/login/refresh/logout, /api/me
      catalog/     categories, products, variants (size × colour), images; storefront + admin routes
      cart/        server cart for logged-in users + pricing for guest carts
      discounts/   discount codes (admin) and validation
      orders/      quote, place order (atomic stock), cancel, expiry
      payments/    Razorpay: start payment, verify signature, webhook
      notifications/ in-app notifications + email via core/messaging.py
      reviews/     verified-purchase reviews + admin moderation
      reports/     sales, top products, discount usage (+ CSV)
      jobs/        scheduled commands (expire_orders)
      admin/       /api/admin/* (admin role only)
      cli.py       management commands (create-admin, seed)
      seed.py      sample chikankari catalog
    backend/alembic/   migrations
    frontend/src/
      api/         fetch client (auto token refresh) + endpoint helpers
      auth.jsx     session context and route guards
      pages/       storefront pages; pages/admin/ for the admin panel
      components/  layouts and shared UI

## Conventions

- Money is stored and sent as integer **paise** (₹1,890 = `189000`); the frontend formats it.
- Uploaded images go to `backend/media/` through `core/storage.py` (swap for S3 later).

## Orders and stock

- Placing an order takes stock immediately with `UPDATE … WHERE stock >= qty`, so the last piece can't be sold twice.
- Orders wait `ORDER_EXPIRY_MINUTES` (15) for payment. Run the expiry job every 5 minutes to cancel unpaid
  orders and return their stock and discount uses:

      */5 * * * *  cd /path/to/backend && .venv/bin/python -m app.jobs.expire_orders

- Shipping is `SHIPPING_FEE` (₹99), free from `FREE_SHIPPING_MIN` (₹1,999). Both are settings in `.env` (in paise).

## Payments (Razorpay)

1. In the Razorpay dashboard (Test Mode): Account & Settings → API Keys → Generate Test Key.
2. Put the keys in `backend/.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) and restart the backend.
   Without keys the store works but "Pay" says online payment isn't set up.
3. Webhook (recommended; it confirms payments even if the customer closes the tab):
   - URL `https://<your-domain>/api/webhooks/razorpay`, events `payment.captured` and `order.paid`
   - Secret: any long random string, also set as `RAZORPAY_WEBHOOK_SECRET`
   - To test locally, expose the backend with `cloudflared tunnel --url http://localhost:8000` and use that URL.

Flow: place order → `POST /api/orders/{number}/pay` creates the Razorpay order → popup → `POST /api/payments/verify`
checks the signature → order becomes `paid`. The webhook does the same independently; whichever arrives first wins.
A payment that lands after the 15-minute hold re-takes stock if available, otherwise the order is flagged
"refund required" in its history.

Test payments: UPI ID `success@razorpay` (or `failure@razorpay`), or a test card from Razorpay's docs ("Test Card Details").

## Fulfilment

Admin → Orders: "To ship" (paid, oldest first) → **Mark as shipped** (courier + tracking no.) → **Mark as delivered**.
Cancelling a paid order returns its stock and moves it to **Refunds due**; refund in the Razorpay dashboard,
then **Mark as refunded**. Every step writes to the order history and notifies the customer (in-app + email).

Email: set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` in `backend/.env` (any SMTP provider, e.g.
Gmail app password, Zoho, Brevo, SES). Without them, emails are printed in the backend log, including
password-reset links.

## Login methods

- **Email + password** (with forgot/reset password)
- **Google**: set `GOOGLE_CLIENT_ID` in `backend/.env` (Google Cloud Console → Credentials → OAuth client ID,
  type Web, authorised JavaScript origin = your site URL). The button appears automatically.
- **Phone OTP**: `OTP_ENABLED=true`. No SMS provider is connected yet, so codes are printed in the backend
  log. Keep it `false` in production until `send_sms` in `core/messaging.py` uses a real provider.

## Docker (production-like)

    docker compose up --build        # → http://localhost:8080

Runs Postgres 18, the backend (migrations run on start), nginx serving the built frontend and proxying
`/api` + `/media`, and a worker that runs the order-expiry job every 5 minutes. Keys and secrets come from
`backend/.env`; set `SITE_URL` and `POSTGRES_PASSWORD` in the environment for a real deployment. Create the
admin inside the container: `docker compose exec backend python -m app.cli create-admin --email … --name …`.

## Login model

Short-lived access token (15 min) kept in memory; refresh token (30 days) in an httpOnly cookie scoped to `/api/auth`.
"Log out of all devices" bumps `users.token_version`, invalidating every issued token.
