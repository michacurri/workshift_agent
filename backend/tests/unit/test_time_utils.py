"""Unit tests for org timezone helpers (Toronto)."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.time_utils import org_today


@pytest.mark.unit
def test_org_today_toronto_late_evening():
    """At 2026-02-19 21:35 Toronto (EST), org_today() is 2026-02-19."""
    # Toronto winter = EST (UTC-5)
    est = timezone(timedelta(hours=-5))
    fixed_now = datetime(2026, 2, 19, 21, 35, 0, tzinfo=est)
    with patch("backend.time_utils.org_now", return_value=fixed_now):
        assert org_today() == date(2026, 2, 19)


@pytest.mark.unit
def test_tomorrow_default_from_today():
    """Default 'tomorrow' when today is 2026-02-19 is 2026-02-20."""
    today = date(2026, 2, 19)
    assert today + timedelta(days=1) == date(2026, 2, 20)
