from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FocusCreate(BaseModel):
    id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    name: str = Field(min_length=2, max_length=140)
    identity: str = Field(default="", max_length=1000)
    why: str = Field(default="", max_length=3000)
    outcome: str = Field(default="", max_length=3000)
    mode: Literal["sustainable", "intense"] = "sustainable"
    daily_minutes: int = Field(default=60, ge=10, le=720)
    cycle_minutes: int = Field(default=50, ge=10, le=180)
    break_minutes: int = Field(default=10, ge=1, le=90)
    target_days: int = Field(default=90, ge=1, le=3650)
    started_on: date = Field(default_factory=date.today)
    next_action: str = Field(default="", max_length=2000)
    curiosity_question: str = Field(default="", max_length=2000)
    ritual: dict[str, bool] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    milestones: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    sessions: list[dict[str, Any]] = Field(default_factory=list, max_length=2000)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Informe um nome válido")
        return cleaned


class FocusUpdate(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=140)
    identity: str | None = Field(default=None, max_length=1000)
    why: str | None = Field(default=None, max_length=3000)
    outcome: str | None = Field(default=None, max_length=3000)
    mode: Literal["sustainable", "intense"] | None = None
    daily_minutes: int | None = Field(default=None, ge=10, le=720)
    cycle_minutes: int | None = Field(default=None, ge=10, le=180)
    break_minutes: int | None = Field(default=None, ge=1, le=90)
    target_days: int | None = Field(default=None, ge=1, le=3650)
    started_on: date | None = None
    next_action: str | None = Field(default=None, max_length=2000)
    curiosity_question: str | None = Field(default=None, max_length=2000)
    ritual: dict[str, bool] | None = None
    health: dict[str, Any] | None = None
    milestones: list[dict[str, Any]] | None = Field(default=None, max_length=200)
    sessions: list[dict[str, Any]] | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class FocusOut(EntityOut, FocusCreate):
    pass


class HabitCreate(BaseModel):
    id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    name: str = Field(min_length=2, max_length=140)
    icon: str = Field(default="📌", min_length=1, max_length=16)
    category: str = Field(default="Pessoal", min_length=2, max_length=60)
    xp: int = Field(default=10, ge=0, le=1000)
    reminder_time: time | None = None
    scheduled_days: list[bool] = Field(default_factory=lambda: [True] * 7)

    @field_validator("name", "category")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("scheduled_days")
    @classmethod
    def validate_days(cls, value: list[bool]) -> list[bool]:
        if len(value) != 7:
            raise ValueError("scheduled_days precisa ter exatamente sete posições")
        return value


class HabitUpdate(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=140)
    icon: str | None = Field(default=None, min_length=1, max_length=16)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    xp: int | None = Field(default=None, ge=0, le=1000)
    reminder_time: time | None = None
    scheduled_days: list[bool] | None = None

    @field_validator("scheduled_days")
    @classmethod
    def validate_optional_days(cls, value: list[bool] | None) -> list[bool] | None:
        if value is not None and len(value) != 7:
            raise ValueError("scheduled_days precisa ter exatamente sete posições")
        return value


class HabitOut(EntityOut, HabitCreate):
    completed_dates: list[date] = Field(default_factory=list)
    streak: int = 0


class GoalCreate(BaseModel):
    id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    term: Literal["Diária", "Semanal", "Mensal", "Anual"] = "Semanal"
    text: str = Field(min_length=2, max_length=240)
    progress: int = Field(default=0, ge=0, le=100)
    category: str = Field(default="Pessoal", min_length=2, max_length=60)
    deadline: date | None = None


class GoalUpdate(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    term: Literal["Diária", "Semanal", "Mensal", "Anual"] | None = None
    text: str | None = Field(default=None, min_length=2, max_length=240)
    progress: int | None = Field(default=None, ge=0, le=100)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    deadline: date | None = None


class GoalOut(EntityOut, GoalCreate):
    pass


class TaskCreate(BaseModel):
    id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F-]{36}$")
    title: str = Field(min_length=2, max_length=240)
    category: str = Field(default="Pessoal", min_length=2, max_length=60)
    priority: Literal["baixa", "média", "alta"] = "média"
    status: Literal["todo", "doing", "done"] = "todo"
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=10080)


class TaskUpdate(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=240)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    priority: Literal["baixa", "média", "alta"] | None = None
    status: Literal["todo", "doing", "done"] | None = None
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=10080)


class TaskOut(EntityOut, TaskCreate):
    pass


class SyncResponse(BaseModel):
    server_time: datetime
    focuses: list[FocusOut]
    habits: list[HabitOut]
    goals: list[GoalOut]
    tasks: list[TaskOut]
