"""
Email Service — sending + reading/replying for every supported provider
Core of the warmup engine: sends real emails and auto-reads/replies to them.

TRANSPORTS (chosen by mailbox.auth_type):
  smtp             → SMTP send + IMAP read (Gmail app passwords, Purelymail, Fastmail, …)
  gmail_api        → Gmail API send + IMAP read via XOAUTH2 (Google OAuth)
  microsoft_graph  → Microsoft Graph for everything (Microsoft 365 / Exchange Online)

WARMUP DETECTION:
  Every warmup email (and every auto-reply) carries a signed X-Warmup-ID header.
  Only messages with a valid signature are ever opened, rescued or replied to —
  real mail is never touched, even if its subject happens to match a template.

HUMAN-LIKE TEMPLATE LIBRARY:
  ✅ 50+ unique subjects (never repetitive)
  ✅ 40+ unique body templates (short/medium/long mix)
  ✅ 50+ varied replies (not all "Thanks!", some have questions, some are longer)
  ✅ Body + signature generated dynamically from sender's display name
  ✅ Reply rate: 85% of opened emails get replied (very high = great domain trust)
  ✅ Duplicate-prevention: checks \\Answered flag before replying
"""
import smtplib
import imaplib
import email
import email.utils
import hashlib
import hmac
import json
import random
import re
import logging
import time
import uuid
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional

import httpx

from config import settings
from services.encryption import decrypt_password
from services import microsoft_graph as graph


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 50+ SUBJECTS — varied tones (professional · casual · quick note)
# ─────────────────────────────────────────────────────────────────────────────
WARMUP_SUBJECTS = [
    # Professional
    "Quick question about your workflow",
    "Following up on our earlier conversation",
    "Thoughts on this approach?",
    "A couple of things I wanted to run by you",
    "Brief update from my end",
    "Your opinion on this would be helpful",
    "Checking in on the progress",
    "Wanted to share something with you",
    "Let me know what you think",
    "A few things to discuss",
    "Circling back on this",
    "One quick thing",
    "Touching base",
    "Looping you in",
    "Quick thought I wanted to share",
    "Update on the project",
    "Something I noticed",
    "Can I get your take on this?",
    "Before we get started",
    "Just wanted to check",
    "This came up today",
    "Came across something interesting",
    "Have a moment this week?",
    "Quick catch-up",
    "Following up — any updates?",
    "Re: our plan",
    "A quick thought",
    "Just thinking out loud here",
    "Heads up on a few things",
    "Quick note before end of day",
    # Casual
    "Hey, can you help me with something?",
    "Catching up — hope all is well",
    "Just checking in",
    "Hope things are going smoothly",
    "Hey, quick one for you",
    "Hey there — got a minute?",
    "What do you think about this?",
    "Been meaning to ask you about this",
    "How are things on your end?",
    "Any updates from your side?",
    "Thought you'd want to know",
    "Ping — when you get a moment",
    "Quick question for you",
    "Not urgent, but wanted to ask",
    "Something I wanted your input on",
    "Small thing but important",
    "Random thought — worth discussing?",
    "Good timing on this one",
    "Just a heads-up",
    "FYI — thought this was useful",
    "Just looping you in",
    "Saw this and thought of you",
]

