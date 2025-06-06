"""Date utilities."""
from datetime import timezone
from dateutil.parser import parse as parse_date

def to_aware_utc(dt):
    if dt is None:
        return None
    parsed = parse_date(dt) if isinstance(dt, str) else dt
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)