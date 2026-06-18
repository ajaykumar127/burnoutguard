#!/usr/bin/env bash
# Burnout Guard — Pi installer.
#
# Installs the Pi skill + extension globally for the Pi coding agent, baking this repo's
# absolute engine path into the rendered copies. Idempotent. Does NOT touch Claude Code.
#
#   ./integrations/pi/install.sh            # install (global)
#   ./integrations/pi/install.sh uninstall  # remove the installed skill + extension
#
# Engine state lives in ~/.burnout-guard/state.json and is never created or deleted here.

set -euo pipefail

ACTION="${1:-install}"

# Resolve repo root from this script's location (integrations/pi/install.sh -> repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENGINE="$REPO/scripts/burnout.py"

PI_HOME="${PI_HOME:-$HOME/.pi/agent}"
SKILL_DST_DIR="$PI_HOME/skills/burnout-guard"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"
EXT_DST_DIR="$PI_HOME/extensions"
EXT_DST="$EXT_DST_DIR/burnout-guard.ts"

SKILL_SRC="$SCRIPT_DIR/skill/SKILL.md"
EXT_SRC="$SCRIPT_DIR/extension/burnout-guard.ts"

render() { # src dst
	sed "s|{{BURNOUT_ENGINE}}|$ENGINE|g; s|{{BURNOUT_REPO}}|$REPO|g" "$1" > "$2"
}

if [ "$ACTION" = "uninstall" ]; then
	rm -f "$SKILL_DST" "$EXT_DST"
	rmdir "$SKILL_DST_DIR" 2>/dev/null || true
	echo "🧯 Removed Pi skill + extension. State in ~/.burnout-guard/ is untouched."
	echo "   Run /reload in Pi to drop the extension from the running session."
	exit 0
fi

# --- preflight -------------------------------------------------------------------------
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found (need 3.10+)."; exit 1; }
[ -f "$ENGINE" ] || { echo "ERROR: engine not found at $ENGINE"; exit 1; }
python3 -m py_compile "$ENGINE" || { echo "ERROR: engine failed to compile."; exit 1; }

# --- install ---------------------------------------------------------------------------
mkdir -p "$SKILL_DST_DIR" "$EXT_DST_DIR"
render "$SKILL_SRC" "$SKILL_DST"
render "$EXT_SRC" "$EXT_DST"

echo "🧯 Burnout Guard (Pi) installed."
echo "   repo:      $REPO"
echo "   engine:    $ENGINE"
echo "   skill:     $SKILL_DST"
echo "   extension: $EXT_DST"
echo
echo "Next:"
echo "  1. In a running Pi session, run /reload to load the extension."
echo "  2. (Optional) verify the engine:  python3 \"$ENGINE\" status"
echo "  3. Disable anytime by removing $EXT_DST + /reload — state is preserved."
