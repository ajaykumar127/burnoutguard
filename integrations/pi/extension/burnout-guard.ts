/**
 * Burnout Guard — Pi extension (Tier 2: real enforcement)
 *
 * A FAITHFUL RELAY, not a second brain. It invents no thresholds, no scoring, and no
 * verdicts. All judgement lives in the engine (scripts/burnout.py); this extension only
 * translates the engine's output into Pi platform behaviour:
 *
 *   - session_start        -> run `status`, inject current level as context, notify.
 *   - before_agent_start   -> run `heartbeat --hook` (records a beat, returns alerts /
 *                             block decision / bg-channel context), cache the turn's
 *                             verdict, surface alerts, inject posture into the prompt.
 *   - tool_call            -> when the engine returned a `block` decision (L4/L5), block
 *                             mutating tools. The engine path itself is always allowed
 *                             so status / override / cooldown / parking stay reachable.
 *
 * Safety valves are the ones the engine already designed: the `bg:` passthrough channel
 * (engine returns context, not a block, so tools are NOT blocked) and the honest escape
 * hatches (disable this extension, delete state, or a logged L4 override). Disabling the
 * extension pauses enforcement but never resets state (~/.burnout-guard/state.json).
 *
 * FAIL-OPEN INVARIANT: if the engine is missing or errors, this extension must NEVER
 * block a tool and NEVER crash a turn. A wellbeing tool that locks you out of your own
 * machine on a bug is worse than useless.
 *
 * Install: integrations/pi/install.sh (renders {{BURNOUT_ENGINE}} below), or set
 * BURNOUT_GUARD_ENGINE to the absolute path of scripts/burnout.py.
 */

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// ---- configuration (env overrides win; install.sh renders the default) ----------------
const ENGINE =
	process.env.BURNOUT_GUARD_ENGINE ||
	"{{BURNOUT_ENGINE}}".replace(/^~/, homedir());

const PYTHON = process.env.BURNOUT_GUARD_PYTHON || "python3";

// Tools the engine's lockout should physically prevent. Reading/searching stay allowed.
const BLOCK_TOOLS = new Set(
	(process.env.BURNOUT_GUARD_BLOCK_TOOLS || "bash,write,edit")
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean),
);

interface EngineOut {
	decision?: string;
	reason?: string;
	systemMessage?: string;
	hookSpecificOutput?: { additionalContext?: string };
}

export default function (pi: ExtensionAPI) {
	const engineOk = existsSync(ENGINE);
	let warned = false;

	// Per-turn verdict cache, read by tool_call. Conservative defaults = never block.
	let turn = { locked: false, reason: "" };

	function warnOnce(ctx: any) {
		if (warned || !ctx?.hasUI) return;
		warned = true;
		ctx.ui.notify(
			`🧯 Burnout Guard: engine not found at ${ENGINE} — enforcement disabled (fail-open). ` +
				`Set BURNOUT_GUARD_ENGINE or run integrations/pi/install.sh.`,
			"warning",
		);
	}

	/** Run the engine; return parsed JSON or null. Never throws. */
	function runEngine(args: string[], stdin?: string): EngineOut | null {
		if (!engineOk) return null;
		try {
			const res = spawnSync(PYTHON, [ENGINE, ...args], {
				input: stdin ?? "",
				encoding: "utf8",
				timeout: 8000,
			});
			if (res.error || typeof res.stdout !== "string") return null;
			const text = res.stdout.trim();
			if (!text) return {};
			try {
				return JSON.parse(text) as EngineOut;
			} catch {
				return {};
			}
		} catch {
			return null;
		}
	}

	// --- session start: surface the current posture as context ---------------------------
	pi.on("session_start", async (_event, ctx) => {
		if (!engineOk) {
			warnOnce(ctx);
			return;
		}
		// `heartbeat --event session-start` returns hookSpecificOutput.additionalContext.
		const out = runEngine(["heartbeat", "--hook", "--event", "session-start"], "{}");
		const cxt = out?.hookSpecificOutput?.additionalContext;
		if (cxt && ctx.hasUI) {
			// One-line console breadcrumb; full context is injected on the first turn.
			ctx.ui.notify(`🧯 ${cxt.replace(/\s+/g, " ").slice(0, 140)}`, "info");
		}
	});

	// --- every prompt: beat + alerts + block decision + posture injection -----------------
	pi.on("before_agent_start", async (event, ctx) => {
		// Reset the turn verdict first so a failed engine call leaves us unlocked.
		turn = { locked: false, reason: "" };
		if (!engineOk) {
			warnOnce(ctx);
			return;
		}

		const prompt = typeof event.prompt === "string" ? event.prompt : "";
		const out = runEngine(["heartbeat", "--hook"], JSON.stringify({ prompt }));
		if (!out) return; // engine hiccup -> stay open

		// Console alert (long stretch / heavy day / late night / throttle reminder).
		if (out.systemMessage && ctx.hasUI) {
			ctx.ui.notify(out.systemMessage, "warning");
		}

		// Lockout: the engine says block. (bg: prompts never reach here as a block —
		// the engine returns additionalContext instead, so tools stay unblocked.)
		const pieces: string[] = [];
		if (out.decision === "block") {
			turn = {
				locked: true,
				reason: out.reason || "Burnout Guard lockout is active.",
			};
			pieces.push(
				`## 🧯 Burnout Guard — LOCKOUT ACTIVE\n\n${turn.reason}\n\n` +
					`Follow the lockout protocol exactly: conversation, status, parking, and the ` +
					`exit ritual are allowed; task work is not. Mutating tools (${[...BLOCK_TOOLS].join(
						", ",
					)}) are blocked at the platform level — the engine CLI itself stays runnable for ` +
					`status / override / cooldown / parked. A medical emergency, safety issue, or acute ` +
					`distress dissolves all lockout framing instantly: help the person.`,
			);
		}

		// bg-channel or session context the engine wants the agent to see.
		const cxt = out.hookSpecificOutput?.additionalContext;
		if (cxt) pieces.push(`## 🧯 Burnout Guard\n\n${cxt}`);

		if (pieces.length === 0) return;
		return {
			message: {
				customType: "burnout-guard",
				content: pieces.join("\n\n"),
				display: false,
			},
			systemPrompt: `${event.systemPrompt}\n\n${pieces.join("\n\n")}`,
		};
	});

	// --- enforcement: block mutating tools while locked -----------------------------------
	pi.on("tool_call", async (event, ctx) => {
		if (!turn.locked) return undefined;
		if (!BLOCK_TOOLS.has(event.toolName)) return undefined;

		// Always let the engine itself run — exit ritual, status, override, parking.
		if (event.toolName === "bash") {
			const cmd = String((event.input as any)?.command ?? "");
			if (cmd.includes("burnout.py") || (ENGINE && cmd.includes(ENGINE))) {
				return undefined;
			}
		}

		if (ctx.hasUI) {
			ctx.ui.notify(`🧯 Lockout: ${event.toolName} blocked. Start a message with "bg:" to talk.`, "warning");
		}
		return {
			block: true,
			reason:
				`Burnout Guard lockout active — ${turn.reason} ` +
				`Task tools are disabled. Conversation, status, parking, and the exit ritual remain ` +
				`open; prefix a message with "bg:" to reach the person-channel during lockout.`,
		};
	});
}