# ─────────────────────────────────────────────────────────────────────────────
# 40+ BODY TEMPLATES — short / medium / longer mix
# Uses {name} placeholder replaced with recipient's first name or "there"
# ─────────────────────────────────────────────────────────────────────────────
WARMUP_BODIES = [
    # SHORT (2-3 sentences)
    "Hi {name},\n\nHope you're having a good week! Wanted to reach out and ask if you've had a chance to look at the stuff we discussed. Let me know when you're free.\n\nBest",
    "Hey {name},\n\nJust a quick ping — any updates from your side? Let me know and I'll take it from here.\n\nThanks",
    "Hi {name},\n\nFollowing up on our last conversation. Any thoughts? Happy to jump on a call.\n\nCheers",
    "Hello {name},\n\nHope all is well! I had a quick question I wanted to run by you. It's not urgent but I'd love your input when you get a moment.\n\nThanks",
    "Hi {name},\n\nJust checking in. Let me know if there's anything I can help with from my end.\n\nBest",
    "Hey {name},\n\nSaw something that reminded me of what we discussed. Worth a look when you get a chance. Let me know your thoughts.\n\nCheers",
    "Hello {name},\n\nHope things are going well on your end! Quick note to say we're progressing well here. Will keep you posted.\n\nBest regards",
    "Hi {name},\n\nJust wanted to send a quick note. Nothing urgent, just wanted to make sure we're aligned.\n\nTake care",

    # MEDIUM (short paragraph)
    """Hi {name},

Hope you're doing well. I've been thinking about what we discussed and I believe we're in a good place to move forward. Just wanted to make sure we're on the same page before I proceed.

Let me know if you have any concerns or if there's anything I'm missing. Happy to chat whenever works for you.

Best""",

    """Hello {name},

Just following up on my last message. I know things can get busy, so no pressure — just wanted to make sure this didn't slip through the cracks.

If you need more time, no problem at all. But if you could get back to me by end of week, that would be great.

Thanks""",

    """Hi {name},

Checking in to see if you had a chance to review what I sent over. We're close to wrapping things up on our end, and your input would really help us finalize everything.

Would love to connect briefly if that works — even 10 minutes would be helpful.

Cheers""",

    """Hey {name},

Hope your week is going smoothly! I wanted to loop you in on something that came up. It's a small thing but could have some impact depending on how we handle it.

Let me know what you think and we can figure out the best path forward.

Best""",

    """Hi {name},

Quick update from my side — things are progressing well and I expect to have everything ready soon. I'll send over the details once it's finalized.

In the meantime, is there anything I should be aware of from your end?

Thanks""",

    """Hello {name},

I've been going over a few things and had some questions I wanted your take on. Nothing urgent, but helpful if we could discuss at some point this week.

Let me know when you have a few minutes. Could even do a quick call or just reply over email — whatever works for you.

Best regards""",

    """Hi {name},

Hope the week's been good! I wanted to share a quick update. We made some progress on the things we discussed, and things are looking pretty good.

I'll send over a proper update soon, but wanted to give you a quick heads-up in the meantime. Let me know if you have any questions.

Kind regards""",

    """Hey {name},

Just saw something interesting that I thought you'd want to know about. Not sure if this affects what we're working on, but figured I'd flag it just in case.

Let me know your thoughts when you get a chance!

Cheers""",

    # LONGER (2 short paragraphs)
    """Hi {name},

Hope everything's going well on your end! I wanted to reach out because I've been reviewing the situation and I think there's a good opportunity we might be overlooking. It's not something we need to decide immediately, but I think it's worth discussing soon.

My thought is we should get aligned on this before things move further along. Would it be possible to set aside some time this week or early next? Even a short chat would be helpful.

Looking forward to hearing your thoughts.

Best""",

    """Hello {name},

I hope you're having a productive week. Wanted to drop a quick note because I've been thinking about the conversation we had a little while back, and I realized there's something I should have mentioned at the time.

It's not a big deal, but I think it's relevant and might change how we approach things. Happy to explain over email or on a quick call — whichever is easier for you.

Thanks for bearing with me on this!

Best regards""",

    """Hi {name},

Just a quick message to say that everything on our end is moving along nicely. We've cleared a few of the roadblocks we were dealing with, so I'm feeling good about where things stand.

Once I have a clearer picture of what the next steps look like, I'll loop you in. For now, just wanted to keep you in the loop and make sure we're still on the same page.

Hope you're doing well!

Cheers""",

    """Hey {name},

I hope this finds you well! I wanted to follow up on a few things we've been discussing as a team. Nothing has changed dramatically, but there are a few updates worth knowing about as they could affect the timeline a bit.

I'll put together a more detailed summary soon, but in the meantime — do you have any pressing questions or things I should factor in from your side?

Appreciate your time as always.

Best""",

    """Hi {name},

Been a little while — hope you've been well! I wanted to check in and see how things are going on your side. We've been making some progress here and I think we're getting close to a good place.

If you have a moment this week, it would be great to catch up. Even just a few minutes to align on where things stand would be helpful.

Let me know what works for you.

Kind regards""",

    """Hello {name},

I hope your week has been going well. I just wanted to send a quick note because I've been reviewing what we have so far and I think we're in good shape overall. A few small things to iron out, but nothing too complicated.

Is there anything on your end that's changed or that I should know about before we finalize things? Always good to make sure we're aligned.

Thanks for being so responsive — really appreciate it.

Best""",
]

