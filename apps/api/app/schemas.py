from datetime import date, datetime, timezone
from .prescription_schemas import StructuredPrescription
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


class SessionIn(StructuredPrescription):
    title: str = Field(min_length=1, max_length=160)
    training_type: str
    venue: Literal["club", "home"] = "club"
    scheduled_start: datetime
    planned_minutes: int = Field(ge=0, le=1440)
    instructions: str = Field(default="", max_length=4000)
    steps: list[str] = Field(default_factory=list, max_length=20)
    athlete_ids: list[str] = Field(default_factory=list)
    group_id: str | None = None
    plan_day_id: str | None = None
    preview_athlete_ids: list[str] | None = None

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
        return value.astimezone(timezone.utc)


class SessionEditIn(StructuredPrescription):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=160)
    training_type: str
    venue: Literal["club", "home"]
    scheduled_start: datetime
    planned_minutes: int = Field(ge=0, le=1440)
    instructions: str = Field(default="", max_length=4000)
    steps: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_details(self):
        validated = SessionIn.model_validate(self.model_dump(exclude={"version"}))
        self.steps = validated.steps
        self.scheduled_start = validated.scheduled_start
        return self


class SessionCancelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


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



class SeriesResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    item_id: str | None = Field(default=None, max_length=64)
    exercise_id: str | None = None
    name: str = Field(min_length=1, max_length=160)
    origin: Literal["prescribed", "added", "substituted"] = "prescribed"
    set_number: int = Field(ge=1, le=100)
    reps: int | None = Field(default=None, ge=0, le=10000)
    kg: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    seconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    meters: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)
    rir: int | None = Field(default=None, ge=0, le=10)
    rpe: int | None = Field(default=None, ge=1, le=10)
    side: Literal["bilateral", "left", "right", "alternating"] | None = None
    load_convention: Literal["total", "per_side", "bodyweight"] | None = None
    comment: str | None = Field(default=None, max_length=1000)


class DisciplineResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    meters: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)
    seconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    elevation_m: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    model: str | None = Field(default=None, max_length=160)
    resistance: str | None = Field(default=None, max_length=160)
    watts: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    cadence: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)
    protocol: str | None = Field(default=None, max_length=2000)
    protocol_version: int | None = Field(default=None, ge=1)
    measure_name: str | None = Field(default=None, max_length=160)
    measure_value: float | None = Field(default=None, allow_inf_nan=False)
    measure_unit: str | None = Field(default=None, max_length=32)


class ExecutionReportIn(ReportIn):
    version: int = Field(ge=1)
    actual_date: date | None = None
    results: list[SeriesResult] = Field(default_factory=list, max_length=1000)
    discipline: DisciplineResult | None = None
    technical_quality: int | None = Field(default=None, ge=1, le=5)
    muscle_fatigue: int | None = Field(default=None, ge=1, le=5)
    pain_intensity: int | None = Field(default=None, ge=0, le=10)
    reason: str = Field(default="", max_length=500)
