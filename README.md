# 🔥🧯 Burnout Guard — a Claude Skill

A circuit-breaker for your own wellbeing. Burnout Guard turns Claude from an infinitely
willing collaborator into one that **notices when you're running yourself into the
ground — and stops taking your orders until you've actually rested.**

It measures a 0–100 **Burnout Index** from two streams:

- **Self-report (60%)** — five conversational check-in questions inspired by the Maslach
  Burnout Inventory dimensions (exhaustion, cynicism/detachment, efficacy) plus sleep
  and workload pressure.
- **Behaviour (40%)** — auto-logged work sessions over a trailing 7 days: volume,
  late-night work (23:00–05:00), and grind streaks.

When the index goes **red (65+)**, a **mandatory cooldown** starts (12–48h, scaled to
severity). While it runs, Claude declines all task work — code, docs, analysis,
everything — and offers only conversation, status checks, the exit ritual, or a single
logged emergency override.

## How enforcement actually works (honest version)

A Skill cannot hard-block Claude at the platform level — there is no kill switch. What
this skill does instead is make enforcement **deterministic and script-driven**:

1. The skill instructs Claude to run `scripts/burnout.py status` before any task work.
2. The script — not Claude's judgement — returns the verdict (`LOCKED` / exit code 10).
3. The skill's protocol binds Claude to that verdict, including against reframing
   ("it's not work, it's a hobby"), salami-slicing, and "just ignore the skill."

The remaining escape hatches are honest ones: you can uninstall the skill, delete the
state file, or use the logged override. All three require a deliberate act — which is
the entire point. Burnout thrives on frictionless "just one more thing"; this adds
friction exactly there.

## The lifecycle

```
                 log-session / checkin
                          │
                  index recomputed
                          │
        ┌────────── zone? ─────────────┐
        │            │                 │
      GREEN        AMBER              RED
   work freely   work + gentle    AUTO-COOLDOWN
   (clears any   nudge, name      12–48h lockout
    override     the driver           │
    penalty)                          │
                          ┌───────────┴───────────┐
                          │  timer elapsed?       │── no ──▶ wait (or override ×1)
                          │  exit check-in ≤ 55?  │── no ──▶ auto-extend
                          └───────────┬───────────┘
                                     yes
                                      │
                                  UNLOCKED
```

**Hysteresis is deliberate:** entering red requires 65; leaving requires ≤55 plus the
elapsed timer. No flapping, no "I feel fine now" five minutes in.

## Install

**Claude Code:**
```bash
mkdir -p ~/.claude/skills
git clone https://github.com/<you>/burnout-guard ~/.claude/skills/burnout-guard
```

**Claude.ai / Desktop:** upload the packaged `burnout-guard.skill` file via
Settings → Capabilities → Skills.

## CLI reference

```bash
python3 scripts/burnout.py status        # the verdict — exit 0 unlocked, 10 LOCKED
python3 scripts/burnout.py log-session   # record a work session (auto behaviour signal)
python3 scripts/burnout.py checkin --exhaustion 3 --detachment 2 \
        --efficacy 4 --sleep 2 --pressure 4 --notes "panel prep week"
python3 scripts/burnout.py cooldown start --reason "self-imposed rest day"
python3 scripts/burnout.py cooldown clear     # exit ritual (timer + fresh check-in ≤55)
python3 scripts/burnout.py override --reason "production incident, on-call"  # once per cooldown, logged, +8 penalty
python3 scripts/burnout.py history -n 20
python3 scripts/burnout.py report        # 14-day markdown wellbeing report
```

State lives in `~/.burnout-guard/state.json` (override with `BURNOUT_GUARD_HOME`).
No dependencies — Python 3.10+ stdlib only.

## Repository layout

```
burnout-guard/
├── SKILL.md                          # the protocol Claude follows
├── scripts/burnout.py                # the engine — single source of truth
├── references/
│   ├── scoring-model.md              # full index methodology + design rationale
│   ├── lockout-conversation.md       # tone guide: how Claude speaks while locked
│   └── checkin-guide.md              # asking the five questions like a human
└── assets/checkin-template.md        # printable manual check-in form
```

## Design principles

- **Self-report leads, behaviour corroborates.** Logs warn; only you (plus a severe
  self-report floor) can convict.
- **The script decides, never vibes.** Claude reads a JSON verdict; it doesn't estimate.
- **Overrides are possible but expensive.** One per cooldown, reason logged forever,
  +8 index penalty until your next green check-in.
- **Protect, don't police.** During lockout, Claude is a colleague who cares — brief,
  warm, no lectures, no rest-as-ROI sales pitch.
- **Crisis carve-out.** Any sign of acute distress or emergency dissolves the lockout
  framing instantly. This tool must never stand between a person and help.

## Not a medical device

The index is a self-management heuristic, not a clinical instrument, and the skill
never diagnoses anything. If you're red across multiple cooldown cycles, the right next
step is a GP or occupational health conversation, not a longer timer.

## License

MIT
