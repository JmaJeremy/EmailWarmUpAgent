"""
Companies Router — Super Admin: manage all companies + approve/reject
"""
import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.company import Company, CompanyStatus
from models.user import User, UserRole
from models.mailbox import Mailbox
from auth.jwt_handler import hash_password
from dependencies import require_super_admin, get_current_user
from config import settings

router = APIRouter(prefix="/companies", tags=["Companies"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    accent_color: Optional[str] = None
    website: Optional[str] = None
    status: Optional[CompanyStatus] = None


class CreateCompanyByAdmin(BaseModel):
    name: str
    email: str
    password: str
    full_name: Optional[str] = None
    accent_color: str = "#F97316"
    website: Optional[str] = None


# ── List all companies (super admin) ─────────────────────────────────────────
@router.get("/")
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    result = []
    for c in companies:
        mailbox_count = db.query(Mailbox).filter(Mailbox.company_id == c.id).count()
        user_count = db.query(User).filter(User.company_id == c.id).count()
        result.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "status": c.status,
            "accent_color": c.accent_color,
            "logo_url": c.logo_url,
            "website": c.website,
            "is_neurogenix": c.is_neurogenix,
            "mailbox_count": mailbox_count,
            "user_count": user_count,
            "created_at": c.created_at,
        })
    return result


# ── Approve company ──────────────────────────────────────────────────────────
@router.post("/{company_id}/approve")
def approve_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.status = CompanyStatus.approved
    db.commit()
    return {"message": f"Company '{company.name}' approved", "status": "approved"}


# ── Reject / Suspend company ─────────────────────────────────────────────────
@router.post("/{company_id}/suspend")
def suspend_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.is_neurogenix:
        raise HTTPException(status_code=400, detail="Cannot suspend Neurogenix company")
    company.status = CompanyStatus.suspended
    db.commit()
    return {"message": f"Company '{company.name}' suspended"}


# ── Create company directly (super admin creates client accounts) ─────────────
@router.post("/create", status_code=201)
def create_company(
    payload: CreateCompanyByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    slug = payload.name.lower().replace(" ", "-")
    slug_base = slug
    i = 1
    while db.query(Company).filter(Company.slug == slug).first():
        slug = f"{slug_base}-{i}"; i += 1

    company = Company(
        id=str(uuid.uuid4()),
        name=payload.name,
        slug=slug,
        accent_color=payload.accent_color,
        website=payload.website,
        status=CompanyStatus.approved,  # Super admin creates = auto-approved
    )
    db.add(company); db.flush()

    user = User(
        id=str(uuid.uuid4()),
        company_id=company.id,
        email=payload.email,
        full_name=payload.full_name or payload.name,
        password_hash=hash_password(payload.password),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    return {"message": "Company and admin user created", "company_id": company.id}


# ── Upload company logo ───────────────────────────────────────────────────────
@router.post("/{company_id}/logo")
async def upload_logo(
    company_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload logo for a company. Super admin can upload for any; admin for own company."""
    if current_user.role != UserRole.super_admin and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Validate file type
    allowed = ["image/jpeg", "image/png", "image/webp", "image/svg+xml"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP, or SVG allowed")

    # Save file
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = file.filename.split(".")[-1]
    filename = f"{company_id}.{ext}"
    file_path = os.path.join(settings.upload_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    company.logo_url = f"/uploads/logos/{filename}"
    db.commit()

    return {"logo_url": company.logo_url, "message": "Logo uploaded successfully"}


# ── Update company settings ───────────────────────────────────────────────────
@router.patch("/{company_id}")
def update_company(
    company_id: str,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.super_admin and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if payload.name: company.name = payload.name
    if payload.accent_color: company.accent_color = payload.accent_color
    if payload.website: company.website = payload.website
    if payload.status and current_user.role == UserRole.super_admin:
        company.status = payload.status

    db.commit()
    return {"message": "Company updated", "company": {"id": company.id, "name": company.name}}


# ── Get full client profile (Super Admin) ────────────────────────────────────
@router.get("/{company_id}/detail")
def get_company_detail(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Full company profile with mailboxes, users, warmup stats."""
    from models.mailbox import WarmupStatus
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    mailboxes = db.query(Mailbox).filter(Mailbox.company_id == company_id).all()
    users = db.query(User).filter(User.company_id == company_id).all()

    active_boxes  = [m for m in mailboxes if m.warmup_status == WarmupStatus.active]
    avg_score     = round(sum(m.warmup_score for m in mailboxes) / len(mailboxes), 1) if mailboxes else 0
    total_sent    = sum(m.total_sent for m in mailboxes)
    total_opened  = sum(m.total_opened for m in mailboxes)
    total_replied = sum(m.total_replied for m in mailboxes)

    return {
        "company": {
            "id":           company.id,
            "name":         company.name,
            "slug":         company.slug,
            "status":       company.status,
            "accent_color": company.accent_color,
            "logo_url":     company.logo_url,
            "website":      company.website,
            "is_neurogenix": company.is_neurogenix,
            "created_at":   company.created_at,
        },
        "stats": {
            "total_mailboxes":  len(mailboxes),
            "active_mailboxes": len(active_boxes),
            "avg_score":        avg_score,
            "total_sent":       total_sent,
            "total_opened":     total_opened,
            "total_replied":    total_replied,
        },
        "mailboxes": [
            {
                "id":             m.id,
                "email_address":  m.email_address,
                "display_name":   m.display_name,
                "warmup_status":  m.warmup_status,
                "current_week":   m.current_week,
                "daily_limit":    m.daily_limit,
                "warmup_score":   m.warmup_score,
                "total_sent":     m.total_sent,
                "total_opened":   m.total_opened,
                "total_replied":  m.total_replied,
                "last_warmup_at": m.last_warmup_at,
            }
            for m in mailboxes
        ],
        "users": [
            {
                "id":        u.id,
                "email":     u.email,
                "full_name": u.full_name,
                "role":      u.role,
                "is_active": u.is_active,
            }
            for u in users
        ],
    }


# ── Change client password (Super Admin) ─────────────────────────────────────
@router.post("/{company_id}/change-password")
def change_client_password(
    company_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Super Admin can reset any client admin user's password."""
    new_password = payload.get("new_password", "").strip()
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Find the admin user for this company
    user = (
        db.query(User)
        .filter(User.company_id == company_id, User.role == UserRole.admin)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="No admin user found for this company")

    user.password_hash = hash_password(new_password)
    db.commit()
    return {"message": f"Password updated for {user.email}"}

