"""Body-signal provider primitives (v7).

A SleepRecord describes ONE night, attributed to the date you WOKE.
Providers return the record for the night that ended on `target`. The engine
uses this to adjust the daily focus pivot and award recovery credit when the
night before was actually restorative.

Quality is normalized to 0-100 across providers so the engine can compare
Apple Health, Whoop, and Oura on the same axis. Each provider documents how
it maps its native metric.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path
from typing import Optional, Protocol


HOME = Path(os.environ.get("BURNOUT_GUARD_HOME", Path.home() / ".burnout-guard"))
AUTH_DIR = HOME / "auth"
SLEEP_DIR = HOME / "sleep"
CACHE_FILE = SLEEP_DIR / "cache.json"
CONFIG_FILE = AUTH_DIR / "providers.json"
CACHE_TTL_HOURS = 4


@dataclass
class SleepRecord:
    """One night of sleep, attributed to the wake date."""
    date: str          # ISO YYYY-MM-DD of the day you woke
    hours: float       # total sleep, in hours
    quality: float     # 0-100; see provider docstring for the source metric
    source: str        # provider name: "apple_health" | "whoop" | "oura" | "manual"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SleepRecord":
        return cls(date=d["date"], hours=float(d["hours"]),
                   quality=float(d["quality"]), source=d["source"])


class Provider(Protocol):
    name: str

    def fetch(self, target: date_cls) -> Optional[SleepRecord]:
        """Return the sleep record for the night ending on `target`, or None."""
        ...


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def load_config() -> dict:
    """Provider config: {'enabled': [name, ...], 'priority': [name, ...]}.
    The first provider in `priority` that returns a record wins; absent
    `priority` falls back to `enabled` order."""
    cfg = _read_json(CONFIG_FILE)
    if "enabled" not in cfg:
        cfg["enabled"] = []
    return cfg


def save_config(cfg: dict) -> None:
    _write_json(CONFIG_FILE, cfg)


def cache_get(provider: str, day: str) -> Optional[SleepRecord]:
    """Return cached record if fresh enough; else None. Cache is keyed by
    (provider, date) so two providers can cache the same date independently."""
    data = _read_json(CACHE_FILE)
    bucket = data.get(provider, {})
    entry = bucket.get(day)
    if not entry:
        return None
    try:
        fetched = datetime.fromisoformat(entry["fetched_at"])
    except (KeyError, ValueError):
        return None
    if datetime.now() - fetched > timedelta(hours=CACHE_TTL_HOURS):
        return None
    rec = entry.get("record")
    if not rec:
        return None
    return SleepRecord.from_dict(rec)


def cache_put(provider: str, day: str, rec: Optional[SleepRecord]) -> None:
    """Store rec (or a tombstone if None) in the per-provider/per-day cache.
    Tombstones prevent hammering the API for nights with no data."""
    data = _read_json(CACHE_FILE)
    bucket = data.setdefault(provider, {})
    bucket[day] = {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "record": rec.to_dict() if rec else None,
    }
    # Prune anything older than 60 days to keep the file small.
    cutoff = (datetime.now().date() - timedelta(days=60)).isoformat()
    for p, b in list(data.items()):
        for d in list(b.keys()):
            if d < cutoff:
                del b[d]
    _write_json(CACHE_FILE, data)
