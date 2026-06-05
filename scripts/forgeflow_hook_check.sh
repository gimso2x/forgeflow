#!/usr/bin/env bash
# forgeflow_hook_check.sh — Verify active hard rules and/or artifact guards
#
# Usage:
#   forgeflow_hook_check.sh --rule <rule-id> [--project <path>]
#   forgeflow_hook_check.sh --all [--project <path>]
#   forgeflow_hook_check.sh --guard-artifacts --task-dir <path> [--stage <stage>]
#
# Exit codes:
#   0 = PASS (all rules/guards satisfied)
#   2 = BLOCK (hard rule violated or artifact guard failed)
#
# Reads hard rules from:
#   ~/.forgeflow/evolution/rules/*.json (global)
#   <project>/.forgeflow/evolution/rules/*.json (project-local, if --project given)
#
# Artifact guard uses:
#   scripts/forgeflow_guard_check.py (stdlib-only, opt-in, no mutation)

set -euo pipefail

RULE_ID=""
CHECK_ALL=false
PROJECT_PATH=""
GUARD_ARTIFACTS=false
TASK_DIR=""
STAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rule)
      RULE_ID="$2"
      shift 2
      ;;
    --all)
      CHECK_ALL=true
      shift
      ;;
    --project)
      PROJECT_PATH="$2"
      shift 2
      ;;
    --guard-artifacts)
      GUARD_ARTIFACTS=true
      shift
      ;;
    --task-dir)
      TASK_DIR="$2"
      shift 2
      ;;
    --stage)
      STAGE="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# --- Artifact guard mode ---
if [[ "$GUARD_ARTIFACTS" == "true" ]]; then
  if [[ -z "$TASK_DIR" ]]; then
    echo "Usage: --guard-artifacts requires --task-dir <path>" >&2
    exit 2
  fi

  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  GUARD_CMD=(python3 "$SCRIPT_DIR/forgeflow_guard_check.py" check-task --task-dir "$TASK_DIR")
  if [[ -n "$STAGE" ]]; then
    GUARD_CMD+=(--stage "$STAGE")
  fi

  if ! "${GUARD_CMD[@]}"; then
    exit 2
  fi
fi

# If only artifact guard was requested (no --rule or --all), exit here
if [[ "$GUARD_ARTIFACTS" == "true" ]] && [[ -z "$RULE_ID" ]] && [[ "$CHECK_ALL" == "false" ]]; then
  exit 0
fi

if [[ -z "$RULE_ID" ]] && [[ "$CHECK_ALL" == "false" ]]; then
  echo "Usage: forgeflow_hook_check.sh --rule <rule-id> | --all [--project <path>] | --guard-artifacts --task-dir <path> [--stage <stage>]" >&2
  exit 2
fi

FORGEFLOW_HOME="${FORGEFLOW_HOME:-$HOME/.forgeflow}"
BLOCKED=false
BLOCK_MESSAGES=()

collect_rules() {
  local rules_dir="$FORGEFLOW_HOME/evolution/rules"
  if [[ -d "$rules_dir" ]]; then
    find "$rules_dir" -name '*.json' -type f 2>/dev/null
  fi
  if [[ -n "$PROJECT_PATH" ]]; then
    local project_rules="$PROJECT_PATH/.forgeflow/evolution/rules"
    if [[ -d "$project_rules" ]]; then
      find "$project_rules" -name '*.json' -type f 2>/dev/null
    fi
  fi
}

check_rule() {
  local rule_file="$1"
  local rule_id
  rule_id=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" < "$rule_file" 2>/dev/null || echo "")

  if [[ -z "$rule_id" ]]; then
    return 0
  fi

  if [[ "$CHECK_ALL" == "false" ]] && [[ "$rule_id" != "$RULE_ID" ]]; then
    return 0
  fi

  local enforcement_mode
  enforcement_mode=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('enforcement',{}).get('mode',''))" < "$rule_file" 2>/dev/null || echo "")

  # Only check hard rules
  if [[ "$enforcement_mode" != "hard_exit_2" ]]; then
    return 0
  fi

  local check_cmd
  check_cmd=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('check',{}).get('command',''))" < "$rule_file" 2>/dev/null || echo "")

  if [[ -z "$check_cmd" ]]; then
    return 0
  fi

  local expected_exit
  expected_exit=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('check',{}).get('expected_exit_code','0'))" < "$rule_file" 2>/dev/null || echo "0")

  local message
  message=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('enforcement',{}).get('message',''))" < "$rule_file" 2>/dev/null || echo "Hard rule violated: $rule_id")

  # Run the check command
  local exit_code=0
  eval "$check_cmd" >/dev/null 2>&1 || exit_code=$?

  if [[ "$exit_code" -ne "$expected_exit" ]]; then
    BLOCKED=true
    BLOCK_MESSAGES+=("[$rule_id] BLOCKED: $message")
  fi
}

# Process rules
while IFS= read -r rule_file; do
  [[ -z "$rule_file" ]] && continue
  check_rule "$rule_file"
done < <(collect_rules)

if [[ "$BLOCKED" == "true" ]]; then
  for msg in "${BLOCK_MESSAGES[@]}"; do
    echo "$msg" >&2
  done
  exit 2
fi

echo "PASS"
exit 0
