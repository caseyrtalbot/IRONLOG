from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import CORS_ORIGINS
from server.db.connection import get_connection
from server.db.schema import init_schema
from server.db.seed_exercises import seed_exercises
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

    @app.on_event("startup")
    def startup():
        db = get_connection()
        init_schema(db)
        seed_exercises(db)
        db.close()

    return app


app = create_app()
