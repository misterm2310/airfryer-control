"""Kleine Helfer."""

from __future__ import annotations

from typing import Any

from ..const import REDACT_KEYS

REDACTED = "**geschwärzt**"


def redact(data: Any) -> Any:
    """Konto- und Gerätekennungen schwärzen (für Anzeige und Diagnose)."""
    if isinstance(data, dict):
        return {
            key: (REDACTED if key in REDACT_KEYS and value not in (None, "") else redact(value))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact(item) for item in data]
    return data
