import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List, Tuple
from src.core.config import SMTPConfig


class EmailService:
    """Production-grade SMTP email client with TLS, multipart support, and error handling."""

    def __init__(self, config: SMTPConfig):
        self.config = config

    def _create_smtp_client(self) -> smtplib.SMTP:
        server = smtplib.SMTP(self.config.host, self.config.port, timeout=15)
        if self.config.use_tls:
            server.starttls()
        if self.config.user and self.config.password:
            server.login(self.config.user, self.config.password)
        return server

    def test_connection(self) -> Tuple[bool, str]:
        """Verify SMTP host connectivity and authentication."""
        try:
            with self._create_smtp_client() as server:
                server.noop()
            return True, "SMTP connection and credentials verified successfully."
        except Exception as e:
            return False, f"SMTP verification failed: {str(e)}"

    def send_email(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None,
        attachments: Optional[List[Path]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Send an email message with HTML body and optional plain-text fallback and attachments.
        
        Returns:
            (success, error_message)
        """
        if not recipient or "@" not in recipient:
            return False, f"Invalid recipient email address: '{recipient}'"

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        msg["To"] = recipient

        # Alternative body container (plain text + html)
        alt_part = MIMEMultipart("alternative")
        if plain_content:
            alt_part.attach(MIMEText(plain_content, "plain", "utf-8"))
        if html_content:
            alt_part.attach(MIMEText(html_content, "html", "utf-8"))
        msg.attach(alt_part)

        # Attachments
        if attachments:
            for file_path in attachments:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{path.name}"'
                    )
                    msg.attach(part)

        try:
            with self._create_smtp_client() as server:
                server.send_message(msg)
            return True, None
        except smtplib.SMTPAuthenticationError as e:
            return False, f"SMTP Authentication failed: {str(e)}"
        except smtplib.SMTPRecipientsRefused as e:
            return False, f"Recipient refused: {str(e)}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
