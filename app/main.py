"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="AlToque Pay API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Report that the API is up and able to serve requests."""
    return {"status": "ok"}
