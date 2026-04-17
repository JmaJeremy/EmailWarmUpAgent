"""
Dashboard Router — Analytics + Stats for the frontend dashboard
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from database import get_db
from models.mailbox import Mailbox, WarmupStatus
from models.warmup_log import WarmupLog
from models.company import Company
from models.user import User, UserRole
from dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Main dashboard stats for the current company."""
    company_id = current_user.company_id

    # ── Mailbox counts ──────────────────────────────────────────────────────
    total_mailboxes = db.query(Mailbox).filter(Mailbox.company_id == company_id).count()
    active_mailboxes = db.query(Mailbox).filter(
        Mailbox.company_id == company_id,
        Mailbox.warmup_status == WarmupStatus.active,
    ).count()
    completed_mailboxes = db.query(Mailbox).filter(
        Mailbox.company_id == company_id,
        Mailbox.warmup_status == WarmupStatus.completed,
    ).count()

    # ── Today's aggregate stats ─────────────────────────────────────────────
    today = date.today()
    today_logs = (
        db.query(
            func.sum(WarmupLog.emails_sent).label("sent"),
            func.sum(WarmupLog.emails_opened).label("opened"),
            func.sum(WarmupLog.emails_replied).label("replied"),
        )
        .join(Mailbox, WarmupLog.mailbox_id == Mailbox.id)
        .filter(Mailbox.company_id == company_id, WarmupLog.log_date == today)
        .first()
    )

    # ── This week aggregate ─────────────────────────────────────────────────
    week_start = today - timedelta(days=today.weekday())
    week_logs = (
        db.query(
            func.sum(WarmupLog.emails_sent).label("sent"),
            func.sum(WarmupLog.emails_opened).label("opened"),
            func.sum(WarmupLog.emails_replied).label("replied"),
        )
        .join(Mailbox, WarmupLog.mailbox_id == Mailbox.id)
        .filter(Mailbox.company_id == company_id, WarmupLog.log_date >= week_start)
        .first()
    )

    # ── Avg warmup score ────────────────────────────────────────────────────
    avg_score = (
        db.query(func.avg(Mailbox.warmup_score))
        .filter(Mailbox.company_id == company_id)
        .scalar()
        or 0.0
    )

    # ── 30-day trend (for chart) ────────────────────────────────────────────
    since = today - timedelta(days=29)
    daily_trend = (
        db.query(
            WarmupLog.log_date,
            func.sum(WarmupLog.emails_sent).label("sent"),
            func.sum(WarmupLog.emails_opened).label("opened"),
            func.sum(WarmupLog.emails_replied).label("replied"),
            func.avg(WarmupLog.score).label("avg_score"),
        )
        .join(Mailbox, WarmupLog.mailbox_id == Mailbox.id)
        .filter(Mailbox.company_id == company_id, WarmupLog.log_date >= since)
        .group_by(WarmupLog.log_date)
        .order_by(WarmupLog.log_date.asc())
        .all()
    )

    # ── Top mailboxes by score ──────────────────────────────────────────────
    top_mailboxes = (
        db.query(Mailbox)
        .filter(Mailbox.company_id == company_id)
        .order_by(Mailbox.warmup_score.desc())
        .limit(5)
        .all()
    )

    # ── Full Pool Data (for visualizer) ─────────────────────────────────────
    all_mailboxes = db.query(Mailbox).filter(Mailbox.company_id == company_id).all()
    vips = [m for m in all_mailboxes if m.email_address.endswith(('@rwaltz.org', '@rwaltz.services', '@rwaltz.dev'))]
    helpers = [m for m in all_mailboxes if not m.email_address.endswith(('@rwaltz.org', '@rwaltz.services', '@rwaltz.dev'))]
    
    from models.external_contact import ExternalContact
    manuals = db.query(ExternalContact).filter(ExternalContact.company_id == company_id, ExternalContact.is_active == True).all()

    # If the user is NOT rwaltz, fallback: treat mailboxes with the company domain as VIP, others as helpers
    if not vips and all_mailboxes:
        # try to guess VIPs based on domain vs generic
        user_email_domain = current_user.email.split('@')[-1]
        vips = [m for m in all_mailboxes if m.email_address.endswith(f"@{user_email_domain}")]
        helpers = [m for m in all_mailboxes if m not in vips]
        # if still empty, just split them
        if not vips:
            vips = all_mailboxes

    return {
        "company_id": company_id,
        "mailboxes": {
            "total": total_mailboxes,
            "active": active_mailboxes,
            "completed": completed_mailboxes,
            "pending": total_mailboxes - active_mailboxes - completed_mailboxes,
        },
        "today": {
            "sent": int(today_logs.sent or 0),
            "opened": int(today_logs.opened or 0),
            "replied": int(today_logs.replied or 0),
            "open_rate": round((today_logs.opened or 0) / max(today_logs.sent or 1, 1) * 100, 1),
            "reply_rate": round((today_logs.replied or 0) / max(today_logs.sent or 1, 1) * 100, 1),
        },
        "this_week": {
            "sent": int(week_logs.sent or 0),
            "opened": int(week_logs.opened or 0),
            "replied": int(week_logs.replied or 0),
        },
        "avg_warmup_score": round(float(avg_score), 1),
        "trend": [
            {
                "date": str(row.log_date),
                "sent": int(row.sent or 0),
                "opened": int(row.opened or 0),
                "replied": int(row.replied or 0),
                "score": round(float(row.avg_score or 0), 1),
            }
            for row in daily_trend
        ],
        "top_mailboxes": [
            {
                "id": m.id,
                "email": m.email_address,
                "score": m.warmup_score,
                "status": m.warmup_status,
                "week": m.current_week,
            }
            for m in top_mailboxes
        ],
        "pool_data": {
            "vips": [
                {"email": m.email_address, "daily_limit": m.daily_limit, "week": m.current_week}
                for m in vips
            ],
            "helpers": [
                {"email": m.email_address, "daily_limit": m.daily_limit}
                for m in helpers
            ],
            "manuals": [
                {"email": c.email_address}
                for c in manuals
            ]
        }
    }


