from datetime import date, datetime, time, timedelta


def calculate_streak(completed_dates: set[date], today: date | None = None) -> int:
    if not completed_dates:
        return 0
    cursor = today or date.today()
    if cursor not in completed_dates:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def in_quiet_hours(current: time, start: time, end: time) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


def within_dispatch_window(
    current: datetime,
    target: time,
    window_seconds: int,
) -> bool:
    target_at = datetime.combine(current.date(), target, tzinfo=current.tzinfo)
    elapsed = (current - target_at).total_seconds()
    return 0 <= elapsed < window_seconds
