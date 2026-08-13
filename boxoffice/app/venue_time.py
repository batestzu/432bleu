"""Venue-local time handling.

Event datetimes are stored NAIVE, in venue-local time. That is the convention
manage.py writes with (`set-date 6 "2026-08-13 19:00"` means 7PM at the venue)
and the convention gate.py's ticket-expiry math reads back. Nothing here changes
that — the storage format is fine. What was broken is the *serialization*: a
naive ISO string handed to a browser is resolved in the viewer's own timezone,
so a fan in Los Angeles was told a 7PM-Eastern show started at 7PM Pacific.

Serializing through venue_iso() pins the instant while leaving the DB alone.
"""
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

VENUE_TZ = ZoneInfo(os.getenv("VENUE_TZ", "America/New_York"))


def venue_iso(dt: Optional[datetime]) -> Optional[str]:
    """Serialize a naive venue-local datetime as an offset-carrying ISO string.

    "2026-08-13T19:00:00" -> "2026-08-13T19:00:00-04:00"

    The offset is resolved per-date, so it follows DST correctly: a January show
    serializes at -05:00, an August show at -04:00.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=VENUE_TZ)
    return dt.isoformat()
