# Contributing to Burnout Guard

Thanks for caring about this. Contributions of all sizes welcome.

## Ground rules

1. **The script decides, never vibes.** Any change that moves enforcement decisions
   from `burnout.py` into Claude's judgement will be declined. Determinism is the
   product.
2. **Protect, don't police.** Tone changes must pass the test: would a tired person
   feel cared for, or managed? No lectures, no diagnoses, no rest-as-ROI.
3. **The safety carve-out is inviolable.** Nothing may ever make the tool an obstacle
   to a person getting help. PRs weakening this are rejected without discussion.
4. **No telemetry, ever.** State stays in the user's local JSON file.
5. **Stdlib only.** The engine must run on Python 3.10+ with zero pip installs.

## Good first contributions

- Threshold tuning data from real use (open a Discussion with your `report` output —
  redact notes!)
- New behavioural signals (e.g. weekend-work weighting, session length if measurable)
- Localisation of the conversation guides
- Test coverage: `tests/` welcomes a pytest suite around `compute_index`, level
  boundaries, and the cooldown state machine

## Workflow

1. Fork → branch (`feat/...`, `fix/...`)
2. Keep `SKILL.md` under 500 lines; deep material goes in `references/`
3. For engine changes, demonstrate boundary behaviour (e.g. a table of index → level
   for the values 24.9/25/54.9/55/64.9/65/84.9/85)
4. Update `CHANGELOG.md`
5. PR with a clear description of which design principle the change serves

## Conduct

Be kind. This project exists because people run themselves into the ground; the
community around it should be the opposite of that energy.
