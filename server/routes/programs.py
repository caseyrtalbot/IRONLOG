from fastapi import APIRouter, Depends, HTTPException

from server.dependencies import get_db
from server.models.program import ProgramGenerate
from server.services import program_service

router = APIRouter()


@router.get("/programs")
def get_programs(athlete_id: int = 1, db=Depends(get_db)):
    return program_service.get_programs(db, athlete_id)


@router.post("/programs/generate")
def generate_program(body: ProgramGenerate, db=Depends(get_db)):
    return program_service.generate_program(db, body)


@router.get("/programs/{id}")
def get_program(id: int, db=Depends(get_db)):
    result = program_service.get_program_detail(db, id)
    if result is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return result


@router.get("/programs/{program_id}/sessions/{session_id}/prescriptions")
def get_session_prescriptions(program_id: int, session_id: int, db=Depends(get_db)):
    return program_service.get_current_week_prescriptions(db, program_id, session_id)


@router.get("/programs/{program_id}/retrospective")
def program_retrospective(program_id: int, db=Depends(get_db)):
    result = program_service.get_program_retrospective(db, program_id)
    if not result:
        raise HTTPException(404, "Program not found")
    return result
