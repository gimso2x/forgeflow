from __future__ import annotations


class RuntimeViolation(Exception):
    """Raised when a requested stage transition violates runtime policy."""

