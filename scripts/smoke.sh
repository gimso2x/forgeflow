#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail() {
  cat >&2 <<EOF
CLAUDE PLUGIN POST-INSTALL SMOKE: FAIL
- $1
- Next checks: reinstall/restart Claude Code, then rerun scripts/smoke.sh.
- Useful commands:
  claude plugin marketplace update forgeflow
  claude plugin update forgeflow@forgeflow
  claude plugin list
EOF
  exit 1
}

pass_step() {
  printf 'PASS: %s\n' "$1"
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing required generated/plugin file: $path"
  pass_step "$path"
}

require_text() {
  local path="$1"
  local needle="$2"
  grep -Fq "$needle" "$path" || fail "missing expected text in $path: $needle"
  pass_step "$path contains $needle"
}

require_file ".claude-plugin/plugin.json"
require_file "adapters/generated/claude/CLAUDE.md"
require_file "skills/init/SKILL.md"
require_file "skills/clarify/SKILL.md"
# Valid labels: small, medium, high. Keep this phrase grep-visible for post-install contract tests.
require_text "prompts/canonical/coordinator.md" "ForgeFlow route labels are exactly \`small\`, \`medium\`, and \`high\`"
require_text "skills/init/SKILL.md" "/forgeflow:init"
require_text "skills/clarify/SKILL.md" "/forgeflow:clarify"

if ! command -v claude >/dev/null 2>&1; then
  fail "claude CLI not found; install/login to Claude Code before running this post-install smoke"
fi

if ! claude plugin validate "$ROOT" >/tmp/forgeflow-claude-plugin-validate.log 2>&1; then
  cat /tmp/forgeflow-claude-plugin-validate.log >&2 || true
  fail "claude plugin validate failed for this checkout"
fi
pass_step "claude plugin validate"

# scripts/smoke_claude_plugin.py covers /forgeflow:clarify route dry-run plus /forgeflow:init fixture writes.
if ! "${PYTHON:-python3}" scripts/smoke_claude_plugin.py "$@"; then
  fail "scripts/smoke_claude_plugin.py failed; check Claude Code login/quota/plugin cache, then reinstall/restart"
fi

cat <<'EOF'
CLAUDE PLUGIN POST-INSTALL SMOKE: PASS
- generated files are present
- route vocabulary is canonical
- claude plugin validate passed
- /forgeflow:clarify and /forgeflow:init smoke passed in a disposable temp fixture
EOF
