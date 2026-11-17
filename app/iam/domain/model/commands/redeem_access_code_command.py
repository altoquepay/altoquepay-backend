from dataclasses import dataclass


@dataclass(frozen=True)
class RedeemAccessCodeCommand:
    dni: str
    code: str
    new_password: str
