from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

TRAINING_TYPES = {"water", "gym", "running", "ergometer", "core", "mobility", "test", "recovery", "rest", "other"}


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MemberIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    roles: set[Literal["club_admin", "coach", "athlete"]]


class GrantIn(BaseModel):
    coach_membership_id: str
    athlete_id: str


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)


class GroupAthleteIn(BaseModel):
    athlete_id: str


class GroupCoachIn(BaseModel):
    coach_membership_id: str


class SessionIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    training_type: str
    venue: Literal["club", "home"] = "club"
    scheduled_start: datetime
    planned_minutes: int = Field(ge=0, le=1440)
    instructions: str = Field(default="", max_length=4000)
    steps: list[str] = Field(default_factory=list, max_length=20)
    athlete_ids: list[str] = Field(default_factory=list)
    group_id: str | None = None

    @model_validator(mode="after")
    def validate_home_details(self):
        self.steps = [step.strip() for step in self.steps]
        if any(not step or len(step) > 500 for step in self.steps):
            raise ValueError("Cada paso debe tener entre 1 y 500 caracteres")
        if self.venue == "home" and not self.steps:
            raise ValueError("Los entrenamientos en casa necesitan indicaciones por pasos")
        return self

    @field_validator("training_type")
    @classmethod
    def check_type(cls, value: str) -> str:
        if value not in TRAINING_TYPES:
            raise ValueError("Tipo de entrenamiento desconocido")
        return value

    @field_validator("scheduled_start")
    @classmethod
    def check_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La fecha y hora necesitan zona horaria")
        return value


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "partial", "skipped"]
    actual_minutes: int | None = Field(default=None, ge=0, le=1440)
    rpe: int | None = Field(default=None, ge=1, le=10)
    feeling: int | None = Field(default=None, ge=1, le=5)
    has_pain: bool = False
    pain_area: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=2000)
    sensations: str | None = Field(default=None, max_length=1000)
    work_done: str | None = Field(default=None, max_length=1000)
    best: str | None = Field(default=None, max_length=1000)
    worst: str | None = Field(default=None, max_length=1000)


