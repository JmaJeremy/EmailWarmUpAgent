"""
OAuth Mailbox Router — Gmail API OAuth2 authorization flow.

Endpoints:
  GET  /mailboxes/oauth/google-url        → returns Google OAuth consent URL
  POST /mailboxes/oauth/google-callback   → exchanges auth code for tokens + saves to mailbox
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from models.mailbox import Mailbox
from config import settings
from dependencies import get_current_user
from services.encryption import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mailboxes/oauth", tags=["Mailbox OAuth"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _google_flow():
    """Build a Google OAuth2 flow from settings."""
    from google_auth_oauthlib.flow import Flow
    client_config = {
        "web": {
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


# ── Step 1: Get consent URL ───────────────────────────────────────────────────
@router.get("/google-url")
def get_google_auth_url(
    mailbox_id: str,
    current_user=Depends(get_current_user),
):
    """Return the Google OAuth consent URL for a specific mailbox."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured in environment variables")

    flow = _google_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",            # always get refresh_token
        state=mailbox_id,            # we pass mailbox_id as state to link on callback
    )
    return {"auth_url": auth_url}


# ── Step 2: Exchange code for tokens ──────────────────────────────────────────
class GoogleCallbackPayload(BaseModel):
    code: str
    mailbox_id: str


@router.post("/google-callback")
def google_callback(
    payload: GoogleCallbackPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Exchange the Google auth code for tokens and save the refresh token
    (encrypted) to the mailbox. Sets auth_type = 'gmail_api'.
    """
    mailbox = db.query(Mailbox).filter(Mailbox.id == payload.mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    try:
        flow = _google_flow()
        flow.fetch_token(code=payload.code)
        creds = flow.credentials

        if not creds.refresh_token:
            raise HTTPException(
                status_code=400,
                detail="No refresh token returned. Please revoke access in your Google account and try again."
            )

        # Store encrypted refresh token
        token_data = json.dumps({
            "refresh_token": creds.refresh_token,
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
        })
        mailbox.oauth_refresh_token_enc = encrypt_password(token_data)
        mailbox.auth_type = "gmail_api"

        # SMTP fields not needed for Gmail API — clear them
        mailbox.smtp_host = "smtp.gmail.com"  # kept for reference
        mailbox.smtp_port = 587

        db.commit()
        logger.info(f"✅ Gmail API connected for mailbox: {mailbox.email_address}")
        return {"status": "connected", "email": mailbox.email_address, "auth_type": "gmail_api"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google OAuth callback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")
