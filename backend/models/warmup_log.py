"""
WarmupLog Model — daily activity record per mailbox
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class WarmupLog(Base):
    __tablename__ = "warmup_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mailbox_id = Column(String(36), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Daily Stats ──────────────────────────────────────────────────────────
    log_date = Column(Date, default=date.today, nullable=False)
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)    # IMAP-verified opens
    emails_replied = Column(Integer, default=0)   # Auto-reply count
    emails_failed = Column(Integer, default=0)    # SMTP failures
    
    # ── Computed ─────────────────────────────────────────────────────────────
    open_rate = Column(Float, default=0.0)    # emails_opened / emails_sent
    reply_rate = Column(Float, default=0.0)   # emails_replied / emails_sent
    score = Column(Float, default=0.0)        # 0-100 daily warmup score

    # ── Week context ─────────────────────────────────────────────────────────
    week_number = Column(Integer, default=1)
    daily_limit_used = Column(Integer, default=0)

    # ── Notes ────────────────────────────────────────────────────────────────
    notes = Column(Text, nullable=True)   # Error messages or special events

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    mailbox = relationship("Mailbox", back_populates="warmup_logs")

    def __repr__(self):
        return f"<WarmupLog mailbox={self.mailbox_id} date={self.log_date} score={self.score}>"
