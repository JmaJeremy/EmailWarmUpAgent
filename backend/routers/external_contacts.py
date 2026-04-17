"""
External Contacts Router — API for managing manual warmup pool members.
No SMTP/IMAP needed — just an email address. The warmup engine sends TO these
people; they reply manually from their own inbox.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from database import SessionLocal
from models.external_contact import ExternalContact
from dependencies import get_current_user

router = APIRouter(prefix="/external-contacts", tags=["External Contacts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ExternalContactCreate(BaseModel):
    email_address: EmailStr
    display_name:  Optional[str] = None
    notes:         Optional[str] = None   # e.g. "Night shift, replies 9PM-7AM"


class ExternalContactOut(BaseModel):
    id:            str
    email_address: str
    display_name:  Optional[str]
    notes:         Optional[str]
    is_active:     bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[ExternalContactOut])
def list_external_contacts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all external contacts for the current company."""
    return (
        db.query(ExternalContact)
        .filter(ExternalContact.company_id == current_user.company_id)
        .order_by(ExternalContact.email_address)
        .all()
    )


@router.post("", response_model=ExternalContactOut, status_code=201)
def add_external_contact(
    data: ExternalContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a new manual team member to the warmup pool."""
    # Prevent duplicates within same company
    existing = (
        db.query(ExternalContact)
        .filter(
            ExternalContact.company_id  == current_user.company_id,
            ExternalContact.email_address == str(data.email_address),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This email is already in your manual pool")

    contact = ExternalContact(
        company_id    = current_user.company_id,
        email_address = str(data.email_address),
        display_name  = data.display_name,
        notes         = data.notes,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_external_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove a contact from the manual pool."""
    contact = (
        db.query(ExternalContact)
        .filter(
            ExternalContact.id         == contact_id,
            ExternalContact.company_id == current_user.company_id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
