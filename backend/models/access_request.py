"""
AccessRequest Model — Stores "Request Access" form submissions from the landing page.
These appear in the Super Admin panel as pending leads.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from database import Base


class AccessRequest(Base):
    """
    A potential client who submitted the "Request Access" form on the login page.
    Super Admin reviews these and can approve → auto-creates a Company + User.
    """
    __tablename__ = "access_requests"

    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name    = Column(String(255), nullable=False)
    email        = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    phone        = Column(String(50), nullable=True)
    message      = Column(Text, nullable=True)          # "Tell us about your use case"

    is_reviewed  = Column(Boolean, default=False)       # Admin has seen it
    is_approved  = Column(Boolean, default=False)       # Admin approved → company created

    created_at   = Column(DateTime, default=datetime.utcnow)
    reviewed_at  = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AccessRequest {self.email} [{self.company_name}]>"
