from fastapi import APIRouter, Depends

from server.dependencies import get_db
from server.routes.helpers import require_found
from server.services import exercise_service

router = APIRouter()


# --- Static routes BEFORE parameterized /{id} ---


@router.get("/exercises/search")
def search_exercises(q: str = "", db=Depends(get_db)):
    return exercise_service.search_exercises(db, q)


@router.get("/exercises/patterns")
def get_movement_patterns(db=Depends(get_db)):
    return exercise_service.get_movement_patterns(db)


@router.get("/exercises/muscles")
def get_muscle_groups(db=Depends(get_db)):
    return exercise_service.get_muscle_groups(db)


# --- List and detail ---


@router.get("/exercises")
def get_exercises(
    pattern: str = "",
    category: str = "",
    equipment: str = "",
    muscle: str = "",
    db=Depends(get_db),
):
    return exercise_service.get_exercises(db, pattern, category, equipment, muscle)


@router.get("/exercises/{id}")
def get_exercise(id: int, db=Depends(get_db)):
    return require_found(exercise_service.get_exercise(db, id), "Exercise")
