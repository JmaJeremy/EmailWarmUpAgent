"""
NeuroGenix WarmUp — FastAPI Main Application
"""
import os
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import create_tables, SessionLocal
from config import settings
from services.scheduler import start_scheduler, stop_scheduler
from routers import auth, companies, mailboxes, warmup, dashboard, external_contacts, access_requests
from routers import oauth_mailbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def seed_super_admin():
    """Create Neurogenix super admin company + user on first run."""
    from models.company import Company, CompanyStatus
    from models.user import User, UserRole
    from auth.jwt_handler import hash_password

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.super_admin_email).first()
        if existing:
            # Force sync the password in case it was changed in Railway ENV
            existing.password_hash = hash_password(settings.super_admin_password)
            db.commit()
            logger.info(f"✅ Super admin already exists. Password synchronized! (active={existing.is_active})")
            return  # Already seeded

        company = db.query(Company).filter(Company.slug == "neurogenix").first()
        if not company:
            company = Company(
                id=str(uuid.uuid4()),
                name="Neurogenix",
                slug="neurogenix",
                status=CompanyStatus.approved,
                accent_color="#F97316",
                is_neurogenix=True,
            )
            db.add(company)
            db.flush()
            logger.info("🏢 Created Neurogenix company")
        else:
            logger.info(f"🏢 Using existing company: {company.name}")

        user = User(
            id=str(uuid.uuid4()),
            company_id=company.id,
            email=settings.super_admin_email,
            full_name="Neurogenix Admin",
            password_hash=hash_password(settings.super_admin_password),
            role=UserRole.super_admin,
            is_active=True,
        )
        db.add(user)
        db.commit()
        logger.info(f"✅ Super admin created: {settings.super_admin_email}")
    except Exception as e:
        logger.error(f"❌ Seed error: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def run_db_migrations():
    """Safely add new columns to existing tables (PostgreSQL ALTER TABLE IF NOT EXISTS)."""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        migrations = [
            "ALTER TABLE mailboxes ADD COLUMN IF NOT EXISTS auth_type VARCHAR(32) DEFAULT 'smtp'",
            "ALTER TABLE mailboxes ADD COLUMN IF NOT EXISTS oauth_refresh_token_enc TEXT",
        ]
        for sql in migrations:
            db.execute(text(sql))
        db.commit()
        logger.info("✅ DB migrations applied")
    except Exception as e:
        logger.warning(f"⚠️ Migration note (may be harmless): {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup + shutdown lifecycle."""
    logger.info("🚀 NeuroGenix WarmUp starting up...")
    # Create tables
    create_tables()
    logger.info("✅ Database tables ready")
    # Run safe column migrations
    run_db_migrations()
    # Seed super admin
    seed_super_admin()
    # Start scheduler
    start_scheduler()
    # Ensure upload dir exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    yield  # App runs here

    logger.info("🔴 Shutting down...")
    stop_scheduler()



app = FastAPI(
    title="NeuroGenix WarmUp API",
    description="Multi-tenant SaaS Email Warmup Platform by Neurogenix",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
_cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://localhost:5173",
]
# Add production frontend URL from env if set
if settings.frontend_url and settings.frontend_url != "http://localhost:5173":
    _cors_origins.append(settings.frontend_url)
# Allow all Railway subdomains in production
_cors_origins.append("https://emailwarmupagent-production.up.railway.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.up\.railway\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded logos) ────────────────────────────────────────────
os.makedirs("uploads/logos", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(mailboxes.router)
app.include_router(warmup.router)
app.include_router(dashboard.router)
app.include_router(external_contacts.router)
app.include_router(access_requests.router)
app.include_router(oauth_mailbox.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": "NeuroGenix WarmUp API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