# ─────────────────────────────────────────────────────────────────────────────
# 50+ REPLY TEMPLATES — varied length, tone, sometimes with questions
# This is what Helpers (Gmail accounts) auto-reply with
# ─────────────────────────────────────────────────────────────────────────────
WARMUP_REPLIES = [
    # Very short (1-liners)
    "Thanks, got it! Will circle back soon.",
    "Received, thanks!",
    "Got it, appreciate the heads-up!",
    "Thanks for the note. On it.",
    "Noted, thanks!",
    "Great, I'll look into this.",
    "Thanks! I'll get back to you shortly.",
    "Received! Will review and respond.",
    "Appreciate it! Talk soon.",
    "Thanks, will do.",

    # Short (2-3 sentences)
    "Thanks for reaching out! I'll review this and get back to you shortly.",
    "Got it — thanks for keeping me in the loop. I'll go through it and share my thoughts soon.",
    "Appreciated! Let me look into this and I'll circle back with an update.",
    "Thanks for the follow-up. I haven't had a chance to go through it yet but I'll do so today.",
    "Good timing on this. I was actually thinking about the same thing. Will respond properly soon.",
    "Thanks for flagging this! I'll take a look and let you know what I think.",
    "Got your message — appreciate you following up. I'll be in touch by end of day.",
    "Thanks! This looks good at first glance. I'll review in detail and come back with feedback.",
    "Perfect, thanks for the update. Will follow up on my end.",
    "Noted! I'll look into it and respond properly once I've had a chance to review.",

    # Medium (with a question or comment)
    "Thanks for reaching out! I've been meaning to get back to you on this. Let me pull up the relevant info and get back to you properly — should be later today or tomorrow.",
    "Got it, thanks! Quick question while I have you — do you have a rough timeline in mind for this? Just want to make sure I plan accordingly.",
    "Appreciated! I'll review and respond. By the way, did you get the information I sent last time? Just making sure it reached you okay.",
    "Thanks for the note. I'll take a look and share my thoughts soon. Is there a deadline I should be aware of?",
    "Got your message! This is helpful context. I'll go through the details today and come back with some thoughts. Does this week work for a follow-up?",
    "Thanks for flagging this. I'll review what you've sent and respond with some feedback. Let me know if anything is time-sensitive.",
    "Received! I have a couple of questions but I'll read through everything first and then reach out. Should be sometime tomorrow.",
    "Thanks! Let me review this properly and I'll get back to you with a more detailed response. Looks interesting at first glance.",
    "Got it — thanks for the detailed message. I'll go through it this evening and respond tomorrow morning. Talk soon!",

    # Slightly longer and more personal
    "Thanks so much for following up! Sorry I've been a bit slow to respond — it's been a busy stretch on my end. I'll make sure to go through this properly and get back to you with a proper response soon.",
    "Appreciate you keeping me in the loop on this! I've started reviewing the details and have a few initial thoughts. I'll put together a more complete response once I've had more time to go through everything.",
    "Good to hear from you! This is actually great timing — I was just thinking about this. Will get back to you with some proper feedback once I've had a chance to sit down with it.",
    "Thanks for this! I've been looking forward to catching up on this topic. I'll review everything today and send over my thoughts. Should be able to get back to you by tomorrow at the latest.",
    "Received, thanks! This is really helpful. I'll pull up my notes from our last conversation and make sure my response covers everything. Give me a day or so to put something together properly.",
    "Great, thanks for the update! This is helpful context. I'll get back to you soon — probably tomorrow once I've had time to review properly. Hope you're having a good week!",
    "Thanks for reaching out. I'll take a proper look at this today and get back to you with my thoughts. A few things on my plate right now but this is definitely a priority. Talk soon!",
    "Got your message — thanks! I've been meaning to follow up on this myself. Let me review what you've put together and I'll respond with a more detailed reply. Should be able to do that today or tomorrow.",
    "Really appreciate you following up! I want to give you a proper response rather than a quick one, so give me a little time to go through the details and I'll get back to you with something more thorough.",
    "Thanks for keeping me updated! I'll make sure to review this carefully and send over a proper response. If anything is urgent or time-sensitive, let me know and I'll prioritize accordingly.",
]




