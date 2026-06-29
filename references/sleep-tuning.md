# Sleep tuning (v7)

Burnout Guard treats sleep as a multiplier on the **daily focus pivot**, not as a
direct input to the burnout index. The index still measures "am I burnt out
right now" from self-reports + behaviour (v6); the v7 work is on **strain**,
the trajectory metric — answering "are the conditions building toward burnout?"

A 6-hour focus day after 8 hours of rest is normal output. The same 6 hours
after 4 hours of broken sleep is a debt event. v7 makes the engine see that
difference when a sleep provider is configured.

## Defaults

These constants live at the top of `scripts/burnout.py`. They are best-effort
defaults from the Whoop/Oura/Apple-Watch literature, NOT validated for any
single person. Tune them once you have a few weeks of data.

| Constant                       | Default | What it gates                                  |
|--------------------------------|---------|------------------------------------------------|
| `SLEEP_GOOD_HOURS`             | 7.0     | hours AT or ABOVE this = restorative side      |
| `SLEEP_GOOD_QUALITY`           | 70.0    | quality (0-100) AT or ABOVE for "good" night   |
| `SLEEP_POOR_HOURS`             | 6.0     | hours BELOW this OR quality below poor = poor  |
| `SLEEP_POOR_QUALITY`           | 50.0    | quality BELOW this = poor night                |
| `SLEEP_PIVOT_GOOD_MULT`        | 1.10    | well-rested: pivot is 10% more forgiving       |
| `SLEEP_PIVOT_POOR_MULT`        | 0.85    | tired: same focus hours land 15% harder        |
| `SLEEP_RECOVERY_CREDIT`        | 0.5     | extra strain-debt reduction on a good night    |
| `CAL_MEETING_STRAIN_PER_HR`    | 0.15    | meeting-hr → focus-equivalent debt-hr          |
| `CAL_BACK_TO_BACK_PENALTY_PER_HR` | 0.10 | longest-b2b-hr → extra debt-hr                  |

A "neutral" night (between the two thresholds) leaves the pivot untouched.

## Quality scoring across providers

The engine compares Whoop, Oura, and Apple Health on a single 0-100 quality
axis. Each provider maps as follows:

- **Whoop:** `score.sleep_performance_percentage` (already 0-100).
- **Oura:** preference order is daily readiness score → composite of `efficiency`
  + restless-period penalty when readiness is unavailable.
- **Apple Health:** whatever you write into the JSON. If you only have duration,
  set quality to 65 and let `hours` drive the verdict.

## Tuning loop

1. Run `burnout.py status --explain` daily for two weeks with a provider
   connected. Note when the verdict surprises you.
2. If the engine treats your "tired but functional" mornings as **poor**,
   raise `SLEEP_POOR_HOURS` or `SLEEP_POOR_QUALITY` toward what your own
   bad mornings actually look like.
3. If the engine never registers a **good** night, lower `SLEEP_GOOD_HOURS`
   or `SLEEP_GOOD_QUALITY` by 5 points and observe.
4. The pivot multipliers (1.10 / 0.85) are deliberately small. If you want
   sleep to dominate, widen them — but understand you're saying that one
   night of bad sleep should change the engine's verdict on a full day's
   work as much as a 15% change in load. That's a strong claim.

## Calendar load

`today.ics` lives at `~/.burnout-guard/calendar/today.ics`. The engine reads it
once per `status` call and **only counts today** — historical calendar load
isn't carried because the file is meant to be re-exported each morning.

A back-to-back stretch is a sequence of meetings with ≤10 minutes between them.
Two or more such meetings count as one stretch.

## What is NOT auto-tuned

The engine deliberately does NOT learn your personal sleep thresholds from
history. That would lock in whatever rhythm you currently have — including
chronic under-sleep. The defaults are aspirational floors, not adaptive
norms. If you want them lower, you have to write that down explicitly in
this file, which forces a moment of "is this really my target, or is this
me rationalizing?".

The personal baseline for `heavy_day_hours` (v4) IS auto-tuned because that's
about your work pattern, not your physiology.
