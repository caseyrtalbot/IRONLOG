from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from server.dependencies import get_db
from server.models.analytics import VolumeLandmarksSave
from server.services import analytics_service

router = APIRouter()


# --- Static routes BEFORE parameterized /{metric} ---


@router.get("/analytics/e1rm")
def get_e1rm(
    athlete_id: int = 1,
    exercise_id: Optional[int] = None,
    days: int = 90,
    db=Depends(get_db),
):
    return analytics_service.get_e1rm(db, athlete_id, exercise_id, days)


@router.get("/analytics/overload")
def get_overload_rec(athlete_id: int = 1, exercise_id: int = 0, db=Depends(get_db)):
    return analytics_service.get_overload_rec(db, athlete_id, exercise_id)


@router.get("/analytics/volume-landmarks")
def get_volume_landmarks(athlete_id: int = 1, db=Depends(get_db)):
    return analytics_service.get_volume_landmarks(db, athlete_id)


@router.post("/analytics/volume-landmarks")
def save_volume_landmarks(body: VolumeLandmarksSave, db=Depends(get_db)):
    return analytics_service.save_volume_landmarks(db, body)


@router.get("/analytics/phase-config")
def get_phase_config(goal: str = "strength", phase: str = "accumulation", experience: str = "intermediate"):
    return analytics_service.get_phase_config(goal, phase, experience)


# --- Parameterized route last ---


@router.get("/analytics/{metric}")
def get_analytics(metric: str, athlete_id: int = 1, days: int = 30, db=Depends(get_db)):
    return analytics_service.get_analytics(db, athlete_id, days, metric)