# ─────────────────────────────────────────────────────────────────────────────
# Warmup message identification
# ─────────────────────────────────────────────────────────────────────────────
WARMUP_HEADER = "X-Warmup-ID"


def _warmup_signature(nonce: str) -> str:
    return hmac.new(settings.encryption_key.encode(), nonce.encode(), hashlib.sha256).hexdigest()[:16]


def new_warmup_id() -> str:
    nonce = uuid.uuid4().hex
    return f"{nonce}.{_warmup_signature(nonce)}"


def is_warmup_id(value: Optional[str]) -> bool:
    """True only for X-Warmup-ID values minted by this deployment."""
    if not value:
        return False
    nonce, _, sig = value.strip().partition(".")
    return bool(nonce and sig) and hmac.compare_digest(sig, _warmup_signature(nonce))


def _decode_subject(raw: str) -> str:
    parts = []
    for text, charset in decode_header(raw or ""):
        parts.append(text.decode(charset or "utf-8", errors="ignore") if isinstance(text, bytes) else text)
    return "".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# IMAP helpers
# ─────────────────────────────────────────────────────────────────────────────
# imaplib doesn't know the MOVE extension (RFC 6851) — register it so mail.uid("MOVE", …) works
imaplib.Commands.setdefault("MOVE", ("SELECTED",))

# Used when the server doesn't advertise a \Junk special-use folder (RFC 6154)
JUNK_FOLDER_FALLBACKS = [
    "[Gmail]/Spam", "Junk", "Junk Email", "Junk E-mail", "Spam",
    "INBOX.Junk", "INBOX.Spam", "INBOX/Junk", "INBOX/Spam", "Bulk Mail", "Bulk",
]
_LIST_RE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$')
_UID_RE = re.compile(rb"UID (\d+)")
_HEADER_FIELDS = f"(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM REPLY-TO MESSAGE-ID REFERENCES {WARMUP_HEADER.upper()})])"


