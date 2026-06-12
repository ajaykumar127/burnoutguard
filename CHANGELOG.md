# Changelog

## v3.0.0 — 2026-06-12

**Attention-time measurement + Claude Code console integration.**

- Behavioural signal rebuilt on heartbeats → continuous work blocks: avg focused
  hours/day (30%), late-night blocks (25%), longest-stretch intensity (25%),
  streaks (20%). Tokens explicitly rejected as a measure (they track Claude's spend,
  not human strain).
- `heartbeat --hook` command + `hook install|uninstall|status` one-command installer
  (settings merged non-destructively, timestamped backup).
- Real console alerts via hook `systemMessage`: 90/150-min continuous stretches,
  4h+ heavy days, late-night starts, L3 throttle reminders — all rate-limited.
- **Platform-level lockout**: at L4/L5 the UserPromptSubmit hook returns
  `decision: block` — prompts are refused before Claude sees them.
- The `bg:` channel: prefixed prompts always pass during lockouts so conversation,
  the exit ritual, parking, and emergencies stay reachable. Crisis carve-out intact.
- Override now grants a 60-minute hook-enforcement grace window.
- SessionStart hook injects current level as context; Stop hook extends blocks.
- `report` gains an Attention section; v2 → v3 state migration; fail-open heartbeat
  (an engine error can never break a prompt).

## v2.0.0 — 2026-06-11

**Graduated levels.** The binary lock becomes a six-level ladder.

- Added L0 Flow / L1 Watch / L2 Friction / L3 Throttle / L4 Lockout / L5 Hard Lockout
- L3 Throttle: single-task mode with `defer` / `parked` parking-lot commands
- L5 Hard Lockout: overrides disabled; exit requires a written recovery plan (`--plan`)
- Automatic L4 → L5 escalation when a new reading hits 85+
- `status` now returns effective level + per-level instruction; exit codes 0/5/10
- Behaviour-only cap raised in semantics: can reach L3, never L4+
- Repeated-lockout advisory in `report` (2+ lockouts/14 days → suggest professional support)
- v1 → v2 state migration
- New docs: complete user guide (docs/GUIDE.md), deployment guide, per-level playbook
  reference, CONTRIBUTING, issue templates

## v1.0.0 — 2026-06-11

- Burnout Index (60% self-report / 40% behavioural), green/amber/red zones
- Auto cooldown at red with hysteresis exit ritual
- Single logged override with penalty; audit trail; 14-day report
