"""
Access Requests Router — Handles public "Request Access" form submissions.
Anyone can submit. Super Admin reviews and approves in the admin panel.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from database import SessionLocal
from models.access_request import AccessRequest
from models.company import Company, CompanyStatus
from models.user import User, UserRole
from auth.jwt_handler import hash_password
from dependencies import get_current_user, require_super_admin
import uuid, re

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Input / Output schemas ────────────────────────────────────────────────────
class AccessRequestCreate(BaseModel):
    full_name:    str
    email:        EmailStr
    company_name: str
    phone:        Optional[str] = None
    message:      Optional[str] = None


class AccessRequestOut(BaseModel):
    id:           str
    full_name:    str
    email:        str
    company_name: str
    phone:        Optional[str]
    message:      Optional[str]
    is_reviewed:  bool
    is_approved:  bool
    created_at:   datetime

    class Config:
        from_attributes = True


# ── Public: submit a request (no auth needed) ─────────────────────────────────
@router.post("/submit", response_model=AccessRequestOut, status_code=201)
def submit_access_request(data: AccessRequestCreate, db: Session = Depends(get_db)):
    """
    Public endpoint — called by the 'Request Access' form on the login page.
    Stores the request for Super Admin to review.
    """
    # Prevent spam: one request per email
    existing = db.query(AccessRequest).filter(AccessRequest.email == str(data.email)).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="We already have a request from this email. Our team will be in touch soon!"
        )

    req = AccessRequest(
        full_name    = data.full_name,
        email        = str(data.email),
        company_name = data.company_name,
        phone        = data.phone,
        message      = data.message,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


# ── Super Admin: list all requests ───────────────────────────────────────────
@router.get("", response_model=List[AccessRequestOut])
def list_access_requests(
    db: Session = Depends(get_db),
    current_user=Depends(require_super_admin),
):
    return (
        db.query(AccessRequest)
        .order_by(AccessRequest.created_at.desc())
        .all()
    )


# ── Super Admin: approve a request (auto-creates Company + User) ─────────────
@router.post("/{request_id}/approve")
def approve_access_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_super_admin),
):
    """
    Approve a request. This automatically:
    1. Creates a new Company for them
    2. Creates their admin User account
    3. Sends them their credentials (TODO: email integration)
    """
    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # If already approved, only block if the company + user actually exist
    if req.is_approved:
        existing_user = db.query(User).filter(User.email == req.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Already approved — company and user already exist")

    # Generate a unique slug from company name
    base_slug = re.sub(r"[^a-z0-9]", "-", req.company_name.lower()).strip("-")
    slug = base_slug
    counter = 1
    while db.query(Company).filter(Company.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create Company
    company = Company(
        id     = str(uuid.uuid4()),
        name   = req.company_name,
        slug   = slug,
        status = CompanyStatus.approved,
    )
    db.add(company)
    db.flush()

    # Generate a temporary password
    temp_password = f"WarmUp@{req.company_name[:4].capitalize()}{str(uuid.uuid4())[:4].upper()}"

    # Create User
    user = User(
        id            = str(uuid.uuid4()),
        company_id    = company.id,
        email         = req.email,
        full_name     = req.full_name,
        password_hash = hash_password(temp_password),
        role          = UserRole.admin,
    )
    db.add(user)

    # Mark request as approved
    req.is_approved  = True
    req.is_reviewed  = True
    req.reviewed_at  = datetime.utcnow()

    db.commit()

    return {
        "status":        "approved",
        "company_id":    company.id,
        "user_id":       user.id,
        "email":         user.email,
        "temp_password": temp_password,
        "note":          "Share these credentials with the client securely",
    }


# ── Super Admin: mark as reviewed (without approving) ────────────────────────
@router.post("/{request_id}/dismiss")
def dismiss_access_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_super_admin),
):
    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.is_reviewed = True
    req.reviewed_at = datetime.utcnow()
    db.commit()
    return {"status": "dismissed"}
