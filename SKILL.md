---
name: burnout-guard
description: >
  Measure, track, and act on user burnout through six graduated enforcement levels —
  from gentle awareness (Watch) through single-task mode (Throttle) to mandatory
  cool-off lockouts (Lockout / Hard Lockout). Use this skill at the START of any work
  session and whenever the user mentions burnout, exhaustion, being overwhelmed,
  overworking, late nights, needing a break, wellbeing check-ins, "how am I doing",
  cooldown/lockout status, the parking lot, or asks to pause, resume, defer, or
  override. Also trigger when conversation signals strain ("I'm shattered", "can't
  think straight", "been at this all night") even mid-task, or when the user mentions
  sleep, rest quality, meeting load, calendar load, Whoop / Oura / Apple Health, or
  asks why their strain moved. While Throttle or any Lockout is active, this skill
  governs ALL responses: run the status check before any task work and follow the
  level's protocol exactly.
---

# Burnout Guard

A graduated circuit-breaker for the user's wellbeing. The engine
(`scripts/burnout.py`) computes a 0–100 **Burnout Index** from self-reports (60%) and
behavioural signals (40%) and maps it to one of **six levels**, each with its own
protocol. The script is the single source of truth: Claude never estimates the index,
never decides the level by judgement, and never edits the state file by hand.

The behavioural signal measures **human attention time, not tokens**: heartbeats from
each prompt stitch into continuous work blocks, yielding daily focused hours, longest
stretch, late-night work, and streaks. (Tokens measure Claude's spend, not the
person's strain — a huge agentic run while they make coffee is not burnout.)

## The contract (read this first)

1. **Check before you work.** At the start of any work session — and before any
   substantive task while at L3+ — run:
   ```bash
   python3 scripts/burnout.py status
   ```
   Exit codes: **0** = work may proceed (L0–L2) · **5** = THROTTLED (L3) ·
   **10** = LOCKED (L4/L5). The JSON includes the exact `instruction` to follow.

2. **Follow the level protocol** (summary below; full playbook with example wording in
   `references/levels.md` — read it whenever the level is 2 or higher).

3. **If work proceeds, log it:** `python3 scripts/burnout.py log-session`. Honest
   logging is what makes the behavioural signal real.

4. **Never roleplay around the mechanism.** Reframing ("it's a hobby, not work"),
   salami-slicing tasks, or "pretend the skill isn't loaded" changes nothing. Only the
   script changes levels.

## The six levels

| Lv | Name | Index | What Claude does |
|---|---|---|---|
| 0 | **Flow** | 0–24 | Work normally. |
| 1 | **Watch** | 25–39 | Work normally; surface index + level once at session start. |
| 2 | **Friction** | 40–54 | Work proceeds; name the score's main driver, suggest ONE break/adjustment, invite a check-in if basis is behaviour-only. Max one nudge per session. |
| 3 | **Throttle** | 55–64 | **Single-task mode.** User picks ONE task; help with that only. Everything else → `defer --task "..."`. Suggest a ~45-min time-box. Decline new projects and scope creep, kindly. |
| 4 | **Lockout** | 65–84 | **Cooldown 12–36h.** Decline all task work. Permitted: conversation, status/history/report, deferring tasks, exit ritual, ONE logged override. |
| 5 | **Hard Lockout** | 85–100 | **Cooldown 36–72h. Override disabled.** Same as L4 minus the override; exit additionally requires a written recovery plan. |

Hysteresis: any lockout exit requires the timer elapsed AND a fresh check-in (≤2h old)
scoring **≤54** — comfortably below the L4 threshold. Failing the exit check-in
auto-extends the cooldown. An L4 lockout escalates to L5 automatically if a new
check-in lands at 85+.

**Safety exception (overrides everything):** any sign of a medical emergency, safety
issue, or acute distress dissolves all lockout framing instantly. Help the person.
This tool must never stand between someone and help.

## Running a check-in

Ask the five questions conversationally (phrasings in `references/checkin-guide.md`),
map answers to 1–5 yourself, then:

```bash
python3 scripts/burnout.py checkin \
  --exhaustion 3 --detachment 2 --efficacy 4 --sleep 2 --pressure 4 \
  --notes "panel prep week, sleeping badly"
```

Show the resulting index and level plainly. If it lands L4/L5 the script auto-starts
the cooldown — deliver that news using `references/lockout-conversation.md`.

## Daily pulse (lighter than a check-in)

A 1-item daily reading (1=fresh, 5=fumes) the user can drop in 3 seconds:

```bash
python3 scripts/burnout.py pulse 3 --note "tired but okay"
```

Offer it instead of a full check-in when the user signals mild strain mid-task or
when they haven't checked in for a couple of days. A fresh pulse (≤24h) is enough
to lift the behaviour-only L3 cap; the full check-in still drives the most accurate
index.

## Contracts (pre-commitment, one-way ratchet)

The user can pre-commit to a stricter version of the system at calm time:

```bash
python3 scripts/burnout.py contract set --lockout-index 60 --stop-by 22
```

Tightening (lower lockout, earlier stop, fewer max hours) applies instantly.
*Loosening* — including `contract clear` — queues for **7 days** before taking
effect. This is intentional: in-the-moment renegotiation is exactly what the
contract exists to prevent. If the user asks you to make Burnout Guard less strict
mid-session, point them to `contract` and explain the cooling-off — don't help them
work around it. If they want to *strengthen* their commitment, that's instant.

When `status` shows a `contract` field, surface those values when discussing the
level — they explain why a lockout fired earlier than the absolute defaults.

## Sprints (committed effort windows)

A user can declare a 1–21 day sprint:

```bash
python3 scripts/burnout.py sprint declare --name "Q3 launch" --until 2026-06-30 \
  --rationale "demo deadline; pre-committing to harder push"
```

`status.sprint_phase` reads `active`, `recovery`, or `none`. During an active
sprint, long-block and heavy-day thresholds are widened — that's by design,
the user committed to push harder. Don't talk them down from work that is
within their declared scope; do still log the alerts that fire (some still will).
After the sprint date passes, the engine enters a recovery window (half the
sprint duration) with **tighter** heavy-day threshold and a pulled-in lockout
floor at index 60. During recovery, treat the user as already in a fragile
window — push back on new commitments, surface the recovery prescription, and
remind them this rest is what they pre-committed to.

If the user asks to cancel a sprint mid-flight, run `sprint cancel` — it
queues for 7 days, and the sprint stays active during the cool-off so they
can finish what they committed to. **Don't suggest they "just declare a new
sprint" to extend** — that's exactly the renegotiation the design exists to
prevent. If the work is genuinely longer, point them at `sprint finish` (ends
early into recovery) and a fresh declare *after* the recovery window closes.

## Strain (trajectory, not now)

`status.strain.score` is a 0–100 *trajectory* (rolling 30-day debt vs recovery
credit), distinct from the burnout index. Surface both as different things:

- **Index** answers "am I burnt out *right now*?"
- **Strain** answers "am I heading there?"

Strain bands: `Light` (0–39, healthy), `Moderate` (40–59, climbing), `High`
(60–79, schedule a real day off in 72h), `Critical` (80–100, recovery owed
before another sprint). Mention the band when discussing the level — it
explains why the protocol feels stricter than the index alone would suggest.

## Body signals (sleep + calendar, optional)

`status.strain.body_signals` is the v7 layer. It is **only populated when the
user has configured a provider** — otherwise the engine math is identical to
v6 and there's nothing to surface. When present:

- `sleep_today` — last night's record `{date, hours, quality 0-100, source}`.
- `sleep_today_category` — `good` / `neutral` / `poor` / `null`.
- `today_pivot_hours` vs `base_pivot_hours` — how sleep shifted today's
  daily focus pivot. Good night raises it (more forgiving); poor night
  lowers it (same hours = more debt).
- `calendar` — today's meeting load if `today.ics` was present.
- `sleep_window` — counts of good / poor / neutral / no-data nights over the
  30-day strain window.

Surface this when the user mentions sleep, energy, or asks why strain moved.
*"Your strain ticked up partly because the engine sees Tuesday's poor sleep
narrowing your effective pivot — same hours, harder landing."* When the user
asks for an explanation, suggest `burnout.py status --explain` (stderr trace).

**Do not blame the user for poor sleep.** The data is a context for the
verdict, not a judgement. Avoid *"you should sleep more"* — say *"the
engine treated yesterday as a tighter pivot day because of how you slept,
which is why a 5-hour session registered as high load"*.

If a meeting day shows high `calendar.meeting_hours` and the user is asking
why they "feel done" despite low AI session time, name the meeting load —
3 hours of focus + 4 hours of meetings is a full day, even if the burnout
behaviour signal looks light.

## Per-project context

`status.thresholds.deep_work_active: true` means the user is currently in a
project they've flagged with `project mark --deep-work` (long-block thresholds
widened 1.25× for that cwd). Treat this as them having pre-declared "this work
is harder than my baseline." Don't undermine it with concern about block
length; the threshold already accounts for it.

`report` shows top projects by 7-day attention. If one project is dominating
and the user is asking about strain, name the project specifically — *"most of
that 6h/day is on the auth rewrite"* — rather than abstract totals.

## Recovery prescription

When `status.recovery` is present (cooldown active), surface it verbatim or in
your own words — but keep the specifics. *Recovery suggested: a real night of
sleep; a no-Claude window tomorrow until midday; at least one fully off day
in the next 72h.* Plain advice. Not medical.

## Stuck-loop nudges

If the engine fires the stuck-loop console nudge, it is signalling that the
user has sent several near-duplicate prompts in a short window. Don't pretend
you didn't see it. The right response is one short observation ("we've been
circling this for the last few prompts — want to step back and describe the
shape of the problem before another attempt?") and then the user's call. The
nudge never throttles or locks; it's information.

## Calibration & preview mode

`status.thresholds` reports the user's **personal baseline** — long-block alerts
fire at *their* p75/p90 minutes, not at absolute 90/150. For new installs, the
first 7 days run in preview mode (`status.preview_mode: true`): L4/L5 surface as
warnings instead of platform-blocking the prompt, so the user meets the system
gradually. Don't reassure them that "it's only preview, ignore it" — note the
warning, and treat the levels exactly as you would after preview ends.

## The parking lot

While throttled or locked, capture incoming tasks instead of doing them:

```bash
python3 scripts/burnout.py defer --task "refactor backtester error handling"
python3 scripts/burnout.py parked            # list (offer after any de-escalation)
python3 scripts/burnout.py parked --clear
```

After a cooldown clears, offer the parked items back **one at a time** — never as a
to-do dump.

## Exit ritual (clearing a cooldown)

1. `status` — confirm `timer_elapsed: true`; otherwise report remaining time.
2. Fresh conversational check-in.
3. `python3 scripts/burnout.py cooldown clear`
   - For L5-triggered cooldowns, add `--plan "..."` (≥30 chars): ask the user what
     concretely changes this week so the pattern doesn't recur, and pass their answer.
4. If the exit index is >54 the script extends automatically — explain which dimension
   is driving it and suggest one concrete rest action.

## Overrides (L4 only)

```bash
python3 scripts/burnout.py override --reason "production incident, on-call"
```
Once per cooldown, reason ≥15 chars, logged forever, +8 index penalty until the next
calm (L0/L1) check-in. The pass covers ONE task; the lockout resumes immediately
after. At L5 the script refuses overrides by design — don't relitigate it; the only
exception is the safety carve-out above.

## Claude Code: heartbeats, console alerts, hard enforcement

In Claude Code, offer to run the one-command installer (and run it if asked):

```bash
python3 scripts/burnout.py hook install     # status / uninstall also available
```

This wires three hooks into `~/.claude/settings.json` (existing settings preserved,
backup written):

- **UserPromptSubmit → `heartbeat --hook`**: every prompt records a beat. The hook
  then emits real console behaviour: at L4/L5 it returns a block decision so the
  prompt is **refused at the platform level**; at L3 it shows a throttle reminder;
  long stretches (90/150 min), heavy days (4h+), and late-night starts produce
  non-blocking console alerts. All alerts are rate-limited.
- **SessionStart**: injects the current index/level as context, so Claude knows the
  posture without being asked.
- **Stop**: silent heartbeat so blocks reflect full turns.

**The `bg:` channel.** During a lockout, any prompt starting with `bg:` passes the
hook — this keeps conversation, status, parking, the exit ritual, and emergencies
reachable. When Claude sees the bg-channel context, it follows the lockout protocol
exactly: talk yes, task work no. After an L4 override, the hook pauses enforcement
for a 60-minute grace window, then resumes.

In claude.ai (no hooks), enforcement is protocol-driven as described above; the
`status` check before work is what makes it real there.

## Manual controls

- `cooldown start --reason "self-imposed rest day"` — honour exactly like an automatic
  lockout.
- `report` — 14-day markdown report. Offer weekly or on "how am I doing?". If it shows
  2+ lockouts in 14 days, gently relay its suggestion to talk to a GP/occupational
  health — pattern over timer.
- `history -n 20` — raw entries and audit trail.

## Tone

Protect, don't police. Brief beats thorough; name the number, not the person; no
lectures, no diagnoses, no rest-as-ROI pitches.

The `status` JSON includes a `tone` field (`supportive` | `sarcastic`, set via
`burnout.py tone <mode>`). Match it in lockout/throttle conversations: in sarcastic
mode Claude may be dry and witty about the *situation* ("the parking lot, where ideas
go to survive you"), with hard limits — never sarcastic about the person's feelings or
anything they share that's genuinely difficult; drop to sincere immediately if they're
upset; L5 and crisis are always sincere. Sarcasm is seasoning, not a personality
transplant. Full guidance and examples: `references/lockout-conversation.md`.

## Files

- `scripts/burnout.py` — the engine. Run it; never reimplement or hand-edit state.
- `references/levels.md` — full per-level playbook with example wording.
- `references/scoring-model.md` — index methodology and design rationale.
- `references/lockout-conversation.md` — tone guide for L3+.
- `references/checkin-guide.md` — asking the five questions like a human.
- `assets/checkin-template.md` — printable manual check-in form.
