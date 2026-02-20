"""Minimal real unit test: org timezone helper (replaces placeholder)."""
import pytest

from backend.config import get_settings
from backend.time_utils import org_tz


@pytest.mark.unit
def test_org_tz_returns_org_timezone():
    """org_tz() returns ZoneInfo for configured org timezone (e.g. America/Toronto)."""
    zone = org_tz()
    assert zone.key == get_settings().org_timezone
