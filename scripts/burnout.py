#!/usr/bin/env python3
"""
burnout.py — Burnout Guard engine.

Single source of truth for burnout scoring, state, and lockout enforcement.
Claude (or a human) interacts with it via subcommands; all decisions about
whether work may proceed come from `status` — never from judgement calls.

Subcommands:
  status                Print current state as JSON (machine-readable verdict).
  log-session           Record that a work session happened (auto behavioural signal).
  checkin               Record a structured self-report (drives 60% of the index).
  cooldown start        Manually start a cooldown (or let red-zone auto-trigger it).
  cooldown clear        Attempt to exit cooldown (requires timer elapsed + exit check-in).
  override              Break glass: bypass lockout once per cooldown, logged, penalised.
  history               Show recent check-ins and sessions.
  report                Markdown wellbeing report for the last 14 days.

State lives in ~/.burnout-guard/state.json (override with BURNOUT_GUARD_HOME).
Exit codes: 0 = unlocked, 10 = LOCKED (cooldown active), 2 = usage error.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------- constants

HOME = Path(os.environ.get("BURNOUT_GUARD_HOME", Path.home() / ".burnout-guard"))
STATE_FILE = HOME / "state.json"

ZONE_GREEN_MAX = 39   # 0–39  green
ZONE_AMBER_MAX = 64   # 40–64 amber
                      # 65+   red -> auto lockout

EXIT_CHECKIN_MAX = 55         # index required to clear a cooldown
BASE_COOLDOWN_HOURS = 12      # at index 65
MAX_COOLDOWN_HOURS = 48       # at index >= 90
OVERRIDE_PENALTY = 8          # added to next computed index after an override
LATE_NIGHT_START, LATE_NIGHT_END = 23, 5   # local hours considered "late night"

SELF_REPORT_WEIGHT = 0.6
BEHAVIOUR_WEIGHT = 0.4

# ---------------------------------------------------------------- state io

def now() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")

def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)

def default_state() -> dict:
    return {
        "version": 1,
        "created_at": iso(now()),
        "sessions": [],        # [{ts, late_night}]
        "checkins": [],        # [{ts, exhaustion, detachment, efficacy, sleep, pressure, notes, index_at_checkin}]
        "cooldown": None,      # {started_at, ends_at, trigger_index, reason, overrides: []}
        "override_penalty": 0, # decays after next clean check-in
        "events": [],          # audit log [{ts, type, detail}]
    }

def load_state() -> dict:
    if not STATE_FILE.exists():
        return default_state()
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        backup = STATE_FILE.with_suffix(".corrupt.json")
        STATE_FILE.rename(backup)
        return default_state()

def save_state(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)

def audit(state: dict, event_type: str, detail: str) -> None:
    state["events"].append({"ts": iso(now()), "type": event_type, "detail": detail})
    state["events"] = state["events"][-500:]

# ---------------------------------------------------------------- scoring

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def self_report_score(state: dict) -> float | None:
    """0–100 from the most recent check-in within 72h. None if stale/absent."""
    if not state["checkins"]:
        return None
    last = state["checkins"][-1]
    if now() - parse(last["ts"]) > timedelta(hours=72):
        return None
    # All scales 1–5. efficacy and sleep are protective -> reversed.
    raw = (
        (last["exhaustion"] - 1) * 1.25 +       # weight 25
        (last["detachment"] - 1) * 1.25 +       # weight 25
        (5 - last["efficacy"]) * 1.0 +          # weight 20
        (5 - last["sleep"]) * 0.75 +            # weight 15
        (last["pressure"] - 1) * 0.75           # weight 15
    )
    # raw max = 4*(1.25+1.25+1.0+0.75+0.75) = 20 -> scale to 100
    return clamp(raw * 5.0, 0, 100)

def behaviour_score(state: dict) -> float:
    """0–100 from logged sessions over the trailing 7 days."""
    cutoff = now() - timedelta(days=7)
    recent = [s for s in state["sessions"] if parse(s["ts"]) >= cutoff]
    if not recent:
        return 0.0

    per_day = len(recent) / 7.0
    late = sum(1 for s in recent if s.get("late_night"))

    # Consecutive active days ending today
    days_active = {parse(s["ts"]).date() for s in recent}
    streak, d = 0, now().date()
    while d in days_active:
        streak += 1
        d -= timedelta(days=1)

    # Component scores
    volume = clamp((per_day - 2) / 6 * 100, 0, 100)      # >2 sessions/day starts counting; 8/day = max
    night = clamp(late / 5 * 100, 0, 100)                 # 5 late-night sessions in a week = max
    grind = clamp((streak - 4) / 6 * 100, 0, 100)         # 5+ day streaks count; 10-day streak = max
    return clamp(0.4 * volume + 0.35 * night + 0.25 * grind, 0, 100)

def compute_index(state: dict) -> dict:
    sr = self_report_score(state)
    bh = behaviour_score(state)
    if sr is None:
        # No fresh self-report: behaviour drives, capped so behaviour alone
        # can push you to amber but not silently into red.
        index = clamp(bh, 0, ZONE_AMBER_MAX)
        basis = "behaviour-only (no check-in in 72h — check-in required for full picture)"
    else:
        index = SELF_REPORT_WEIGHT * sr + BEHAVIOUR_WEIGHT * bh
        # Severe self-report floor: a crisis-level check-in must be able to trigger
        # red even when behavioural data is sparse (e.g. work done off-platform).
        index = max(index, sr * 0.85)
        basis = "blended (60% self-report, 40% behaviour; severe self-report floor applies)"
    index = clamp(index + state.get("override_penalty", 0), 0, 100)
    zone = "green" if index <= ZONE_GREEN_MAX else "amber" if index <= ZONE_AMBER_MAX else "red"
    return {
        "index": round(index, 1),
        "zone": zone,
        "self_report": None if sr is None else round(sr, 1),
        "behaviour": round(bh, 1),
        "basis": basis,
        "override_penalty": state.get("override_penalty", 0),
    }

def cooldown_hours_for(index: float) -> int:
    span = clamp((index - ZONE_AMBER_MAX - 1) / (90 - ZONE_AMBER_MAX - 1), 0, 1)
    return int(round(BASE_COOLDOWN_HOURS + span * (MAX_COOLDOWN_HOURS - BASE_COOLDOWN_HOURS)))

# ---------------------------------------------------------------- cooldown

def start_cooldown(state: dict, index: float, reason: str) -> dict:
    hours = cooldown_hours_for(index)
    state["cooldown"] = {
        "started_at": iso(now()),
        "ends_at": iso(now() + timedelta(hours=hours)),
        "trigger_index": index,
        "reason": reason,
        "overrides": [],
    }
    audit(state, "cooldown_start", f"index={index} hours={hours} reason={reason}")
    return state["cooldown"]

def cooldown_status(state: dict) -> dict:
    cd = state.get("cooldown")
    if not cd:
        return {"locked": False}
    remaining = parse(cd["ends_at"]) - now()
    timer_elapsed = remaining.total_seconds() <= 0
    return {
        "locked": True,
        "started_at": cd["started_at"],
        "ends_at": cd["ends_at"],
        "timer_elapsed": timer_elapsed,
        "remaining_human": "0h 0m" if timer_elapsed else
            f"{int(remaining.total_seconds() // 3600)}h {int(remaining.total_seconds() % 3600 // 60)}m",
        "trigger_index": cd["trigger_index"],
        "reason": cd["reason"],
        "overrides_used": len(cd.get("overrides", [])),
        "exit_requires": f"timer elapsed AND a fresh check-in with index <= {EXIT_CHECKIN_MAX}",
    }

# ---------------------------------------------------------------- commands

def cmd_status(args):
    state = load_state()
    score = compute_index(state)
    cd = cooldown_status(state)
    verdict = {
        "score": score,
        "cooldown": cd,
        "verdict": "LOCKED" if cd["locked"] else "UNLOCKED",
        "instruction": (
            "Cooldown active. Decline all task/work requests. Offer only: wellbeing "
            "conversation, status checks, exit check-in (if timer elapsed), or logged override."
            if cd["locked"] else
            "Work may proceed. Log this session with `log-session` if it is a work session."
        ),
    }
    print(json.dumps(verdict, indent=2))
    sys.exit(10 if cd["locked"] else 0)

def cmd_log_session(args):
    state = load_state()
    hour = datetime.now().hour
    late = hour >= LATE_NIGHT_START or hour < LATE_NIGHT_END
    state["sessions"].append({"ts": iso(now()), "late_night": late})
    state["sessions"] = state["sessions"][-1000:]
    audit(state, "session", f"late_night={late}")
    score = compute_index(state)
    # Auto-trigger lockout on red, if not already locked
    if score["zone"] == "red" and not state.get("cooldown"):
        start_cooldown(state, score["index"], "auto: red zone on session log")
    save_state(state)
    print(json.dumps({"logged": True, "late_night": late, "score": score,
                      "cooldown": cooldown_status(state)}, indent=2))

def cmd_checkin(args):
    state = load_state()
    for field in ("exhaustion", "detachment", "efficacy", "sleep", "pressure"):
        v = getattr(args, field)
        if not 1 <= v <= 5:
            print(f"error: --{field} must be 1–5", file=sys.stderr)
            sys.exit(2)
    entry = {
        "ts": iso(now()),
        "exhaustion": args.exhaustion, "detachment": args.detachment,
        "efficacy": args.efficacy, "sleep": args.sleep, "pressure": args.pressure,
        "notes": args.notes or "",
    }
    state["checkins"].append(entry)
    state["checkins"] = state["checkins"][-365:]
    score = compute_index(state)
    entry["index_at_checkin"] = score["index"]
    # A clean (green) check-in decays any override penalty
    if score["zone"] == "green":
        state["override_penalty"] = 0
    audit(state, "checkin", f"index={score['index']} zone={score['zone']}")
    if score["zone"] == "red" and not state.get("cooldown"):
        start_cooldown(state, score["index"], "auto: red zone on check-in")
    save_state(state)
    print(json.dumps({"recorded": True, "score": score,
                      "cooldown": cooldown_status(state)}, indent=2))

def cmd_cooldown(args):
    state = load_state()
    if args.action == "start":
        score = compute_index(state)
        cd = start_cooldown(state, max(score["index"], ZONE_AMBER_MAX + 1),
                            args.reason or "manual start")
        save_state(state)
        print(json.dumps({"started": True, "cooldown": cooldown_status(state)}, indent=2))
    elif args.action == "clear":
        cd = cooldown_status(state)
        if not cd["locked"]:
            print(json.dumps({"cleared": False, "detail": "no active cooldown"}, indent=2))
            return
        if not cd["timer_elapsed"]:
            print(json.dumps({"cleared": False,
                              "detail": f"timer not elapsed — {cd['remaining_human']} remaining"}, indent=2))
            sys.exit(10)
        score = compute_index(state)
        fresh = state["checkins"] and (now() - parse(state["checkins"][-1]["ts"]) < timedelta(hours=2))
        if not fresh:
            print(json.dumps({"cleared": False,
                              "detail": "exit check-in required (within last 2h) before clearing"}, indent=2))
            sys.exit(10)
        if score["index"] > EXIT_CHECKIN_MAX:
            ext = start_cooldown(state, score["index"], "extension: exit check-in still too high")
            save_state(state)
            print(json.dumps({"cleared": False, "extended": True,
                              "detail": f"index {score['index']} > {EXIT_CHECKIN_MAX}; cooldown extended",
                              "cooldown": cooldown_status(state)}, indent=2))
            sys.exit(10)
        state["cooldown"] = None
        audit(state, "cooldown_clear", f"exit index={score['index']}")
        save_state(state)
        print(json.dumps({"cleared": True, "score": score}, indent=2))

def cmd_override(args):
    state = load_state()
    cd = state.get("cooldown")
    if not cd:
        print(json.dumps({"override": False, "detail": "no active cooldown"}, indent=2))
        return
    if len(cd.get("overrides", [])) >= 1:
        print(json.dumps({"override": False,
                          "detail": "override already used for this cooldown — lockout stands"}, indent=2))
        sys.exit(10)
    if not args.reason or len(args.reason.strip()) < 15:
        print("error: --reason of at least 15 characters is required (it is logged)", file=sys.stderr)
        sys.exit(2)
    cd["overrides"].append({"ts": iso(now()), "reason": args.reason.strip()})
    state["override_penalty"] = state.get("override_penalty", 0) + OVERRIDE_PENALTY
    audit(state, "override", args.reason.strip())
    save_state(state)
    print(json.dumps({
        "override": True,
        "detail": "One-time pass granted for THIS task only. Lockout resumes immediately after. "
                  f"+{OVERRIDE_PENALTY} penalty applied to future indices until a green check-in.",
    }, indent=2))

def cmd_history(args):
    state = load_state()
    print(json.dumps({
        "recent_checkins": state["checkins"][-args.n:],
        "recent_sessions": state["sessions"][-args.n:],
        "recent_events": state["events"][-args.n:],
    }, indent=2))

def cmd_report(args):
    state = load_state()
    score = compute_index(state)
    cd = cooldown_status(state)
    cutoff = now() - timedelta(days=14)
    sessions = [s for s in state["sessions"] if parse(s["ts"]) >= cutoff]
    checkins = [c for c in state["checkins"] if parse(c["ts"]) >= cutoff]
    late = sum(1 for s in sessions if s.get("late_night"))
    lines = [
        "# Burnout Guard — 14-day report",
        f"\n**Current index:** {score['index']} ({score['zone'].upper()}) — {score['basis']}",
        f"**Lockout:** {'ACTIVE until ' + cd['ends_at'] if cd['locked'] else 'none'}",
        f"\n## Behaviour\n- Sessions: {len(sessions)} ({late} late-night)",
        f"- Behaviour score: {score['behaviour']}/100",
        f"\n## Self-report\n- Check-ins: {len(checkins)}",
    ]
    if checkins:
        last = checkins[-1]
        lines.append(f"- Latest ({last['ts']}): exhaustion {last['exhaustion']}/5, "
                     f"detachment {last['detachment']}/5, efficacy {last['efficacy']}/5, "
                     f"sleep {last['sleep']}/5, pressure {last['pressure']}/5")
        if last.get("notes"):
            lines.append(f"- Notes: {last['notes']}")
    lines.append(f"\n## Audit\n- Events logged: {len(state['events'])}")
    print("\n".join(lines))

# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(prog="burnout.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("log-session").set_defaults(fn=cmd_log_session)

    ci = sub.add_parser("checkin")
    for f, h in [("exhaustion", "How drained do you feel? 1=fresh 5=running on fumes"),
                 ("detachment", "How cynical/detached from the work? 1=engaged 5=checked out"),
                 ("efficacy", "How effective do you feel? 1=useless 5=on top of it"),
                 ("sleep", "Sleep quality last night? 1=terrible 5=great"),
                 ("pressure", "Workload pressure? 1=light 5=crushing")]:
        ci.add_argument(f"--{f}", type=int, required=True, help=h)
    ci.add_argument("--notes", type=str, default="")
    ci.set_defaults(fn=cmd_checkin)

    cd = sub.add_parser("cooldown")
    cd.add_argument("action", choices=["start", "clear"])
    cd.add_argument("--reason", type=str, default="")
    cd.set_defaults(fn=cmd_cooldown)

    ov = sub.add_parser("override")
    ov.add_argument("--reason", type=str, required=True,
                    help="Why this lockout must be bypassed (logged, min 15 chars)")
    ov.set_defaults(fn=cmd_override)

    hi = sub.add_parser("history")
    hi.add_argument("-n", type=int, default=10)
    hi.set_defaults(fn=cmd_history)

    sub.add_parser("report").set_defaults(fn=cmd_report)

    args = p.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
