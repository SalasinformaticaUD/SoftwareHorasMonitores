from __future__ import annotations

import re
import unicodedata
from datetime import datetime, time, timedelta

from django.utils import timezone


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    compact = re.sub(r"\s+", " ", without_marks).strip().lower()
    return compact


def localize_datetime(value: datetime) -> datetime:
    if timezone.is_aware(value):
        return value
    return timezone.make_aware(value, timezone.get_current_timezone())


def combine_day_and_time(day, hour: time) -> datetime:
    return localize_datetime(datetime.combine(day, hour))


def overlap_in_minutes(start_a: time, end_a: time, start_b: time, end_b: time) -> int:
    start = max(start_a, start_b)
    end = min(end_a, end_b)
    if end <= start:
        return 0
    return int(duration_in_minutes(end) - duration_in_minutes(start))


def duration_in_minutes(worked_time: time) -> int:
    return int(worked_time.hour * 60 + worked_time.minute)


def duration_between_times(start: time, end: time) -> int:
    if end <= start:
        return 0
    start_delta = timedelta(hours=start.hour, minutes=start.minute, seconds=start.second)
    end_delta = timedelta(hours=end.hour, minutes=end.minute, seconds=end.second)
    return int((end_delta - start_delta).total_seconds() // 60)


def _next_hour(hour: int) -> int:
    return min(hour + 1, 23)


def normalize_session_start(value: time) -> time:
    seconds_into_hour = value.minute * 60 + value.second
    if seconds_into_hour <= 5 * 60:
        return time(hour=value.hour, minute=0)
    if seconds_into_hour < 45 * 60:
        return time(hour=value.hour, minute=30)
    return time(hour=_next_hour(value.hour), minute=0)


def normalize_session_end(value: time) -> time:
    seconds_into_hour = value.minute * 60 + value.second
    if seconds_into_hour < 15 * 60:
        return time(hour=value.hour, minute=0)
    if seconds_into_hour < 45 * 60:
        return time(hour=value.hour, minute=30)
    return time(hour=_next_hour(value.hour), minute=0)


def late_minutes(actual_start: time, scheduled_start: time, tolerance_minutes: int = 5) -> int:
    delta = duration_in_minutes(actual_start) - duration_in_minutes(scheduled_start) - tolerance_minutes
    if int(delta) <= tolerance_minutes:
        return 0
    return int(delta)
