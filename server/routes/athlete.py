from fastapi import APIRouter, Depends

from server.dependencies import get_db
from server.models.athlete import AthleteCreate
from server.services import athlete_service

router = APIRouter()


@router.get("/athlete")
def get_athlete(id: int = 1, db=Depends(get_db)):
    return athlete_service.get_athlete(db, id)


@router.post("/athlete")
def save_athlete(body: AthleteCreate, db=Depends(get_db)):
    return athlete_service.save_athlete(db, body)
