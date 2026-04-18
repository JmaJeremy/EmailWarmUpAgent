"""
Mailbox Model — SMTP/IMAP credentials + warmup state
Supports auth_type: smtp | gmail_api | microsoft_graph
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Integer, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
import enum


class WarmupStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    error = "error"
    pending = "pending"  # newly added, not yet started


class Mailbox(Base):
    __tablename__ = "mailboxes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # ── Identity ────────────────────────────────────────────────────────────
    email_address = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)

    # ── Auth type (smtp | gmail_api | microsoft_graph) ──────────────────────
    auth_type = Column(String(32), default="smtp", nullable=False)
    oauth_refresh_token_enc = Column(Text, nullable=True)  # encrypted OAuth refresh token

    # ── SMTP (Sending) ───────────────────────────────────────────────────────
    smtp_host = Column(String(255), nullable=False)
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String(255), nullable=False)
    smtp_password_enc = Column(Text, nullable=False)  # fernet-encrypted
    smtp_use_tls = Column(Boolean, default=True)

    # ── IMAP (Reading/Replying) ──────────────────────────────────────────────
    imap_host = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993)
    imap_user = Column(String(255), nullable=False)
    imap_password_enc = Column(Text, nullable=False)  # fernet-encrypted
    imap_use_ssl = Column(Boolean, default=True)

    # ── Warmup State ─────────────────────────────────────────────────────────
    warmup_status = Column(Enum(WarmupStatus), default=WarmupStatus.pending, nullable=False)
    current_week = Column(Integer, default=1)       # Week 1-8 of ramp schedule
    daily_limit = Column(Integer, default=3)        # Emails sent per day
    total_sent = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_replied = Column(Integer, default=0)
    warmup_score = Column(Float, default=0.0)       # 0-100 health score
    
    # ── Dates ────────────────────────────────────────────────────────────────
    warmup_started_at = Column(DateTime, nullable=True)
    last_warmup_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="mailboxes")
    warmup_logs = relationship("WarmupLog", back_populates="mailbox", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Mailbox {self.email_address} [Week {self.current_week}]>"
