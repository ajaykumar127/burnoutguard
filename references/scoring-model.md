# Burnout Guard — Scoring Model

## Design principles

1. **Self-report leads, behaviour corroborates.** Burnout is subjective experience first;
   activity logs are a proxy. Hence 60/40 weighting.
2. **Behaviour alone can warn but not convict.** Without a fresh check-in, the index is
   capped at 64 (top of L3 Throttle). Activity logs can narrow your day to one task,
   but nobody gets locked out purely by a counter.
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

| Lv | Name | Range | Effect |
|---|---|---|---|
| 0 | Flow | 0–24 | Normal operation. Calm check-ins here clear override penalties. |
| 1 | Watch | 25–39 | Normal + score surfaced once per session. |
| 2 | Friction | 40–54 | Work proceeds; one nudge per session, check-in invited. |
| 3 | Throttle | 55–64 | Single-task mode; parking lot for everything else; ~45-min time-box. |
| 4 | Lockout | 65–84 | Auto cooldown, 12h at 65 → 36h at 84. One logged override available. |
| 5 | Hard Lockout | 85–100 | Auto cooldown, 36h at 85 → 72h at 100. Override disabled; exit requires a written recovery plan. An active L4 cooldown escalates to L5 if a new reading hits 85+. |

## Exit conditions

`cooldown clear` succeeds only when:
1. Timer has fully elapsed, AND
2. A check-in exists from within the last 2 hours, AND
3. The current index is ≤54 (back inside Friction — the 65→54 gap is the hysteresis
   band), AND
4. For L5-triggered cooldowns: a written recovery plan (`--plan`, ≥30 chars) in the
   user's own words.

Failing condition 3 auto-extends the cooldown based on the new index.

## Override economics

- L4 only — at L5 the script refuses overrides entirely.
- One override per cooldown. Second attempts are refused by the script.
- Reason (≥15 chars) is stored permanently in the audit log.
- +8 penalty added to every future index until the next *green* check-in — i.e. an
  override makes the next lockout slightly easier to trigger. The cost is real but small.
- The penalty clears on the next calm (L0/L1) check-in.

## Worked example

Week of heavy interview prep: 38 sessions in 7 days (5.4/day), 4 late-night sessions,
7-day streak.

- Volume: (5.4−2)/6 = 0.57 → 57. Night: 4/5 → 80. Streak: (7−4)/6 = 0.5 → 50.
- Behaviour = 0.4×57 + 0.35×80 + 0.25×50 = 63.3

Check-in: exhaustion 4, detachment 3, efficacy 3, sleep 2, pressure 5.

- Raw = 3×1.25 + 2×1.25 + 2×1.0 + 3×0.75 + 4×0.75 = 13.5 → ×5 = 67.5

Index = max(0.6×67.5 + 0.4×63.3, 67.5×0.85) = max(65.8, 57.4) = **65.8 → L4 Lockout**. Cooldown ≈ 13h.
