"""Email sending — graceful degradation when SMTP is not configured."""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "sentinel@engine.local")


def is_email_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email. Returns True if sent, False if SMTP not configured or failed."""
    if not is_email_configured():
        logger.debug(f"SMTP not configured — skipping email to {to}: {subject}")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


def send_verification_email(to: str, token: str, base_url: str = "") -> bool:
    """Send email verification link."""
    verify_url = f"{base_url}/verify?token={token}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">Verify your Sentinel account</h2>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_url}" style="display: inline-block; padding: 10px 24px;
           background: #34d399; color: #fff; text-decoration: none; border-radius: 6px;
           font-weight: 600;">Verify Email</a></p>
        <p style="color: #666; font-size: 12px; margin-top: 20px;">
            If you didn't create this account, you can ignore this email.
        </p>
    </div>
    """
    return send_email(to, "Verify your Sentinel account", html)


def send_password_reset_email(to: str, token: str, base_url: str = "") -> bool:
    """Send password reset link."""
    reset_url = f"{base_url}/reset-password?token={token}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">Reset your password</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}" style="display: inline-block; padding: 10px 24px;
           background: #34d399; color: #fff; text-decoration: none; border-radius: 6px;
           font-weight: 600;">Reset Password</a></p>
        <p style="color: #666; font-size: 12px; margin-top: 20px;">
            This link expires in 1 hour. If you didn't request this, you can ignore this email.
        </p>
    </div>
    """
    return send_email(to, "Reset your Sentinel password", html)
