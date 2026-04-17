"""
Company Model — each tenant in the SaaS platform
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from database import Base
import enum


class CompanyStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    suspended = "suspended"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    status = Column(Enum(CompanyStatus), default=CompanyStatus.pending, nullable=False)
    
    # Branding — each client can have custom accent color + logo
    accent_color = Column(String(20), default="#F97316")  # orange default
    logo_url = Column(String(500), nullable=True)         # uploaded logo path
    website = Column(String(200), nullable=True)
    
    # Meta
    is_neurogenix = Column(Boolean, default=False)  # True only for Neurogenix company
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    mailboxes = relationship("Mailbox", back_populates="company", cascade="all, delete-orphan")
    external_contacts = relationship("ExternalContact", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.name} [{self.status}]>"
