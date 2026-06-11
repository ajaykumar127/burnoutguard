#!/usr/bin/env python3
"""
burnout.py — Burnout Guard engine (v2, graduated levels).

Single source of truth for burnout scoring, level state, and enforcement.
Claude (or a human) interacts via subcommands; whether and how work proceeds
comes from `status` — never from judgement calls.

THE SIX LEVELS
  L0  Flow          0–24   normal operation
  L1  Watch        25–39   normal + score surfaced once per session
  L2  Friction     40–54   work allowed; breaks suggested; check-in nudged
  L3  Throttle     55–64   single-task mode; everything else goes to the parking lot
  L4  Lockout      65–84   mandatory cooldown 12–36h; one logged override available
  L5  Hard Lockout 85–100  cooldown 36–72h; NO override; exit needs a recovery plan

Subcommands:
  status            JSON verdict: index, level, instruction. Exit 0/5/10 (see below).
  log-session       Record a work session (behavioural signal; may escalate level).
  checkin           Structured self-report (drives 60% of the index).
  defer             Park a task while throttled/locked:  defer --task "..."
  parked            List the parking lot (use when de-escalating to resume work).
  cooldown start    Self-imposed lockout:  cooldown start --reason "..."
  cooldown clear    Exit ritual. L5-triggered cooldowns also need --plan "..."
  override          L4 only, once per cooldown, logged, penalised.
  history           Recent raw entries and audit events.
  report            14-day markdown wellbeing report.

State: ~/.burnout-guard/state.json (override with BURNOUT_GUARD_HOME).
Exit codes: 0 = work may proceed (L0–L2), 5 = THROTTLED (L3), 10 = LOCKED (L4/L5),
2 = usage error.
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

LEVELS = [
    # (level, name, min_index, max_index)
    (0, "Flow",          0,  24),
    (1, "Watch",        25,  39),
    (2, "Friction",     40,  54),
    (3, "Throttle",     55,  64),
    (4, "Lockout",      65,  84),
    (5, "Hard Lockout", 85, 100),
]

LEVEL_INSTRUCTIONS = {
    0: "Normal operation. Log work sessions with `log-session`.",
    1: "Normal operation, but surface the index and level once at the start of the "
       "session. No restrictions.",
    2: "Work proceeds. Name the main driver of the score, suggest one break or "
       "adjustment, and invite a check-in if the basis is behaviour-only. Do not nag "
       "more than once per session.",
    3: "THROTTLED — single-task mode. Ask the user to pick ONE task; help with that "
       "task only. Defer everything else with `defer --task`. Suggest a ~45 minute "
       "time-box. Decline new projects and scope expansions until the level drops.",
    4: "LOCKED — cooldown active. Decline all task work. Offer only: conversation, "
       "status/history/report, deferring tasks to the parking lot, the exit ritual "
       "(if timer elapsed), or ONE logged override for genuine emergencies.",
    5: "HARD LOCKOUT — cooldown active, override DISABLED. Decline all task work. "
       "Offer only: conversation, status/history/report, deferring tasks, and the "
       "exit ritual (timer + check-in + written recovery plan). The only exception "
       "is a genuine crisis/safety situation, which dissolves all lockout framing.",
}

EXIT_INDEX_MAX = 54            # exit ritual requires index at or below this (top of L2)
RECOVERY_PLAN_MIN_CHARS = 30   # required to clear an L5-triggered cooldown
OVERRIDE_PENALTY = 8           # added to future indices until next L0/L1 check-in
LATE_NIGHT_START, LATE_NIGHT_END = 23, 5

SELF_REPORT_WEIGHT = 0.6
BEHAVIOUR_WEIGHT = 0.4
SEVERE_SELF_REPORT_FLOOR = 0.85   # index >= self_report * this

# ---------------------------------------------------------------- state io

def now() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")

def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)

def default_state() -> dict:
    return {
        "version": 2,
        "created_at": iso(now()),
        "sessions": [],
        "checkins": [],
        "cooldown": None,       # {started_at, ends_at, trigger_index, trigger_level,
                                #  reason, overrides: [], recovery_plan: None}
        "parking_lot": [],      # [{ts, task}]
        "override_penalty": 0,
        "events": [],
    }

def load_state() -> dict:
    if not STATE_FILE.exists():
        return default_state()
    try:
        state = json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        STATE_FILE.rename(STATE_FILE.with_suffix(".corrupt.json"))
        return default_state()
    if state.get("version", 1) < 2:   # migrate v1 -> v2
        state.setdefault("parking_lot", [])
        if state.get("cooldown"):
            state["cooldown"].setdefault("trigger_level", 4)
            state["cooldown"].setdefault("recovery_plan", None)
        state["version"] = 2
    return state

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
    raw = (
        (last["exhaustion"] - 1) * 1.25 +
        (last["detachment"] - 1) * 1.25 +
        (5 - last["efficacy"]) * 1.0 +
        (5 - last["sleep"]) * 0.75 +
        (last["pressure"] - 1) * 0.75
    )
    return clamp(raw * 5.0, 0, 100)   # raw max 20 -> 100

def behaviour_score(state: dict) -> float:
    """0–100 from logged sessions over the trailing 7 days."""
    cutoff = now() - timedelta(days=7)
    recent = [s for s in state["sessions"] if parse(s["ts"]) >= cutoff]
    if not recent:
        return 0.0
    per_day = len(recent) / 7.0
    late = sum(1 for s in recent if s.get("late_night"))
    days_active = {parse(s["ts"]).date() for s in recent}
    streak, d = 0, now().date()
    while d in days_active:
        streak += 1
        d -= timedelta(days=1)
    volume = clamp((per_day - 2) / 6 * 100, 0, 100)
    night = clamp(late / 5 * 100, 0, 100)
    grind = clamp((streak - 4) / 6 * 100, 0, 100)
    return clamp(0.4 * volume + 0.35 * night + 0.25 * grind, 0, 100)

def level_for(index: float) -> tuple[int, str]:
    for lvl, name, lo, hi in reversed(LEVELS):
        if index >= lo:
            return lvl, name
    return 0, "Flow"

def compute_index(state: dict) -> dict:
    sr = self_report_score(state)
    bh = behaviour_score(state)
    if sr is None:
        # Behaviour alone can warn (up to L3 Throttle) but never lock (L4+).
        index = clamp(bh, 0, 64)
        basis = "behaviour-only (no check-in in 72h; capped at L3 — check-in invited)"
    else:
        index = SELF_REPORT_WEIGHT * sr + BEHAVIOUR_WEIGHT * bh
        index = max(index, sr * SEVERE_SELF_REPORT_FLOOR)
        basis = "blended (60% self-report, 40% behaviour; severe self-report floor)"
    index = clamp(index + state.get("override_penalty", 0), 0, 100)
    lvl, name = level_for(index)
    return {
        "index": round(index, 1),
        "level": lvl,
        "level_name": name,
        "self_report": None if sr is None else round(sr, 1),
        "behaviour": round(bh, 1),
        "basis": basis,
        "override_penalty": state.get("override_penalty", 0),
    }

def cooldown_hours_for(index: float, level: int) -> int:
    if level >= 5:   # 36h at 85 -> 72h at 100
        span = clamp((index - 85) / 15, 0, 1)
        return int(round(36 + span * 36))
    span = clamp((index - 65) / 19, 0, 1)   # 12h at 65 -> 36h at 84
    return int(round(12 + span * 24))

# ---------------------------------------------------------------- cooldown

def start_cooldown(state: dict, index: float, level: int, reason: str) -> dict:
    hours = cooldown_hours_for(index, level)
    state["cooldown"] = {
        "started_at": iso(now()),
        "ends_at": iso(now() + timedelta(hours=hours)),
        "trigger_index": index,
        "trigger_level": level,
        "reason": reason,
        "overrides": [],
        "recovery_plan": None,
    }
    audit(state, "cooldown_start", f"L{level} index={index} hours={hours} reason={reason}")
    return state["cooldown"]

def maybe_escalate(state: dict, score: dict, source: str) -> None:
    """Auto-start or upgrade a cooldown when the level reaches L4/L5."""
    lvl, idx = score["level"], score["index"]
    cd = state.get("cooldown")
    if lvl >= 4 and not cd:
        start_cooldown(state, idx, lvl, f"auto: L{lvl} on {source}")
    elif cd and lvl == 5 and cd.get("trigger_level", 4) < 5:
        start_cooldown(state, idx, 5, f"escalation: L4 -> L5 on {source}")

def cooldown_status(state: dict) -> dict:
    cd = state.get("cooldown")
    if not cd:
        return {"locked": False}
    remaining = parse(cd["ends_at"]) - now()
    timer_elapsed = remaining.total_seconds() <= 0
    lvl = cd.get("trigger_level", 4)
    exit_req = (f"timer elapsed AND fresh check-in (2h) with index <= {EXIT_INDEX_MAX}"
                + (" AND a written recovery plan (--plan)" if lvl >= 5 else ""))
    return {
        "locked": True,
        "lock_level": lvl,
        "started_at": cd["started_at"],
        "ends_at": cd["ends_at"],
        "timer_elapsed": timer_elapsed,
        "remaining_human": "0h 0m" if timer_elapsed else
            f"{int(remaining.total_seconds() // 3600)}h {int(remaining.total_seconds() % 3600 // 60)}m",
        "trigger_index": cd["trigger_index"],
        "reason": cd["reason"],
        "override_available": lvl < 5 and len(cd.get("overrides", [])) == 0,
        "overrides_used": len(cd.get("overrides", [])),
        "exit_requires": exit_req,
    }

# ---------------------------------------------------------------- commands

def cmd_status(args):
    state = load_state()
    score = compute_index(state)
    cd = cooldown_status(state)
    if cd["locked"]:
        effective = max(score["level"], cd["lock_level"], 4)
        verdict, code = "LOCKED", 10
    elif score["level"] == 3:
        effective, verdict, code = 3, "THROTTLED", 5
    else:
        effective, verdict, code = score["level"], "UNLOCKED", 0
    print(json.dumps({
        "score": score,
        "effective_level": effective,
        "effective_level_name": dict((l, n) for l, n, *_ in LEVELS)[effective],
        "cooldown": cd,
        "parking_lot_size": len(state["parking_lot"]),
        "verdict": verdict,
        "instruction": LEVEL_INSTRUCTIONS[effective],
    }, indent=2))
    sys.exit(code)

def cmd_log_session(args):
    state = load_state()
    hour = datetime.now().hour
    late = hour >= LATE_NIGHT_START or hour < LATE_NIGHT_END
    state["sessions"].append({"ts": iso(now()), "late_night": late})
    state["sessions"] = state["sessions"][-1000:]
    audit(state, "session", f"late_night={late}")
    score = compute_index(state)
    maybe_escalate(state, score, "session log")
    save_state(state)
    print(json.dumps({"logged": True, "late_night": late, "score": score,
                      "cooldown": cooldown_status(state)}, indent=2))

def cmd_checkin(args):
    state = load_state()
    for field in ("exhaustion", "detachment", "efficacy", "sleep", "pressure"):
        v = getattr(args, field)
        if not 1 <= v <= 5:
            print(f"error: --{field} must be 1-5", file=sys.stderr)
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
    if score["level"] <= 1:           # a calm check-in clears any override penalty
        state["override_penalty"] = 0
        score = compute_index(state)
    audit(state, "checkin", f"index={score['index']} L{score['level']}")
    maybe_escalate(state, score, "check-in")
    save_state(state)
    print(json.dumps({"recorded": True, "score": score,
                      "cooldown": cooldown_status(state)}, indent=2))

def cmd_defer(args):
    state = load_state()
    task = (args.task or "").strip()
    if len(task) < 3:
        print("error: --task description required", file=sys.stderr)
        sys.exit(2)
    state["parking_lot"].append({"ts": iso(now()), "task": task})
    audit(state, "defer", task[:120])
    save_state(state)
    print(json.dumps({"deferred": True, "parking_lot_size": len(state["parking_lot"]),
                      "detail": "Parked. It will be waiting when the level drops."}, indent=2))

def cmd_parked(args):
    state = load_state()
    if args.clear:
        n = len(state["parking_lot"])
        state["parking_lot"] = []
        audit(state, "parking_lot_clear", f"cleared {n}")
        save_state(state)
        print(json.dumps({"cleared": n}, indent=2))
        return
    print(json.dumps({"parking_lot": state["parking_lot"]}, indent=2))

def cmd_cooldown(args):
    state = load_state()
    if args.action == "start":
        score = compute_index(state)
        idx = max(score["index"], 65)
        lvl = max(score["level"], 4)
        start_cooldown(state, idx, lvl, args.reason or "manual start")
        save_state(state)
        print(json.dumps({"started": True, "cooldown": cooldown_status(state)}, indent=2))
        return
    # clear
    cd = cooldown_status(state)
    if not cd["locked"]:
        print(json.dumps({"cleared": False, "detail": "no active cooldown"}, indent=2))
        return
    if not cd["timer_elapsed"]:
        print(json.dumps({"cleared": False,
                          "detail": f"timer not elapsed — {cd['remaining_human']} remaining"}, indent=2))
        sys.exit(10)
    fresh = state["checkins"] and (now() - parse(state["checkins"][-1]["ts"]) < timedelta(hours=2))
    if not fresh:
        print(json.dumps({"cleared": False,
                          "detail": "exit check-in required (within last 2h) before clearing"}, indent=2))
        sys.exit(10)
    score = compute_index(state)
    if score["index"] > EXIT_INDEX_MAX:
        start_cooldown(state, score["index"], max(score["level"], 4),
                       "extension: exit check-in still too high")
        save_state(state)
        print(json.dumps({"cleared": False, "extended": True,
                          "detail": f"index {score['index']} > {EXIT_INDEX_MAX}; cooldown extended",
                          "cooldown": cooldown_status(state)}, indent=2))
        sys.exit(10)
    if cd["lock_level"] >= 5:
        plan = (args.plan or "").strip()
        if len(plan) < RECOVERY_PLAN_MIN_CHARS:
            print(json.dumps({"cleared": False,
                              "detail": f"L5 exit requires --plan of >= {RECOVERY_PLAN_MIN_CHARS} chars: "
                                        "what changes this week so this doesn't recur?"}, indent=2))
            sys.exit(10)
        state["cooldown"]["recovery_plan"] = plan
        audit(state, "recovery_plan", plan[:200])
    audit(state, "cooldown_clear", f"exit index={score['index']}")
    state["cooldown"] = None
    save_state(state)
    out = {"cleared": True, "score": score,
           "parking_lot_size": len(state["parking_lot"])}
    if state["parking_lot"]:
        out["detail"] = "Parking lot has items — offer to resume them one at a time."
    print(json.dumps(out, indent=2))

def cmd_override(args):
    state = load_state()
    cd = state.get("cooldown")
    if not cd:
        print(json.dumps({"override": False, "detail": "no active cooldown"}, indent=2))
        return
    if cd.get("trigger_level", 4) >= 5:
        print(json.dumps({"override": False,
                          "detail": "Hard Lockout (L5): overrides are disabled by design. "
                                    "Crisis/safety situations are handled in conversation, "
                                    "not via override."}, indent=2))
        sys.exit(10)
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
    print(json.dumps({"override": True,
                      "detail": "One-time pass for THIS task only; lockout resumes after. "
                                f"+{OVERRIDE_PENALTY} penalty until the next calm (L0/L1) check-in."},
                     indent=2))

def cmd_history(args):
    state = load_state()
    print(json.dumps({
        "recent_checkins": state["checkins"][-args.n:],
        "recent_sessions": state["sessions"][-args.n:],
        "recent_events": state["events"][-args.n:],
        "parking_lot": state["parking_lot"],
    }, indent=2))

def cmd_report(args):
    state = load_state()
    score = compute_index(state)
    cd = cooldown_status(state)
    cutoff = now() - timedelta(days=14)
    sessions = [s for s in state["sessions"] if parse(s["ts"]) >= cutoff]
    checkins = [c for c in state["checkins"] if parse(c["ts"]) >= cutoff]
    late = sum(1 for s in sessions if s.get("late_night"))
    lockouts = [e for e in state["events"]
                if e["type"] == "cooldown_start" and parse(e["ts"]) >= cutoff]
    lines = [
        "# Burnout Guard — 14-day report",
        f"\n**Current index:** {score['index']} — **L{score['level']} {score['level_name']}**",
        f"**Basis:** {score['basis']}",
        f"**Lockout:** {'ACTIVE (L' + str(cd['lock_level']) + ') until ' + cd['ends_at'] if cd['locked'] else 'none'}",
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
    lines += [
        f"\n## Enforcement\n- Lockouts triggered (14d): {len(lockouts)}",
        f"- Parking lot: {len(state['parking_lot'])} item(s)",
        f"- Override penalty in effect: +{state.get('override_penalty', 0)}",
        f"\n## Audit\n- Events logged: {len(state['events'])}",
    ]
    if len(lockouts) >= 2:
        lines.append("\n> Two or more lockouts in 14 days. The pattern, not the timer, "
                     "is the signal — consider a conversation with a GP or occupational "
                     "health rather than another cooldown cycle.")
    print("\n".join(lines))

# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(prog="burnout.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("log-session").set_defaults(fn=cmd_log_session)

    ci = sub.add_parser("checkin")
    for f, h in [("exhaustion", "1=fresh 5=running on fumes"),
                 ("detachment", "1=engaged 5=checked out"),
                 ("efficacy", "1=useless 5=on top of it"),
                 ("sleep", "1=terrible 5=great"),
                 ("pressure", "1=light 5=crushing")]:
        ci.add_argument(f"--{f}", type=int, required=True, help=h)
    ci.add_argument("--notes", type=str, default="")
    ci.set_defaults(fn=cmd_checkin)

    df = sub.add_parser("defer")
    df.add_argument("--task", type=str, required=True)
    df.set_defaults(fn=cmd_defer)

    pk = sub.add_parser("parked")
    pk.add_argument("--clear", action="store_true")
    pk.set_defaults(fn=cmd_parked)

    cd = sub.add_parser("cooldown")
    cd.add_argument("action", choices=["start", "clear"])
    cd.add_argument("--reason", type=str, default="")
    cd.add_argument("--plan", type=str, default="",
                    help="Recovery plan, required to clear an L5 cooldown")
    cd.set_defaults(fn=cmd_cooldown)

    ov = sub.add_parser("override")
    ov.add_argument("--reason", type=str, required=True)
    ov.set_defaults(fn=cmd_override)

    hi = sub.add_parser("history")
    hi.add_argument("-n", type=int, default=10)
    hi.set_defaults(fn=cmd_history)

    sub.add_parser("report").set_defaults(fn=cmd_report)

    args = p.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
