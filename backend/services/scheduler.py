"""
Scheduler — Runs the warmup engine every hour throughout IST working hours.

The engine itself decides whether it's inside the send window (9 AM – 9 PM IST).
By running every hour, emails are spread naturally across the day instead of
one giant 9 AM burst that looks like a bot.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from database import SessionLocal
from services.warmup_engine import WarmupEngine

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def warmup_hourly_job():
    """
    Called every hour. The WarmupEngine checks if we're inside IST working hours.
    If yes → sends a micro-batch. If no → returns immediately (no emails sent).
    """
    logger.info("⏰ Hourly warmup job triggered")
    db = SessionLocal()
    try:
        engine = WarmupEngine(db)
        result = engine.run_daily_cycle()
        logger.info(f"📊 Warmup result: {result['status']} — {result.get('total_sent', 0)} sent")
    except Exception as e:
        logger.error(f"❌ Warmup job failed: {e}", exc_info=True)
    finally:
        db.close()


def scheduler_listener(event):
    if event.exception:
        logger.error(f"Scheduler job {event.job_id} crashed: {event.exception}")
    else:
        logger.info(f"Scheduler job {event.job_id} completed OK")


def start_scheduler():
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    scheduler.add_listener(scheduler_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # Run every hour — engine decides if it should send based on IST window
    scheduler.add_job(
        warmup_hourly_job,
        trigger=IntervalTrigger(hours=1),
        id="hourly_warmup",
        name="Hourly Email Warmup Micro-Batch",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=1800,  # 30 min grace
    )

    scheduler.start()
    logger.info("✅ Scheduler started — warmup runs every hour (active 9 AM – 9 PM IST)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_next_run() -> str:
    job = scheduler.get_job("hourly_warmup")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return "Not scheduled"
