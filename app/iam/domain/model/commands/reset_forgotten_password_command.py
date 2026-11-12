from dataclasses import dataclass


@dataclass(frozen=True)
class ResetForgottenPasswordCommand:
    token: str
    new_password: str
