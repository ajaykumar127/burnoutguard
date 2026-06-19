# Burnout Guard on Pi

An alternate install path for the [Pi coding agent](https://github.com/earendil-works)
(`pi`). **Additive and non-destructive** — nothing here changes how Burnout Guard
behaves under Claude Code. The scoring engine (`scripts/burnout.py`) is shared and
unmodified in spirit; the only engine change is an optional second beat source
(Pi session transcripts) that is completely inert unless a Pi sessions directory exists.

The port mirrors the three layers of the Claude Code integration:

| Tier | What it gives you | What it is |
|---|---|---|
| **0 — CLI** | The full engine, by hand | `python3 scripts/burnout.py …` — works on any platform, zero install |
| **1 — Skill** | Protocol enforcement (claude.ai-equivalent) | A Pi skill that makes the agent run `status` and obey the verdict |
| **2 — Extension** | Real platform enforcement | A Pi TypeScript extension: heartbeats, console alerts, and tool-blocking lockouts |

## Quick start

```bash
git clone https://github.com/ajaykumar127/burnoutguard /tmp/burnout-guard
cd /tmp/burnout-guard
./integrations/pi/install.sh
```

Then enable it in Pi:

- If Pi is already running: type `/reload`
- If Pi is not running: start Pi normally

Pi users do **not** run `burnout.py hook install`; that hook installer is for Claude
Code only. The Pi installer installs a Pi extension instead.

`install.sh` installs globally into Pi's auto-discovery paths:

- skill: `~/.pi/agent/skills/burnout-guard/SKILL.md`
- extension: `~/.pi/agent/extensions/burnout-guard.ts`

Pi loads global extensions automatically. `/reload` enables the newly installed
extension in an already-running session; a new Pi session loads it at startup.
`install.sh` renders the absolute path of the checkout you ran it from, so if you
remove a temporary `/tmp/burnout-guard` checkout later, reinstall from the new
checkout location.

Uninstall (state preserved): `./integrations/pi/install.sh uninstall` + `/reload`.

## How each tier maps from Claude Code to Pi

### Tier 0 — engine (unchanged)
Pure Python 3.10+ stdlib, state in `~/.burnout-guard/state.json`. Every command runs
from a Pi `bash` call exactly as documented in the root README.

### Tier 1 — skill (`integrations/pi/skill/SKILL.md`)
Same `SKILL.md` frontmatter convention Pi uses. The contract is identical: run
`burnout.py status` before task work, obey exit codes `0/5/10`, follow the level
protocol. This is deterministic-by-protocol enforcement and works even with the
extension disabled. `install.sh` renders the absolute engine/repo paths into the
installed copy.

### Tier 2 — extension (`integrations/pi/extension/burnout-guard.ts`)
Pi has no "refuse the prompt before the model sees it" hook (Claude Code's
`UserPromptSubmit` block). Pi's equivalent teeth are **tool-call blocking**, so the
extension translates the engine's `block` verdict into "block mutating tools
(`bash`/`write`/`edit`) at L4/L5." It is a faithful relay — it invents no thresholds:

| Claude Code hook | Pi event | Behaviour |
|---|---|---|
| `SessionStart` | `session_start` | run `status`, surface level as context |
| `UserPromptSubmit` (beat + alerts + block) | `before_agent_start` | run `heartbeat --hook`, record beat, surface alerts, inject posture |
| platform prompt-block at L4/L5 | `tool_call` → `{ block: true }` | block mutating tools while locked |
| `bg:` passthrough | (engine-driven) | engine returns context not a block, so tools stay open |

**Beats:** the engine reads Pi sessions at `~/.pi/agent/sessions/**/*.jsonl`
(`PI_SESSIONS_PATH` to override), filtering out auto-injected skill/template messages so
only genuine human prompts count. This gives cross-project visibility and retroactive
backfill, mirroring the Claude `~/.claude/projects` reader.

## Safety & escape hatches (unchanged in spirit)

- **Fail-open:** if the engine is missing or errors, the extension blocks nothing and
  crashes no turn. A wellbeing tool must never wall you out on a bug.
- **`bg:` channel:** start any prompt with `bg:` during a lockout to keep conversation,
  status, parking, and the exit ritual reachable.
- **Disable ≠ reset:** removing/disabling the extension pauses enforcement but preserves
  your burnout state in `~/.burnout-guard/state.json`. Re-enabling resumes the verdict.
- **Honest exits only:** uninstall, delete the state file, or use the logged L4 override.

## Configuration (env)

| Variable | Default | Purpose |
|---|---|---|
| `BURNOUT_GUARD_ENGINE` | rendered by installer | absolute path to `scripts/burnout.py` |
| `BURNOUT_GUARD_PYTHON` | `python3` | python interpreter |
| `BURNOUT_GUARD_BLOCK_TOOLS` | `bash,write,edit` | tools blocked during lockout |
| `PI_SESSIONS_PATH` | `~/.pi/agent/sessions` | Pi session transcript root (beat source) |
| `BURNOUT_GUARD_HOME` | `~/.burnout-guard` | engine state directory |
