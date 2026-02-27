from typing import Literal, Optional

from pydantic import BaseModel


class AthleteCreate(BaseModel):
    id: int = 1
    name: str
    age: Optional[int] = None
    body_weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    training_age: Optional[int] = None
    experience_level: Literal[
        "beginner", "intermediate", "advanced", "elite"
    ] = "intermediate"
    primary_goal: Literal[
        "strength", "hypertrophy", "power", "endurance", "general"
    ] = "strength"
    training_days_per_week: int = 4
    session_duration_min: int = 75
