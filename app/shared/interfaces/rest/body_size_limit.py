"""Stops reading a request body past a size, before Starlette spools uploads to disk."""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The 2 MB product image plus the rest of its multipart form.
MAXIMUM_BODY_BYTES = 3 * 1024 * 1024


class BodySizeLimit:
    """Answers 413 once a body passes MAXIMUM_BODY_BYTES, counting what arrives.

    It counts instead of trusting Content-Length, which a client may leave out or fake.
    The error is raised while the route reads the body, so the usual error handler answers it.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > MAXIMUM_BODY_BYTES:
                raise HTTPException(413, "The request body is larger than 3 MB.")
            return message

        await self.app(scope, limited_receive, send)
