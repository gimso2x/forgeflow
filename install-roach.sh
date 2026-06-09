#!/usr/bin/env bash
# ForgeFlow installer for Roach Code
# Usage: bash <(curl -sL https://raw.githubusercontent.com/gimso2x/forgeflow/main/install-roach.sh)
#
# Or: bash install-roach.sh          # from a forgeflow clone
#     bash install-roach.sh --update  # force update existing install

set -euo pipefail

REPO="https://github.com/gimso2x/forgeflow.git"
FORGEFLOW_DIR="${FORGEFLOW_DIR:-$HOME/.forgeflow/repo}"
SKILL_TARGET="${SKILL_TARGET:-$HOME/.roach-code/skills/forgeflow}"
CONFIG_FILE=""

# --- Detect OS and config path ---
detect_config() {
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$(uname -s)" == *"MINGW"* || "$(uname -s)" == *"CYGWIN"* ]]; then
    # Windows (Git Bash / MSYS2)
    local win_home
    win_home="$(cd "$USERPROFILE" 2>/dev/null && pwd)" || win_home="$HOME"
    CONFIG_FILE="${win_home}/roach-code.toml"
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    CONFIG_FILE="$HOME/.config/roach-code/config.toml"
    # fallback
    if [[ ! -f "$CONFIG_FILE" ]]; then
      CONFIG_FILE="$HOME/roach-code.toml"
    fi
  else
    CONFIG_FILE="$HOME/.config/roach-code/config.toml"
    if [[ ! -f "$CONFIG_FILE" ]]; then
      CONFIG_FILE="$HOME/roach-code.toml"
    fi
  fi
  # Check workspace-local config too
  if [[ -f "./roach-code.toml" ]]; then
    CONFIG_FILE="./roach-code.toml"
  fi
}

# --- Clone or update repo ---
clone_or_update() {
  if [[ -d "$FORGEFLOW_DIR/.git" ]]; then
    echo " Updating forgeflow repo..."
    git -C "$FORGEFLOW_DIR" pull --ff-only || {
      echo "ERROR: git pull failed. Remove $FORGEFLOW_DIR and retry."
      exit 1
    }
  else
    echo " Cloning forgeflow repo..."
    mkdir -p "$(dirname "$FORGEFLOW_DIR")"
    git clone --depth 1 "$REPO" "$FORGEFLOW_DIR"
  fi
}

# --- Copy files ---
install_skills() {
  echo " Installing to $SKILL_TARGET..."
  mkdir -p "$SKILL_TARGET"

  # Copy skill directories
  for dir in skills/*/; do
    local name
    name="$(basename "$dir")"
    mkdir -p "$SKILL_TARGET/$name"
    cp -r "$dir"* "$SKILL_TARGET/$name/" 2>/dev/null || true
  done

  # Copy skill root files
  cp skills/SKILLS.md "$SKILL_TARGET/" 2>/dev/null || true
  cp skills/_template.md "$SKILL_TARGET/" 2>/dev/null || true

  # Copy templates, scripts, docs
  mkdir -p "$SKILL_TARGET/templates"
  cp -r templates/* "$SKILL_TARGET/templates/" 2>/dev/null || true

  mkdir -p "$SKILL_TARGET/scripts"
  cp -r scripts/* "$SKILL_TARGET/scripts/" 2>/dev/null || true

  mkdir -p "$SKILL_TARGET/docs"
  cp -r docs/* "$SKILL_TARGET/docs/" 2>/dev/null || true

  echo " Skills, templates, scripts, docs copied."
}

# --- Update roach-code.toml ---
update_config() {
  if [[ -z "$CONFIG_FILE" || ! -f "$CONFIG_FILE" ]]; then
    echo ""
    echo " No roach-code.toml found. Add this to your config manually:"
    echo ""
    echo '   [skills]'
    echo "   paths = [\"$(echo "$SKILL_TARGET" | sed "s|$HOME|~|")\"]"
    echo ""
    return
  fi

  # Normalize path for toml (use forward slashes, $HOME → ~)
  local pretty_path
  pretty_path="$(echo "$SKILL_TARGET" | sed "s|$HOME|~|")"

  if grep -q '\[skills\]' "$CONFIG_FILE"; then
    if grep -q 'paths.*=' "$CONFIG_FILE"; then
      # paths already exists — check if forgeflow is there
      if grep -q 'forgeflow' "$CONFIG_FILE"; then
        echo " roach-code.toml already has forgeflow skill path."
      else
        echo " WARNING: [skills] paths exists but doesn't include forgeflow."
        echo "   Add this path: $pretty_path"
      fi
    else
      # [skills] exists but no paths — add it
      # Use a portable approach
      local tmp
      tmp="$(mktemp)"
      awk -v path="$pretty_path" '
        /^\[skills\]/ { print; print "paths = [" path "]"; next }
        { print }
      ' "$CONFIG_FILE" > "$tmp" && mv "$tmp" "$CONFIG_FILE"
      echo " Added paths to [skills] in $CONFIG_FILE"
    fi
  else
    # No [skills] section — append
    echo "" >> "$CONFIG_FILE"
    echo "[skills]" >> "$CONFIG_FILE"
    echo "paths = [\"$pretty_path\"]" >> "$CONFIG_FILE"
    echo " Added [skills] section to $CONFIG_FILE"
  fi
}

# --- Main ---
main() {
  echo ""
  echo " ForgeFlow installer for Roach Code"
  echo " ==================================="
  echo ""

  # If running from inside a forgeflow clone, use local files
  if [[ -f "skills/forgeflow/SKILL.md" && -f "VERSION" ]]; then
    echo " Detected local forgeflow clone."
    FORGEFLOW_DIR="$(pwd)"
    cd "$FORGEFLOW_DIR"
  else
    detect_config
    clone_or_update
    cd "$FORGEFLOW_DIR"
  fi

  install_skills
  detect_config
  update_config

  # --- Post-install smoke test ---
  echo ""
  echo " Running post-install smoke test..."
  local smoke_pass=true

  # Check core skill files exist
  for f in \
    "$SKILL_TARGET/forgeflow/SKILL.md" \
    "$SKILL_TARGET/clarify/SKILL.md" \
    "$SKILL_TARGET/templates/brief.md" \
    "$SKILL_TARGET/templates/run-state.json"; do
    if [[ ! -f "$f" ]]; then
      echo "  WARNING: Missing file: $f"
      smoke_pass=false
    fi
  done

  # Check scripts are present
  if [[ -f "$SKILL_TARGET/scripts/forgeflow_storage.py" ]]; then
    if python3 "$SKILL_TARGET/scripts/forgeflow_storage.py" --help >/dev/null 2>&1; then
      echo "  forgeflow_storage.py: OK"
    else
      echo "  WARNING: forgeflow_storage.py failed --help check"
      smoke_pass=false
    fi
  fi

  if $smoke_pass; then
    echo "  Smoke test: PASS"
  else
    echo "  Smoke test: WARNINGS (see above). Installation may be incomplete."
  fi

  echo ""
  echo " Done!"
  echo ""
  echo " Usage:"
  echo "   /forgeflow:ff-loop \"your task description\""
  echo "   /forgeflow:clarify \"your task\""
  echo ""
  echo " Update:"
  echo "   bash $FORGEFLOW_DIR/install-roach.sh --update"
  echo ""
}

main "$@"
