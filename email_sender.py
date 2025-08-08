"""
Email sender module for market research reports
Supports SendGrid and SMTP
"""

import os
from typing import Optional
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

load_dotenv()


class EmailSender:
    """Handle email sending through SendGrid or SMTP"""
    
    def __init__(self):
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL')
        self.to_email = os.getenv('TO_EMAIL')
        
    def send_sendgrid(self, subject: str, html_content: str) -> bool:
        """Send email using SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=self.from_email,
                to_emails=self.to_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            
            print(f"Email sent successfully! Status code: {response.status_code}")
            return True
            
        except Exception as e:
            print(f"Error sending email via SendGrid: {e}")
            return False
    
    def send_smtp(self, subject: str, html_content: str, 
                  smtp_server: str = "smtp.gmail.com", 
                  smtp_port: int = 587,
                  smtp_username: Optional[str] = None,
                  smtp_password: Optional[str] = None) -> bool:
        """Send email using SMTP (fallback option)"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            # Create HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            print("Email sent successfully via SMTP!")
            return True
            
        except Exception as e:
            print(f"Error sending email via SMTP: {e}")
            return False
    
    def send(self, subject: str, html_content: str) -> bool:
        """Send email using available method"""
        if self.sendgrid_api_key:
            return self.send_sendgrid(subject, html_content)
        else:
            print("SendGrid API key not found. Use SMTP configuration.")
            # You can add SMTP credentials to .env if needed
            smtp_username = os.getenv('SMTP_USERNAME', self.from_email)
            smtp_password = os.getenv('SMTP_PASSWORD')
            if smtp_password:
                return self.send_smtp(subject, html_content, 
                                    smtp_username=smtp_username,
                                    smtp_password=smtp_password)
            else:
                print("No email configuration found.")
                return False