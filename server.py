"""calendar_three_day, fetch events for today + the next two days.

Modelled directly on the bundled calendar_week widget's server: same
per-day bucketing, same slim event shape, just a 3-day window starting
today instead of a 7-day window starting on the configured week-start
day. app.calendar_time / app.tz_resolve are imported lazily with a
UTC / local-logic fallback so the widget stays importable and testable
outside a Tesserae install (same pattern as the calendar_schedule
community widget).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo
from pathlib import Path
from typing import Any

from flask import current_app

DAYS_AHEAD = 3


def _parse_feeds_filter(s: str) -> list[str] | None:
    s = (s or "").strip()
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]


def _app_timezone() -> tzinfo:
    try:
        from app.tz_resolve import app_timezone

        return app_timezone()
    except ImportError:
        return UTC


def _local_midnight_utc(day: date, zone: tzinfo) -> datetime:
    try:
        from app.calendar_time import local_midnight_utc

        return local_midnight_utc(day, zone)
    except ImportError:
        return datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)


def _all_day_event_date_keys(
    event: dict[str, Any], window_start: date, window_end: date
) -> list[str]:
    try:
        from app.calendar_time import all_day_event_date_keys

        return all_day_event_date_keys(event, window_start, window_end)
    except ImportError:
        start_raw = str(event.get("start") or "")
        if not start_raw:
            return []
        try:
            start = date.fromisoformat(start_raw.split("T")[0])
        except ValueError:
            return []
        end_raw = str(event.get("end") or "")
        if end_raw:
            try:
                end = date.fromisoformat(end_raw.split("T")[0])
            except ValueError:
                end = start + timedelta(days=1)
        else:
            end = start + timedelta(days=1)
        if end <= start:
            end = start + timedelta(days=1)
        cur = max(start, window_start)
        stop = min(end, window_end)
        keys: list[str] = []
        while cur < stop:
            keys.append(cur.isoformat())
            cur += timedelta(days=1)
        return keys


def _timed_event_date_keys(
    event: dict[str, Any], zone: tzinfo, window_start: date, window_end: date
) -> list[str]:
    """A timed (non-all-day) event's [start, end) span can itself cross
    midnight or run several days (an overnight block, a multi-day trip)
    — bucketing it only on its start day would make it vanish from
    every day after that."""
    try:
        from app.calendar_time import timed_event_date_keys

        return timed_event_date_keys(event, zone, window_start, window_end)
    except ImportError:
        start_raw = str(event.get("start") or "")
        try:
            start_local = datetime.fromisoformat(start_raw)
        except ValueError:
            return [start_raw.split("T")[0]] if start_raw else []
        if start_local.tzinfo is None:
            start_local = start_local.replace(tzinfo=UTC)
        start_local = start_local.astimezone(zone)

        end_raw = str(event.get("end") or "")
        end_local = start_local
        if end_raw:
            try:
                parsed_end = datetime.fromisoformat(end_raw)
            except ValueError:
                parsed_end = None
            if parsed_end is not None:
                if parsed_end.tzinfo is None:
                    parsed_end = parsed_end.replace(tzinfo=UTC)
                end_local = parsed_end.astimezone(zone)

        start_date = start_local.date()
        end_date = end_local.date()
        if end_date > start_date and end_local.time() == time.min:
            end_date -= timedelta(days=1)
        end_date = max(start_date, end_date)

        cur = max(start_date, window_start)
        stop = min(end_date + timedelta(days=1), window_end)
        keys: list[str] = []
        while cur < stop:
            keys.append(cur.isoformat())
            cur += timedelta(days=1)
        return keys


def fetch(
    options: dict[str, Any], settings: dict[str, Any], *, ctx: dict[str, Any]
) -> dict[str, Any]:
    del settings, ctx
    registry = current_app.config["PLUGIN_REGISTRY"]
    core = registry.get("calendar_core")
    if core is None or core.server_module is None:
        return {"error": "calendar_core plugin not installed.", "days": []}

    zone = _app_timezone()
    today = datetime.now(zone).date()
    start_date = today
    end_date = start_date + timedelta(days=DAYS_AHEAD)

    start_dt = _local_midnight_utc(start_date, zone)
    end_dt = _local_midnight_utc(end_date, zone)

    feeds_filter = _parse_feeds_filter(options.get("feeds_filter") or "")
    try:
        events = core.server_module.load_events(
            feeds_filter,
            start_dt,
            end_dt,
            data_dir=Path(core.data_dir),
        )
    except Exception as err:
        return {"error": f"{type(err).__name__}: {err}", "days": []}

    buckets: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        if ev.get("all_day"):
            day_keys = _all_day_event_date_keys(ev, start_date, end_date)
        else:
            day_keys = _timed_event_date_keys(ev, zone, start_date, end_date)
        for day_key in day_keys:
            buckets.setdefault(day_key, []).append(ev)

    days = []
    cur = start_date
    while cur < end_date:
        all_evs = buckets.get(cur.isoformat(), [])
        days.append(
            {
                "date": cur.isoformat(),
                "day": cur.day,
                "is_today": cur == today,
                "weekday": cur.weekday(),  # 0=Mon
                "events": [
                    {
                        "summary": e["summary"],
                        "start": e["start"],
                        "end": e.get("end"),
                        "all_day": e.get("all_day", False),
                        "colour": e.get("feed_colour"),
                        "location": e.get("location") or "",
                    }
                    for e in all_evs
                ],
            }
        )
        cur += timedelta(days=1)

    return {
        "start": start_date.isoformat(),
        "end": (end_date - timedelta(days=1)).isoformat(),
        "days": days,
    }
