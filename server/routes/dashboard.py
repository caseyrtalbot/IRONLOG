from fastapi import APIRouter, Depends

from server.dependencies import get_db
from server.services import dashboard_service

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(athlete_id: int = 1, db=Depends(get_db)):
    return dashboard_service.get_dashboard(db, athlete_id)
