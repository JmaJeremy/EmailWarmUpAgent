"""
Microsoft Graph — OAuth2 + mail operations for Microsoft 365 / Exchange Online mailboxes.

Everything goes over HTTPS to graph.microsoft.com, so it works regardless of whether
SMTP AUTH or IMAP is enabled for the tenant/mailbox.

Delegated permissions required on the Entra ID app registration:
  offline_access · User.Read · Mail.ReadWrite · Mail.Send
"""
import base64
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from config import settings
from services.encryption import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MS_SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
]

# Invisible named property used to remember which messages we already replied to
# (Graph has no direct equivalent of the IMAP \Answered flag).
REPLIED_PROP_ID = "String {9c3f6a52-4d1e-4b7a-9a43-0f3d6b1c2e71} Name WarmupReplied"


# ── OAuth helpers ─────────────────────────────────────────────────────────────
def is_configured() -> bool:
    return bool(settings.microsoft_client_id and settings.microsoft_client_secret and settings.microsoft_tenant_id)


def _authority() -> str:
    return f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0"


def build_auth_url(state: str, login_hint: Optional[str] = None) -> str:
    import urllib.parse
    params = {
        "client_id":     settings.microsoft_client_id,
        "response_type": "code",
        "redirect_uri":  settings.microsoft_redirect_uri,
        "response_mode": "query",
        "scope":         " ".join(MS_SCOPES),
        "state":         state,
        "prompt":        "select_account",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{_authority()}/authorize?" + urllib.parse.urlencode(params)


def _token_request(data: dict) -> dict:
    payload = {
        "client_id":     settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "scope":         " ".join(MS_SCOPES),
        **data,
    }
    resp = httpx.post(f"{_authority()}/token", data=payload, timeout=30)
    body = resp.json()
    if resp.status_code != 200 or "access_token" not in body:
        raise RuntimeError(body.get("error_description") or body.get("error") or f"HTTP {resp.status_code}")
    return body


def exchange_code(code: str) -> dict:
    return _token_request({
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": settings.microsoft_redirect_uri,
    })


def get_me(access_token: str) -> dict:
    resp = httpx.get(
        f"{GRAPH_BASE}/me?$select=mail,userPrincipalName,displayName",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def encode_token_blob(refresh_token: str) -> str:
    return encrypt_password(json.dumps({"refresh_token": refresh_token}))


# ── Per-mailbox Graph client ──────────────────────────────────────────────────
class GraphMailbox:
    """Thin wrapper around the Graph mail endpoints for one connected mailbox."""

    def __init__(self, mailbox):
        self.mailbox = mailbox
        self._access_token: Optional[str] = None
        self._expires_at = 0.0

    # ── Auth ─────────────────────────────────────────────────────────────────
    def _token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        if not self.mailbox.oauth_refresh_token_enc:
            raise RuntimeError("Mailbox is not connected to Microsoft — click 'Connect with Microsoft'")

        blob = json.loads(decrypt_password(self.mailbox.oauth_refresh_token_enc))
        tokens = _token_request({"grant_type": "refresh_token", "refresh_token": blob["refresh_token"]})
        self._access_token = tokens["access_token"]
        self._expires_at = time.time() + int(tokens.get("expires_in", 3600))

        # Microsoft rotates refresh tokens — persist the new one
        new_refresh = tokens.get("refresh_token")
        if new_refresh and new_refresh != blob["refresh_token"]:
            self.mailbox.oauth_refresh_token_enc = encode_token_blob(new_refresh)
            from sqlalchemy.orm import object_session
            from sqlalchemy.orm.exc import UnmappedInstanceError
            try:
                session = object_session(self.mailbox)
            except UnmappedInstanceError:
                session = None
            if session:
                session.commit()
        return self._access_token

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token()}"
        for attempt in range(3):
            resp = httpx.request(method, f"{GRAPH_BASE}{path}", headers=headers, timeout=30, **kwargs)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt * 5))
                logger.warning(f"Graph {resp.status_code} on {path} — retrying in {wait}s")
                time.sleep(min(wait, 60))
                continue
            break
        if resp.status_code >= 400:
            raise RuntimeError(f"Graph {method} {path} → {resp.status_code}: {resp.text[:300]}")
        return resp

    # ── Operations ───────────────────────────────────────────────────────────
    def me(self) -> dict:
        return self._request("GET", "/me?$select=mail,userPrincipalName,displayName").json()

    def send_mime(self, msg) -> None:
        """Send a pre-built MIME message (keeps our headers + threading intact)."""
        raw = base64.b64encode(msg.as_bytes())
        self._request("POST", "/me/sendMail", content=raw, headers={"Content-Type": "text/plain"})

    def list_recent(self, folder: str, is_read: bool, days: int = 7, top: int = 50) -> list:
        """Recent messages in a well-known folder ('inbox', 'junkemail') filtered by read state."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {
            "$filter":  f"receivedDateTime ge {since} and isRead eq {'true' if is_read else 'false'}",
            "$orderby": "receivedDateTime desc",
            "$top":     str(top),
            "$select":  "id,subject,from,replyTo,internetMessageId,internetMessageHeaders",
            "$expand":  f"singleValueExtendedProperties($filter=id eq '{REPLIED_PROP_ID}')",
        }
        return self._request("GET", f"/me/mailFolders/{folder}/messages", params=params).json().get("value", [])

    def mark_read_and_flag(self, message_id: str) -> None:
        self._request("PATCH", f"/me/messages/{message_id}", json={
            "isRead": True,
            "flag": {"flagStatus": "flagged"},
        })

    def move_to_inbox(self, message_id: str) -> str:
        return self._request("POST", f"/me/messages/{message_id}/move", json={"destinationId": "inbox"}).json()["id"]

    def mark_replied(self, message_id: str) -> None:
        self._request("PATCH", f"/me/messages/{message_id}", json={
            "singleValueExtendedProperties": [{"id": REPLIED_PROP_ID, "value": "true"}],
        })

    def inbox_reachable(self) -> None:
        self._request("GET", "/me/mailFolders/inbox?$select=id")


def message_header(message: dict, name: str) -> Optional[str]:
    for h in message.get("internetMessageHeaders") or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def already_replied(message: dict) -> bool:
    return any(p.get("value") == "true" for p in message.get("singleValueExtendedProperties") or [])


def sender_address(message: dict) -> str:
    reply_to = message.get("replyTo") or []
    src = reply_to[0] if reply_to else message.get("from") or {}
    return (src.get("emailAddress") or {}).get("address", "")
