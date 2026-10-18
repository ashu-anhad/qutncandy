# TODO / Known gaps

Single list of everything pending, deferred or knowingly left out. Updated at the end of each phase.
Last updated: 2026-10-19 (logo added, style guide in BRAND.md). All planned phases are built.

## Needs you (owner actions)

- [x] Admin account: `admin@qutncandy.com` created (2026-10-19). `ashuanhad@gmail.com` stays a customer account
- [ ] Add Razorpay **test** keys to `backend/.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`), then restart the backend
- [ ] Do one real test payment end to end (UPI `success@razorpay`). Phase 4 is only tested with simulated Razorpay so far
- [ ] Set up the Razorpay webhook (`payment.captured`, `order.paid`) with `RAZORPAY_WEBHOOK_SECRET`. Needs a tunnel locally or a real domain
- [x] Google sign-in: Client ID set in `backend/.env`, real sign-in done with ashuanhad@gmail.com (2026-10-19)
- [ ] Phone OTP: pick an SMS provider (MSG91 / Twilio / Gupshup; Indian SMS needs DLT template registration)
      so codes are actually texted. Today they're only printed in the backend log
- [ ] Try the Docker setup (`docker compose up --build`). Written but never run here (Docker isn't installed)
- [ ] Decide: offer **Cash on Delivery** alongside Razorpay? (currently online payment only)
- [ ] Choose an email provider and set `SMTP_*` in `backend/.env`. Until then emails (order updates,
      password reset links) only appear in the backend log
- [ ] Replace the sample catalog (12 seeded products with generated placeholder images) with real products and photos
- [x] Logo received; header, login, footer, home hero, favicon and app icon use it (2026-10-19)
- [ ] Optional: get the logo as a vector (SVG) and a light/reversed version for dark backgrounds. Current assets
      are cut from the 1254 px PNG (sharp at all sizes used on the site)
- [ ] Turn the project into a git repository (`git init`). There is no version control yet

## Phases (all built)

Phases 1–4 (foundation, catalog, cart & checkout, payments) are complete; details in README.md.

### Phase 5: Orders and tracking ✅ done
- [x] Admin orders screen: status tabs, search, detail, mark shipped (courier + tracking no.), mark delivered
- [x] Admin cancel of **paid** orders (stock returned, moves to "Refunds due")
- [x] "Refund required" orders surfaced: `orders.refund_status`, Refunds due tab + dashboard tile, Mark as refunded
- [x] Customer tracking: progress bar, courier + tracking number
- [x] In-app notifications (bell + unread count, notifications page) and emails on every status change
- [x] `core/messaging.py` (send_email via SMTP / log fallback; send_sms placeholder)
- [x] Admin inventory view: low / out of stock filters, inline restock
- [x] Admin dashboard with work-queue counts and last-24h revenue
- [x] Forgot / reset password (30-minute single-use link by email)

### Phase 6: Extras ✅ done
- [x] Reviews: verified-purchase only (delivered orders), admin approval, cached `avg_rating` / `review_count`,
      stars on cards and product page, "Write a review" from delivered orders
- [x] Google sign-in (`POST /api/auth/google`, links to an existing account with the same email). Live locally
- [x] Phone OTP login (6-digit code, 5 min, 5 attempts, 30 s resend wait, 5 per hour). Needs SMS provider
- [x] Admin reports: revenue/orders by day or month (IST), top products, discount usage, CSV export
- [x] Docker: backend, frontend (nginx), Postgres, expiry worker (`docker-compose.yml`). Untested here

### Next: Deployment (planned, free setup — see [DEPLOYMENT.md](DEPLOYMENT.md))
- [ ] Answer the open questions at the end of DEPLOYMENT.md (Oracle signup OK?, SSH access). Domain: qutncandy.com
- [ ] Owner setup, all free: GitHub repo, Oracle Cloud Always Free VM, GoDaddy DNS records, Gmail app password,
      Razorpay test keys, Google authorised origins
- [ ] Code + server work: git, prod compose with Caddy, prod settings, deploy/rollback script, nightly backups,
      rate limiting, admin password change
- [ ] Go-live checklist with Razorpay test keys

### Later (to plan): launch readiness and admin polish
- [ ] Policy pages, GST invoices, change-password screen, new-order email to store, rate limiting
- [ ] Hardcoded values → admin settings, product "work" field, image reorder/resize, HTML emails

## Known gaps (built, but incomplete)

- [ ] No "change password" screen in My account (only Forgot password → email link)
- [ ] Email verification on signup doesn't exist
- [ ] Order **expiry job isn't scheduled for local dev** (the Docker setup has a worker for it). Locally, unpaid
      orders hold stock until cancelled. Cron: `*/5 * * * * cd backend && .venv/bin/python -m app.jobs.expire_orders`
- [ ] Refunds can't be issued from the app (no Razorpay refund API call). Refund in the Razorpay dashboard for now
- [ ] `payment.failed` webhook events are ignored (customer isn't told; order just stays awaiting payment)
- [ ] Admin isn't notified of new paid orders (must check the dashboard). Could email the store on each order
- [ ] Courier/tracking can't be edited after marking shipped; no clickable courier tracking links
- [ ] No returns/exchanges, partial cancellation or per-item refunds (whole order only)
- [ ] Customers can't cancel paid orders themselves (they're told to contact the store; no contact page/email shown yet)
- [ ] Notification bell refreshes every 60 s (no live push)
- [ ] Emails are plain text (no HTML templates/branding)
- [ ] Discount codes have no per-customer limit (only a total usage limit)
- [ ] No stock-change history (deliberately left out of the simple design). Admins edit stock directly
- [ ] Product images can't be reordered or resized/optimised on upload
- [ ] Search is simple `ILIKE`. Upgrade to Postgres full-text if search quality matters
- [ ] Customers aren't notified when their review is approved/rejected (they see the status on the product page)
- [ ] Phone-only accounts get no emails (no email on file) and can't add an email/password later; email accounts
      can't add a phone number. No account merging beyond Google ↔ same email
- [ ] Reports: no refunds/returns netting (cancelled orders are simply excluded), no cost/profit, no per-category view
- [ ] Google tokens are checked via Google's tokeninfo endpoint (one network call per Google login). Fine at small scale;
      switch to local JWT verification (`google-auth`) if login volume grows
- [ ] Docker runs migrations on backend start; with several backend replicas, run them as a separate one-off step
- [ ] No frontend tests (backend has 84 pytest tests)

### Hardcoded values that could move to the database / admin
- [ ] Colour swatch hex codes (`frontend/src/lib/format.js` → `COLOUR_HEX`); unknown colours show grey
- [ ] Size display order (`backend/app/catalog/service.py` → `SIZE_ORDER`)
- [ ] Price filter bands on the product list (`frontend/src/pages/ProductList.jsx`)
- [ ] "Work: Hand-embroidered Lucknowi chikankari" line on every product page (should be a product field)
- [ ] Home hero and footer text
- [ ] Shipping fee, free-shipping threshold, payment hold time (`backend/.env` settings, not admin-editable)

## Before going live

- [ ] **Change the admin password.** `admin@qutncandy.com` uses a 5-character password (below the app's own
      8-character minimum, set directly at the owner's request) that was also shared in chat
- [ ] Strong `JWT_SECRET`, `COOKIE_SECURE=true`, production `CORS_ORIGINS`
- [ ] Razorpay **live** keys (needs Razorpay KYC) and production webhook
- [ ] Google: publish the OAuth consent screen (out of "Testing") and add the production domain to authorised
      JavaScript origins; otherwise only listed test users can sign in
- [ ] (Real store) Move media to S3/R2 + CDN (swap `backend/app/core/storage.py`) and DB to managed Postgres
- [ ] Rate limiting on login and forgot-password (OTP has its own per-number limits), security headers
- [ ] `OTP_ENABLED=false` in production until a real SMS provider is connected (local `.env` has it on)
- [ ] **GST**: prices are treated as tax-inclusive with no GST breakdown, GSTIN or tax invoices. Needed for an Indian store
- [ ] Legal/policy pages: privacy policy, terms, shipping, returns/refunds, contact details. Razorpay requires these
      on the site before activating live payments
- [ ] Database backups
- [ ] HTTPS hosting for frontend + backend, schedule the expiry job
- [ ] Remove sample seed data from production

## Decisions made (not gaps, for reference)

- Checkout requires login (guest carts are supported, guest checkout is not)
- Discount uses are counted when an order is placed (released on cancel/expiry), not on payment
- Stock is taken at order placement; unpaid orders are held 15 minutes
- Razorpay is called directly with `httpx` (no SDK)
- Deleting a product never affects past orders (order items keep their own copy)
- Refunds are issued manually in Razorpay, then recorded in admin ("Mark as refunded")
- Cancelling an order (any reason) returns its stock and discount use
- Reset links are stateless tokens; using one signs the user out everywhere and invalidates the link
- Reviews: one per customer per product; editing sends it back for approval
- Report "revenue" = order totals (after discounts, incl. shipping) of paid/shipped/delivered orders;
  product "sales" = line totals before order-level discounts. Days are India time
- Brand: **QutnCandy** (qutncandy.com / .in), tagline "Wear your confidence". Full style guide in [BRAND.md](BRAND.md):
  colours sampled from the logo (cream `#f6f0e8`, ink `#1f1d18`, gold `#967950`/`#ae9062`/`#c7a775`, link `#7d6440`),
  Cormorant Garamond + Jost, sparkle and gold-rule motifs; chart colour `#b08436`
- Internal names unchanged on purpose: database `cutencandy`, DB user `candy`, project folder
