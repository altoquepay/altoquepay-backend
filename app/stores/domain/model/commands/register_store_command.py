from dataclasses import dataclass, field

from app.shared.domain.value_objects import Ruc


@dataclass(frozen=True)
class RegisterStoreCommand:
    business_name: str
    ruc: Ruc
    admin_full_name: str
    admin_email: str
    # Kept out of the representation so it never reaches a log or a traceback.
    admin_password: str = field(repr=False)
