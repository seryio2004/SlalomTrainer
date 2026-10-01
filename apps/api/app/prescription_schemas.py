"""Structured prescriptions: explicit units, stable items and nullable targets."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExerciseTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64)
    exercise_id: str | None = None
    name: str = Field(min_length=1, max_length=160)
    instructions: str = Field(default="", max_length=2000)
    sets: int | None = Field(default=None, ge=1, le=100)
    reps: int | None = Field(default=None, ge=0, le=10000)
    kg: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    seconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    meters: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)
    rest_seconds: int | None = Field(default=None, ge=0, le=86400)
    rir: int | None = Field(default=None, ge=0, le=10)
    target_rpe: int | None = Field(default=None, ge=1, le=10)
    side: Literal["bilateral", "left", "right", "alternating"] | None = None
    intensity: str | None = Field(default=None, max_length=160)
    zone: str | None = Field(default=None, max_length=160)
    load_convention: Literal["total", "per_side", "bodyweight"] | None = None


class PrescriptionBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    instructions: str = Field(default="", max_length=2000)
    exercises: list[ExerciseTarget] = Field(default_factory=list, max_length=100)


class DisciplineTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    water_subtype: Literal["technique", "base", "intensity", "simulation", "specific"] | None = None
    runs: int | None = Field(default=None, ge=0, le=1000)
    meters: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)
    seconds: float | None = Field(default=None, ge=0, le=86400, allow_inf_nan=False)
    target_rpe: int | None = Field(default=None, ge=1, le=10)
    model: str | None = Field(default=None, max_length=160)
    resistance: str | None = Field(default=None, max_length=160)
    protocol: str | None = Field(default=None, max_length=2000)
    protocol_version: int | None = Field(default=None, ge=1)


class StructuredPrescription(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    details: DisciplineTarget | None = None
    objective: str = Field(default="", max_length=2000)
    blocks: list[PrescriptionBlock] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def unique_items(self):
        ids = [block.id for block in self.blocks]
        if len(set(ids)) != len(ids):
            raise ValueError("Los bloques necesitan identificadores únicos")
        items = [exercise.id for block in self.blocks for exercise in block.exercises]
        if len(set(items)) != len(items):
            raise ValueError("Los ejercicios necesitan identificadores únicos")
        return self
