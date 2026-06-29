"""Oura sleep provider.

Auth: Personal Access Token (PAT). Oura supports both OAuth and PATs; for a
single-user local CLI a PAT is dramatically simpler — generate one at
https://cloud.ouraring.com/personal-access-tokens and `burnout.py sleep
connect oura --token <token>` stores it locally.

Endpoint: GET /v2/usercollection/sleep?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD

Quality mapping: Oura's `sleep_score_delta` is a small +/- around the daily
score and not directly comparable. We prefer the daily readiness score
(/v2/usercollection/daily_readiness) when present; if not, fall back to a
composite from `efficiency` and `restless_periods`.

Stdlib only — urllib.request + json. No `requests` dep.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date as date_cls, timedelta
from typing import Optional

from .base import AUTH_DIR, SleepRecord, _read_json, _write_json, cache_get, cache_put


NAME = "oura"
TOKEN_FILE = AUTH_DIR / "oura.json"
BASE_URL = "https://api.ouraring.com/v2/usercollection"
TIMEOUT_S = 8


def save_token(token: str) -> None:
    _write_json(TOKEN_FILE, {"access_token": token.strip()})


def load_token() -> Optional[str]:
    data = _read_json(TOKEN_FILE)
    return data.get("access_token")


def fetch(target: date_cls) -> Optional[SleepRecord]:
    day = target.isoformat()
    cached = cache_get(NAME, day)
    if cached:
        return cached
    token = load_token()
    if not token:
        return None
    rec = _fetch_live(target, token)
    cache_put(NAME, day, rec)
    return rec


def _fetch_live(target: date_cls, token: str) -> Optional[SleepRecord]:
    # Pull a small window so a late-syncing watch still produces a hit.
    start = (target - timedelta(days=2)).isoformat()
    end = target.isoformat()
    sleep_rows = _api_get(f"/sleep?start_date={start}&end_date={end}", token)
    if sleep_rows is None:
        return None
    # Pick the longest sleep session that ENDED on `target`. Oura may return
    # multiple rows per day (naps); we want the main night.
    candidates = [r for r in sleep_rows
                  if r.get("day") == target.isoformat()
                  and r.get("type") in (None, "long_sleep", "sleep")]
    if not candidates:
        return None
    main = max(candidates, key=lambda r: r.get("total_sleep_duration", 0))
    hours = float(main.get("total_sleep_duration", 0)) / 3600.0
    if hours <= 0:
        return None

    quality = _readiness_quality(target, token)
    if quality is None:
        quality = _heuristic_quality(main)

    return SleepRecord(date=target.isoformat(), hours=round(hours, 2),
                       quality=round(quality, 1), source=NAME)


def _readiness_quality(target: date_cls, token: str) -> Optional[float]:
    rows = _api_get(f"/daily_readiness?start_date={target.isoformat()}"
                    f"&end_date={target.isoformat()}", token)
    if not rows:
        return None
    score = rows[0].get("score")
    return float(score) if score is not None else None


def _heuristic_quality(row: dict) -> float:
    """Fallback when readiness is absent. efficiency is 0-100; restless
    periods we cap-normalize. Mean of the two with light clamping."""
    eff = float(row.get("efficiency", 70))
    restless = float(row.get("restless_periods", 5))
    restless_score = max(0.0, 100.0 - restless * 5.0)  # 0 restless → 100, 20 → 0
    return max(0.0, min(100.0, (eff + restless_score) / 2.0))


def _api_get(path: str, token: str) -> Optional[list]:
    req = urllib.request.Request(BASE_URL + path,
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    return None
