"""
Auth Router — Login, Register, Me
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
from models.user import User, UserRole
from models.company import Company, CompanyStatus
from auth.jwt_handler import hash_password, verify_password, create_access_token
from dependencies import get_current_user
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ─────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    company_name: str
    email: EmailStr
    password: str
    full_name: str | None = None
    website: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    company: dict


# ── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new company + admin user.
    Company starts as 'pending' — Neurogenix super admin must approve.
    """
    # Check email uniqueness
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate URL-safe slug from company name
    slug = payload.company_name.lower().replace(" ", "-").replace("_", "-")
    slug_base = slug
    counter = 1
    while db.query(Company).filter(Company.slug == slug).first():
        slug = f"{slug_base}-{counter}"
        counter += 1

    # Create company (pending approval)
    company = Company(
        id=str(uuid.uuid4()),
        name=payload.company_name,
        slug=slug,
        website=payload.website,
        status=CompanyStatus.pending,
    )
    db.add(company)
    db.flush()

    # Create admin user
    user = User(
        id=str(uuid.uuid4()),
        company_id=company.id,
        email=payload.email,
        full_name=payload.full_name or payload.email.split("@")[0],
        password_hash=hash_password(payload.password),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()

    return {
        "message": "Registration successful. Your account is pending approval by Neurogenix.",
        "company_id": company.id,
        "status": "pending",
    }


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with email + password. Returns JWT access token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    company = db.query(Company).filter(Company.id == user.company_id).first()

    # Pending companies can't log in (except super admins)
    if company.status == CompanyStatus.pending and user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=403,
            detail="Your company is pending approval. Contact Neurogenix support.",
        )

    if company.status == CompanyStatus.suspended:
        raise HTTPException(status_code=403, detail="Company account suspended")

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role, "company_id": user.company_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "accent_color": company.accent_color,
            "logo_url": company.logo_url,
            "status": company.status,
            "is_neurogenix": company.is_neurogenix,
        },
    }


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current authenticated user + company info."""
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "last_login": current_user.last_login,
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "accent_color": company.accent_color,
            "logo_url": company.logo_url,
            "status": company.status,
            "is_neurogenix": company.is_neurogenix,
        } if company else None,
    }


# ── Google OAuth Login ────────────────────────────────────────────────────────
class GoogleLoginRequest(BaseModel):
    credential: str  # The ID token from Google Sign-In

@router.post("/google")
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Verify a Google ID token (from Google Sign-In button) and return a JWT session.
    Only works if the email already has an account in the platform.
    """
    from config import settings

    if not settings.google_client_id:
        raise HTTPException(
            status_code=501,
            detail="Google login is not configured yet. Set GOOGLE_CLIENT_ID in .env"
        )

    # Verify the Google token
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    email = idinfo.get("email", "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="Could not get email from Google token")

    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=403,
            detail=f"No account found for {email}. Request access from the login page."
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    company = db.query(Company).filter(Company.id == user.company_id).first()
    if company.status == CompanyStatus.pending and user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Company pending approval")
    if company.status == CompanyStatus.suspended:
        raise HTTPException(status_code=403, detail="Company account suspended")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role, "company_id": user.company_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":        user.id,
            "email":     user.email,
            "full_name": user.full_name,
            "role":      user.role,
        },
        "company": {
            "id":           company.id,
            "name":         company.name,
            "slug":         company.slug,
            "accent_color": company.accent_color,
            "logo_url":     company.logo_url,
            "status":       company.status,
            "is_neurogenix": company.is_neurogenix,
        },
    }
