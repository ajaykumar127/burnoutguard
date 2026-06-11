# Burnout Guard — Scoring Model

## Design principles

1. **Self-report leads, behaviour corroborates.** Burnout is subjective experience first;
   activity logs are a proxy. Hence 60/40 weighting.
2. **Behaviour alone can warn but not convict.** Without a fresh check-in, the index is
   capped at amber (64). Nobody gets locked out purely by an activity counter.
3. **Hysteresis everywhere.** Entering red is easy; leaving requires both time AND a
   verified improvement (exit check-in ≤55). This prevents flapping and prevents
   "I feel fine now" rationalisation five minutes into a 24-hour cooldown.
4. **Friction on overrides, not prohibition.** Real emergencies happen. One override per
   cooldown, a logged reason, and a +8 penalty makes bypassing possible but expensive.

## Self-report component (60%)

Five 1–5 scales, inspired by the three Maslach Burnout Inventory dimensions
(emotional exhaustion, depersonalisation/cynicism, reduced personal accomplishment),
plus two well-evidenced moderators (sleep, workload pressure).

| Scale | Direction | Weight (of 100) | MBI dimension |
|---|---|---|---|
| Exhaustion | higher = worse | 25 | Emotional exhaustion |
| Detachment | higher = worse | 25 | Cynicism / depersonalisation |
| Efficacy | higher = BETTER (reversed) | 20 | Personal accomplishment |
| Sleep quality | higher = BETTER (reversed) | 15 | Moderator |
| Pressure | higher = worse | 15 | Moderator |

Score = weighted sum normalised to 0–100. A check-in is "fresh" for 72 hours; after
that, the model degrades gracefully to behaviour-only mode.

> Note: this is a self-management heuristic, not a clinical instrument. It deliberately
> does not diagnose anything. If scores stay red across multiple cooldown cycles, the
> right tool is a conversation with a GP or occupational health, not a longer cooldown.

## Behavioural component (40%)

Computed from auto-logged sessions over the trailing 7 days:

| Signal | Weight | Curve |
|---|---|---|
| Volume (sessions/day) | 40% | 0 below 2/day, max at 8/day |
| Late-night work (23:00–05:00 local) | 35% | max at 5 late-night sessions/week |
| Grind streak (consecutive active days) | 25% | 0 below 5 days, max at 10 days |

Late-night weighting is deliberately high: night work is the single best cheap proxy for
"this has stopped being sustainable."

## Index, zones, cooldown duration

```
index = max( 0.6 × self_report + 0.4 × behaviour,  self_report × 0.85 ) + override_penalty
```

The `self_report × 0.85` floor exists so a crisis-level check-in can trigger red even
when behavioural data is sparse (much of the user's work may happen off-platform).
Behaviour corroborates and amplifies; it is never required to convict.

| Zone | Range | Effect |
|---|---|---|
| Green | 0–39 | Normal operation. Clears any override penalty. |
| Amber | 40–64 | Work proceeds; Claude should gently surface the score and suggest a check-in or break. |
| Red | 65–100 | Automatic cooldown starts. |

Cooldown duration interpolates linearly: 12h at index 65 → 48h at index ≥90.

## Exit conditions

`cooldown clear` succeeds only when:
1. Timer has fully elapsed, AND
2. A check-in exists from within the last 2 hours, AND
3. The current index is ≤55 (comfortably below the red threshold — that gap is the
   hysteresis band).

Failing condition 3 auto-extends the cooldown based on the new index.

## Override economics

- One override per cooldown. Second attempts are refused by the script.
- Reason (≥15 chars) is stored permanently in the audit log.
- +8 penalty added to every future index until the next *green* check-in — i.e. an
  override makes the next lockout slightly easier to trigger. The cost is real but small.

## Worked example

Week of heavy interview prep: 38 sessions in 7 days (5.4/day), 4 late-night sessions,
7-day streak.

- Volume: (5.4−2)/6 = 0.57 → 57. Night: 4/5 → 80. Streak: (7−4)/6 = 0.5 → 50.
- Behaviour = 0.4×57 + 0.35×80 + 0.25×50 = 63.3

Check-in: exhaustion 4, detachment 3, efficacy 3, sleep 2, pressure 5.

- Raw = 3×1.25 + 2×1.25 + 2×1.0 + 3×0.75 + 4×0.75 = 13.5 → ×5 = 67.5

Index = 0.6×67.5 + 0.4×63.3 = **65.8 → RED**. Cooldown ≈ 12h.
