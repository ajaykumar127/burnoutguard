# 🔥🧯 Burnout Guard

**A Claude Skill that measures your burnout — and graduates from gentle nudges to
refusing your commands entirely until you've actually rested.**

Burnout doesn't announce itself. It compounds through a hundred frictionless
"just one more thing"s, usually with an infinitely willing AI on the other side.
Burnout Guard makes Claude the first collaborator that notices — and the first one
willing to say no.

```
$ python3 scripts/burnout.py status
{
  "score": { "index": 71.4, "level": 4, "level_name": "Lockout", ... },
  "verdict": "LOCKED",
  "instruction": "Decline all task work. Offer only: conversation, status,
                  deferring tasks, the exit ritual, or ONE logged override."
}
```

## The six levels

| Lv | Name | Index | What changes |
|---|---|---|---|
| 0 | **Flow** | 0–24 | Nothing. Invisible. |
| 1 | **Watch** | 25–39 | One sentence at session start, then silence. |
| 2 | **Friction** | 40–54 | Claude names the driver, suggests one adjustment. Work continues. |
| 3 | **Throttle** | 55–64 | Single-task mode. Everything else goes to the parking lot. ~45-min time-box. |
| 4 | **Lockout** | 65–84 | 12–36h cooldown. No task work. One logged emergency override. |
| 5 | **Hard Lockout** | 85–100 | 36–72h. No override. Exit requires a written recovery plan. |

The index blends a five-question self-report (60%, Maslach-inspired: exhaustion,
detachment, efficacy, plus sleep and pressure) with behavioural signals (40%: session
volume, late-night work, grind streaks). Escalation is automatic; de-escalation
demands evidence — elapsed time **and** an exit check-in scoring ≤54. Hysteresis by
design: you can't argue your way out five minutes after the timer.

## What it measures — attention time, not tokens

Tokens measure Claude's spend, not your strain: a 2M-token agentic run while you make
coffee is not burnout; four hours of *you* typing at 1am is. So the behavioural signal
is built from **heartbeats** — every prompt records a beat, beats under 15 minutes
apart stitch into continuous work blocks, and the trailing week yields: average
focused hours/day, longest unbroken stretch, late-night blocks, and active-day
streaks. Self-report still carries 60%; behaviour corroborates.

**v3.2 adds a second beat source: Claude Code transcripts** at
`~/.claude/projects/**/*.jsonl`. Every prompt across every project becomes a beat,
merged into the same pipeline — so you get cross-project visibility, retroactive
backfill (no hook install needed for history), and resilience if the hook is ever
disabled. `burnout.py report` now renders a 14-day focus **sparkline** and a 7×24
**hour-of-day × day-of-week heatmap** so you can actually see where your focus is
landing, plus all-time records: longest sprint and longest active-day streak.

## Sprints, strain, projects (v5)

The block + day model captures *now*. v5 captures *trajectory*: the multi-week
sprint pattern that actually drives burnout.

- **Multi-week strain** (Whoop-style debt model). 0–100 trajectory derived from
  a rolling 30-day balance: hours over your typical daily pivot accumulate as
  *debt*; light and rest days earn *recovery credit*. One bad week barely
  registers; three of them get you to Critical. Surfaced as a banded advisory
  in `status.strain` and `report`.
- **Sprint declaration.** `burnout.py sprint declare --name "Q3 launch"
  --until 2026-06-30` pre-commits you to a 1–21 day push. During: long-block
  and heavy-day thresholds widen so the system stops crying wolf during work
  you said you'd do. After: an automatic recovery window (half the sprint
  length) with tighter heavy-day and a pulled-in lockout floor at index 60.
  **Cancel queues 7 days** — same one-way ratchet as contracts.
- **Per-project rollup.** Transcripts carry `cwd`, so `report` shows attention
  by codebase. `burnout.py project mark --path X --deep-work` raises the
  long-block thresholds by 1.25× when actively in that cwd. Lockout boundary
  unaffected — deep work still has limits.
