"""Private helper functions for the calculations package.

Extracted from the legacy calculations.py god module as part of the
SOLID decomposition (Spec 3). These helpers are intentionally private
(not in __all__) and imported only within the package.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _ensure_aware(dt: datetime) -> datetime:
    """Convert naive datetime to aware (UTC) if needed."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
