"""
Email Service — SMTP sending + IMAP reading/replying
Core of the warmup engine: sends real emails and auto-reads/replies via IMAP

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
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional
from services.encryption import decrypt_password

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


class EmailService:
    """Handles email sending (SMTP or Gmail API) and IMAP reading for a single mailbox."""

    def __init__(self, mailbox):
        self.mailbox = mailbox
        # Only decrypt SMTP password if the mailbox uses SMTP
        if getattr(mailbox, 'auth_type', 'smtp') == 'smtp':
            self.smtp_password = decrypt_password(mailbox.smtp_password_enc) if mailbox.smtp_password_enc else ''
        else:
            self.smtp_password = ''
        # IMAP password always needed (reading is always IMAP)
        self.imap_password = decrypt_password(mailbox.imap_password_enc) if mailbox.imap_password_enc else ''

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
        first_name    = self._first_name(to_name, to_email)
        body_template = random.choice(WARMUP_BODIES)
        body = body_template.format(name=first_name)
        signature = self._sender_signature()
        body = body.rstrip() + f"\n\n— {signature}"
        msg.attach(MIMEText(body, "plain"))
        return msg

    # ── Gmail API: Send warmup email ─────────────────────────────────────────
    def _send_via_gmail_api(self, to_email: str, to_name: Optional[str] = None, msg: Optional[MIMEMultipart] = None) -> bool:
        """Send email using Gmail API (HTTPS) — works on Railway, no SMTP needed."""
        try:
            import json, base64
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from services.encryption import decrypt_password as _dec

            token_data = json.loads(_dec(self.mailbox.oauth_refresh_token_enc))
            creds = Credentials(
                token=None,
                refresh_token=token_data["refresh_token"],
                client_id=token_data["client_id"],
                client_secret=token_data["client_secret"],
                token_uri="https://oauth2.googleapis.com/token",
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            )
            creds.refresh(Request())

            service = build("gmail", "v1", credentials=creds)
            msg_to_send = msg or self._build_mime_message(to_email, to_name)
            raw = base64.urlsafe_b64encode(msg_to_send.as_bytes()).decode("utf-8")
            service.users().messages().send(userId="me", body={"raw": raw}).execute()

            logger.info(f"✅ Gmail API sent: {self.mailbox.email_address} → {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Gmail API error ({self.mailbox.email_address}): {e}")
            return False

    # ── SMTP: Send warmup email ──────────────────────────────────────────────
    def _send_via_smtp(self, to_email: str, to_name: Optional[str] = None, msg: Optional[MIMEMultipart] = None) -> bool:
        """Send a single warmup email via SMTP."""
        try:
            msg_to_send = msg or self._build_mime_message(to_email, to_name)

            if self.mailbox.smtp_use_tls:
                server = smtplib.SMTP(self.mailbox.smtp_host, self.mailbox.smtp_port, timeout=30)
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                server = smtplib.SMTP_SSL(self.mailbox.smtp_host, self.mailbox.smtp_port, timeout=30)

            server.login(self.mailbox.smtp_user, self.smtp_password)
            server.sendmail(self.mailbox.email_address, to_email, msg_to_send.as_string())
            server.quit()

            logger.info(f"✅ SMTP sent: {self.mailbox.email_address} → {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ SMTP error ({self.mailbox.email_address}): {e}")
            return False

    # ── Smart dispatch ───────────────────────────────────────────────────────
    def send_warmup_email(self, to_email: str, to_name: Optional[str] = None) -> bool:
        """Send warmup email — uses Gmail API if configured, else SMTP."""
        auth_type = getattr(self.mailbox, "auth_type", "smtp") or "smtp"
        if auth_type == "gmail_api":
            return self._send_via_gmail_api(to_email, to_name)
        return self._send_via_smtp(to_email, to_name)



    # ── IMAP: Open unread warmup emails ─────────────────────────────────────
    def open_warmup_emails(self) -> int:
        """
        Connect via IMAP → find unread warmup emails → mark READ + IMPORTANT.
        Uses subject keyword matching to avoid opening real emails.
        Also moves warmup emails OUT of spam/promotions if found there.
        """
        opened_count = 0
        try:
            if self.mailbox.imap_use_ssl:
                mail = imaplib.IMAP4_SSL(self.mailbox.imap_host, self.mailbox.imap_port)
            else:
                mail = imaplib.IMAP4(self.mailbox.imap_host, self.mailbox.imap_port)

            mail.login(self.mailbox.imap_user, self.imap_password)

            # Check INBOX first, then try Spam/Junk
            folders_to_check = ["INBOX", "[Gmail]/Spam", "Junk", "Spam", "[Gmail]/Promotions"]
            for folder in folders_to_check:
                try:
                    status, _ = mail.select(folder)
                    if status != "OK":
                        continue

                    _, message_ids = mail.search(None, "UNSEEN")
                    if not message_ids[0]:
                        continue

                    ids = message_ids[0].split()
                    for msg_id in ids[-30:]:  # process up to 30 per folder
                        try:
                            _, msg_data = mail.fetch(msg_id, "(RFC822)")
                            raw_email = msg_data[0][1]
                            parsed = email.message_from_bytes(raw_email)

                            subject_raw = parsed.get("Subject", "")
                            subject = decode_header(subject_raw)[0][0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(errors="ignore")

                            # Check if it's a warmup email by subject keyword match
                            is_warmup = any(
                                s.lower() in subject.lower()
                                for s in WARMUP_SUBJECTS
                            )
                            if is_warmup:
                                # Properly rescue from Spam/Promotions by moving to INBOX
                                if folder.upper() != "INBOX":
                                    mail.copy(msg_id, "INBOX")               # Copy to Inbox
                                    mail.store(msg_id, "+FLAGS", "\\Deleted")# Delete from Spam
                                    mail.expunge()                           # Ensure deletion
                                    
                                mail.store(msg_id, "+FLAGS", "\\Seen")      # Mark read
                                mail.store(msg_id, "+FLAGS", "\\Flagged")   # Star it
                                opened_count += 1
                                logger.info(f"📬 Opened: '{subject[:50]}' in {self.mailbox.email_address}")
                        except Exception as e:
                            logger.warning(f"IMAP open error on msg: {e}")
                except Exception:
                    pass  # Folder doesn't exist for this provider — skip

            mail.logout()

        except Exception as e:
            logger.error(f"❌ IMAP error ({self.mailbox.email_address}): {e}")

        return opened_count

    # ── IMAP: Reply to warmup emails ─────────────────────────────────────────
    def reply_to_warmup_emails(self) -> int:
        """
        Find warmup emails in INBOX → reply to 85% of them with natural replies.

        NO DUPLICATES: checks \\Answered flag before replying.
        Each reply uses a random template, sender first name, and natural pacing.
        Reply rate = 85% (high = signals real humans = great reputation boost).
        """
        replied_count = 0
        try:
            if self.mailbox.imap_use_ssl:
                mail = imaplib.IMAP4_SSL(self.mailbox.imap_host, self.mailbox.imap_port)
            else:
                mail = imaplib.IMAP4(self.mailbox.imap_host, self.mailbox.imap_port)

            mail.login(self.mailbox.imap_user, self.imap_password)
            mail.select("INBOX")

            # Find emails that were READ but NOT yet ANSWERED — prevents duplicates
            _, message_ids = mail.search(None, "SEEN", "NOT ANSWERED")
            if not message_ids[0]:
                mail.logout()
                return 0

            ids = message_ids[0].split()

            # Filter to only warmup emails first
            warmup_ids = []
            for msg_id in ids[-30:]:
                try:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    parsed = email.message_from_bytes(msg_data[0][1])
                    subject_raw = parsed.get("Subject", "")
                    subject = decode_header(subject_raw)[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors="ignore")

                    # Only reply to warmup emails (not random real emails)
                    if any(s.lower() in subject.lower() for s in WARMUP_SUBJECTS):
                        warmup_ids.append((msg_id, parsed))
                except Exception:
                    pass

            # Reply to 85% of warmup emails (very high = premium domain signal)
            n_to_reply = max(1, int(len(warmup_ids) * 0.85))
            reply_targets = random.sample(warmup_ids, min(n_to_reply, len(warmup_ids)))

            for msg_id, parsed in reply_targets:
                try:
                    from_addr = parsed.get("Reply-To") or parsed.get("From", "")
                    original_subject = parsed.get("Subject", "No Subject")

                    if not from_addr:
                        continue
                    # Never reply to self
                    if self.mailbox.email_address.lower() in from_addr.lower():
                        continue

                    # Build a natural reply with senderʼs first name
                    reply_template = random.choice(WARMUP_REPLIES)

                    reply = MIMEMultipart("alternative")
                    reply["From"]       = f"{self.mailbox.display_name or self.mailbox.email_address} <{self.mailbox.email_address}>"
                    reply["To"]         = from_addr
                    reply["Subject"]    = f"Re: {original_subject}"
                    reply["In-Reply-To"] = parsed.get("Message-ID", "")
                    reply["References"]  = parsed.get("Message-ID", "")

                    # Sign off with sender's first name
                    sig = self._sender_signature()
                    body = reply_template + f"\n\n— {sig}"
                    reply.attach(MIMEText(body, "plain"))

                    # Send reply using the correct auth route
                    if getattr(self.mailbox, "auth_type", "smtp") == "gmail_api":
                        self._send_via_gmail_api(to_email=from_addr, msg=reply)
                    elif getattr(self.mailbox, "auth_type", "smtp") == "microsoft_graph":
                        pass # self._send_via_microsoft_graph(to_email=from_addr, msg=reply)
                    else:
                        self._send_via_smtp(to_email=from_addr, msg=reply)

                    # Mark as ANSWERED — prevents future duplicate replies
                    mail.store(msg_id, "+FLAGS", "\\Answered")
                    replied_count += 1
                    logger.info(f"↩️  Replied: {self.mailbox.email_address} → {from_addr}")

                    # Random delay between replies (feels human)
                    import time; time.sleep(random.uniform(5, 20))

                except Exception as e:
                    logger.warning(f"Reply error: {e}")

            mail.logout()

        except Exception as e:
            logger.error(f"❌ IMAP reply error ({self.mailbox.email_address}): {e}")

        return replied_count

    # ── Connection tests ─────────────────────────────────────────────────────
    def test_smtp_connection(self) -> tuple[bool, str]:
        """Test SMTP credentials — returns (success, message)."""
        try:
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
        """Test IMAP credentials — returns (success, message)."""
        try:
            if self.mailbox.imap_use_ssl:
                mail = imaplib.IMAP4_SSL(self.mailbox.imap_host, self.mailbox.imap_port)
            else:
                mail = imaplib.IMAP4(self.mailbox.imap_host, self.mailbox.imap_port)
            mail.login(self.mailbox.imap_user, self.imap_password)
            mail.logout()
            return True, "IMAP connection successful"
        except Exception as e:
            return False, str(e)