- **Stuck-loop detection.** Conservative heuristic on recent prompt content:
  if four near-duplicate prompts land in ten minutes, you get one console
  nudge ("looks like a stuck loop, fresh perspective in ten minutes will land
  more than another retry now"). Cannot trigger throttle or lockout. Half an
  hour spiraling depletes more than two hours flowing — the engine should
  notice.
- **Recovery prescription.** Lockout exit is no longer just a timer. The
  engine derives plain-language advice from your last sleep score, late-night
  blocks, and current strain — *recovery suggested: a real night of sleep, a
  no-Claude window tomorrow until midday, at least one fully off day in the
  next 72h*.

## Personal calibration + pre-commitment contracts

v4 rejects the "pick a profile" model that other wellbeing tools default to.
Profiles are a loophole — they let users argue the threshold down at exactly the
wrong moment. Instead:

- **Personal baseline.** After 14 days of observed activity, alert thresholds are
  *your* p75/p90, clamped to absolute floors (60/120 min long-block, 3h heavy day)
  so a couch-potato baseline can't disable protection, and ceilings (150/300 min,
  8h) so a marathon baseline still has a real cap. Marathon user gets alerts at
  their 90th percentile; recovery user at theirs. No profile to pick.
- **Contracts (one-way ratchet).** Pre-commit to a stricter version at calm time:
  `burnout.py contract set --lockout-index 60 --stop-by 22`. Tightening applies
  instantly. *Loosening* (or `contract clear`) queues for **7 days** before taking
  effect — designed specifically against in-the-moment renegotiation
  (Beeminder/Stickk lineage). Configurability is a one-way ratchet *toward*
  protection only.
- **Daily pulse.** `burnout.py pulse 3 --note "..."` is a 3-second 1-item burnout
  reading (West et al.'s validated single-item measure). Smooths the self-report
  curve and lifts the behaviour-only L3 cap when fresh. Doesn't replace the full
  5-item check-in — it complements it.
- **Sustainable rhythm streak.** Replaces grind streak as the goal: consecutive
  days with work AND no over-long block AND no late-night block. The rhythm we
  actually want to grow.
- **Preview mode.** First 7 days from install, L4/L5 surface as warnings instead
  of platform-blocking. Day-one users meet the system gradually.

## Real enforcement + console alerts in Claude Code

```bash
python3 scripts/burnout.py hook install
```

One command wires the engine into Claude Code's hooks (settings preserved, backup
written). From then on:

- **Console alerts**, right in your terminal, rate-limited:
  - `🧯 100 minutes continuous — good moment for a short break.`
  - `🧯 You've been at this 2h 40m without a real gap. Strong nudge: stand up, water, 10 minutes away. The code will keep.`
  - `🧯 4.2h of focused Claude work today. Worth deciding now when today ends.`
  - late-night session warnings, and L3 single-task-mode reminders.
- **Platform-level lockout**: at L4/L5 the UserPromptSubmit hook returns a block
  decision — your prompt is *refused before Claude ever sees it*, with the remaining
  time and the exit path printed in the console. This is not protocol compliance;
  it's the platform saying no.
- **The `bg:` channel**: any prompt starting with `bg:` always passes — so
  conversation, venting, status checks, parking tasks, the exit ritual, and anything
  urgent or personal stay reachable during a lockout. Claude still won't do task work
  there; it's a door for the person, not the to-do list.
- **SessionStart context** so Claude knows your level the moment a session opens.

On claude.ai (no hooks), enforcement is deterministic-by-protocol: the skill requires
Claude to run `burnout.py status` before task work and binds it to the script's
verdict — explicitly including against reframing, salami-slicing, and "just ignore
the skill."

The remaining escape hatches are honest ones: uninstall it, delete the state file, or
use the logged override (+8 index penalty, one per cooldown, 60-minute grace window,
disabled entirely at L5). All require a deliberate act. That deliberateness *is* the
product.

**And one rule outranks every level:** any sign of a genuine crisis, safety issue, or
acute distress dissolves all lockout framing instantly. This tool never stands between
a person and help.

