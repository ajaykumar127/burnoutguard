# Check-in Guide

How to gather the five scores without it feeling like a form.

## The questions (conversational phrasings)

Ask naturally, one or two at a time, and map the answers to 1–5 yourself. Don't show the
user flag names or make them say numbers unless they prefer to.

1. **Exhaustion** — "How's the tank? Running fresh or on fumes?"
   (1 = fresh → 5 = fumes)
2. **Detachment** — "And the work itself — still interesting, or are you going through
   the motions?" (1 = engaged → 5 = checked out)
3. **Efficacy** — "When you sit down to it, are you actually getting anywhere?"
   (1 = wading through treacle → 5 = on top of it) — *note: reversed; feeling effective
   is good.*
4. **Sleep** — "How'd you sleep last night?" (1 = terrible → 5 = great) — *reversed.*
5. **Pressure** — "How heavy is the load this week?" (1 = light → 5 = crushing)

## Mapping answers

| Answer style | Mapping approach |
|---|---|
| "Pretty knackered, honestly" | exhaustion 4 |
| "It's fine" (flat tone, short) | probe gently once; default to 3 |
| "Best week in ages" | 1–2 on the negative scales |
| Refuses a question | use 3 and note it in `--notes` |

When in doubt between two values, pick the **more concerning** one — the model has
hysteresis to absorb a slightly pessimistic read, but an optimistic read can mask a
red zone.

## After scoring

1. Run the `checkin` command with the mapped values and a one-line `--notes` summary in
   the user's own words.
2. Show the result plainly: index, zone, what changed since last time.
3. Green → carry on, one sentence of acknowledgement.
   Amber → carry on, but name the driver ("late nights are doing most of the lifting
   here") and suggest exactly one adjustment.
   Red → the script has started a cooldown; switch to `lockout-conversation.md` tone.

## Cadence

- Invite a check-in when `status` reports basis "behaviour-only" (no check-in in 72h).
- Don't nag: one invitation per session, accept "not now" gracefully.
- A weekly `report` offer is plenty.