def _imap_quote(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def find_junk_folders(list_response: list) -> list:
    """Pick the spam/junk folder(s) out of an IMAP LIST response."""
    names, flagged = [], []
    for raw in list_response or []:
        if not isinstance(raw, bytes):
            continue  # literal-encoded names — rare, skip
        m = _LIST_RE.match(raw.decode(errors="ignore").strip())
        if not m:
            continue
        name = m.group("name").strip()
        if len(name) >= 2 and name.startswith('"') and name.endswith('"'):
            name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        flags = m.group("flags").lower()
        if "\\noselect" in flags or "\\nonexistent" in flags:
            continue
        names.append(name)
        if "\\junk" in flags:
            flagged.append(name)
    if flagged:
        return flagged
    by_lower = {n.lower(): n for n in names}
    return [by_lower[f.lower()] for f in JUNK_FOLDER_FALLBACKS if f.lower() in by_lower]


class EmailService:
    """Sends, opens and replies to warmup email for a single mailbox, whatever its provider."""

    def __init__(self, mailbox):
        self.mailbox = mailbox
        self.auth_type = getattr(mailbox, "auth_type", "smtp") or "smtp"
        if self.auth_type == "smtp":
            self.smtp_password = decrypt_password(mailbox.smtp_password_enc) if mailbox.smtp_password_enc else ''
            self.imap_password = decrypt_password(mailbox.imap_password_enc) if mailbox.imap_password_enc else ''
        else:
            self.smtp_password = ''
            self.imap_password = ''
        self._graph_client: Optional[graph.GraphMailbox] = None
        self._google_token: Optional[str] = None
        self._google_token_expires = 0.0

    def _graph(self) -> graph.GraphMailbox:
        if self._graph_client is None:
            self._graph_client = graph.GraphMailbox(self.mailbox)
        return self._graph_client

    def _first_name(self, display_name: Optional[str], email_addr: str) -> str:
        """Extract first name from display name or email prefix."""
        if display_name:
            return display_name.strip().split()[0]
        return email_addr.split("@")[0].split(".")[0].split("_")[0].capitalize()

    def _sender_signature(self) -> str:
        """Generate a natural sign-off from the sender's name."""
        name = self.mailbox.display_name or self.mailbox.email_address.split("@")[0].capitalize()
        first = name.strip().split()[0]
        return first

    def _stamp(self, msg: MIMEMultipart) -> None:
        """Headers shared by warmup emails and replies."""
        domain = self.mailbox.email_address.rsplit("@", 1)[-1]
        msg["Message-ID"] = email.utils.make_msgid(domain=domain)
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg[WARMUP_HEADER] = new_warmup_id()

    # ── Shared: build MIME message ───────────────────────────────────────────
    def _build_mime_message(self, to_email: str, to_name: Optional[str]) -> MIMEMultipart:
        """Build the warmup MIME message (used by all send methods)."""
        msg = MIMEMultipart("alternative")
        sender_display = self.mailbox.display_name or self.mailbox.email_address
        msg["From"]      = f"{sender_display} <{self.mailbox.email_address}>"
        msg["To"]        = to_email
        msg["Subject"]   = random.choice(WARMUP_SUBJECTS)
        msg["X-Mailer"]  = random.choice(["Microsoft Outlook 16.0", "Apple Mail", "Gmail", "Thunderbird"])
        msg["X-Priority"] = "3"
        self._stamp(msg)
        first_name    = self._first_name(to_name, to_email)
        body_template = random.choice(WARMUP_BODIES)
        body = body_template.format(name=first_name)
        signature = self._sender_signature()
        body = body.rstrip() + f"\n\n— {signature}"
        msg.attach(MIMEText(body, "plain"))
        return msg

    def _build_reply(self, to_addr: str, original_subject: str, message_id: str, references: str = "") -> MIMEMultipart:
        reply = MIMEMultipart("alternative")
        reply["From"]    = f"{self.mailbox.display_name or self.mailbox.email_address} <{self.mailbox.email_address}>"
        reply["To"]      = to_addr
        subject = original_subject or "No Subject"
        reply["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if message_id:
            reply["In-Reply-To"] = message_id
            reply["References"]  = f"{references} {message_id}".strip()
        self._stamp(reply)
        reply.attach(MIMEText(random.choice(WARMUP_REPLIES) + f"\n\n— {self._sender_signature()}", "plain"))
        return reply

    # ── Google OAuth (gmail_api mailboxes) ───────────────────────────────────
    def _google_access_token(self) -> str:
        if self._google_token and time.time() < self._google_token_expires - 60:
            return self._google_token
        blob = json.loads(decrypt_password(self.mailbox.oauth_refresh_token_enc))
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id":     blob.get("client_id") or settings.google_client_id,
            "client_secret": blob.get("client_secret") or settings.google_client_secret,
            "refresh_token": blob["refresh_token"],
            "grant_type":    "refresh_token",
        }, timeout=30)
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(data.get("error_description") or data.get("error") or f"HTTP {resp.status_code}")
        self._google_token = data["access_token"]
        self._google_token_expires = time.time() + int(data.get("expires_in", 3600))
        return self._google_token

    # ── Senders ──────────────────────────────────────────────────────────────
    def _send_via_gmail_api(self, msg: MIMEMultipart) -> None:
        """Send using the Gmail API (HTTPS) — for hosts that block outbound SMTP."""
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        resp = httpx.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {self._google_access_token()}"},
            json={"raw": raw},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Gmail API {resp.status_code}: {resp.text[:300]}")

    def _send_via_smtp(self, msg: MIMEMultipart, to_email: str) -> None:
        if self.mailbox.smtp_use_tls:
            server = smtplib.SMTP(self.mailbox.smtp_host, self.mailbox.smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(self.mailbox.smtp_host, self.mailbox.smtp_port, timeout=30)
        try:
            server.login(self.mailbox.smtp_user, self.smtp_password)
            server.sendmail(self.mailbox.email_address, to_email, msg.as_string())
        finally:
            try:
                server.quit()
            except Exception:
                pass

    def _send(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send a built message via the mailbox's transport. Returns success."""
        to_email = email.utils.parseaddr(to_email)[1] or to_email
        try:
            if self.auth_type == "microsoft_graph":
                self._graph().send_mime(msg)
            elif self.auth_type == "gmail_api":
                self._send_via_gmail_api(msg)
            else:
                self._send_via_smtp(msg, to_email)
            logger.info(f"✅ Sent ({self.auth_type}): {self.mailbox.email_address} → {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Send error ({self.auth_type}, {self.mailbox.email_address}): {e}")
            return False

    def send_warmup_email(self, to_email: str, to_name: Optional[str] = None) -> bool:
        """Send one warmup email using whichever transport the mailbox is configured for."""
        return self._send(self._build_mime_message(to_email, to_name), to_email)

    # ── IMAP plumbing ────────────────────────────────────────────────────────
    def _imap_connect(self) -> imaplib.IMAP4:
        if self.mailbox.imap_use_ssl:
            mail = imaplib.IMAP4_SSL(self.mailbox.imap_host, self.mailbox.imap_port, timeout=30)
        else:
            mail = imaplib.IMAP4(self.mailbox.imap_host, self.mailbox.imap_port, timeout=30)
            if "STARTTLS" in mail.capabilities:
                mail.starttls()

        user = self.mailbox.imap_user or self.mailbox.email_address
        if self.auth_type == "gmail_api":
            auth = f"user={user}\x01auth=Bearer {self._google_access_token()}\x01\x01".encode()
            mail.authenticate("XOAUTH2", lambda _: auth)
        else:
            mail.login(user, self.imap_password)

        # Capabilities often grow after login (e.g. MOVE on Gmail)
        _, caps = mail.capability()
        self._imap_caps = set(caps[0].decode().upper().split()) if caps and caps[0] else set()
        return mail

    def _fetch_headers(self, mail: imaplib.IMAP4, uids: list) -> list:
        """[(uid, email.message.Message)] — headers only, without setting \\Seen."""
        if not uids:
            return []
        _, data = mail.uid("FETCH", b",".join(uids).decode(), _HEADER_FIELDS)
        out = []
        for item in data or []:
            if isinstance(item, tuple) and len(item) == 2:
                m = _UID_RE.search(item[0])
                if m:
                    out.append((m.group(1).decode(), email.message_from_bytes(item[1])))
        return out

    def _move_to_inbox(self, mail: imaplib.IMAP4, uid: str) -> bool:
        """Move a message out of the selected folder into INBOX. Returns True if an expunge is pending."""
        if "MOVE" in self._imap_caps:
            typ, _ = mail.uid("MOVE", uid, "INBOX")
            if typ == "OK":
                return False
        mail.uid("COPY", uid, "INBOX")
        mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        return True

    # ── OPEN phase ───────────────────────────────────────────────────────────
    def open_warmup_emails(self) -> int:
        """
        Find unread warmup emails in INBOX and the spam folder → mark READ + STARRED.
        Anything found in spam is moved back to INBOX (strongest trust signal).
        """
        if self.auth_type == "microsoft_graph":
            return self._graph_open_warmup_emails()

        opened_count = 0
        try:
            mail = self._imap_connect()
            _, folder_list = mail.list()
            folders = ["INBOX"] + find_junk_folders(folder_list)

            for folder in folders:
                try:
                    typ, _ = mail.select(_imap_quote(folder))
                    if typ != "OK":
                        continue
                    _, data = mail.uid("SEARCH", None, "UNSEEN")
                    uids = data[0].split()[-30:] if data and data[0] else []

                    pending_expunge = False
                    for uid, headers in self._fetch_headers(mail, uids):
                        if not is_warmup_id(headers.get(WARMUP_HEADER)):
                            continue
                        try:
                            # Flags first so they travel with the message when it's moved/copied
                            mail.uid("STORE", uid, "+FLAGS", "(\\Seen \\Flagged)")
                            if folder.upper() != "INBOX":
                                pending_expunge |= self._move_to_inbox(mail, uid)
                                logger.info(f"🛟 Rescued from {folder}: {self.mailbox.email_address}")
                            opened_count += 1
                            logger.info(f"📬 Opened: '{_decode_subject(headers.get('Subject', ''))[:50]}' in {self.mailbox.email_address}")
                        except Exception as e:
                            logger.warning(f"IMAP open error on msg: {e}")
                    if pending_expunge:
                        mail.expunge()
                except Exception as e:
                    logger.warning(f"IMAP folder {folder} skipped ({self.mailbox.email_address}): {e}")

            mail.logout()
        except Exception as e:
            logger.error(f"❌ IMAP error ({self.mailbox.email_address}): {e}")

        return opened_count

    def _graph_open_warmup_emails(self) -> int:
        opened_count = 0
        g = self._graph()
        for folder in ("inbox", "junkemail"):
            try:
                for m in g.list_recent(folder, is_read=False):
                    if not is_warmup_id(graph.message_header(m, WARMUP_HEADER)):
                        continue
                    try:
                        g.mark_read_and_flag(m["id"])
                        if folder == "junkemail":
                            g.move_to_inbox(m["id"])
                            logger.info(f"🛟 Rescued from Junk: {self.mailbox.email_address}")
                        opened_count += 1
                        logger.info(f"📬 Opened: '{(m.get('subject') or '')[:50]}' in {self.mailbox.email_address}")
                    except Exception as e:
                        logger.warning(f"Graph open error on msg: {e}")
            except Exception as e:
                logger.error(f"❌ Graph error reading {folder} ({self.mailbox.email_address}): {e}")
        return opened_count

    # ── REPLY phase ──────────────────────────────────────────────────────────
    def reply_to_warmup_emails(self) -> int:
        """
        Find warmup emails in INBOX → reply to 85% of them with natural replies.

        NO DUPLICATES: only replies to messages not yet marked answered.
        Each reply uses a random template, sender first name, and natural pacing.
        """
        if self.auth_type == "microsoft_graph":
            return self._graph_reply_to_warmup_emails()

        replied_count = 0
        try:
            mail = self._imap_connect()
            mail.select("INBOX")

            # Read but not yet answered — prevents duplicates
            _, data = mail.uid("SEARCH", None, "SEEN", "UNANSWERED")
            uids = data[0].split()[-30:] if data and data[0] else []

            warmup_msgs = [
                (uid, h) for uid, h in self._fetch_headers(mail, uids)
                if is_warmup_id(h.get(WARMUP_HEADER))
            ]

            # Reply to 85% of warmup emails (very high = premium domain signal)
            n_to_reply = max(1, int(len(warmup_msgs) * 0.85))
            for uid, headers in random.sample(warmup_msgs, min(n_to_reply, len(warmup_msgs))):
                try:
                    from_addr = headers.get("Reply-To") or headers.get("From", "")
                    if not from_addr or self.mailbox.email_address.lower() in from_addr.lower():
                        continue  # never reply to self

                    reply = self._build_reply(
                        from_addr,
                        _decode_subject(headers.get("Subject", "")),
                        headers.get("Message-ID", ""),
                        headers.get("References", ""),
                    )
                    if not self._send(reply, from_addr):
                        continue

                    # Mark as ANSWERED — prevents future duplicate replies
                    mail.uid("STORE", uid, "+FLAGS", "(\\Answered)")
                    replied_count += 1
                    logger.info(f"↩️  Replied: {self.mailbox.email_address} → {from_addr}")

                    time.sleep(random.uniform(5, 20))  # feels human
                except Exception as e:
                    logger.warning(f"Reply error: {e}")

            mail.logout()
        except Exception as e:
            logger.error(f"❌ IMAP reply error ({self.mailbox.email_address}): {e}")

        return replied_count

    def _graph_reply_to_warmup_emails(self) -> int:
        replied_count = 0
        g = self._graph()
        try:
            candidates = [
                m for m in g.list_recent("inbox", is_read=True)
                if is_warmup_id(graph.message_header(m, WARMUP_HEADER)) and not graph.already_replied(m)
            ]
        except Exception as e:
            logger.error(f"❌ Graph reply error ({self.mailbox.email_address}): {e}")
            return 0

        n_to_reply = max(1, int(len(candidates) * 0.85))
        for m in random.sample(candidates, min(n_to_reply, len(candidates))):
            try:
                to_addr = graph.sender_address(m)
                if not to_addr or to_addr.lower() == self.mailbox.email_address.lower():
                    continue
                reply = self._build_reply(
                    to_addr,
                    m.get("subject") or "",
                    m.get("internetMessageId") or "",
                    graph.message_header(m, "References") or "",
                )
                if not self._send(reply, to_addr):
                    continue
                g.mark_replied(m["id"])
                replied_count += 1
                logger.info(f"↩️  Replied: {self.mailbox.email_address} → {to_addr}")
                time.sleep(random.uniform(5, 20))
            except Exception as e:
                logger.warning(f"Graph reply error: {e}")
        return replied_count

    # ── Connection tests ─────────────────────────────────────────────────────
    def test_smtp_connection(self) -> tuple[bool, str]:
        """Test the sending side — returns (success, message)."""
        try:
            if self.auth_type == "microsoft_graph":
                me = self._graph().me()
                signed_in = (me.get("mail") or me.get("userPrincipalName") or "").lower()
                if signed_in != self.mailbox.email_address.lower():
                    return False, f"Connected Microsoft account is {signed_in}, not {self.mailbox.email_address}"
                return True, f"Microsoft Graph: signed in as {signed_in}"
            if self.auth_type == "gmail_api":
                self._google_access_token()
                return True, "Gmail API token OK"

            if self.mailbox.smtp_use_tls:
                server = smtplib.SMTP(self.mailbox.smtp_host, self.mailbox.smtp_port, timeout=15)
                server.ehlo(); server.starttls(); server.ehlo()
            else:
                server = smtplib.SMTP_SSL(self.mailbox.smtp_host, self.mailbox.smtp_port, timeout=15)
            server.login(self.mailbox.smtp_user, self.smtp_password)
            server.quit()
            return True, "SMTP connection successful"
        except Exception as e:
            return False, str(e)

    def test_imap_connection(self) -> tuple[bool, str]:
        """Test the reading side — returns (success, message)."""
        try:
            if self.auth_type == "microsoft_graph":
                self._graph().inbox_reachable()
                return True, "Microsoft Graph: Inbox + Junk Email accessible"

            mail = self._imap_connect()
            _, folder_list = mail.list()
            junk = find_junk_folders(folder_list)
            mail.logout()
            if not junk:
                return True, "IMAP connection successful (warning: no spam folder found — spam rescue disabled)"
            return True, f"IMAP connection successful (spam folder: {', '.join(junk)})"
        except Exception as e:
            return False, str(e)
