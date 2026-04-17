"""
Warmup Engine — Fully Dynamic, Human-Like Core Logic
═══════════════════════════════════════════════════════════════════════════════

HOW THIS ENGINE WORKS:
───────────────────────────────────────────────────────────────────────────────
Every mailbox (VIP or Helper) sends warmup emails to ALL other mailboxes in
the company pool PLUS all External Contacts (manual team members / colleagues).

POOL COMPOSITION (fully dynamic — no hardcoded size):
  • VIP Mailboxes  — the rwaltz.org/services/dev domains we are warming up
  • Helper Mailboxes — Gmail/personal accounts used to boost the pool
  • External Contacts — team members (strikin.com etc.) who reply manually

SENDING LOGIC:
  • Runs on an interval basis (called every hour by the scheduler)
  • Each call, each mailbox sends only a FRACTION of its daily quota
  • Spread randomly through 9 AM – 9 PM IST (3:30 – 15:30 UTC)
  • Different random delay, different random message template each time
  • Zero sending outside working hours (looks like a real human at a desk)

VOLUME RAMP (3-week accelerated schedule for fast campaign readiness):
  Week 1: 8 emails/day per mailbox  (1 email per person in pool ~8-10 people)
  Week 2: 20 emails/day per mailbox (2 emails per some people in pool)
  Week 3: 40 emails/day per mailbox (3+ emails per person)
  Week 4+: 60/day  (fully warm — ready for cold outreach)
═══════════════════════════════════════════════════════════════════════════════
"""
import random
import logging
from datetime import datetime, date, timezone
from typing import List
from sqlalchemy.orm import Session
from models.mailbox import Mailbox, WarmupStatus
from models.warmup_log import WarmupLog
from models.external_contact import ExternalContact
from services.email_service import EmailService

logger = logging.getLogger(__name__)

# ── Accelerated 3-week ramp ──────────────────────────────────────────────────
WEEKLY_VOLUME = {
    1:  8,   # Week 1 — 1 email to each person in an ~8-person pool
    2:  20,  # Week 2 — 2 emails to most people
    3:  40,  # Week 3 — 3-4 emails per person per day (very active)
    4:  50,
    5:  55,
    6:  60,
    7:  60,
    8:  60,
}

DAYS_PER_WEEK = 7

# ── IST working hours in UTC (9 AM IST = 3:30 UTC, 9 PM IST = 15:30 UTC) ────
SEND_WINDOW_START_UTC = 3   # 3 AM UTC = 8:30 AM IST (start a bit early)
SEND_WINDOW_END_UTC   = 16  # 4 PM UTC = 9:30 PM IST


def get_daily_limit(week: int) -> int:
    return WEEKLY_VOLUME.get(min(week, 8), 60)


def is_within_send_window() -> bool:
    """Return True if current UTC hour is within IST working hours."""
    now_utc_hour = datetime.now(timezone.utc).hour
    return SEND_WINDOW_START_UTC <= now_utc_hour <= SEND_WINDOW_END_UTC


def calculate_warmup_score(emails_sent: int, emails_opened: int, emails_replied: int, week: int) -> float:
    """
    Score = open_rate (40%) + reply_rate (40%) + volume_progress (20%)
    Range: 0 – 100
    """
    if emails_sent == 0:
        return 0.0
    open_rate       = min(emails_opened / emails_sent, 1.0)
    reply_rate      = min(emails_replied / emails_sent, 1.0)
    volume_progress = min(week / 8, 1.0)
    return round((open_rate * 40) + (reply_rate * 40) + (volume_progress * 20), 2)