## Quick start

```bash
# Claude Code
mkdir -p ~/.claude/skills
git clone https://github.com/<you>/burnout-guard ~/.claude/skills/burnout-guard

# Claude.ai / Desktop: download burnout-guard.skill from Releases,
# upload via Settings → Capabilities → Skills
```

Then just work. Say *"let's do a check-in"* when you're curious. Full walkthrough,
scenarios, tuning guide and FAQ: **[docs/GUIDE.md](docs/GUIDE.md)**.

## CLI

```bash
burnout.py status                 # the verdict — exit 0 (L0–L2) / 5 (Throttle) / 10 (Locked)
burnout.py hook install           # wire heartbeats + alerts + enforcement into Claude Code
burnout.py heartbeat --hook       # (called by hooks) record beat, emit alerts/blocks
burnout.py log-session            # manual behavioural signal (claude.ai surfaces)
burnout.py pulse 3 --note "..."   # daily 1-item burnout reading (1=fresh, 5=fumes)
burnout.py checkin --exhaustion 3 --detachment 2 --efficacy 4 --sleep 2 --pressure 4
burnout.py contract set --lockout-index 60 --stop-by 22 --max-daily-hours 4
burnout.py contract show          # current contract + effective + resolved thresholds
burnout.py contract clear         # 7-day cooling-off if it was tightening protection
burnout.py sprint declare --name "Q3 launch" --until 2026-06-30 --rationale "..."
burnout.py sprint show            # current sprint + phase + effective thresholds
burnout.py sprint finish          # end early; recovery window starts now
burnout.py sprint cancel          # 7-day cool-off; sprint stays active during it
burnout.py project mark --path /path/to/repo --deep-work
burnout.py project list           # top focus by cwd (last 7d) + flagged projects
burnout.py defer --task "..."     # parking lot (L3+)
burnout.py parked                 # list parked tasks
burnout.py cooldown start --reason "self-imposed rest day"
burnout.py cooldown clear [--plan "..."]    # exit ritual; --plan required after L5
burnout.py override --reason "..."          # L4 only, once, logged, penalised
burnout.py tone sarcastic         # opt-in dry wit ("supportive" to revert, "show" to check)
burnout.py report                 # 14-day wellbeing report (with sparkline + heatmap)
```

Python 3.10+ stdlib only. State: `~/.burnout-guard/state.json` — local, never
transmitted, yours to delete.

## Repository

```
burnout-guard/
├── SKILL.md                      # the protocol Claude follows
├── scripts/burnout.py            # the engine — single source of truth
├── references/
│   ├── levels.md                 # per-level playbook with example wording
│   ├── scoring-model.md          # index methodology + design rationale
│   ├── lockout-conversation.md   # tone guide for L3+
│   └── checkin-guide.md          # asking five questions like a human
├── assets/checkin-template.md
└── docs/
    ├── GUIDE.md                  # complete user guide
    └── DEPLOY.md                 # publishing + release workflow
```

## Design principles

- **Self-report leads, behaviour corroborates** — logs can throttle you, only you can
  lock yourself (severe self-report floor included for off-platform crunch).
- **The script decides, never vibes.**
- **Graduated, not binary** — the right response to index 47 is a sentence, not a wall.
- **Friction on overrides, prohibition at the top.**
- **Protect, don't police** — brief, warm, no lectures, no diagnoses, no rest-as-ROI.
- **Sarcasm with a floor** — opt-in dry wit (`tone sarcastic`): *"100 minutes
  straight. The bug will still be there after you blink. Wild concept, I know: a
  break."* Automatically softens at L5 and never touches genuine distress.

## Not a medical device

A self-management heuristic, not a clinical instrument. If the 14-day report shows
repeated lockouts, it will tell you what it thinks: the next conversation belongs with
a GP or occupational health, not a longer timer.

## Contributing

PRs and tuning reports welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The three
non-negotiables: determinism stays in the script, tone stays kind, and the safety
carve-out is inviolable.

## License

MIT
