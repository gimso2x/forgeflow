from __future__ import annotations

import os


def get_active_adapter() -> str:
    """Detect the active AI adapter based on environment variables."""
    if os.environ.get("GEMINI_CLI") == "1":
        return "gemini"
    if os.environ.get("CLAUDE_CODE") == "1":
        return "claude"
    # Default fallback
    return "gemini"


def get_adapter_config() -> dict[str, str]:
    """Return naming conventions for the active adapter."""
    adapter = get_active_adapter()
    if adapter == "gemini":
        return {
            "adapter": "gemini",
            "dot_dir": ".gemini",
            "metadata_file": "GEMINI.md",
            "name": "Gemini CLI",
        }
    else:
        return {
            "adapter": "claude",
            "dot_dir": ".claude",
            "metadata_file": "CLAUDE.md",
            "name": "Claude Code",
        }
