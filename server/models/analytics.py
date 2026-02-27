from pydantic import BaseModel


class LandmarkEntry(BaseModel):
    muscle_group: str
    mev: int
    mav_low: int
    mav_high: int
    mrv: int


class VolumeLandmarksSave(BaseModel):
    athlete_id: int = 1
    landmarks: list[LandmarkEntry] = []