@router.get("/super-admin")
def super_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Super admin: platform-wide stats across all companies."""
    if current_user.role != UserRole.super_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Super admin only")

    total_companies = db.query(Company).count()
    active_companies = db.query(Company).filter(Company.status == "approved").count()
    pending_companies = db.query(Company).filter(Company.status == "pending").count()
    total_mailboxes = db.query(Mailbox).count()
    active_mailboxes = db.query(Mailbox).filter(Mailbox.warmup_status == WarmupStatus.active).count()

    today = date.today()
    today_send_total = (
        db.query(func.sum(WarmupLog.emails_sent))
        .filter(WarmupLog.log_date == today)
        .scalar() or 0
    )

    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    company_stats = []
    for c in companies:
        mb_count = db.query(Mailbox).filter(Mailbox.company_id == c.id).count()
        active_mb = db.query(Mailbox).filter(
            Mailbox.company_id == c.id, Mailbox.warmup_status == WarmupStatus.active
        ).count()
        avg_score = db.query(func.avg(Mailbox.warmup_score)).filter(Mailbox.company_id == c.id).scalar() or 0
        company_stats.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "accent_color": c.accent_color,
            "logo_url": c.logo_url,
            "mailboxes": mb_count,
            "active_mailboxes": active_mb,
            "avg_score": round(float(avg_score), 1),
            "created_at": c.created_at,
        })

    return {
        "platform": {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "pending_companies": pending_companies,
            "total_mailboxes": total_mailboxes,
            "active_mailboxes": active_mailboxes,
            "emails_sent_today": int(today_send_total),
        },
        "companies": company_stats,
    }
