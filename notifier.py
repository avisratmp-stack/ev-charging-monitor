import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_availability_email(config, station_name, new_status, timestamp):
    if not config.SMTP_ENABLED:
        return
    if new_status != "available":
        return

    recipients = [r.strip() for r in config.SMTP_TO.split(",") if r.strip()]
    if not recipients:
        return

    subject = f"EV Station Available: {station_name}"
    body_html = f"""\
<div style="font-family:sans-serif; padding:20px; background:#0f1117; color:#e8eaed;">
    <h2 style="color:#10b981; margin-top:0;">Station Available!</h2>
    <p><strong>{station_name}</strong> is now available for charging.</p>
    <p style="color:#9aa0a6;">Detected at: {timestamp}</p>
</div>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.sendmail(config.SMTP_FROM, recipients, msg.as_string())
        logger.info(f"Email sent for {station_name}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
