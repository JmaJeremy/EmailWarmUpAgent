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


# ── Step 2: Exchange code for tokens (Google redirects here) ──────────────────
@router.get("/google-callback")
def google_callback(
    code: str,
    state: str,   # mailbox_id passed as 'state' param
    db: Session = Depends(get_db),
    error: str = None,
):
    """
    Google redirects here after user authorizes.
    Exchanges auth code for tokens → saves encrypted refresh token to mailbox.
    Then redirects back to the frontend.
    """
    from fastapi.responses import RedirectResponse

    frontend_url = settings.frontend_url.rstrip("/")

    if error:
        return RedirectResponse(f"{frontend_url}/mailboxes?oauth_error={error}")

    mailbox = db.query(Mailbox).filter(Mailbox.id == state).first()
    if not mailbox:
        return RedirectResponse(f"{frontend_url}/mailboxes?oauth_error=mailbox_not_found")

    try:
        flow = _google_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        if not creds.refresh_token:
            return RedirectResponse(
                f"{frontend_url}/mailboxes?oauth_error=no_refresh_token"
            )

        token_data = json.dumps({
            "refresh_token": creds.refresh_token,
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
        })
        mailbox.oauth_refresh_token_enc = encrypt_password(token_data)
        mailbox.auth_type = "gmail_api"
        mailbox.smtp_host = "smtp.gmail.com"
        mailbox.smtp_port = 587
        db.commit()

        logger.info(f"✅ Gmail API connected: {mailbox.email_address}")
        return RedirectResponse(
            f"{frontend_url}/mailboxes?oauth_success={mailbox.email_address}"
        )

    except Exception as e:
        logger.error(f"❌ Google OAuth callback error: {e}", exc_info=True)
        return RedirectResponse(f"{frontend_url}/mailboxes?oauth_error=token_exchange_failed")

