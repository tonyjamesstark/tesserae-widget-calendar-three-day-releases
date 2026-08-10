"""Smoke tests for the calendar_three_day widget.

Same stub-current_app setup as the calendar_day (custom) and
calendar_schedule community widgets: patch calendar_core's
load_events so the tests exercise the 3-day window + bucketing logic
without reaching real ICS feeds or the Tesserae core.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


def _stub_calendar_core(events: list[dict[str, Any]]) -> MagicMock:
    core = MagicMock()
    core.server_module.load_events.return_value = events
    core.data_dir = "/tmp/calendar_core_unused"
    return core


def _stub_app(events: list[dict[str, Any]]) -> MagicMock:
    registry = MagicMock()
    registry.get.return_value = _stub_calendar_core(events)
    app = MagicMock()
    app.config = {"PLUGIN_REGISTRY": registry}
    return app


def test_missing_calendar_core_surfaces_error() -> None:
    registry = MagicMock()
    registry.get.return_value = None
    app = MagicMock()
    app.config = {"PLUGIN_REGISTRY": registry}
    with patch.object(server, "current_app", app):
        out = server.fetch(options={}, settings={}, ctx={})
    assert "error" in out
    assert out["days"] == []


def test_fetch_returns_exactly_three_days_starting_today() -> None:
    app = _stub_app([])
    with patch.object(server, "current_app", app):
        out = server.fetch(options={}, settings={}, ctx={})
    assert len(out["days"]) == 3
    assert out["days"][0]["is_today"] is True
    assert out["days"][1]["is_today"] is False
    assert out["days"][2]["is_today"] is False
    today = datetime.now(UTC).date()
    assert out["start"] == today.isoformat()
    assert out["end"] == (today + timedelta(days=2)).isoformat()


def test_events_bucket_into_the_right_day() -> None:
    today = datetime.now(UTC).date()
    tomorrow = today + timedelta(days=1)
    app = _stub_app(
        [
            {
                "summary": "Standup",
                "start": f"{today.isoformat()}T09:00:00+00:00",
                "end": f"{today.isoformat()}T09:30:00+00:00",
                "all_day": False,
                "feed_colour": "#3366CC",
            },
            {
                "summary": "Dentist",
                "start": f"{tomorrow.isoformat()}T14:00:00+00:00",
                "all_day": False,
            },
        ]
    )
    with patch.object(server, "current_app", app):
        out = server.fetch(options={}, settings={}, ctx={})
    assert [e["summary"] for e in out["days"][0]["events"]] == ["Standup"]
    assert [e["summary"] for e in out["days"][1]["events"]] == ["Dentist"]
    assert out["days"][2]["events"] == []


def test_all_day_event_is_bucketed_and_flagged() -> None:
    today = datetime.now(UTC).date()
    app = _stub_app(
        [
            {
                "summary": "Conference",
                "start": today.isoformat(),
                "all_day": True,
                "feed_colour": "#3366CC",
            },
        ]
    )
    with patch.object(server, "current_app", app):
        out = server.fetch(options={}, settings={}, ctx={})
    assert out["days"][0]["events"][0]["summary"] == "Conference"
    assert out["days"][0]["events"][0]["all_day"] is True


def test_multi_day_all_day_event_appears_on_every_covered_day() -> None:
    today = datetime.now(UTC).date()
    app = _stub_app(
        [
            {
                "summary": "Conference",
                "start": today.isoformat(),
                "end": (today + timedelta(days=3)).isoformat(),
                "all_day": True,
                "feed_colour": "#3366CC",
            },
        ]
    )
    with patch.object(server, "current_app", app):
        out = server.fetch(options={}, settings={}, ctx={})
    for day in out["days"]:
        assert [e["summary"] for e in day["events"]] == ["Conference"], day["date"]


def test_multi_day_timed_event_appears_on_every_covered_day() -> None:
    # Regression: a *timed* (non-all-day) event spanning several days used
    # to be bucketed only on its start day and silently vanish from every
    # day after that, unlike all-day events.
    today = datetime.now(UTC).date()
    app = _stub_app(
        [
            {
                "summary": "Trip",
                "start": f"{today.isoformat()}T16:00:00",
                "end": f"{(today + timedelta(days=2)).isoformat()}T10:00:00",
                "all_day": False,
                "feed_colour": "#3366CC",
            },
        ]
    )
    with patch.object(server, "current_app", app):
        out = server.fetch(options={}, settings={}, ctx={})
    for day in out["days"]:
        assert [e["summary"] for e in day["events"]] == ["Trip"], day["date"]


def test_feeds_filter_parses_comma_separated_list() -> None:
    assert server._parse_feeds_filter("") is None
    assert server._parse_feeds_filter(" ") is None
    assert server._parse_feeds_filter("a,b,c") == ["a", "b", "c"]
    assert server._parse_feeds_filter("a , b,  c  ") == ["a", "b", "c"]
