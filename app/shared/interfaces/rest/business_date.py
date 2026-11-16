"""The business date that every bounded context uses for its rules."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.shared.infrastructure.config import get_settings


def get_business_today() -> date:
    """Return today in the time zone of the business, which may differ from the server's."""
    return get_business_now().date()


def get_business_now() -> datetime:
    """Return the current time in the time zone of the business."""
    return datetime.now(ZoneInfo(get_settings().app_timezone))
