# Email WarmUp Agent

A production-grade, multi-tenant SaaS platform that warms up email mailboxes (Gmail, Google Workspace, Microsoft 365 / Exchange Online, Purelymail, and any SMTP/IMAP provider) so that cold outreach emails land in the inbox instead of the spam folder.

The platform automates the same behavior a human would perform if they had to manually build sender reputation: send a small, steadily increasing volume of emails between trusted mailboxes, open them, reply to them, rescue any that hit spam, and track every signal that mail providers (Gmail, Outlook) use to score the sender.

---

## Table of Contents

1. [Business Use Case](#1-business-use-case)
2. [Product Features](#2-product-features)
3. [System Architecture](#3-system-architecture)
4. [How the WarmUp Engine Works](#4-how-the-warmup-engine-works)
5. [Tech Stack](#5-tech-stack)
6. [Project Structure](#6-project-structure)
7. [Setup — Docker or Local](#7-setup)
8. [Environment Variables](#8-environment-variables)
9. [Mailbox Providers](#9-mailbox-providers)
10. [Deployment (Docker / Railway)](#10-deployment)
11. [Access Control & Roles](#11-access-control--roles)
12. [API Reference](#12-api-reference)
13. [Database Schema](#13-database-schema)
14. [Operations & Troubleshooting](#14-operations--troubleshooting)

---

## 1. Business Use Case

### The Problem

Cold email is one of the highest-ROI outbound channels for B2B sales, recruiting, and partnerships — but it only works if the email actually reaches the prospect's inbox. Brand-new mailboxes and freshly purchased domains have zero sending reputation. The moment a new mailbox starts sending 50–100 cold emails a day, Gmail and Outlook flag it as a spammer and route everything to the spam folder. Reputation, once burned, takes weeks to recover.

The industry workaround is **email warmup**: send a small, organic-looking volume of emails between trusted mailboxes, get those emails opened and replied to, and gradually scale up over 6–8 weeks. The result is a positive sending reputation by the time the mailbox is used for real outreach.

### Who This Is Built For

- **B2B sales teams** running cold-outreach campaigns at scale
- **Recruiting agencies** sourcing candidates over email
- **Founders and growth marketers** launching new domains
- **Agencies** managing dozens of client mailboxes across multiple tenants

### What This Platform Replaces

Off-the-shelf warmup services like Mailwarm, Lemwarm, Warmup Inbox and Instantly cost $20–$50 per mailbox per month, run on shared infrastructure, and give you zero control over the warmup pool, the templates, or the analytics. This platform is a **self-hosted alternative** that gives an organization full control over:

- Which mailboxes participate in the warmup pool (only your own mailboxes — no shared pool)
- How aggressive the daily ramp-up is
- The exact open / reply / spam-rescue logic
- Full per-mailbox analytics and history
- Multi-tenant isolation, so an agency can host warmup for many clients on one deployment

### Key Outcomes

- **Inbox placement rate above 95%** by the end of the 8-week ramp
- **Warmup score ≥ 80** signals the mailbox is ready for production cold outreach
- **Per-tenant isolation** so client A never sees client B's mailboxes or data
- **Zero external dependencies** on shared warmup pools — all activity is between mailboxes you control

---

## 2. Product Features

- **Multi-tenant SaaS** — companies, users, mailboxes, and warmup logs are isolated by `company_id`. A super-admin tier sees every tenant.
- **8-week progressive ramp** — automatic daily volume increase from 3 → 60 emails per day per mailbox.
- **Three-phase daily cycle** — SEND → OPEN → REPLY runs once per day per active mailbox.
- **Spam rescue** — recipients automatically pull warmup mail out of the Spam folder back into the Inbox, which is the strongest possible signal to Gmail/Outlook that the sender is trusted.
- **Three connection modes per mailbox:**
  - **SMTP + IMAP** with app passwords (Gmail, Purelymail, Fastmail, Zoho, iCloud, Yahoo, any standard provider)
  - **Microsoft 365** via Microsoft Graph + OAuth 2.0 (Exchange Online / Outlook — no SMTP AUTH or IMAP needed)
  - **Gmail API** via OAuth 2.0 (optional; for hosts that block outbound SMTP — e.g., Railway)
- **Automatic spam-folder detection** — uses the IMAP `\Junk` special-use flag, falling back to common names (`[Gmail]/Spam`, `Junk Email`, `Spam`, `INBOX.Junk`, …).
- **Signed warmup header** — every warmup email carries an HMAC-signed `X-Warmup-ID`; only those messages are ever opened, rescued or replied to, so real mail is never touched.
- **Encrypted credential storage** — Fernet symmetric encryption for SMTP passwords and OAuth refresh tokens at rest.
- **Real-time analytics** — per-mailbox health score, 30-day open/reply/spam-rescue charts, deliverability trend.
- **Brandable per tenant** — each company can upload its own logo and set an accent color used across the dashboard.
- **External-contact reply mode** — once a mailbox passes warmup, real prospect contacts can be added and the engine will reply only to genuine inbound mail (turning the warmup engine into a low-touch auto-responder).
- **JWT auth** with bcrypt-hashed passwords and role-based access control.

---

## 3. System Architecture

```
                            ┌──────────────────────────────┐
                            │      Browser (React SPA)     │
                            │   Vite + Tailwind + Recharts │
                            └──────────────┬───────────────┘
                                           │  HTTPS / JSON
                                           │  Bearer JWT
                                           ▼
                            ┌──────────────────────────────┐
                            │     FastAPI Application      │
                            │  ┌────────────────────────┐  │
                            │  │  Routers (REST API)    │  │
                            │  │  auth · companies ·    │  │
                            │  │  mailboxes · warmup ·  │  │
                            │  │  dashboard · oauth     │  │
                            │  └───────────┬────────────┘  │
                            │              │               │
                            │  ┌───────────▼────────────┐  │
                            │  │   Service Layer        │  │
                            │  │  warmup_engine.py      │  │
                            │  │  email_service.py      │  │
                            │  │  scheduler.py          │  │
                            │  │  encryption.py         │  │
                            │  └───────────┬────────────┘  │
                            └──────────────┼───────────────┘
                                           │
                ┌──────────────────────────┼──────────────────────────┐
                │                          │                          │
                ▼                          ▼                          ▼
   ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
   │   PostgreSQL         │  │   APScheduler        │  │   Mail Providers     │
   │   (Railway prod)     │  │   Daily 09:00 UTC    │  │   Gmail · Outlook    │
   │   SQLite (local)     │  │   warmup cycle tick  │  │   SMTP / IMAP        │
   │                      │  │                      │  │   Gmail API (OAuth)  │
   │   SQLAlchemy ORM     │  └──────────────────────┘  └──────────────────────┘
   └──────────────────────┘
```

### Request Flow — A Daily Warmup Cycle

1. **09:00 UTC** — APScheduler fires `run_daily_warmup()` in `services/scheduler.py`.
2. The warmup engine in `services/warmup_engine.py` selects every mailbox with `status = "active"` and groups them by `company_id` (the warmup pool is intra-tenant, never cross-tenant).
3. For each mailbox, the engine computes today's send target from the 8-week ramp table, picks recipients from the same pool, and submits **SEND** tasks to `services/email_service.py`.
4. `email_service.py` chooses the transport based on `mailbox.auth_type`:
   - `smtp` → SMTP send + IMAP read (any host)
   - `microsoft_graph` → Microsoft Graph for send + read (`services/microsoft_graph.py`)
   - `gmail_api` → Gmail REST API send + IMAP (XOAUTH2) read, using the stored OAuth refresh token
5. After all sends complete, the engine enters the **OPEN** phase: each recipient mailbox finds unread warmup messages by their signed `X-Warmup-ID` header (headers are fetched with `BODY.PEEK`, so real mail stays unread), marks them as read and flagged, and — critically — if the message landed in the spam/junk folder, moves it back to `INBOX`.
6. Roughly 70% of opened messages get a **REPLY** sent back to the original sender. Two-way conversation is the single strongest deliverability signal.
7. Every send, open, spam-rescue, and reply is written to the `warmup_logs` table, which powers the analytics endpoints.

---

## 4. How the WarmUp Engine Works

```
📬 SEND PHASE
Each active mailbox sends N warmup emails per day to other mailboxes
in the same company's pool. Volume increases each week
(Week 1 → 3/day, Week 8 → 60/day).

📖 OPEN PHASE
Each recipient mailbox checks INBOX (and Spam) via IMAP or Gmail API,
finds warmup emails by their X-Warmup-ID header, marks them READ
and STARRED. Any email that hit Spam is moved back to INBOX —
this is the single most powerful trust signal to Gmail/Outlook.

↩️ REPLY PHASE
~70% of opened emails get a real reply sent back to the original
sender. Two-way conversations dramatically outperform one-way
opens for reputation building.

📊 SCORE
score = (open_rate × 0.40)
      + (reply_rate × 0.40)
      + (week_progress × 0.20)
score ≥ 80 → mailbox is ready for production cold outreach
```

### 8-Week Ramp Schedule

| Week | Emails / Day | Target Open Rate |
|------|--------------|------------------|
| 1    | 3            | 80%              |
| 2    | 6            | 75%              |
| 3    | 12           | 70%              |
| 4    | 20           | 65%              |
| 5    | 30           | 60%              |
| 6    | 40           | 55%              |
| 7    | 50           | 50%              |
| 8    | 60           | 45%              |

---

## 5. Tech Stack

**Backend**
- Python 3.11+, FastAPI, Uvicorn
- SQLAlchemy 2.x ORM, lightweight in-app DDL migrations
- PostgreSQL (production) / SQLite (local dev)
- APScheduler for the daily warmup tick
- `aiosmtplib`, `aioimaplib`, `httpx` for mail I/O
- `python-jose`, `passlib[bcrypt]` for auth
- `cryptography` (Fernet) for at-rest credential encryption
- `google-api-python-client`, `google-auth-oauthlib` for Gmail API + OAuth 2.0

**Frontend**
- React 18, Vite 5
- TailwindCSS 3, Lucide icons
- React Router 6, Axios
- Recharts for analytics
- `@react-oauth/google` for the Connect-with-Google flow

**Infrastructure**
- Docker Compose (Postgres + backend + nginx-served frontend) for self-hosting
- Railway also supported for managed Postgres + service hosting
- No special CI required — any GitHub-connected runner works

---

## 6. Project Structure

```
Email Warm Up Agent/
├── README.md
├── .gitignore
├── docker-compose.yml             Postgres + backend + frontend
├── .env.docker.example            Template for the Docker .env
│
├── backend/
│   ├── main.py                    FastAPI app, startup lifecycle, seed + migrations
│   ├── config.py                  Pydantic settings loaded from .env
│   ├── database.py                SQLAlchemy engine (SQLite local / Postgres prod)
│   ├── dependencies.py            JWT auth dependency, role guards
│   ├── requirements.txt
│   │
│   ├── auth/
│   │   └── jwt_handler.py         JWT encode/decode + bcrypt hashing
│   │
│   ├── models/
│   │   ├── company.py             Multi-tenant companies
│   │   ├── user.py                Users with role enum (super_admin / admin / viewer)
│   │   ├── mailbox.py             SMTP/IMAP creds + warmup state + auth_type
│   │   ├── warmup_log.py          Per-day per-mailbox activity log
│   │   ├── access_request.py     New-tenant signup approval queue
│   │   └── external_contact.py    Real prospect contacts (post-warmup auto-reply)
│   │
│   ├── services/
│   │   ├── warmup_engine.py       The three-phase daily warmup logic
│   │   ├── email_service.py       SMTP/IMAP, Gmail API and Graph transport layer
│   │   ├── microsoft_graph.py     Microsoft 365 OAuth + Graph mail operations
│   │   ├── scheduler.py           APScheduler (daily 09:00 UTC tick)
│   │   └── encryption.py          Fernet at-rest encryption for credentials
│   │
│   └── routers/
│       ├── auth.py                /auth/login, /auth/register, /auth/me
│       ├── companies.py           Super-admin: list/approve/suspend tenants
│       ├── mailboxes.py           CRUD + start/pause warmup per mailbox
│       ├── oauth_mailbox.py       Google OAuth callback + Gmail API mailbox connect
│       ├── warmup.py              Manual trigger + per-mailbox log retrieval
│       ├── dashboard.py           Stats + 30-day analytics
│       ├── external_contacts.py   Real-prospect contact list management
│       └── access_requests.py     New tenant signup review
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx                Router + protected routes
        ├── index.css              Tailwind layers
        ├── contexts/
        │   └── AuthContext.jsx    JWT state, login, logout
        ├── api/
        │   └── client.js          Axios instance + every REST call
        ├── components/
        │   └── Layout.jsx         Sidebar, navbar, brand color
        └── pages/
            ├── Login.jsx          Premium split login + signup request
            ├── Dashboard.jsx      KPIs + 30-day deliverability charts
            ├── Mailboxes.jsx      Add / pause / resume mailboxes
            ├── WarmupStats.jsx    Per-mailbox health score and history
            ├── SuperAdmin.jsx     Cross-tenant control panel
            └── Settings.jsx       Logo upload + accent color
```

---

## 7. Setup

### 7.1 Docker (recommended)

Requires Docker with the Compose plugin. Runs Postgres, the backend and the frontend (nginx) as three containers.

```bash
git clone https://github.com/PJDEEPESH/EmailWarmUpAgent.git
cd EmailWarmUpAgent
cp .env.docker.example .env      # fill in the secrets (openssl rand -base64 48)
docker compose up -d --build
```

Open **http://localhost:8080** (or whatever `PUBLIC_URL` / `HTTP_PORT` you set) and log in with `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD`.

- nginx serves the React build and proxies `/api/*` to the backend, so everything is one origin (no CORS setup).
- Postgres data lives in the `db-data` volume and uploaded logos in `uploads` — both survive `docker compose down` / rebuilds (but not `down -v`).
- Compose refuses to start until the required secrets are set, so the insecure defaults in `config.py` are never used.
- **Run one backend container only.** The warmup scheduler runs in-process; a second replica would send duplicate emails.
- Logs: `docker compose logs -f backend`. Upgrade: `git pull && docker compose up -d --build`.

For HTTPS, put any reverse proxy (Caddy, Traefik, nginx, Cloudflare Tunnel) in front of port 8080 and set `PUBLIC_URL` to the https address. HTTPS is required for Microsoft 365 sign-in unless you browse via `http://localhost`.

### 7.2 Local development (without Docker)

Prerequisites: Python **3.11+**, Node.js **18+**, Git.

#### Backend

```powershell
# Windows PowerShell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env       # then fill in the values (see §8)
uvicorn main:app --reload --port 8000
```

```bash
# macOS / Linux
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then fill in the values (see §8)
uvicorn main:app --reload --port 8000
```

On first run the backend will automatically:

- create the SQLite database `neurogenix_warmup.db`
- apply lightweight column migrations
- seed the super-admin company and user from `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD`
- start the APScheduler daily warmup job

Interactive API docs: **http://localhost:8000/docs**

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts at **http://localhost:5173** and calls the backend on `:8000`.

#### First Login

Log in with the super-admin credentials configured in `backend/.env`. Change `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` before running in any non-local environment — the seed step re-syncs the password into the database on every boot, so the env value is always authoritative.

---

## 8. Environment Variables

For Docker, everything goes in the root `.env` (template: `.env.docker.example`; `PUBLIC_URL` becomes `FRONTEND_URL`). For local development, the backend loads `backend/.env` (template: `backend/.env.example`).

| Variable                | Required                | Example                                                 | Notes                                                                                                                          |
| ----------------------- | ----------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `DATABASE_URL`          | yes                     | `sqlite:///./neurogenix_warmup.db` or `postgresql://…`  | Railway injects this automatically in production.                                                                              |
| `JWT_SECRET_KEY`        | yes                     | random 64-char string                                   | Used to sign access tokens. Rotate to invalidate all sessions.                                                                 |
| `ENCRYPTION_KEY`        | yes                     | 32-byte url-safe base64 (Fernet)                        | Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`                      |
| `SUPER_ADMIN_EMAIL`     | yes                     | `admin@yourbrand.com`                                   | Seeded on first boot.                                                                                                          |
| `SUPER_ADMIN_PASSWORD`  | yes                     | strong password                                         | Re-synced into the database on every boot, so changing it in env actually rotates the password.                                |
| `FRONTEND_URL`          | yes                     | `http://localhost:5173`                                 | Added to the CORS allow-list.                                                                                                  |
| `GOOGLE_CLIENT_ID`      | only for Gmail API mode | from Google Cloud Console                               | OAuth 2.0 web client.                                                                                                          |
| `GOOGLE_CLIENT_SECRET`  | only for Gmail API mode |                                                         | Keep secret.                                                                                                                   |
| `GOOGLE_REDIRECT_URI`   | only for Gmail API mode | `http://localhost:8000/oauth/google/callback`           | Must match the value registered in Google Cloud Console exactly.                                                               |
| `UPLOAD_DIR`            | optional                | `uploads/logos`                                         | Where tenant logos are stored.                                                                                                 |
| `MICROSOFT_TENANT_ID`   | only for Microsoft 365  | Directory (tenant) ID from Entra ID                     | See §9.2.                                                                                                                      |
| `MICROSOFT_CLIENT_ID`   | only for Microsoft 365  | Application (client) ID                                 |                                                                                                                                |
| `MICROSOFT_CLIENT_SECRET` | only for Microsoft 365 | client secret **value**                                | Expires (max 24 months) — renew it before then.                                                                                |
| `MICROSOFT_REDIRECT_URI` | optional               | `https://warmup.example.com/api/mailboxes/oauth/microsoft-callback` | Defaults to `{FRONTEND_URL}/api/mailboxes/oauth/microsoft-callback`.                                                 |

Frontend env (`frontend/.env`):

| Variable                | Example                  |
| ----------------------- | ------------------------ |
| `VITE_API_URL`          | `http://localhost:8000`  |
| `VITE_GOOGLE_CLIENT_ID` | same as backend `GOOGLE_CLIENT_ID` |

---

## 9. Mailbox Providers

| Provider | Connection type | Notes |
|---|---|---|
| Gmail / Google Workspace | SMTP + IMAP, **app password** | Preset available. Needs 2-Step Verification. |
| Microsoft 365 / Exchange Online / Outlook | **Microsoft 365** (Graph OAuth) | Password login for SMTP/IMAP is being retired by Microsoft — use this mode. |
| Purelymail | SMTP + IMAP | Preset available. |
| Fastmail, Zoho, iCloud, Yahoo | SMTP + IMAP, app password | Presets available. |
| Anything else | SMTP + IMAP | Enter host/port manually. Port 465 automatically switches to implicit TLS. |

Use **Test connection** (the Wi-Fi icon on a mailbox card) after adding a mailbox. For IMAP it also reports which spam folder was detected; if it says *no spam folder found*, spam rescue is disabled for that mailbox.

### 9.1 Gmail / Google Workspace — App Passwords

1. Enable 2-Step Verification on the Google account.
2. Visit **Google Account → Security → App passwords**.
3. Generate a new app password.
4. In the dashboard: **Add Mailbox → SMTP + IMAP → Gmail preset**, enter the address and the 16-character app password in both password fields.

Make sure IMAP is enabled (Gmail → Settings → Forwarding and POP/IMAP).

### 9.2 Microsoft 365 / Exchange Online

One-time setup by a tenant admin, in the **Microsoft Entra admin center**:

1. **App registrations → New registration**
   - Supported account types: **Accounts in this organizational directory only (single tenant)**
   - Redirect URI: platform **Web**, value `{PUBLIC_URL}/api/mailboxes/oauth/microsoft-callback` — e.g. `https://warmup.example.com/api/mailboxes/oauth/microsoft-callback`. Microsoft only accepts `https://` or `http://localhost`.
2. From the app's **Overview**, copy the **Application (client) ID** and **Directory (tenant) ID**.
3. **Certificates & secrets → New client secret** — copy the secret's **Value** (not the ID). Note the expiry date.
4. **API permissions → Add a permission → Microsoft Graph → Delegated permissions**: `offline_access`, `User.Read`, `Mail.ReadWrite`, `Mail.Send`. Then click **Grant admin consent for <your org>**.
5. Set `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` in `.env` and run `docker compose up -d`.

Adding a mailbox: **Add Mailbox → Microsoft 365 → Add & Connect**, then sign in **as that mailbox** (use a private window if your browser is signed in as someone else). The app checks the signed-in account matches the mailbox address. Sending, reading, flagging and moving out of **Junk Email** all go through Microsoft Graph, so SMTP AUTH and IMAP can stay disabled in the tenant.

If a mailbox's password changes or consent is revoked, open the card's details and click **Reconnect Microsoft account**.

### 9.3 Gmail API via OAuth (optional)

Only needed when the host blocks outbound SMTP (e.g. Railway). Create an OAuth 2.0 Web client in Google Cloud Console with redirect URI `{PUBLIC_URL}/api/mailboxes/oauth/google-callback` (Docker) and enable the Gmail API, then set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`. A **Connect with Google** button appears on Gmail mailboxes. The app requests the full `https://mail.google.com/` scope (sending via the Gmail API, reading via IMAP XOAUTH2), which Google classifies as restricted — fine for your own accounts in testing mode, but publishing the app requires Google verification.

---

## 10. Deployment

### Docker (any VPS or home server)

See §7.1 — the same `docker compose up -d --build` is the production deployment. Most VPS providers allow outbound SMTP on 587/465, so SMTP + IMAP mailboxes work directly; a few (and some residential ISPs) block it, in which case use Microsoft 365 / Gmail API modes or ask the provider to unblock it.

### Railway

The application also deploys on Railway with no Dockerfile required — Railway's Nixpacks builder detects FastAPI + Vite automatically.

1. **Push to GitHub** (this repo).
2. In Railway, **New Project → Deploy from GitHub repo** and pick this repository.
3. Add a **PostgreSQL** plugin. Railway injects `DATABASE_URL` automatically.
4. Set the following service variables (Settings → Variables):

   ```
   JWT_SECRET_KEY=<long random string>
   ENCRYPTION_KEY=<Fernet key, see §8>
   SUPER_ADMIN_EMAIL=admin@yourbrand.com
   SUPER_ADMIN_PASSWORD=<strong password>
   FRONTEND_URL=https://<your-frontend>.up.railway.app
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://<your-backend>.up.railway.app/oauth/google/callback
   ```

5. **Start command** — Railway picks this up automatically; if you set it manually:

   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

6. Deploy the **frontend** as a second Railway service (or any static host — Vercel, Netlify, Cloudflare Pages). Build command `npm run build`, output directory `dist`.

7. Update `FRONTEND_URL` and `GOOGLE_REDIRECT_URI` in the backend service to point to the deployed frontend, then redeploy.

**Note on outbound SMTP.** Railway blocks outbound port 587. Mailboxes connected via SMTP will fail to send in that environment — use the Gmail API connection mode (§9 option B) for production on Railway.

---

## 11. Access Control & Roles

| Role          | Capabilities                                                                       |
| ------------- | ---------------------------------------------------------------------------------- |
| `super_admin` | Cross-tenant. Approve / suspend companies, view every mailbox across the platform. |
| `admin`       | Manage their own company's mailboxes, run warmup, view analytics.                  |
| `viewer`      | Read-only view of their own company's dashboards and mailboxes.                    |

Every mailbox, warmup log, and external contact is scoped by `company_id`. The JWT carries `user_id`, `company_id`, and `role`; all queries are filtered by `company_id` in the router layer.

---

## 12. API Reference

The full OpenAPI 3 spec is served at **`/docs`** (Swagger UI) and **`/redoc`** (ReDoc) by the running backend. Key endpoint groups:

- `POST /auth/login` — exchange email + password for a JWT
- `GET  /auth/me` — current user + company
- `POST /access-requests` — public signup queue (super-admin approves)
- `GET  /companies` · `PATCH /companies/{id}` — super-admin tenant management
- `GET  /mailboxes` · `POST /mailboxes` · `PATCH /mailboxes/{id}` — CRUD
- `POST /mailboxes/{id}/start` · `POST /mailboxes/{id}/pause` — warmup state
- `GET  /mailboxes/oauth/microsoft-url` · `GET /mailboxes/oauth/microsoft-callback` — Microsoft 365 connect
- `GET  /mailboxes/oauth/google-url` · `GET /mailboxes/oauth/google-callback` — Gmail API connect
- `POST /warmup/trigger/{mailbox_id}` — manually run a cycle for one mailbox (admin only)
- `GET  /warmup/logs/{mailbox_id}` — daily history for analytics
- `GET  /dashboard/stats` — summary KPIs (today's sends, opens, replies, spam rescues)
- `GET  /dashboard/trend` — 30-day timeseries
- `POST /external-contacts` — add real prospects (post-warmup auto-reply mode)

---

## 13. Database Schema

Five primary tables, all keyed by UUID and scoped by `company_id` (except `companies` itself).

```
companies
  id · name · slug · status (pending|approved|suspended)
  accent_color · logo_url · is_neurogenix · created_at

users
  id · company_id → companies.id
  email · password_hash · full_name
  role (super_admin|admin|viewer) · is_active · created_at

mailboxes
  id · company_id → companies.id
  email · display_name · provider
  auth_type (smtp|gmail_api|microsoft_graph)
  smtp_host · smtp_port · smtp_username · smtp_password_enc
  imap_host · imap_port · imap_username
  oauth_refresh_token_enc
  status (active|paused|warmed_up)
  warmup_week · daily_target · warmup_score
  created_at · last_run_at

warmup_logs
  id · mailbox_id → mailboxes.id · company_id
  date · sent_count · opened_count · replied_count · spam_rescued_count
  inbox_placement_rate · created_at

external_contacts
  id · mailbox_id · email · notes · created_at

access_requests
  id · company_name · contact_email · status · created_at
```

---

## 14. Operations & Troubleshooting

**Daily cycle didn't run.** Check the backend logs around 09:00 UTC for `run_daily_warmup` lines. The scheduler logs every tick. If the process restarts mid-cycle, partial progress is committed per mailbox, so re-running by hand via `POST /warmup/trigger/{mailbox_id}` is safe.

**Mailbox stuck in "Connecting".** Almost always credentials. For SMTP this means the app password was revoked or 2FA was disabled. For Gmail API this means the refresh token was revoked from the Google account's third-party access page.

**Emails are going to spam and not being rescued.** Run **Test connection** on the recipient mailbox — the IMAP result names the spam folder it detected. If none was found, the provider uses an unusual folder name; add it to `JUNK_FOLDER_FALLBACKS` in `services/email_service.py`. Also confirm IMAP is enabled (Gmail → Settings → Forwarding and POP/IMAP). Gmail API mailboxes connected before the scope change must be reconnected.

**Outbound SMTP on Railway times out.** This is expected — Railway blocks port 587 outbound. Switch the affected mailbox to the Gmail API auth mode (§9.3), or self-host with Docker.

**Microsoft 365: "Connection failed: wrong_account".** You signed in as a different Microsoft account than the mailbox address. Retry in a private window.

**Microsoft 365: AADSTS50011 (redirect URI mismatch).** The redirect URI registered in Entra ID must exactly match `{PUBLIC_URL}/api/mailboxes/oauth/microsoft-callback`.

**Microsoft 365 mailboxes stop working after ~1–2 years.** The client secret expired. Create a new one in Entra ID and update `MICROSOFT_CLIENT_SECRET`.

**Resetting the super-admin password.** Update `SUPER_ADMIN_PASSWORD` in the deployment environment and restart the backend. The seed step on startup will re-hash and overwrite the existing password.

**Local Postgres instead of SQLite.** Set `DATABASE_URL=postgresql://user:pass@localhost:5432/warmup` in `backend/.env`. SQLAlchemy handles both transparently (plain `postgres://` / `postgresql://` URLs are pinned to the bundled psycopg2 driver).
