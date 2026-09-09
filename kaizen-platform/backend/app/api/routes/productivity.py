from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, Database
from app.core.scheduling import calculate_streak
from app.models import FocusProject, Goal, Habit, HabitCompletion, Task
from app.productivity_schemas import (
    FocusCreate,
    FocusOut,
    FocusUpdate,
    GoalCreate,
    GoalOut,
    GoalUpdate,
    HabitCreate,
    HabitOut,
    HabitUpdate,
    SyncResponse,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)


router = APIRouter(tags=["produtividade"])
ModelT = TypeVar("ModelT", FocusProject, Habit, Goal, Task)


def utcnow() -> datetime:
    return datetime.now(UTC)


def check_version(entity: Any, expected_version: int | None) -> None:
    if expected_version is not None and entity.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Este item foi alterado em outro dispositivo.",
                "current_version": entity.version,
            },
        )


async def owned_entity(
    db: Database,
    model: type[ModelT],
    entity_id: str,
    user_id: str,
    *,
    include_deleted: bool = False,
) -> ModelT:
    conditions = [model.id == entity_id, model.user_id == user_id]
    if not include_deleted:
        conditions.append(model.deleted_at.is_(None))
    entity = await db.scalar(select(model).where(*conditions))
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")
    return entity


async def existing_client_entity(
    db: Database,
    model: type[ModelT],
    entity_id: str | None,
    user_id: str,
) -> ModelT | None:
    """Torna POSTs com ID do cliente seguros para repetição pela fila offline."""
    if not entity_id:
        return None
    entity = await db.get(model, entity_id)
    if not entity:
        return None
    if entity.user_id == user_id and entity.deleted_at is None:
        return entity
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Este identificador já foi utilizado.",
    )


async def deactivate_other_focuses(db: Database, user_id: str, keep_id: str) -> None:
    await db.execute(
        update(FocusProject)
        .where(
            FocusProject.user_id == user_id,
            FocusProject.id != keep_id,
            FocusProject.is_active.is_(True),
            FocusProject.deleted_at.is_(None),
        )
        .values(is_active=False, version=FocusProject.version + 1, updated_at=utcnow())
    )


def apply_update(entity: Any, payload: Any) -> None:
    data = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    nullable_fields = {
        Habit: {"reminder_time"},
        Goal: {"deadline"},
        Task: {"due_at", "estimated_minutes"},
        FocusProject: set(),
    }
    allowed_nulls = nullable_fields.get(type(entity), set())
    for key, value in data.items():
        if value is None and key not in allowed_nulls:
            continue
        setattr(entity, key, value)
    entity.version += 1
    entity.updated_at = utcnow()


async def habit_outputs(db: Database, habits: list[Habit]) -> list[HabitOut]:
    if not habits:
        return []
    habit_ids = [habit.id for habit in habits]
    completions = (
        await db.scalars(
            select(HabitCompletion)
            .where(HabitCompletion.habit_id.in_(habit_ids))
            .order_by(HabitCompletion.completed_on)
        )
    ).all()
    by_habit: dict[str, list[date]] = defaultdict(list)
    for completion in completions:
        by_habit[completion.habit_id].append(completion.completed_on)
    outputs: list[HabitOut] = []
    for habit in habits:
        data = HabitOut.model_validate(habit).model_dump()
        data["completed_dates"] = by_habit[habit.id]
        data["streak"] = calculate_streak(set(by_habit[habit.id]))
        outputs.append(HabitOut(**data))
    return outputs


@router.get("/focuses", response_model=list[FocusOut])
async def list_focuses(db: Database, user: CurrentUser) -> list[FocusProject]:
    return list(
        (
            await db.scalars(
                select(FocusProject)
                .where(FocusProject.user_id == user.id, FocusProject.deleted_at.is_(None))
                .order_by(FocusProject.is_active.desc(), FocusProject.updated_at.desc())
            )
        ).all()
    )


