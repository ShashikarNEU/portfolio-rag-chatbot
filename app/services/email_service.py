from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
        html_content = (
            f"<h2>New Portfolio Inquiry</h2>"
            f"<p><strong>Name:</strong> {name}</p>"
            f"<p><strong>Email:</strong> <a href='mailto:{email}'>{email}</a></p>"
            f"<hr>"
            f"<p><strong>Message:</strong></p>"
            f"<p>{inquiry}</p>"
        )
        message = Mail(
            from_email=self._sender,
            to_emails=self._recipient,
            subject=f"Portfolio Contact: {name}",
            html_content=html_content,
        )
        try:
            response = self._client.send(message)
            return 200 <= response.status_code < 300
        except Exception:
            return False
