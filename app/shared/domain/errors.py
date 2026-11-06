"""Error raised by the domain and application layers of every bounded context."""

from typing import Any


class BusinessError(Exception):
    """A broken business rule, rendered by the global handler with the common error format."""

    def __init__(
        self,
        code: str,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
        status: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.details = details
        self.status = status
