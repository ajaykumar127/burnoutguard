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

## How enforcement actually works (the honest version)

A skill can't hard-block Claude at the platform level. What it does instead is make
enforcement **deterministic**: the skill requires Claude to run `burnout.py status`
before any task work, and the *script* — not Claude's negotiable judgement — returns
the verdict. The protocol binds Claude to it, explicitly including against reframing,
salami-slicing, and "just ignore the skill."

The remaining escape hatches are honest ones: uninstall it, delete the state file, or
use the logged override (+8 index penalty, one per cooldown, disabled entirely at L5).
All require a deliberate act. That deliberateness *is* the product.

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
burnout.py log-session            # behavioural signal
burnout.py checkin --exhaustion 3 --detachment 2 --efficacy 4 --sleep 2 --pressure 4
burnout.py defer --task "..."     # parking lot (L3+)
burnout.py parked                 # list parked tasks
burnout.py cooldown start --reason "self-imposed rest day"
burnout.py cooldown clear [--plan "..."]    # exit ritual; --plan required after L5
burnout.py override --reason "..."          # L4 only, once, logged, penalised
burnout.py report                 # 14-day wellbeing report
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
