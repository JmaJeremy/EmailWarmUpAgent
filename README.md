# NeuroGenix WarmUp — SaaS Email Warmup Platform

> **Powered by Neurogenix** | Multi-tenant email warmup SaaS

---

## How the Warmup Engine Works

```
📬 SEND PHASE
Each active mailbox sends N warmup emails/day to other mailboxes in the pool.
Volume increases each week: Week 1→3/day, Week 8→60/day.

📖 OPEN PHASE  
Each recipient mailbox checks INBOX via IMAP, finds warmup emails,
marks them READ + STARRED (signals trust to Gmail/Outlook).

↩️ REPLY PHASE
~70% of opened emails get a real SMTP reply.
2-way conversations = strongest domain trust signal.

📊 SCORE
Score = (Open Rate × 40%) + (Reply Rate × 40%) + (Week Progress × 20%)
Score ≥ 80 = mailbox ready for cold outreach ✅
```

### 8-Week Ramp Schedule
| Week | Emails/Day | Target Open Rate |
|------|-----------|-----------------|
| 1    | 3         | 80%             |
| 2    | 6         | 75%             |
| 3    | 12        | 70%             |
| 4    | 20        | 65%             |
| 5    | 30        | 60%             |
| 6    | 40        | 55%             |
| 7    | 50        | 50%             |
| 8    | 60        | 45%             |

---

## Local Setup (Windows)

### 1. Backend

```powershell
cd "Email Warm Up Agent\backend"

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

**First run automatically:**
- Creates `neurogenix_warmup.db` (SQLite)
- Creates Neurogenix super admin account
- Starts daily warmup scheduler

**Super Admin Login:**
- Email: `admin@neurogenix.ai`
- Password: `Neurogenix@2025!`

API docs: http://localhost:8000/docs

---

### 2. Frontend

```powershell
cd "Email Warm Up Agent\frontend"

npm install
npm run dev
```

Frontend: http://localhost:5173

---

## Project Structure

```
Email Warm Up Agent/
├── backend/
│   ├── main.py              ← FastAPI app + startup seed
│   ├── database.py          ← SQLAlchemy (SQLite local / PostgreSQL Railway)
│   ├── config.py            ← All settings via .env
│   ├── dependencies.py      ← JWT auth middleware
│   ├── models/
│   │   ├── company.py       ← Multi-tenant companies
│   │   ├── user.py          ← Users with roles
│   │   ├── mailbox.py       ← SMTP/IMAP + warmup state
│   │   └── warmup_log.py    ← Daily activity logs
│   ├── auth/
│   │   └── jwt_handler.py   ← JWT + bcrypt
│   ├── services/
│   │   ├── warmup_engine.py ← Core 3-phase warmup logic
│   │   ├── email_service.py ← SMTP send + IMAP open/reply
│   │   ├── scheduler.py     ← APScheduler (daily 9am UTC)
│   │   └── encryption.py    ← Fernet encryption for passwords
│   └── routers/
│       ├── auth.py          ← Login, register, me
│       ├── companies.py     ← Super admin company management
│       ├── mailboxes.py     ← CRUD + start/pause warmup
│       ├── warmup.py        ← Trigger cycles, get logs
│       └── dashboard.py     ← Stats + analytics
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── Login.jsx        ← Premium split login
        │   ├── Dashboard.jsx    ← Stats + 30-day charts
        │   ├── Mailboxes.jsx    ← Manage mailboxes
        │   ├── WarmupStats.jsx  ← Per-mailbox analytics
        │   ├── SuperAdmin.jsx   ← Neurogenix admin panel
        │   └── Settings.jsx     ← Logo upload + brand color
        ├── components/
        │   └── Layout.jsx       ← Sidebar + navbar
        ├── contexts/
        │   └── AuthContext.jsx  ← JWT auth state
        └── api/
            └── client.js        ← Axios + all API calls
```

---

## Access Control

| Role         | What They Can Do                         |
|--------------|------------------------------------------|
| super_admin  | See ALL companies, approve/suspend, full access |
| admin        | Manage their company's mailboxes + run warmup |
| viewer       | Read-only view of their company's data   |

---

## Deploying to Railway

1. Push code to GitHub
2. Create Railway project → link GitHub repo
3. Add environment variables:
   ```
   DATABASE_URL=postgresql://...  (Railway provides this)
   JWT_SECRET_KEY=your-secret
   SUPER_ADMIN_EMAIL=admin@neurogenix.ai
   SUPER_ADMIN_PASSWORD=StrongPassword!
   ENCRYPTION_KEY=your-32-char-key
   ```
4. Railway auto-detects FastAPI and deploys ✅
5. Change `FRONTEND_URL` in backend env to Railway frontend URL

---

## Gmail / Google Workspace Setup

Enable 2FA, then create an **App Password**:
1. Google Account → Security → 2-Step Verification → App passwords
2. Select "Mail" → "Windows Computer"
3. Use the 16-char app password as your SMTP/IMAP password

SMTP: `smtp.gmail.com:587` (TLS)  
IMAP: `imap.gmail.com:993` (SSL)

---

*© 2025 Neurogenix — AI-Powered Growth Infrastructure*
