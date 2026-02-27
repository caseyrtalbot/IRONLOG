from typing import Literal, Optional

from pydantic import BaseModel


class SetLog(BaseModel):
    exercise_id: int
    set_number: int = 1
    set_type: Literal[
        "warmup", "working", "backoff", "amrap", "drop", "cluster"
    ] = "working"
    weight: Optional[float] = None
    reps: Optional[int] = None
    rpe: Optional[float] = None
    rir: Optional[int] = None
    tempo: str = ""
    rest_seconds: Optional[int] = None
    notes: str = ""


class WorkoutSave(BaseModel):
    athlete_id: int = 1
    program_id: Optional[int] = None
    session_id: Optional[int] = None
    date: Optional[str] = None
    duration_min: Optional[int] = None
    notes: str = ""
    session_rpe: Optional[float] = None
    body_weight: Optional[float] = None
    sets: list[SetLog] = []
