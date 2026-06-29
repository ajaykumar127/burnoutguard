"""Apple Health sleep provider.

No network, no auth. Reads ~/.burnout-guard/sleep/apple_health.json which
the user populates with an iOS Shortcut (one-shot, runs in the background
each morning). The Shortcut writes JSON shaped like:

    {
      "records": [
        {"date": "2026-06-25", "hours": 7.4, "quality": 78},
        {"date": "2026-06-24", "hours": 5.9, "quality": 52}
      ]
    }

Quality is your call — sensible mappings:
  - Sleep score from a paired Apple Watch app (Pillow, AutoSleep) → use as-is
  - Sleep stages: ((deep + REM) / total) * 100 is a reasonable proxy
  - If you only have duration, set quality to 65 (neutral) and let `hours`
    drive the verdict alone

We accept either an object with `records:` or a bare list of records.
"""

from __future__ import annotations

import json
from datetime import date as date_cls
from pathlib import Path
from typing import Optional

from .base import SLEEP_DIR, SleepRecord, cache_get, cache_put


SOURCE_FILE = SLEEP_DIR / "apple_health.json"
NAME = "apple_health"


def fetch(target: date_cls) -> Optional[SleepRecord]:
    """Return the most-recent record on or before `target`. Apple Health is
    a local file read, so we don't bother with the network cache — but we
    still respect the cache contract for consistency with Whoop/Oura."""
    day = target.isoformat()
    cached = cache_get(NAME, day)
    if cached:
        return cached
    rec = _read_for(target)
    cache_put(NAME, day, rec)
    return rec


def _read_for(target: date_cls) -> Optional[SleepRecord]:
    if not SOURCE_FILE.exists():
        return None
    try:
        data = json.loads(SOURCE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    records = data.get("records") if isinstance(data, dict) else data
    if not isinstance(records, list):
        return None

    target_str = target.isoformat()
    best: Optional[dict] = None
    for r in records:
        if not isinstance(r, dict) or "date" not in r or "hours" not in r:
            continue
        if r["date"] > target_str:
            continue
        if best is None or r["date"] > best["date"]:
            best = r
    if not best:
        return None
    try:
        return SleepRecord(date=str(best["date"]),
                           hours=float(best["hours"]),
                           quality=float(best.get("quality", 65.0)),
                           source=NAME)
    except (TypeError, ValueError):
        return None
