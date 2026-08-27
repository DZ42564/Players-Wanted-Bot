from datetime import datetime, timezone

from game_commands import parse_eastern_datetime


def test_winter_eastern_time_converts_to_utc():
    ts = parse_eastern_datetime("2026-01-15", "19:00")
    assert datetime.fromtimestamp(ts, timezone.utc).isoformat() == "2026-01-16T00:00:00+00:00"


def test_summer_eastern_time_converts_to_utc_with_dst():
    ts = parse_eastern_datetime("2026-08-15", "19:00")
    assert datetime.fromtimestamp(ts, timezone.utc).isoformat() == "2026-08-15T23:00:00+00:00"
