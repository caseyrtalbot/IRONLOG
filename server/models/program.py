from typing import Literal, Optional

from pydantic import BaseModel


class ProgramGenerate(BaseModel):
    athlete_id: int = 1
    goal: Literal[
        "strength", "hypertrophy", "power", "endurance", "general"
    ] = "strength"
    phase: Literal[
        "accumulation", "intensification", "realization", "deload"
    ] = "accumulation"
    split: Literal["upper_lower", "push_pull_legs", "full_body"] = "upper_lower"
    weeks: int = 4
    days_per_week: int = 4
    name: Optional[str] = None
