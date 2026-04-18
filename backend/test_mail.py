import os
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models.mailbox import Mailbox
from services.email_service import EmailService

def test_single_email():
    db = SessionLocal()
    try:
        jay = db.query(Mailbox).filter_by(email_address='jay@rwaltz.org').first()
        joe = db.query(Mailbox).filter_by(email_address='joe@rwaltz.org').first()
        
        if not jay or not joe:
            print("Mailboxes not found.")
            return
            
        print(f"Testing mail from {jay.email_address} (auth: {jay.auth_type}) to {joe.email_address}")
        
        email_service = EmailService(db)
        # Attempt to send a test email from Jay to Joe
        subject = "Test Gmail API via Warmup Platform"
        body = "Hello Joe,\n\nThis is a test from the updated Neurogenix Warmup platform utilizing the Gmail API OAuth bypass.\n\nBest,\nJay"
        
        success = email_service.send_warmup_email(
            from_mailbox=jay,
            to_email=joe.email_address,
            subject=subject,
            body=body
        )
        
        if success:
            print("✅ SUCCESS! The email was sent successfully.")
        else:
            print("❌ FAILED. The email could not be sent.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_single_email()
