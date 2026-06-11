# Changelog

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
