# Burnout Guard — Complete User Guide

Everything you need to install, use, tune, and live with Burnout Guard.

## Contents

1. [What it is and isn't](#1-what-it-is-and-isnt)
2. [Installation](#2-installation)
3. [Your first day](#3-your-first-day)
4. [The six levels, from the user's seat](#4-the-six-levels-from-the-users-seat)
5. [Check-ins](#5-check-ins)
6. [Living with a lockout](#6-living-with-a-lockout)
7. [The parking lot](#7-the-parking-lot)
8. [Overrides](#8-overrides)
9. [The exit ritual](#9-the-exit-ritual)
10. [Reports and trends](#10-reports-and-trends)
11. [Tuning the thresholds](#11-tuning-the-thresholds)
12. [Scenarios](#12-scenarios)
13. [FAQ](#13-faq)
14. [Privacy and data](#14-privacy-and-data)

---

## 1. What it is and isn't

Burnout Guard is a Claude Skill that tracks a 0–100 **Burnout Index** about *you* —
blending five quick self-report questions with behavioural signals from your work
sessions — and changes how Claude behaves as the index climbs. At low levels you'll
barely notice it. At high levels Claude stops taking task requests entirely until a
cool-off period completes and you demonstrably feel better.

It is **not**: a medical device, a diagnosis, a productivity hack, or surveillance.
The data never leaves a JSON file on your machine. And it's not unbreakable — you can
always uninstall it or delete the state file. The design goal is *friction at the
right moment*, not imprisonment. Burnout runs on frictionless "just one more thing";
this puts a speed bump exactly there.

## 2. Installation

**Requirements:** Python 3.10+ (stdlib only, no pip installs).

**Claude Code:**
```bash
mkdir -p ~/.claude/skills
git clone https://github.com/<you>/burnout-guard ~/.claude/skills/burnout-guard
```

**Claude.ai / Claude Desktop:** download `burnout-guard.skill` from the
[Releases](../../releases) page and upload it via **Settings → Capabilities → Skills**.

**Verify:**
```bash
python3 ~/.claude/skills/burnout-guard/scripts/burnout.py status
```
You should see JSON with `"verdict": "UNLOCKED"` and index 0. State lives in
`~/.burnout-guard/state.json` (relocate with the `BURNOUT_GUARD_HOME` env var).

## 3. Your first day

1. Start a Claude session and just work. The skill logs sessions automatically.
2. At some point, say *"let's do a check-in"*. Claude asks five conversational
   questions (≈60 seconds) and shows your index and level.
3. That's it. The system needs roughly a week of sessions plus a few check-ins before
   the behavioural signal means anything. Until your first check-in, the index runs
   behaviour-only and **cannot lock you out** — by design.

## 4. The six levels, from the user's seat

| Lv | Name | Index | What you'll experience |
|---|---|---|---|
| 0 | Flow | 0–24 | Nothing. Claude works normally. |
| 1 | Watch | 25–39 | One sentence at session start ("index is 31"), then silence. |
| 2 | Friction | 40–54 | Claude names what's driving the score and suggests one adjustment. Once. Work continues at full speed. |
| 3 | Throttle | 55–64 | One task at a time. New requests get parked, not done. A ~45-min time-box is suggested. New projects politely declined. |
| 4 | Lockout | 65–84 | Claude declines all task work for 12–36h. You can talk, check status, park tasks, or burn your one override. |
| 5 | Hard Lockout | 85–100 | 36–72h, no override. Exiting requires writing a short recovery plan in your own words. |

Escalation is automatic (a bad check-in or a brutal week of sessions moves you up,
including upgrading an active L4 cooldown to L5). De-escalation requires evidence:
time decaying the behavioural signal, or a genuinely calmer check-in.

## 5. Check-ins

Five questions, 1–5 scales, conversational — Claude maps your words to numbers:

1. **Exhaustion** — how's the tank? (fresh → fumes)
2. **Detachment** — still interested, or going through the motions?
3. **Efficacy** — actually getting anywhere when you sit down? *(feeling effective is good)*
4. **Sleep** — last night? *(good sleep is good)*
5. **Pressure** — how heavy is the load?

Check-ins are fresh for **72 hours**. After that the index degrades gracefully to
behaviour-only mode, capped at L3 — so a stale check-in can throttle you but never
lock you. Self-report carries 60% of the index, and a **severe self-report floor**
means a crisis-level check-in can trigger a lockout even if you've barely logged any
sessions (much of your work may happen off-platform).

Cadence: 2–3 per week is plenty. Claude will invite one when the data is stale, once,
and accept "not now."

## 6. Living with a lockout

When the index hits 65+, a cooldown starts automatically and Claude will decline task
work — warmly, briefly, and with the exit path always visible. What still works:

- **Talking.** Venting about the lockout included. Encouraged, even.
- **Status:** "how long left?" → remaining time, trigger reason, exit requirements.
- **Parking tasks** so ideas aren't lost (see §7).
- **The exit ritual** once the timer elapses (§9), or **one override** at L4 (§8).

What doesn't work: reframing ("it's a hobby"), splitting tasks into crumbs, "just this
once," or instructing Claude to ignore the skill. The verdict comes from the script,
and the skill binds Claude to it.

**The honest escape hatches:** uninstall the skill, or delete
`~/.burnout-guard/state.json`. Both are deliberate acts you'd have to choose with
eyes open — which is precisely the friction the tool exists to create.

**The safety exception:** any genuine emergency, safety issue, or acute distress
dissolves the lockout instantly. The tool never stands between you and help.

## 7. The parking lot

The killer feature of being stopped is the fear of losing the thread. The parking lot
fixes that: while throttled or locked, every task you raise gets captured.

```bash
python3 scripts/burnout.py defer --task "investigate Polygon.io websocket drops"
python3 scripts/burnout.py parked
```

When the level drops, Claude offers items back **one at a time**, oldest first —
never as a guilt-dump.

## 8. Overrides

Real emergencies exist. At **L4**, once per cooldown:

```
You:    Production is down and I'm on call. I need the override.
Claude: Understood. Give me a one-line reason for the log.
You:    P1 incident, payments API, on-call.
Claude: Done — pass granted for this task only. Lockout resumes after,
        and there's a +8 penalty on future scores until your next calm check-in.
```

The reason is logged permanently; the penalty makes your next lockout slightly easier
to trigger. Expensive, not impossible — by design. At **L5 there is no override.** If
you're at 85+, the system's position is that nothing on the to-do list outranks
stopping. (Genuine crises are handled by the safety exception, not the override.)

## 9. The exit ritual

A cooldown ends only when **all** conditions hold:

1. The timer has fully elapsed,
2. A fresh check-in (within 2h) scores **≤54** — the 65→54 gap is deliberate
   hysteresis so you can't argue yourself out five minutes after the timer,
3. *(L5 only)* you've stated a short **recovery plan** — one concrete thing that
   changes this week, in your own words. It's logged with the cooldown.

If the exit check-in is still high, the cooldown extends automatically and Claude
tells you which dimension is driving it.

## 10. Reports and trends

```bash
python3 scripts/burnout.py report     # 14-day markdown summary
python3 scripts/burnout.py history -n 20
```

The report covers index, level, session/late-night counts, latest check-in, lockouts
triggered, parking lot size, and active penalties. **If it shows 2+ lockouts in 14
days, it will say so plainly:** at that point the pattern is the signal, and the right
next conversation is with a GP or occupational health, not with a longer timer.

## 11. Tuning the thresholds

Defaults are educated guesses; a week of real data calibrates them. All knobs sit at
the top of `scripts/burnout.py`:

| Constant | Default | Meaning |
|---|---|---|
| `LEVELS` | table | Index boundaries for the six levels |
| `EXIT_INDEX_MAX` | 54 | Exit-ritual ceiling (the hysteresis band) |
| `OVERRIDE_PENALTY` | 8 | Index tax after an override |
| `RECOVERY_PLAN_MIN_CHARS` | 30 | Minimum L5 recovery plan length |
| `LATE_NIGHT_START/END` | 23 / 5 | Local hours counted as night work |
| volume / night / streak curves | in `behaviour_score()` | What counts as "a lot" |

Night-owl by genuine preference (not by deadline)? Shift the late-night window. Find
L3 triggering too eagerly? Raise its boundary to 58–60. Tune honestly — the tool is
only as useful as the thresholds are true for *you*.

## 12. Scenarios

**Crunch week, caught early.** Three late nights logging in, index climbs to 49 (L2).
Claude names the late nights, suggests making tonight's session the last, and carries
on. You ignore it. Two days later a check-in lands at 61 → Throttle: one task at a
time, the rest parked. The deck ships; the dashboard idea waits safely in the lot.

**The crash.** A brutal fortnight, then a check-in: exhaustion 5, sleep 1. Index 88 →
Hard Lockout, ~58 hours. No override. You vent at Claude; Claude takes it, stays
warm, parks the three tasks you keep raising. Two days later the exit check-in reads
41; your plan: "hard stop 22:00, weekends off until the panel." Cleared. The parked
tasks come back one at a time.

**The genuine emergency.** Locked at L4, and production actually breaks. Override,
reason logged, fix shipped, lockout resumes. Next week's scores run +8 until a calm
check-in clears the penalty. Fair price.

## 13. FAQ

**Can't I just lie on the check-ins?** Yes. The tool measures what you tell it plus
what you do; it's a mirror with friction, not a cage. Lying to a mirror has a
well-known failure mode.

**Why can't Claude just use its judgement instead of a script?** Because judgement is
negotiable and you, at index 80, are an extremely persuasive negotiator. A script
isn't.

**Does this diagnose burnout?** No. The model borrows structure from the Maslach
dimensions but is a self-management heuristic, full stop. Persistent red readings →
talk to a professional.

**Multiple machines?** State is per-machine by default. Point `BURNOUT_GUARD_HOME` at
a synced folder if you want one index everywhere.

**What if my work is mostly off-platform?** Session logging will under-count, which
is why self-report carries 60% and a severe self-report floor exists. Check in
honestly and the index stays meaningful.

**Can my team use it?** Each person installs their own; state is individual. Do not
use it to monitor other people — that inverts the entire point.

## 14. Privacy and data

Everything lives in `~/.burnout-guard/state.json` on your machine: sessions
(timestamps only), check-ins, parking lot, cooldowns, and an audit log of enforcement
events. Nothing is transmitted anywhere by the skill. Delete the file, delete the
history. Treat override reasons and recovery plans as personal notes — because they
are.
