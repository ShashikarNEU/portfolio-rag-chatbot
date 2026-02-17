from datetime import datetime, timezone

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, ReplyTo

from app.config import settings


class EmailService:
    """SendGrid wrapper for sending portfolio contact emails."""

    _instance: "EmailService | None" = None

    def __init__(self) -> None:
        self._client = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        self._sender = settings.sender_email or settings.recipient_email
        self._recipient = settings.recipient_email

    @classmethod
    def get_instance(cls) -> "EmailService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def send_contact_email(
        self, name: str, email: str, inquiry: str,
    ) -> bool:
        """Send a contact email to the portfolio owner.

        Returns True on 2xx status, False otherwise.
        """
        timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

        plain_content = (
            f"New Portfolio Inquiry\n"
            f"{'=' * 40}\n\n"
            f"You received a new message through your portfolio chatbot.\n\n"
            f"Sender Details\n"
            f"{'-' * 40}\n"
            f"Name:  {name}\n"
            f"Email: {email}\n"
            f"Date:  {timestamp}\n\n"
            f"Message\n"
            f"{'-' * 40}\n"
            f"{inquiry}\n\n"
            f"{'=' * 40}\n"
            f"Reply directly to this email to respond to {name}.\n"
            f"This message was sent via your Portfolio RAG Chatbot.\n"
        )

        html_content = (
            f"<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;'>"
            f"  <div style='background: #1a1a2e; color: #ffffff; padding: 24px; border-radius: 8px 8px 0 0;'>"
            f"    <h1 style='margin: 0; font-size: 22px;'>New Portfolio Inquiry</h1>"
            f"    <p style='margin: 4px 0 0; opacity: 0.8; font-size: 13px;'>{timestamp}</p>"
            f"  </div>"
            f"  <div style='border: 1px solid #e0e0e0; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;'>"
            f"    <p style='margin: 0 0 16px; color: #555; font-size: 14px;'>"
            f"      You received a new message through your portfolio chatbot."
            f"    </p>"
            f"    <table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>"
            f"      <tr>"
            f"        <td style='padding: 8px 12px; background: #f8f9fa; font-weight: bold; width: 80px; border: 1px solid #e0e0e0;'>Name</td>"
            f"        <td style='padding: 8px 12px; border: 1px solid #e0e0e0;'>{name}</td>"
            f"      </tr>"
            f"      <tr>"
            f"        <td style='padding: 8px 12px; background: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0;'>Email</td>"
            f"        <td style='padding: 8px 12px; border: 1px solid #e0e0e0;'>"
            f"          <a href='mailto:{email}' style='color: #0066cc;'>{email}</a>"
            f"        </td>"
            f"      </tr>"
            f"    </table>"
            f"    <div style='background: #f8f9fa; padding: 16px; border-radius: 6px; border-left: 4px solid #1a1a2e;'>"
            f"      <h3 style='margin: 0 0 8px; font-size: 14px; color: #333;'>Message</h3>"
            f"      <p style='margin: 0; color: #444; line-height: 1.6;'>{inquiry}</p>"
            f"    </div>"
            f"    <hr style='border: none; border-top: 1px solid #e0e0e0; margin: 24px 0 12px;'>"
            f"    <p style='margin: 0; font-size: 12px; color: #999;'>"
            f"      Reply directly to this email to respond to {name}. "
            f"      Sent via Portfolio RAG Chatbot."
            f"    </p>"
            f"  </div>"
            f"</div>"
        )

        message = Mail(
            from_email=self._sender,
            to_emails=self._recipient,
            subject=f"Portfolio Contact: {name}",
            plain_text_content=plain_content,
            html_content=html_content,
        )
        message.reply_to = ReplyTo(email, name)

        try:
            response = self._client.send(message)
            return 200 <= response.status_code < 300
        except Exception:
            return False
