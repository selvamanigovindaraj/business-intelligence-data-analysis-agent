from __future__ import annotations


def filter_output(text: str) -> str:
    """Strip PII and policy-violating content from *text* before returning to user."""
    raise NotImplementedError


def mask_pii(text: str) -> str:
    """Replace detected PII (email, phone, SSN) with placeholder tokens."""
    raise NotImplementedError