class WarmupEngine:
    """
    Orchestrates hourly warmup micro-batches for all active mailboxes.
    Called every hour by the scheduler — sends a fraction of the daily quota
    each time so sends are spread naturally across the day.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Public entry point (called by scheduler every hour) ──────────────────
    def run_daily_cycle(self, company_id: str = None) -> dict:
        """
        Run one hourly micro-batch for all active mailboxes.
        
        If called outside IST working hours (9 AM – 9 PM), returns early.
        Otherwise, sends a random fraction of each mailbox's daily quota.
        """
        if not is_within_send_window():
            logger.info(f"💤 Outside send window — engine idle until {SEND_WINDOW_START_UTC}:00 UTC")
            return {"status": "outside_window", "processed": 0}

        logger.info("🔥 Warmup micro-batch starting...")

        # Fetch all active automated mailboxes
        query = self.db.query(Mailbox).filter(Mailbox.warmup_status == WarmupStatus.active)
        if company_id:
            query = query.filter(Mailbox.company_id == company_id)
        active_mailboxes = query.all()

        if not active_mailboxes:
            return {"status": "no_mailboxes", "processed": 0}

        if len(active_mailboxes) < 2:
            return {"status": "insufficient_pool", "processed": 0, "note": "Need at least 2 mailboxes"}

        logger.info(f"📬 Automated pool: {len(active_mailboxes)} mailboxes")

        results = []
        for mailbox in active_mailboxes:
            # Stagger each mailbox with a random sleep (feels human)
            import time; time.sleep(random.uniform(3, 12))
            result = self._process_mailbox(mailbox, active_mailboxes)
            results.append(result)

        self._advance_weeks(active_mailboxes)

        total_sent    = sum(r.get("sent", 0) for r in results)
        total_opened  = sum(r.get("opened", 0) for r in results)
        total_replied = sum(r.get("replied", 0) for r in results)

        logger.info(f"✅ Micro-batch: {total_sent} sent, {total_opened} opened, {total_replied} replied")
        return {
            "status": "completed",
            "processed": len(active_mailboxes),
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_replied": total_replied,
            "results": results,
        }

    # ── Process a single mailbox ──────────────────────────────────────────────
    def _process_mailbox(self, mailbox: Mailbox, pool: List[Mailbox]) -> dict:
        """
        Send warmup emails from one mailbox to a dynamic mix of:
          • Other automated mailboxes in the pool (auto-open + auto-reply)
          • External contacts in the same company (human manual replies)
        
        Each call sends only a micro-batch fraction of the daily limit.
        Multiple hourly calls across the day complete the full daily quota.
        """
        logger.info(f"  → {mailbox.email_address} (Week {mailbox.current_week})")

        daily_limit = mailbox.daily_limit if mailbox.daily_limit else get_daily_limit(mailbox.current_week)

        # ── Build combined recipient list ────────────────────────────────────
        # Automated pool members (exclude self)
        auto_recipients = [m for m in pool if m.id != mailbox.id]

        # External contacts for this company
        ext_contacts = (
            self.db.query(ExternalContact)
            .filter(
                ExternalContact.company_id == mailbox.company_id,
                ExternalContact.is_active == True,
            )
            .all()
        )

        # Combine: 70% automated, 30% external (or all automated if no externals)
        all_targets = []
        if ext_contacts:
            n_auto = max(1, int(daily_limit * 0.7))
            n_ext  = max(1, int(daily_limit * 0.3))
            auto_pick = random.sample(auto_recipients, min(n_auto, len(auto_recipients)))
            ext_pick  = random.sample(ext_contacts, min(n_ext, len(ext_contacts)))
            all_targets = auto_pick + ext_pick
        else:
            # No external contacts yet — send to all automated pool members or daily_limit
            all_targets = random.sample(auto_recipients, min(daily_limit, len(auto_recipients)))

        # Shuffle so order looks completely random
        random.shuffle(all_targets)

        # ── Micro-batch sizing: send ~1/8th of daily quota per hourly call ──
        # This spreads emails naturally across the 8 active hours of the day
        micro_batch_size = max(1, len(all_targets) // 8)
        targets = all_targets[:micro_batch_size]

        svc = EmailService(mailbox)
        sent_count   = 0
        failed_count = 0

        # ── SEND PHASE ───────────────────────────────────────────────────────
        for target in targets:
            if hasattr(target, "email_address"):
                to_email = target.email_address
                to_name  = getattr(target, "display_name", None)
            else:
                continue  # safety guard

            success = svc.send_warmup_email(to_email=to_email, to_name=to_name)
            if success:
                sent_count += 1
            else:
                failed_count += 1
            import time; time.sleep(random.uniform(15, 90))  # very human pacing

        if sent_count == 0:
            return {"mailbox": mailbox.email_address, "sent": 0, "opened": 0, "replied": 0}

        # ── OPEN PHASE (short random delay before checking inbox) ────────────
        import time; time.sleep(random.uniform(60, 180))
        opened_count = svc.open_warmup_emails()

        # ── REPLY PHASE (another short delay) ───────────────────────────────
        import time; time.sleep(random.uniform(30, 90))
        replied_count = svc.reply_to_warmup_emails()

        # ── SCORE + LOG ──────────────────────────────────────────────────────
        score      = calculate_warmup_score(sent_count, opened_count, replied_count, mailbox.current_week)
        open_rate  = round(opened_count / sent_count, 3) if sent_count > 0 else 0
        reply_rate = round(replied_count / sent_count, 3) if sent_count > 0 else 0

        log_entry = WarmupLog(
            mailbox_id        = mailbox.id,
            log_date          = date.today(),
            emails_sent       = sent_count,
            emails_opened     = opened_count,
            emails_replied    = replied_count,
            emails_failed     = failed_count,
            open_rate         = open_rate,
            reply_rate        = reply_rate,
            score             = score,
            week_number       = mailbox.current_week,
            daily_limit_used  = len(targets),
        )
        self.db.add(log_entry)

        mailbox.total_sent     += sent_count
        mailbox.total_opened   += opened_count
        mailbox.total_replied  += replied_count
        mailbox.warmup_score    = score
        mailbox.last_warmup_at  = datetime.utcnow()
        if not mailbox.warmup_started_at:
            mailbox.warmup_started_at = datetime.utcnow()

        self.db.commit()

        logger.info(
            f"    ✅ {mailbox.email_address}: sent={sent_count}, opened={opened_count}, "
            f"replied={replied_count}, score={score}"
        )

        return {
            "mailbox":  mailbox.email_address,
            "sent":     sent_count,
            "opened":   opened_count,
            "replied":  replied_count,
            "score":    score,
            "week":     mailbox.current_week,
        }

    # ── Advance week counter ─────────────────────────────────────────────────
    def _advance_weeks(self, mailboxes: List[Mailbox]):
        for mailbox in mailboxes:
            if mailbox.warmup_started_at and mailbox.current_week < 8:
                days_active    = (datetime.utcnow() - mailbox.warmup_started_at).days
                expected_week  = min((days_active // DAYS_PER_WEEK) + 1, 8)
                if expected_week > mailbox.current_week:
                    logger.info(f"  📈 {mailbox.email_address}: Week {mailbox.current_week} → Week {expected_week}")
                    mailbox.current_week = expected_week
                    mailbox.daily_limit  = get_daily_limit(expected_week)
                    if expected_week >= 8:
                        mailbox.warmup_status = WarmupStatus.completed
                        logger.info(f"  🎉 {mailbox.email_address}: WARMUP COMPLETE!")
        self.db.commit()

    # ── Manual trigger (single mailbox — for testing) ────────────────────────
    def run_single_mailbox(self, mailbox_id: str) -> dict:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            return {"error": "Mailbox not found"}

        pool = (
            self.db.query(Mailbox)
            .filter(
                Mailbox.company_id == mailbox.company_id,
                Mailbox.warmup_status == WarmupStatus.active,
            )
            .all()
        )

        if len(pool) < 2:
            return {"error": "Need at least 2 active mailboxes in company pool"}

        return self._process_mailbox(mailbox, pool)
