#!/usr/bin/env bash
set -euo pipefail
exec "${PYTHON:-python3}" "$(dirname "$0")/validate_markdown_links.py"
