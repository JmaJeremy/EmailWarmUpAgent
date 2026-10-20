"""
OAuth Mailbox Router — Google (Gmail API) and Microsoft (Graph) authorization flows.

Endpoints:
  GET  /mailboxes/oauth/google-url           → returns Google OAuth consent URL
  GET  /mailboxes/oauth/google-callback      → exchanges auth code for tokens + saves to mailbox
  GET  /mailboxes/oauth/microsoft-url        → returns Microsoft sign-in URL
  GET  /mailboxes/oauth/microsoft-callback   → exchanges auth code for tokens + saves to mailbox
"""
import json
import logging
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from models.mailbox import Mailbox
from models.user import User, UserRole
from config import settings
from dependencies import require_admin
from services.encryption import encrypt_password, decrypt_password
from services import microsoft_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mailboxes/oauth", tags=["Mailbox OAuth"])

# Full mail scope: Gmail API sending + IMAP (XOAUTH2) reading/flagging/moving
GOOGLE_SCOPES = ["https://mail.google.com/"]


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


def _make_state(mailbox_id: str, provider: str) -> str:
    """Signed, short-lived state so the callback can trust which mailbox it is for."""
    return jwt.encode(
        {"mid": mailbox_id, "prv": provider, "exp": datetime.utcnow() + timedelta(minutes=15)},
        settings.jwt_secret_key, algorithm=settings.jwt_algorithm,
    )


def _read_state(state: str, provider: str):
    try:
        payload = jwt.decode(state, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    return payload.get("mid") if payload.get("prv") == provider else None


def _owned_mailbox(db: Session, mailbox_id: str, user: User) -> Mailbox:
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox or (user.role != UserRole.super_admin and mailbox.company_id != user.company_id):
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return mailbox


def _back_to_frontend(**params) -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/mailboxes?" + urllib.parse.urlencode(params))


# ── Step 1: Get consent URL ───────────────────────────────────────────────────
@router.get("/google-url")
def get_google_auth_url(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return the Google OAuth consent URL for a specific mailbox."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured in environment variables")
    _owned_mailbox(db, mailbox_id, current_user)

    logger.info(f"🔑 Google OAuth URL requested for mailbox: {mailbox_id}")
    logger.info(f"   redirect_uri: {settings.google_redirect_uri}")

    # Build auth URL manually — no PKCE code_challenge (google_auth_oauthlib adds it automatically)
    params = {
        "client_id":              settings.google_client_id,
        "redirect_uri":           settings.google_redirect_uri,
        "response_type":          "code",
        "scope":                  " ".join(GOOGLE_SCOPES),
        "access_type":            "offline",
        "include_granted_scopes": "true",
        "prompt":                 "consent",
        "state":                  _make_state(mailbox_id, "google"),
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"auth_url": auth_url}


# ── Step 2: Exchange code for tokens (Google redirects here) ──────────────────
@router.get("/google-callback")
def google_callback(
    state: str,   # signed mailbox_id
    code: str = None,
    db: Session = Depends(get_db),
    error: str = None,
):
    """
    Google redirects here after user authorizes.
    Exchanges auth code for tokens → saves encrypted refresh token to mailbox.
    Then redirects back to the frontend.
    """
    frontend_url = settings.frontend_url.rstrip("/")

    if error:
        return _back_to_frontend(oauth_error=error)

    mailbox_id = _read_state(state, "google")
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first() if mailbox_id else None
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



# ── Microsoft 365 / Exchange Online ───────────────────────────────────────────
@router.get("/microsoft-url")
def get_microsoft_auth_url(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return the Microsoft sign-in URL for a specific mailbox."""
    if not microsoft_graph.is_configured():
        raise HTTPException(
            status_code=501,
            detail="Microsoft OAuth not configured — set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET and MICROSOFT_TENANT_ID",
        )
    mailbox = _owned_mailbox(db, mailbox_id, current_user)
    return {"auth_url": microsoft_graph.build_auth_url(_make_state(mailbox.id, "microsoft"), mailbox.email_address)}


@router.get("/microsoft-callback")
def microsoft_callback(
    state: str,
    code: str = None,
    error: str = None,
    error_description: str = None,
    db: Session = Depends(get_db),
):
    """Microsoft redirects here after sign-in → store the encrypted refresh token on the mailbox."""
    if error:
        return _back_to_frontend(oauth_error=error, detail=(error_description or "")[:200])

    mailbox_id = _read_state(state, "microsoft")
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first() if mailbox_id else None
    if not mailbox or not code:
        return _back_to_frontend(oauth_error="mailbox_not_found")

    try:
        tokens = microsoft_graph.exchange_code(code)
        if not tokens.get("refresh_token"):
            return _back_to_frontend(oauth_error="no_refresh_token")

        me = microsoft_graph.get_me(tokens["access_token"])
        signed_in = (me.get("mail") or me.get("userPrincipalName") or "").lower()
        if signed_in != mailbox.email_address.lower():
            return _back_to_frontend(
                oauth_error="wrong_account",
                detail=f"Signed in as {signed_in}, but this mailbox is {mailbox.email_address}",
            )

        mailbox.oauth_refresh_token_enc = microsoft_graph.encode_token_blob(tokens["refresh_token"])
        mailbox.auth_type = "microsoft_graph"
        db.commit()
        logger.info(f"✅ Microsoft Graph connected: {mailbox.email_address}")
        return _back_to_frontend(oauth_success=mailbox.email_address)
    except Exception as e:
        logger.error(f"❌ Microsoft OAuth callback error: {type(e).__name__}: {e}", exc_info=True)
        return _back_to_frontend(oauth_error="token_exchange_failed", detail=str(e)[:200])
