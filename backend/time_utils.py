"""Org timezone helpers: all date-only and 'today/tomorrow' logic uses org time (e.g. America/Toronto)."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from backend.config import get_settings


def org_tz() -> ZoneInfo:
    """Org timezone (e.g. America/Toronto) for date-only and urgent cutoff logic."""
    return ZoneInfo(get_settings().org_timezone)


def org_now() -> datetime:
    """Current datetime in org timezone (timezone-aware)."""
    return datetime.now(org_tz())


def org_today() -> date:
    """Current calendar date in org timezone (for 'today' / 'tomorrow' semantics)."""
    return org_now().date()
