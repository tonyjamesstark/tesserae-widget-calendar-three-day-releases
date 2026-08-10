# Calendar, Three Day

A [Tesserae](https://github.com/dmellok/tesserae) widget: today plus the next
two days as a three-column timetable. Combines the bundled `calendar_day`
widget's auto-fit hour-axis timetable rendering with the `calendar_schedule`
community widget's day-bucketing approach, narrowed to a fixed 3-day window
starting today (no picker — see [Caveats](#caveats)).

Reads from the same `calendar_core` feeds the other calendar_* widgets use.

## Install

Settings, Widgets, Browse community widgets, search "Calendar Three Day",
Install. Restart Tesserae when prompted.

Make sure you have at least one feed configured in **Widgets → Calendar Feeds**
(provided by `calendar_core`, ships bundled).

## Cell options

- **Feed IDs**: restrict to specific feeds (comma-separated). Blank includes
  every enabled feed.
- **Hide event labels**: paint every event block as its feed-colour bar only,
  no title text. Useful on 1-bit panels or as a glance-friendly heatmap.

## Layout

Three columns (today, tomorrow, the day after), each a day-of-week + day-
number header above a shared hour axis. Events are positioned blocks with a
feed-coloured left stripe; today's column also carries the now-line. The
hour axis auto-fits to the busiest day's actual event range with one hour of
padding, same as `calendar_day`.

```
        TUE 7        WED 8        THU 9
09:00  [Standup]
11:00               [Review]
                                  [Dentist]
```

## What you need

- `calendar_core` plugin installed (ships bundled with Tesserae).
- At least one iCal feed configured in **Widgets → Calendar Feeds**.

## Caveats

- The 3-day window always starts today; there's no "start on a fixed day of
  the week" option (that's what `calendar_week` is for).
- All-day events render as pills in a per-column strip above the hour axis,
  same treatment as the bundled `calendar_day` widget. A multi-day event
  shows once per day it overlaps rather than as a single entity spanning
  columns — not yet implemented.

## Licence

AGPL-3.0-or-later.
