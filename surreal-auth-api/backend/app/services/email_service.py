import smtplib
from email.message import EmailMessage

from app.core import config


def send_email(to_email: str, subject: str, body_text: str) -> None:
    if not config.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not set")
    if not config.SMTP_FROM:
        raise RuntimeError("SMTP_FROM is not set (or SMTP_USER is missing)")

    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body_text)

    if config.SMTP_USE_SSL:
        server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT)
    else:
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)

    try:
        server.ehlo()
        if config.SMTP_USE_TLS and not config.SMTP_USE_SSL:
            server.starttls()
            server.ehlo()
        if config.SMTP_USER and config.SMTP_PASSWORD:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass

