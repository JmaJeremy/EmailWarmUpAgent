"""
Mailboxes Router — CRUD for mailboxes + connection testing
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from database import get_db
from models.mailbox import Mailbox, WarmupStatus
from models.user import User, UserRole
from services.encryption import encrypt_password, decrypt_password
from services.email_service import EmailService
from dependencies import get_current_user, require_admin

router = APIRouter(prefix="/mailboxes", tags=["Mailboxes"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class MailboxCreate(BaseModel):
    email_address: EmailStr
    display_name: Optional[str] = None
    # smtp (SMTP + IMAP credentials) | microsoft_graph (connect via Microsoft sign-in afterwards)
    auth_type: Literal["smtp", "microsoft_graph"] = "smtp"
    # SMTP
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    # IMAP
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: bool = True


class MailboxUpdate(BaseModel):
    display_name: Optional[str] = None
    warmup_status: Optional[WarmupStatus] = None
    smtp_password: Optional[str] = None
    imap_password: Optional[str] = None
    daily_limit: Optional[int] = None

def _mailbox_to_dict(m: Mailbox, include_creds: bool = False) -> dict:
    d = {
        "id": m.id,
        "company_id": m.company_id,
        "email_address": m.email_address,
        "display_name": m.display_name,
        "auth_type": getattr(m, "auth_type", "smtp") or "smtp",  # smtp | gmail_api | microsoft_graph
        "oauth_connected": bool(m.oauth_refresh_token_enc),
        "smtp_host": m.smtp_host,
        "smtp_port": m.smtp_port,
        "smtp_user": m.smtp_user,
        "smtp_use_tls": m.smtp_use_tls,
        "imap_host": m.imap_host,
        "imap_port": m.imap_port,
        "imap_user": m.imap_user,
        "imap_use_ssl": m.imap_use_ssl,
        "warmup_status": m.warmup_status,
        "current_week": m.current_week,
        "daily_limit": m.daily_limit,
        "total_sent": m.total_sent,
        "total_opened": m.total_opened,
        "total_replied": m.total_replied,
        "warmup_score": m.warmup_score,
        "warmup_started_at": m.warmup_started_at,
        "last_warmup_at": m.last_warmup_at,
        "created_at": m.created_at,
    }
    return d



def _get_user_company_id(current_user: User) -> str:
    return current_user.company_id


# ── List mailboxes ────────────────────────────────────────────────────────────
@router.get("/")
def list_mailboxes(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Super admin can filter by company; others see only own
    if current_user.role == UserRole.super_admin and company_id:
        target_company = company_id
    else:
        target_company = current_user.company_id

    mailboxes = (
        db.query(Mailbox)
        .filter(Mailbox.company_id == target_company)
        .order_by(Mailbox.created_at.desc())
        .all()
    )
    return [_mailbox_to_dict(m) for m in mailboxes]


# ── Add mailbox ───────────────────────────────────────────────────────────────
@router.post("/", status_code=201)
def add_mailbox(
    payload: MailboxCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Check duplicate
    existing = db.query(Mailbox).filter(
        Mailbox.company_id == current_user.company_id,
        Mailbox.email_address == payload.email_address,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mailbox already added for this company")

    if payload.auth_type == "microsoft_graph":
        # Everything goes through Graph; the SMTP/IMAP columns are informational only
        payload.smtp_host, payload.smtp_port, payload.smtp_use_tls = "smtp.office365.com", 587, True
        payload.imap_host, payload.imap_port, payload.imap_use_ssl = "outlook.office365.com", 993, True
        payload.smtp_user = payload.imap_user = payload.email_address
        payload.smtp_password = payload.imap_password = ""
    else:
        missing = [f for f in ("smtp_host", "smtp_user", "smtp_password", "imap_host", "imap_user", "imap_password")
                   if not getattr(payload, f)]
        if missing:
            raise HTTPException(status_code=422, detail=f"Missing fields: {', '.join(missing)}")

    mailbox = Mailbox(
        id=str(uuid.uuid4()),
        company_id=current_user.company_id,
        email_address=payload.email_address,
        display_name=payload.display_name or payload.email_address.split("@")[0],
        auth_type=payload.auth_type,
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_user=payload.smtp_user,
        smtp_password_enc=encrypt_password(payload.smtp_password),
        smtp_use_tls=payload.smtp_use_tls,
        imap_host=payload.imap_host,
        imap_port=payload.imap_port,
        imap_user=payload.imap_user,
        imap_password_enc=encrypt_password(payload.imap_password),
        imap_use_ssl=payload.imap_use_ssl,
        warmup_status=WarmupStatus.pending,
        current_week=1,
        daily_limit=3,
    )
    db.add(mailbox)
    db.commit()
    return {"message": "Mailbox added", "mailbox": _mailbox_to_dict(mailbox)}


# ── Get single mailbox ────────────────────────────────────────────────────────
@router.get("/{mailbox_id}")
def get_mailbox(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if current_user.role != UserRole.super_admin and mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _mailbox_to_dict(mailbox)


# ── Update mailbox ────────────────────────────────────────────────────────────
@router.patch("/{mailbox_id}")
def update_mailbox(
    mailbox_id: str,
    payload: MailboxUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if current_user.role != UserRole.super_admin and mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if payload.display_name: mailbox.display_name = payload.display_name
    if payload.warmup_status: mailbox.warmup_status = payload.warmup_status
    if payload.smtp_password: mailbox.smtp_password_enc = encrypt_password(payload.smtp_password)
    if payload.imap_password: mailbox.imap_password_enc = encrypt_password(payload.imap_password)
    if payload.daily_limit is not None: mailbox.daily_limit = payload.daily_limit

    db.commit()
    return {"message": "Mailbox updated", "mailbox": _mailbox_to_dict(mailbox)}


# ── Delete mailbox ────────────────────────────────────────────────────────────
@router.delete("/{mailbox_id}")
def delete_mailbox(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if current_user.role != UserRole.super_admin and mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(mailbox)
    db.commit()
    return {"message": "Mailbox deleted"}


# ── Start / Pause warmup ──────────────────────────────────────────────────────
@router.post("/{mailbox_id}/start-warmup")
def start_warmup(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox or mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if mailbox.auth_type in ("microsoft_graph", "gmail_api") and not mailbox.oauth_refresh_token_enc:
        raise HTTPException(status_code=400, detail="Connect this mailbox to its provider before starting warmup")
    mailbox.warmup_status = WarmupStatus.active
    db.commit()
    return {"message": f"Warmup started for {mailbox.email_address}"}


@router.post("/{mailbox_id}/pause-warmup")
def pause_warmup(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox or mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    mailbox.warmup_status = WarmupStatus.paused
    db.commit()
    return {"message": f"Warmup paused for {mailbox.email_address}"}


# ── Test connections ──────────────────────────────────────────────────────────
@router.post("/{mailbox_id}/test")
def test_connections(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox or mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    svc = EmailService(mailbox)
    smtp_ok, smtp_msg = svc.test_smtp_connection()
    imap_ok, imap_msg = svc.test_imap_connection()

    return {
        "smtp": {"success": smtp_ok, "message": smtp_msg},
        "imap": {"success": imap_ok, "message": imap_msg},
        "overall": smtp_ok and imap_ok,
    }

