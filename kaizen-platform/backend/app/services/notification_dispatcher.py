from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.scheduling import in_quiet_hours, within_dispatch_window
from app.models import Goal, Habit, NotificationDelivery, NotificationPreference, Task
from app.notification_schemas import NotificationPayload
from app.services.notifications import send_to_user


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def preferences_for(
    db: AsyncSession,
    user_id: str,
    cache: dict[str, NotificationPreference],
) -> NotificationPreference:
    if user_id in cache:
        return cache[user_id]
    preferences = await db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    if not preferences:
        preferences = NotificationPreference(user_id=user_id)
        db.add(preferences)
        await db.flush()
    cache[user_id] = preferences
    return preferences


async def was_delivered(db: AsyncSession, dedupe_key: str) -> bool:
    return (
        await db.scalar(
            select(NotificationDelivery.id).where(
                NotificationDelivery.dedupe_key == dedupe_key
            )
        )
    ) is not None


async def deliver_once(
    db: AsyncSession,
    *,
    user_id: str,
    dedupe_key: str,
    payload: NotificationPayload,
) -> int:
    if await was_delivered(db, dedupe_key):
        return 0
    sent, _ = await send_to_user(db, user_id, payload)
    if sent:
        db.add(
            NotificationDelivery(
                user_id=user_id,
                dedupe_key=dedupe_key,
                notification_type=payload.notification_type,
                title=payload.title,
                body=payload.body,
                sent_devices=sent,
            )
        )
        await db.commit()
    return sent


async def dispatch_habit_reminders(
    db: AsyncSession,
    now: datetime,
    preferences_cache: dict[str, NotificationPreference],
) -> int:
    habits = list(
        (
            await db.scalars(
                select(Habit).where(
                    Habit.deleted_at.is_(None),
                    Habit.reminder_time.is_not(None),
                )
            )
        ).all()
    )
    sent = 0
    window = settings.notification_worker_interval_seconds + 15
    for habit in habits:
        preferences = await preferences_for(db, habit.user_id, preferences_cache)
        if not preferences.enabled or not preferences.habit_reminders:
            continue
        try:
            local_now = now.astimezone(ZoneInfo(preferences.timezone))
        except ZoneInfoNotFoundError:
            local_now = now.astimezone(ZoneInfo("America/Sao_Paulo"))
        if in_quiet_hours(
            local_now.timetz().replace(tzinfo=None),
            preferences.quiet_hours_start,
            preferences.quiet_hours_end,
        ):
            continue
        # O frontend usa domingo na posição zero; weekday() usa segunda na posição zero.
        day_index = (local_now.weekday() + 1) % 7
        scheduled_days = habit.scheduled_days or [True] * 7
        if day_index >= len(scheduled_days) or not scheduled_days[day_index]:
            continue
        if not within_dispatch_window(local_now, habit.reminder_time, window):
            continue
        local_date = local_now.date().isoformat()
        sent += await deliver_once(
            db,
            user_id=habit.user_id,
            dedupe_key=f"habit:{habit.id}:{local_date}:{habit.reminder_time.isoformat()}",
            payload=NotificationPayload(
                title=f"Hora de {habit.name}",
                body="Uma ação pequena agora mantém sua evolução em movimento.",
                url="/?page=habits",
                notification_type="habit_reminder",
                tag=f"habit-{habit.id}",
            ),
        )
    return sent


async def dispatch_task_reminders(
    db: AsyncSession,
    now: datetime,
    preferences_cache: dict[str, NotificationPreference],
) -> int:
    window = settings.notification_worker_interval_seconds + 15
    upper_due = now + timedelta(minutes=30, seconds=window)
    tasks = list(
        (
            await db.scalars(
                select(Task).where(
                    Task.deleted_at.is_(None),
                    Task.status != "done",
                    Task.due_at.is_not(None),
                    Task.due_at >= now,
                    Task.due_at <= upper_due,
                )
            )
        ).all()
    )
    sent = 0
    for task in tasks:
        preferences = await preferences_for(db, task.user_id, preferences_cache)
        if not preferences.enabled or not preferences.task_reminders:
            continue
        try:
            local_now = now.astimezone(ZoneInfo(preferences.timezone))
        except ZoneInfoNotFoundError:
            local_now = now.astimezone(ZoneInfo("America/Sao_Paulo"))
        if in_quiet_hours(
            local_now.timetz().replace(tzinfo=None),
            preferences.quiet_hours_start,
            preferences.quiet_hours_end,
        ):
            continue
        due_at = as_utc(task.due_at)
        target_at = due_at - timedelta(minutes=30)
        elapsed = (now - target_at).total_seconds()
        if not 0 <= elapsed < window:
            continue
        sent += await deliver_once(
            db,
            user_id=task.user_id,
            dedupe_key=f"task:{task.id}:{due_at.isoformat()}",
            payload=NotificationPayload(
                title="Tarefa em 30 minutos",
                body=task.title,
                url="/?page=tasks",
                notification_type="task_reminder",
                tag=f"task-{task.id}",
            ),
        )
    return sent


async def dispatch_goal_alerts(
    db: AsyncSession,
    now: datetime,
    preferences_cache: dict[str, NotificationPreference],
) -> int:
    window = settings.notification_worker_interval_seconds + 15
    goals = list(
        (
            await db.scalars(
                select(Goal).where(
                    Goal.deleted_at.is_(None),
                    Goal.progress < 100,
                    Goal.deadline.is_not(None),
                    Goal.deadline >= (now.date() - timedelta(days=1)),
                    Goal.deadline <= (now.date() + timedelta(days=1)),
                )
            )
        ).all()
    )
    sent = 0
    for goal in goals:
        preferences = await preferences_for(db, goal.user_id, preferences_cache)
        if not preferences.enabled or not preferences.goal_alerts:
            continue
        try:
            local_now = now.astimezone(ZoneInfo(preferences.timezone))
        except ZoneInfoNotFoundError:
            local_now = now.astimezone(ZoneInfo("America/Sao_Paulo"))
        if local_now.date() != goal.deadline:
            continue
        if not within_dispatch_window(local_now, time(9, 0), window):
            continue
        sent += await deliver_once(
            db,
            user_id=goal.user_id,
            dedupe_key=f"goal:{goal.id}:{goal.deadline.isoformat()}",
            payload=NotificationPayload(
                title="Meta com prazo hoje",
                body=goal.text,
                url="/?page=goals",
                notification_type="goal_alert",
                tag=f"goal-{goal.id}",
            ),
        )
    return sent


async def dispatch_due_notifications(db: AsyncSession, now: datetime | None = None) -> int:
    current = as_utc(now or datetime.now(UTC))
    preferences_cache: dict[str, NotificationPreference] = {}
    sent = await dispatch_habit_reminders(db, current, preferences_cache)
    sent += await dispatch_task_reminders(db, current, preferences_cache)
    sent += await dispatch_goal_alerts(db, current, preferences_cache)
    await db.commit()
    return sent
