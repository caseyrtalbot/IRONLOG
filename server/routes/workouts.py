from fastapi import APIRouter, Depends

from server.dependencies import get_db
from server.routes.helpers import require_found
from server.models.workout import WorkoutSave
from server.services import workout_service

router = APIRouter()


@router.post("/workouts")
def save_workout(body: WorkoutSave, db=Depends(get_db)):
    return workout_service.save_workout(db, body)


@router.get("/workouts")
def get_workouts(athlete_id: int = 1, limit: int = 20, offset: int = 0, db=Depends(get_db)):
    return workout_service.get_workouts(db, athlete_id, limit, offset)


@router.get("/workouts/{id}")
def get_workout_detail(id: int, db=Depends(get_db)):
    return require_found(workout_service.get_workout_detail(db, id), "Workout")


@router.delete("/workouts/{id}")
def delete_workout(id: int, db=Depends(get_db)):
    return require_found(workout_service.delete_workout(db, id), "Workout")
