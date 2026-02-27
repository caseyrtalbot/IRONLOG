import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.config import CORS_ORIGINS
from server.db.connection import get_connection
from server.db.schema import init_schema
from server.db.seed_exercises import seed_exercises
from server.db.seed_muscles import seed_muscles
from server.routes import athlete, exercises, programs, workouts, analytics, dashboard


def create_app():
    app = FastAPI(title="IRONLOG", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(athlete.router, tags=["athlete"])
    app.include_router(exercises.router, tags=["exercises"])
    app.include_router(programs.router, tags=["programs"])
    app.include_router(workouts.router, tags=["workouts"])
    app.include_router(analytics.router, tags=["analytics"])
    app.include_router(dashboard.router, tags=["dashboard"])

    # Serve frontend static files
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(_root, "index.html"))

    app.mount("/js", StaticFiles(directory=os.path.join(_root, "js")), name="js")
    app.mount("/static", StaticFiles(directory=_root), name="static")

    @app.get("/style.css")
    def serve_css():
        return FileResponse(os.path.join(_root, "style.css"))

    @app.on_event("startup")
    def startup():
        db = get_connection()
        try:
            init_schema(db)
            seed_exercises(db)
            seed_muscles(db)
            _migrate_legacy_landmarks(db)
        finally:
            db.close()

    return app


def _migrate_legacy_landmarks(db):
    """Rename legacy muscle group names in volume_landmarks."""
    # back → split into lats + upper_back
    legacy_back = db.execute(
        "SELECT * FROM volume_landmarks WHERE muscle_group = 'back'"
    ).fetchall()
    for row in legacy_back:
        for new_group in ("lats", "upper_back"):
            db.execute(
                """INSERT OR IGNORE INTO volume_landmarks
                   (athlete_id, muscle_group, mev, mav_low, mav_high, mrv)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [row["athlete_id"], new_group, row["mev"],
                 row["mav_low"], row["mav_high"], row["mrv"]],
            )
        db.execute(
            "DELETE FROM volume_landmarks WHERE id = ?", [row["id"]]
        )

    # shoulders → split into front_delts + side_delts + rear_delts
    legacy_shoulders = db.execute(
        "SELECT * FROM volume_landmarks WHERE muscle_group = 'shoulders'"
    ).fetchall()
    for row in legacy_shoulders:
        for new_group in ("front_delts", "side_delts", "rear_delts"):
            db.execute(
                """INSERT OR IGNORE INTO volume_landmarks
                   (athlete_id, muscle_group, mev, mav_low, mav_high, mrv)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [row["athlete_id"], new_group, row["mev"],
                 row["mav_low"], row["mav_high"], row["mrv"]],
            )
        db.execute(
            "DELETE FROM volume_landmarks WHERE id = ?", [row["id"]]
        )

    db.commit()


app = create_app()
