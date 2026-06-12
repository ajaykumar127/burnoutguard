# Changelog

## v3.2.0 — 2026-06-12

**Transcript signal, all-time records, CLI graphs.**

- Second beat source: Claude Code transcripts at `~/.claude/projects/**/*.jsonl`.
  Every user prompt becomes a beat, merged into the existing block-stitching
  pipeline. Cross-project visibility, retroactive backfill (no hook needed for
  history), and resilience when the hook isn't installed. Best-effort: missing or
  unreadable transcripts silently fall back to heartbeats. 30-day lookback cap,
  500-file cap to keep `status` snappy.
- All-time records persisted in `state.records`: longest single sprint
  (`longest_block_min_alltime` + when), longest active-day streak, current streak.
  Updated on every score computation, surfaced in `status` and `report`.
- `report` gains two CLI graphs (stdlib Unicode, no deps):
  - 14-day daily-focus sparkline (`▁▂▃▄▅▆▇█`)
  - 7×24 hour-of-day × day-of-week heatmap in local time, so you can see when
    your focus actually lands
- v3 → v4 state migration; `from __future__ import annotations` for cleaner
  forward-compat (the engine now imports cleanly on Python 3.9 too, though 3.10+
  remains the supported floor).

## v3.1.0 — 2026-06-12

**Tone modes.** `burnout.py tone sarcastic|supportive|show`.

- Full two-voice message catalogue for all console alerts, lockout notices,
  throttle reminders, and the bg: channel acknowledgement
- Claude matches the configured register in lockout/throttle conversations
- Guardrails: sarcasm targets the situation never the person, auto-softens to
  sincere at L5 (engine-enforced), and drops instantly for genuine distress
  (skill-enforced); `status` now exposes the active tone

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
