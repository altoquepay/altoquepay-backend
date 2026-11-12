import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.iam.application.ports.password_reset_notifier import PasswordResetNotifier
from app.shared.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class SmtpPasswordResetNotifier(PasswordResetNotifier):
    """Sends the reset email by SMTP, or logs the link when no SMTP server is configured."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_reset_link(self, email: str, link: str) -> None:
        if not self._settings.smtp_host:
            # Lets developers reset passwords locally without an email account.
            logger.warning("SMTP_HOST is not set. Password reset link for %s: %s", email, link)
            return
        await asyncio.to_thread(self._send, self._build_message(email, link))

    def _build_message(self, email: str, link: str) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = "Restablece tu contraseña de AlToque Pay"
        message["From"] = self._settings.smtp_user
        message["To"] = email
        message.set_content(
            "Recibimos una solicitud para restablecer tu contraseña de AlToque Pay.\n\n"
            f"Elige una nueva contraseña aquí: {link}\n\n"
            f"El enlace vence en {self._settings.reset_token_minutes} minutos y solo sirve "
            "una vez. Si no lo pediste, ignora este correo."
        )
        return message

    def _send(self, message: EmailMessage) -> None:
        settings = self._settings
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
