from email.message import EmailMessage
import logging

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_otp_email_message(
    to_email: str, otp: str, subject_prefix: str = "Verification Code"
) -> EmailMessage:
    """Build the multipart HTML verification email message."""
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = f"[{settings.app_name}] {subject_prefix}: {otp}"

    plain_text = (
        f"Hello,\n\n"
        f"Your verification code for {subject_prefix} is: {otp}\n"
        f"This code is valid for 5 minutes. Please do not share it with anyone.\n\n"
        f"Regards,\n{settings.app_name}"
    )
    msg.set_content(plain_text)

    html_content = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 520px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #b91c1c; color: #ffffff; padding: 18px; border-radius: 12px 12px 0 0; text-align: center;">
        <h2 style="margin: 0; font-size: 20px; font-weight: bold;">🦅 {settings.app_name}</h2>
    </div>
    <div style="border: 1px solid #e2e8f0; border-top: none; padding: 28px 24px; border-radius: 0 0 12px 12px; background-color: #ffffff;">
        <p style="margin-top: 0; font-size: 15px;">Hello HUST Student,</p>
        <p style="font-size: 14px; color: #475569;">Your verification code for <strong>{subject_prefix}</strong> is:</p>
        <div style="text-align: center; margin: 24px 0;">
            <span style="display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #b91c1c; background-color: #fef2f2; border: 1px dashed #f87171; padding: 10px 24px; border-radius: 8px;">
                {otp}
            </span>
        </div>
        <p style="font-size: 13px; color: #64748b; margin-bottom: 0;">This code is valid for <strong>5 minutes</strong>. Never share this code with anyone to protect your account.</p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0 16px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 0;">Automated email from {settings.app_name}.</p>
    </div>
</body>
</html>
"""
    msg.add_alternative(html_content, subtype="html")
    return msg


async def send_otp_email(
    to_email: str, otp: str, subject_prefix: str = "Verification Code"
) -> bool:
    """Send HTML verification OTP email to HUST student via aiosmtplib.

    Returns True if delivery succeeded, False if SMTP sending failed.
    Never logs raw emails, recipient addresses, or OTP values.
    """
    try:
        msg = build_otp_email_message(to_email, otp, subject_prefix)

        clean_password = (
            settings.email_password.replace(" ", "")
            if settings.email_password
            else None
        )

        is_ssl = settings.email_port == 465
        start_tls = True if (settings.email_port == 587 or (settings.email_use_tls and not is_ssl)) else None

        await aiosmtplib.send(
            msg,
            hostname=settings.email_host,
            port=settings.email_port,
            username=settings.email_username or None,
            password=clean_password,
            use_tls=is_ssl,
            start_tls=start_tls,
            timeout=15.0,
        )
        logger.info("Successfully sent verification OTP email.")
        return True
    except Exception as e:
        logger.warning("SMTP delivery failed with error: %s", type(e).__name__)
        return False
