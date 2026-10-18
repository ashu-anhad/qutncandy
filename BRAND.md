# QutnCandy brand & style guide

**QutnCandy** · Wear your confidence · Handcrafted Lucknowi chikankari in pure cotton · qutncandy.com / qutncandy.in

Everything here is derived from the logo (`brand/qutncandy-logo-original.png`, 1254×1254). Colours were sampled from it;
tokens live at the top of `frontend/src/index.css`. Use tokens, never raw hex values, in components.

## Logo

| Asset | File | Use |
|---|---|---|
| Full logo (monogram + wordmark + rule + tagline), transparent | `frontend/public/brand/logo-full.png` (1026×804) | Home hero (desktop), large brand moments |
| QC monogram, transparent | `frontend/public/brand/mark.png` (512×512, sharp on Retina) | Header (40px), admin sidebar (32px), login card (64px), footer (56px) |
| App icons (monogram on cream) | `favicon-32.png`, `apple-touch-icon.png` (180), `brand/icon-512.png` | Browser tab, phone home screen |
| Original | `brand/qutncandy-logo-original.png` | Source; regenerate assets from this |

Rules:
- Place the logo on **light grounds only** (`--bg`, `--surface`, white). Its ink parts disappear on dark backgrounds.
  A light/reversed version is needed before using it on dark or photographic backgrounds.
- Keep clear space of at least the height of the "Q" bowl's stroke on all sides; never stretch (always `height: auto`).
- In text, write the name **QutnCandy** (one word, capital Q and C). The spaced capital form `QUTNCANDY`, with the
  **A in gold**, is only for the wordmark (`<Wordmark />` in `components/Brand.jsx`).

## Colour

| Token | Hex | Role | Contrast on cream |
|---|---|---|---|
| `--bg` | `#f6f0e8` | Page background (the logo's ground) | — |
| `--surface` | `#fffcf7` | Cards, header, inputs | — |
| `--text` / `--accent` | `#1f1d18` | Text, primary buttons, selected chips (the logo's ink) | 14.9 : 1 |
| `--muted` | `#6b6257` | Secondary text | 5.3 : 1 |
| `--link` | `#7d6440` | Text links (logo gold, deepened for reading) | 4.9 : 1 |
| `--gold` | `#967950` | Icons, stars, progress, active indicators, focus ring (logo gold, dark end) | 3.6 : 1 |
| `--gold-mid` | `#ae9062` | Decoration only (logo gold, mid) | 2.7 : 1 |
| `--gold-light` | `#c7a775` | Decoration only: hairlines, sparkles (logo gold, light end) | 2.0 : 1 |
| `--gold-gradient` | `#c7a775 → #ae9062 → #967950` | Decorative fills echoing the gold "C" | — |
| `--gold-soft` | `#f0e6d6` | Selected / active backgrounds (menu item, chosen address, unread notification) | — |
| `--border` | `#e6dccd` | Hairline borders | — |

Status colours are **only** for meaning, never decoration, and always paired with a word:
`--ok #3d7a50` (in stock, paid, delivered) · `--warn #8f5a0a` (low stock, awaiting payment) · `--danger #a8322a`
(out of stock, cancelled, errors), each with a light `-bg` and `-border` tint.

Rules:
- **Text is ink, muted or `--link`.** Never set text in `--gold-mid` / `--gold-light` (unreadable on cream).
- Gold is the accent, not the main colour: buttons stay ink; gold marks what's active, selected or special.
- Charts use `--chart-bar #b08436`: the logo's softer golds read as grey in a chart and fail the chart-colour
  checks, so data marks use this slightly richer gold. Text in charts stays ink/muted.

## Typography

| Use | Font | Notes |
|---|---|---|
| Wordmark, page titles (`h1`), category tiles, stat numbers | **Cormorant Garamond** 500/600 | Echoes the logo's high-contrast roman capitals. Lining numerals forced (default old-style "0" looks like "o") |
| Body, UI, buttons, `h2`/`h3` | **Jost** 400/500/600 | Geometric sans, close to the logo's tagline lettering |
| Eyebrows / tagline | Jost, uppercase, letter-spacing 0.2–0.32em | e.g. "WEAR YOUR CONFIDENCE" |

Both load from Google Fonts in `frontend/index.html`, with system fallbacks.

## Motifs

- **Sparkle**: the logo's four-point star (`<Sparkle />`). Small, gold, used sparingly as an accent.
- **Gold rule with sparkle**: hairline–sparkle–hairline, as under the logo's wordmark (`<RuleSpark />`). Use under a
  hero headline or as a footer divider; at most one per screen section.
- Generous whitespace, thin 1px borders, 10px corner radius, no heavy shadows.

## Components (quick reference)

- **Primary button**: ink fill, cream text; hover `--accent-hover`. One per view where possible.
- **Secondary button**: transparent, ink border and text; hover `--gold-soft`.
- **Links**: `--link`, underline on hover.
- **Focus**: 2px `--gold` outline, offset 2px, on every interactive element.
- **Pills**: status colour text + matching border + tint (e.g. Paid = ok).
- **Notices**: `notice` (warn tint) for things needing action; `notice-ok` (ok tint) for confirmations.
- **Selected state**: `--gold` border + `--gold-soft` background.

## Voice

Warm, confident, crafted. Short sentences; speak to the customer ("Your order is on its way").
Name the craft properly: chikankari, bakhiya, phanda, jaali, mul cotton. Prices in ₹ with Indian grouping (₹1,890).