@router.post("/focuses", response_model=FocusOut, status_code=status.HTTP_201_CREATED)
async def create_focus(
    payload: FocusCreate,
    db: Database,
    user: CurrentUser,
) -> FocusProject:
    existing = await existing_client_entity(db, FocusProject, payload.id, user.id)
    if existing:
        return existing
    focus = FocusProject(user_id=user.id, **payload.model_dump(exclude_none=True))
    db.add(focus)
    try:
        await db.flush()
        if focus.is_active:
            await deactivate_other_focuses(db, user.id, focus.id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        repeated = await existing_client_entity(db, FocusProject, payload.id, user.id)
        if repeated:
            return repeated
        raise HTTPException(status_code=409, detail="Não foi possível criar este foco.") from None
    await db.refresh(focus)
    return focus


@router.patch("/focuses/{focus_id}", response_model=FocusOut)
async def update_focus(
    focus_id: str,
    payload: FocusUpdate,
    db: Database,
    user: CurrentUser,
) -> FocusProject:
    focus = await owned_entity(db, FocusProject, focus_id, user.id)
    check_version(focus, payload.expected_version)
    apply_update(focus, payload)
    if focus.is_active:
        await deactivate_other_focuses(db, user.id, focus.id)
    await db.commit()
    await db.refresh(focus)
    return focus


@router.delete("/focuses/{focus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_focus(
    focus_id: str,
    db: Database,
    user: CurrentUser,
    version: int | None = Query(default=None, ge=1),
) -> Response:
    focus = await owned_entity(db, FocusProject, focus_id, user.id)
    check_version(focus, version)
    focus.deleted_at = utcnow()
    focus.updated_at = focus.deleted_at
    focus.version += 1
    focus.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/habits", response_model=list[HabitOut])
async def list_habits(db: Database, user: CurrentUser) -> list[HabitOut]:
    habits = list(
        (
            await db.scalars(
                select(Habit)
                .where(Habit.user_id == user.id, Habit.deleted_at.is_(None))
                .order_by(Habit.created_at)
            )
        ).all()
    )
    return await habit_outputs(db, habits)


@router.post("/habits", response_model=HabitOut, status_code=status.HTTP_201_CREATED)
async def create_habit(payload: HabitCreate, db: Database, user: CurrentUser) -> HabitOut:
    existing = await existing_client_entity(db, Habit, payload.id, user.id)
    if existing:
        return (await habit_outputs(db, [existing]))[0]
    habit = Habit(user_id=user.id, **payload.model_dump(exclude_none=True))
    db.add(habit)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        repeated = await existing_client_entity(db, Habit, payload.id, user.id)
        if repeated:
            return (await habit_outputs(db, [repeated]))[0]
        raise HTTPException(
            status_code=409,
            detail="Não foi possível criar este hábito.",
        ) from None
    await db.refresh(habit)
    return (await habit_outputs(db, [habit]))[0]


@router.patch("/habits/{habit_id}", response_model=HabitOut)
async def update_habit(
    habit_id: str,
    payload: HabitUpdate,
    db: Database,
    user: CurrentUser,
) -> HabitOut:
    habit = await owned_entity(db, Habit, habit_id, user.id)
    check_version(habit, payload.expected_version)
    apply_update(habit, payload)
    await db.commit()
    await db.refresh(habit)
    return (await habit_outputs(db, [habit]))[0]


@router.put("/habits/{habit_id}/completions/{completed_on}", response_model=HabitOut)
async def complete_habit(
    habit_id: str,
    completed_on: date,
    db: Database,
    user: CurrentUser,
) -> HabitOut:
    habit = await owned_entity(db, Habit, habit_id, user.id)
    completion = await db.scalar(
        select(HabitCompletion).where(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.completed_on == completed_on,
        )
    )
    if not completion:
        db.add(HabitCompletion(habit_id=habit.id, completed_on=completed_on))
        habit.version += 1
        habit.updated_at = utcnow()
        await db.commit()
        await db.refresh(habit)
    return (await habit_outputs(db, [habit]))[0]


@router.delete("/habits/{habit_id}/completions/{completed_on}", response_model=HabitOut)
async def uncomplete_habit(
    habit_id: str,
    completed_on: date,
    db: Database,
    user: CurrentUser,
) -> HabitOut:
    habit = await owned_entity(db, Habit, habit_id, user.id)
    completion = await db.scalar(
        select(HabitCompletion).where(
            HabitCompletion.habit_id == habit.id,
            HabitCompletion.completed_on == completed_on,
        )
    )
    if completion:
        await db.delete(completion)
        habit.version += 1
        habit.updated_at = utcnow()
        await db.commit()
        await db.refresh(habit)
    return (await habit_outputs(db, [habit]))[0]


@router.delete("/habits/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: str,
    db: Database,
    user: CurrentUser,
    version: int | None = Query(default=None, ge=1),
) -> Response:
    habit = await owned_entity(db, Habit, habit_id, user.id)
    check_version(habit, version)
    habit.deleted_at = utcnow()
    habit.updated_at = habit.deleted_at
    habit.version += 1
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/goals", response_model=list[GoalOut])
async def list_goals(db: Database, user: CurrentUser) -> list[Goal]:
    return list(
        (
            await db.scalars(
                select(Goal)
                .where(Goal.user_id == user.id, Goal.deleted_at.is_(None))
                .order_by(Goal.created_at)
            )
        ).all()
    )


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(payload: GoalCreate, db: Database, user: CurrentUser) -> Goal:
    existing = await existing_client_entity(db, Goal, payload.id, user.id)
    if existing:
        return existing
    goal = Goal(user_id=user.id, **payload.model_dump(exclude_none=True))
    db.add(goal)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        repeated = await existing_client_entity(db, Goal, payload.id, user.id)
        if repeated:
            return repeated
        raise HTTPException(status_code=409, detail="Não foi possível criar esta meta.") from None
    await db.refresh(goal)
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    db: Database,
    user: CurrentUser,
) -> Goal:
    goal = await owned_entity(db, Goal, goal_id, user.id)
    check_version(goal, payload.expected_version)
    apply_update(goal, payload)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    db: Database,
    user: CurrentUser,
    version: int | None = Query(default=None, ge=1),
) -> Response:
    goal = await owned_entity(db, Goal, goal_id, user.id)
    check_version(goal, version)
    goal.deleted_at = utcnow()
    goal.updated_at = goal.deleted_at
    goal.version += 1
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(db: Database, user: CurrentUser) -> list[Task]:
    return list(
        (
            await db.scalars(
                select(Task)
                .where(Task.user_id == user.id, Task.deleted_at.is_(None))
                .order_by(Task.created_at)
            )
        ).all()
    )


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, db: Database, user: CurrentUser) -> Task:
    existing = await existing_client_entity(db, Task, payload.id, user.id)
    if existing:
        return existing
    task = Task(user_id=user.id, **payload.model_dump(exclude_none=True))
    db.add(task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        repeated = await existing_client_entity(db, Task, payload.id, user.id)
        if repeated:
            return repeated
        raise HTTPException(
            status_code=409,
            detail="Não foi possível criar esta tarefa.",
        ) from None
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Database,
    user: CurrentUser,
) -> Task:
    task = await owned_entity(db, Task, task_id, user.id)
    check_version(task, payload.expected_version)
    apply_update(task, payload)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: Database,
    user: CurrentUser,
    version: int | None = Query(default=None, ge=1),
) -> Response:
    task = await owned_entity(db, Task, task_id, user.id)
    check_version(task, version)
    task.deleted_at = utcnow()
    task.updated_at = task.deleted_at
    task.version += 1
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sync/pull", response_model=SyncResponse)
async def pull_sync(
    db: Database,
    user: CurrentUser,
    since: datetime | None = None,
) -> SyncResponse:
    def changed(model: Any) -> Any:
        conditions = [model.user_id == user.id]
        if since:
            conditions.append(model.updated_at > since)
        return select(model).where(*conditions).order_by(model.updated_at)

    focuses = list((await db.scalars(changed(FocusProject))).all())
    habits = list((await db.scalars(changed(Habit))).all())
    goals = list((await db.scalars(changed(Goal))).all())
    tasks = list((await db.scalars(changed(Task))).all())
    return SyncResponse(
        server_time=utcnow(),
        focuses=[FocusOut.model_validate(item) for item in focuses],
        habits=await habit_outputs(db, habits),
        goals=[GoalOut.model_validate(item) for item in goals],
        tasks=[TaskOut.model_validate(item) for item in tasks],
    )
