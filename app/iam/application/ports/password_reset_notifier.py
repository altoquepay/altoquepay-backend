from abc import ABC, abstractmethod


class PasswordResetNotifier(ABC):
    @abstractmethod
    async def send_reset_link(self, email: str, link: str) -> None:
        """Send the link that lets the owner of the email choose a new password."""
