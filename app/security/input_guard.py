from __future__ import annotations


class InputGuardError(ValueError):
    """Raised when a user message fails safety checks."""


def validate_input(text: str) -> str:
    """Sanitise and validate *text*; raise InputGuardError if unsafe."""
    raise NotImplementedError


def detect_prompt_injection(text: str) -> bool:
    """Return True if *text* looks like a prompt injection attempt."""
    raise NotImplementedError
