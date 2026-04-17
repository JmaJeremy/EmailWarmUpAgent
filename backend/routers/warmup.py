"""
Warmup Router — Trigger warmup cycles, get logs, manual run
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta
from database import get_db
from models.mailbox import Mailbox, WarmupStatus
from models.warmup_log import WarmupLog
from models.user import User, UserRole
from services.warmup_engine import WarmupEngine
from services.scheduler import get_next_run
from dependencies import get_current_user, require_admin, require_super_admin

router = APIRouter(prefix="/warmup", tags=["Warmup"])

WEEKLY_VOLUME = {1: 3, 2: 6, 3: 12, 4: 20, 5: 30, 6: 40, 7: 50, 8: 60}


def _run_warmup_bg(company_id: str, db: Session):
    engine = WarmupEngine(db)
    engine.run_daily_cycle(company_id=company_id)


# ── Trigger warmup for own company ───────────────────────────────────────────
@router.post("/run")
def trigger_warmup(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Manually trigger warmup cycle for current user's company."""
    active = (
        db.query(Mailbox)
        .filter(
            Mailbox.company_id == current_user.company_id,
            Mailbox.warmup_status == WarmupStatus.active,
        )
        .count()
    )
    if active < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 active mailboxes to run warmup"
        )

    background_tasks.add_task(_run_warmup_bg, current_user.company_id, db)
    return {"message": "Warmup cycle started in background", "active_mailboxes": active}


# ── Trigger warmup for all companies (super admin) ───────────────────────────
@router.post("/run-all")
def trigger_warmup_all(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Super admin: run warmup for all active companies."""
    background_tasks.add_task(_run_warmup_bg, None, db)
    return {"message": "Global warmup cycle started"}


# ── Single mailbox manual run ─────────────────────────────────────────────────
@router.post("/run-mailbox/{mailbox_id}")
def trigger_single_mailbox(
    mailbox_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Manually run warmup for a single mailbox."""
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox or mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    def _single_run():
        engine = WarmupEngine(db)
        engine.run_single_mailbox(mailbox_id)

    background_tasks.add_task(_single_run)
    return {"message": f"Warmup started for {mailbox.email_address}"}


# ── Get warmup logs ───────────────────────────────────────────────────────────
@router.get("/logs/{mailbox_id}")
def get_warmup_logs(
    mailbox_id: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get daily warmup logs for a mailbox (last N days)."""
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if current_user.role != UserRole.super_admin and mailbox.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    since = date.today() - timedelta(days=days)
    logs = (
        db.query(WarmupLog)
        .filter(WarmupLog.mailbox_id == mailbox_id, WarmupLog.log_date >= since)
        .order_by(WarmupLog.log_date.asc())
        .all()
    )

    return [
        {
            "date": str(log.log_date),
            "sent": log.emails_sent,
            "opened": log.emails_opened,
            "replied": log.emails_replied,
            "failed": log.emails_failed,
            "open_rate": log.open_rate,
            "reply_rate": log.reply_rate,
            "score": log.score,
            "week": log.week_number,
        }
        for log in logs
    ]


# ── Warmup status overview ────────────────────────────────────────────────────
@router.get("/status")
def warmup_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Overview of warmup status for user's company mailboxes."""
    mailboxes = db.query(Mailbox).filter(Mailbox.company_id == current_user.company_id).all()

    result = []
    for m in mailboxes:
        # Today's log
        today_log = (
            db.query(WarmupLog)
            .filter(WarmupLog.mailbox_id == m.id, WarmupLog.log_date == date.today())
            .first()
        )

        # Progress to next week
        days_until_next_week = max(0, 7 - ((date.today() - (m.warmup_started_at.date() if m.warmup_started_at else date.today())).days % 7))

        result.append({
            "id": m.id,
            "email": m.email_address,
            "display_name": m.display_name,
            "status": m.warmup_status,
            "current_week": m.current_week,
            "daily_limit": WEEKLY_VOLUME.get(m.current_week, 60),
            "next_week_in_days": days_until_next_week,
            "warmup_score": m.warmup_score,
            "total_sent": m.total_sent,
            "total_opened": m.total_opened,
            "total_replied": m.total_replied,
            "last_warmup": m.last_warmup_at,
            "today": {
                "sent": today_log.emails_sent if today_log else 0,
                "opened": today_log.emails_opened if today_log else 0,
                "replied": today_log.emails_replied if today_log else 0,
                "score": today_log.score if today_log else 0,
            },
        })

    return {
        "mailboxes": result,
        "next_scheduled_run": get_next_run(),
    }
