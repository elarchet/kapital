"""Built-in institution parser profiles.

An :class:`InstitutionProfile` bundles everything the ingestion pipeline needs
to interpret a given institution's export: the display name, the country, the
default account label, and the canonical column/type mappings.

Import templates reference a profile by ``institution_key`` (e.g.
``"trading212"``). Because every row in an uploaded file is assumed to come
from the same institution, the profile is resolved once per import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.services.institutions.trading212 import TRADING212_PROFILE_DATA


@dataclass(frozen=True)
class InstitutionProfile:
    """A built-in parser profile for a single institution."""

    key: str
    name: str
    default_account_name: str
    country: str | None = None
    mappings: dict[str, Any] = field(default_factory=dict)


TRADING212_PROFILE = InstitutionProfile(**TRADING212_PROFILE_DATA)

# Registry of built-in profiles keyed by ``institution_key``.
INSTITUTION_PROFILES: dict[str, InstitutionProfile] = {
    TRADING212_PROFILE.key: TRADING212_PROFILE,
}


def get_profile(institution_key: str | None) -> InstitutionProfile | None:
    """Return the built-in profile for *institution_key*, or ``None``."""
    if not institution_key:
        return None
    return INSTITUTION_PROFILES.get(institution_key)


__all__ = [
    "INSTITUTION_PROFILES",
    "TRADING212_PROFILE",
    "InstitutionProfile",
    "get_profile",
]
