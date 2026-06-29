"""Calendar load (v7).

Reads ~/.burnout-guard/calendar/today.ics if present and returns a summary
of meeting load: total meeting hours, longest back-to-back stretch, and
count of context switches. Engine treats meeting hours as STRAIN, not focus
— a 6-hour day of back-to-back calls is taxing even if you wrote zero code.

The user supplies the .ics file themselves (cron + `gcalcli`, a Shortcut, a
Calendar app's export — whatever's local to them). We don't bake in a Google
OAuth flow; the engine stays standalone.

The parser is intentionally small: VEVENT blocks, DTSTART/DTEND/SUMMARY,
no recurrence expansion (the user exports today's resolved events).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


HOME = Path(os.environ.get("BURNOUT_GUARD_HOME", Path.home() / ".burnout-guard"))
ICS_FILE = HOME / "calendar" / "today.ics"

BACK_TO_BACK_GAP_MIN = 10  # gap ≤ this counts events as back-to-back


@dataclass
class CalendarLoad:
    meeting_hours: float
    longest_b2b_min: int          # longest unbroken stretch of meetings
    b2b_stretches: int            # how many back-to-back stretches ≥ 2 meetings
    meeting_count: int
    source: str = "ics"

    def to_dict(self) -> dict:
        return {"meeting_hours": round(self.meeting_hours, 2),
                "longest_b2b_min": self.longest_b2b_min,
                "b2b_stretches": self.b2b_stretches,
                "meeting_count": self.meeting_count,
                "source": self.source}


def load_today(target: Optional[date_cls] = None,
               path: Optional[Path] = None) -> Optional[CalendarLoad]:
    """Return today's calendar load, or None when no .ics file is present
    (zero-config path). Errors parsing the file also return None — calendar
    load is auxiliary; the engine should never break because the ICS is malformed."""
    p = path or ICS_FILE
    target = target or datetime.now().date()
    if not p.exists():
        return None
    try:
        events = _parse_ics(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    todays = [e for e in events if _hits(e, target)]
    if not todays:
        return CalendarLoad(0.0, 0, 0, 0)
    return _summarize(todays)


def _hits(event: tuple, target: date_cls) -> bool:
    start, end, _summary = event
    return start.date() == target or (start.date() < target <= end.date())


def _summarize(events: list[tuple]) -> CalendarLoad:
    events.sort(key=lambda e: e[0])
    meeting_seconds = 0.0
    longest_b2b = 0
    stretches = 0
    cur_stretch_start = None
    cur_stretch_end = None
    cur_stretch_count = 0
    for start, end, _ in events:
        meeting_seconds += (end - start).total_seconds()
        if cur_stretch_end is None:
            cur_stretch_start, cur_stretch_end, cur_stretch_count = start, end, 1
            continue
        gap = (start - cur_stretch_end).total_seconds() / 60.0
        if gap <= BACK_TO_BACK_GAP_MIN:
            cur_stretch_end = max(cur_stretch_end, end)
            cur_stretch_count += 1
        else:
            if cur_stretch_count >= 2:
                stretches += 1
                longest_b2b = max(longest_b2b,
                                  int((cur_stretch_end - cur_stretch_start).total_seconds() / 60))
            cur_stretch_start, cur_stretch_end, cur_stretch_count = start, end, 1
    if cur_stretch_end and cur_stretch_count >= 2:
        stretches += 1
        longest_b2b = max(longest_b2b,
                          int((cur_stretch_end - cur_stretch_start).total_seconds() / 60))

    return CalendarLoad(
        meeting_hours=meeting_seconds / 3600.0,
        longest_b2b_min=longest_b2b,
        b2b_stretches=stretches,
        meeting_count=len(events),
    )


# ---------------------------------------------------------------- ICS parsing

# We unfold continuation lines (RFC 5545 §3.1: lines starting with WS continue
# the previous line) before splitting on CRLF/LF.
_FOLD_RE = re.compile(r"\r?\n[ \t]")


def _unfold(text: str) -> str:
    return _FOLD_RE.sub("", text)


def _parse_ics(text: str) -> list[tuple[datetime, datetime, str]]:
    text = _unfold(text)
    events: list[tuple[datetime, datetime, str]] = []
    in_event = False
    cur: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            cur = {}
        elif line == "END:VEVENT":
            in_event = False
            start = cur.get("DTSTART")
            end = cur.get("DTEND")
            if start and end:
                events.append((start, end, cur.get("SUMMARY", "")))
        elif in_event:
            key, _, val = line.partition(":")
            if not _:
                continue
            base = key.split(";", 1)[0]
            if base in ("DTSTART", "DTEND"):
                dt = _parse_dt(val, key)
                if dt:
                    cur[base] = dt
            elif base == "SUMMARY":
                cur["SUMMARY"] = val
    return events


def _parse_dt(value: str, key_full: str) -> Optional[datetime]:
    """Parse an ICS date-time. Accepts:
        20260626T140000Z         (UTC)
        20260626T140000          (floating / local)
        20260626                 (DATE — all-day; we treat as midnight-to-midnight local)
    """
    value = value.strip()
    try:
        if len(value) == 8 and "T" not in value:
            d = datetime.strptime(value, "%Y%m%d")
            return d.replace(tzinfo=None)
        if value.endswith("Z"):
            d = datetime.strptime(value[:-1], "%Y%m%dT%H%M%S")
            return d.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        return datetime.strptime(value, "%Y%m%dT%H%M%S")
    except ValueError:
        return None
