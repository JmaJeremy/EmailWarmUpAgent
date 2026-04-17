"""
ExternalContact Model — Manual warmup pool members (no SMTP/IMAP required).
These are real humans (team members, colleagues) who receive warmup emails
and reply manually. They are NOT automated — they are real people helping
build domain trust.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class ExternalContact(Base):
    """
    Represents a manual warmup pool member.
    
    The warmup engine will send emails TO this address from the VIP/Helper
    mailboxes. A real human then manually opens and replies from their inbox.
    No credentials needed — only an email address.
    """
    __tablename__ = "external_contacts"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id  = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    email_address = Column(String(255), nullable=False, index=True)
    display_name  = Column(String(255), nullable=True)
    notes         = Column(Text, nullable=True)       # e.g. "Night shift — replies 9PM-7AM"

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="external_contacts")

    def __repr__(self):
        return f"<ExternalContact {self.email_address}>"
