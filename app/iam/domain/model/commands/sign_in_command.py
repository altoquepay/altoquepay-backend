from dataclasses import dataclass


@dataclass(frozen=True)
class SignInCommand:
    username: str
    password: str
