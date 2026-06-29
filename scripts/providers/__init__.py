"""Provider registry (v7).

Exposes `get_sleep_record(target_date)` — the single entry point the engine
uses. Inert when no providers are configured: returns None and the engine
behaves exactly as v6.

Priority order is taken from `~/.burnout-guard/auth/providers.json`:
  {"enabled": ["apple_health", "oura"], "priority": ["whoop", "apple_health"]}
If `priority` is absent, `enabled` order is used. First provider to return a
non-None record wins; we do NOT blend providers because mixing two devices'
quality metrics on one night yields noise, not signal.
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Optional

from . import apple_health, oura, whoop
from .base import SleepRecord, load_config, save_config


_PROVIDERS = {
    apple_health.NAME: apple_health,
    oura.NAME: oura,
    whoop.NAME: whoop,
}


def available() -> list[str]:
    return list(_PROVIDERS.keys())


def enabled() -> list[str]:
    cfg = load_config()
    pri = cfg.get("priority")
    en = cfg.get("enabled", [])
    if pri:
        # priority wins for ordering, but only providers also in `enabled` count
        return [p for p in pri if p in en] + [e for e in en if e not in pri]
    return en


def enable(name: str) -> None:
    if name not in _PROVIDERS:
        raise ValueError(f"unknown provider: {name}")
    cfg = load_config()
    if name not in cfg["enabled"]:
        cfg["enabled"].append(name)
    save_config(cfg)


def disable(name: str) -> None:
    cfg = load_config()
    cfg["enabled"] = [n for n in cfg["enabled"] if n != name]
    if "priority" in cfg:
        cfg["priority"] = [n for n in cfg["priority"] if n != name]
    save_config(cfg)


def get_sleep_record(target: date_cls) -> Optional[SleepRecord]:
    """First-hit-wins across enabled providers. Errors in any one provider
    fall through silently — the engine MUST keep running on a flaky network."""
    for name in enabled():
        mod = _PROVIDERS.get(name)
        if not mod:
            continue
        try:
            rec = mod.fetch(target)
        except Exception:
            rec = None
        if rec:
            return rec
    return None


__all__ = ["SleepRecord", "available", "enabled", "enable", "disable",
           "get_sleep_record"]
