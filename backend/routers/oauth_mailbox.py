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

    logger.info(f"🔑 Google OAuth URL requested for mailbox: {mailbox_id}")
    logger.info(f"   redirect_uri: {settings.google_redirect_uri}")

    import urllib.parse
    # Build auth URL manually — no PKCE code_challenge (google_auth_oauthlib adds it automatically)
    params = {
        "client_id":              settings.google_client_id,
        "redirect_uri":           settings.google_redirect_uri,
        "response_type":          "code",
        "scope":                  " ".join(GOOGLE_SCOPES),
        "access_type":            "offline",
        "include_granted_scopes": "true",
        "prompt":                 "consent",
        "state":                  mailbox_id,
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
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
        import requests as http_requests

        # Exchange the auth code for tokens directly via HTTP POST
        # (avoids PKCE code_verifier issue with google_auth_oauthlib)
        token_response = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri":  settings.google_redirect_uri,
                "grant_type":    "authorization_code",
            },
        )
        token_data_raw = token_response.json()
        logger.info(f"🔄 Token exchange response keys: {list(token_data_raw.keys())}")

        if "error" in token_data_raw:
            logger.error(f"❌ Token exchange error: {token_data_raw}")
            import urllib.parse
            detail = urllib.parse.quote(str(token_data_raw.get("error_description", token_data_raw.get("error")))[:200])
            return RedirectResponse(f"{frontend_url}/mailboxes?oauth_error=google_rejected&detail={detail}")

        refresh_token = token_data_raw.get("refresh_token")
        if not refresh_token:
            logger.error(f"❌ No refresh_token in response. Keys: {list(token_data_raw.keys())}")
            return RedirectResponse(f"{frontend_url}/mailboxes?oauth_error=no_refresh_token")

        token_data = json.dumps({
            "refresh_token": refresh_token,
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
        import urllib.parse
        error_detail = urllib.parse.quote(str(e)[:200])
        logger.error(f"❌ Google OAuth callback error: {type(e).__name__}: {e}", exc_info=True)
        return RedirectResponse(f"{frontend_url}/mailboxes?oauth_error=token_exchange_failed&detail={error_detail}")

