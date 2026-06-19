import html
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "tickets@432bleu.com")
PLAY_URL = os.getenv("PLAY_URL", "https://play.432bleu.com")


def send_ticket_email(
    to_email: str,
    name: str,
    event_name: str,
    event_date: str,
    tier_label: str,
    code: str,
) -> None:
    safe_name = html.escape(name)
    safe_event = html.escape(event_name)
    safe_date = html.escape(event_date)
    safe_tier = html.escape(tier_label)
    safe_code = html.escape(code)

    body = f"""
    <div style="background:#02060a;color:#e0f7ff;font-family:monospace;padding:40px;max-width:600px;margin:0 auto;border:1px solid #0a2a35;">
        <h1 style="color:#00e5ff;letter-spacing:6px;margin:0 0 4px;">432 BLEU</h1>
        <p style="color:#555;margin:0 0 32px;letter-spacing:2px;font-size:12px;">VIRTUAL VENUE</p>

        <h2 style="color:#e0f7ff;font-weight:normal;">Your ticket is confirmed.</h2>
        <p>Hey {safe_name},</p>
        <p>You're in for <strong style="color:#00e5ff;">{safe_event}</strong>.</p>
        <p style="color:#556;">{safe_date}</p>

        <div style="background:#040d10;border:1px solid #00e5ff;padding:28px;margin:28px 0;text-align:center;border-radius:4px;">
            <p style="color:#556;margin:0 0 10px;font-size:12px;letter-spacing:3px;">{safe_tier.upper()} ACCESS CODE</p>
            <p style="font-size:36px;letter-spacing:10px;color:#00e5ff;margin:0;font-weight:bold;">{safe_code}</p>
        </div>

        <p>Enter this code at the door:</p>
        <p><a href="{PLAY_URL}" style="color:#00e5ff;">{PLAY_URL}</a></p>

        <p style="color:#333;font-size:11px;margin-top:40px;border-top:1px solid #0a2a35;padding-top:16px;">
            Single-use code. Do not share. See you in there.
        </p>
    </div>
    """

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=f"Your ticket — {safe_event} | 432 BLEU",
        html_content=body,
    )
    SendGridAPIClient(SENDGRID_API_KEY).send(message)
