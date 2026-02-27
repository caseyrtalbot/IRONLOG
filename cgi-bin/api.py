#!/usr/bin/env python3
"""
IRONLOG - World-Class Strength Training API
SQLite-backed CGI API for workout tracking, progressive overload, and periodized programming.
"""

import json
import os
import sqlite3
import sys
import hashlib
import math
from datetime import datetime, timedelta
from urllib.parse import parse_qs

DB_PATH = "ironlog.db"

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db

def init_db():
    db = get_db()

    # --- SCHEMA ---
    db.executescript("""
    CREATE TABLE IF NOT EXISTS athletes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        body_weight REAL,
        body_fat_pct REAL,
        training_age INTEGER DEFAULT 0,
        experience_level TEXT DEFAULT 'intermediate' CHECK(experience_level IN ('beginner','intermediate','advanced','elite')),
        primary_goal TEXT DEFAULT 'strength' CHECK(primary_goal IN ('strength','hypertrophy','power','endurance','general')),
        training_days_per_week INTEGER DEFAULT 4,
        session_duration_min INTEGER DEFAULT 75,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        movement_pattern TEXT NOT NULL,
        primary_muscles TEXT NOT NULL,
        secondary_muscles TEXT DEFAULT '',
        equipment TEXT DEFAULT 'barbell',
        bilateral INTEGER DEFAULT 1,
        complexity INTEGER DEFAULT 2 CHECK(complexity BETWEEN 1 AND 5),
        fatigue_rating INTEGER DEFAULT 3 CHECK(fatigue_rating BETWEEN 1 AND 5),
        mev_sets_per_week INTEGER DEFAULT 6,
        mrv_sets_per_week INTEGER DEFAULT 20,
        notes TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        phase TEXT NOT NULL CHECK(phase IN ('accumulation','intensification','realization','deload','transition')),
        goal TEXT NOT NULL CHECK(goal IN ('strength','hypertrophy','power','endurance','general')),
        mesocycle_weeks INTEGER DEFAULT 4,
        current_week INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active' CHECK(status IN ('active','completed','paused')),
        config TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (athlete_id) REFERENCES athletes(id)
    );

    CREATE TABLE IF NOT EXISTS program_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER NOT NULL,
        day_number INTEGER NOT NULL,
        name TEXT NOT NULL,
        focus TEXT DEFAULT '',
        session_order INTEGER DEFAULT 1,
        FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS program_exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        exercise_id INTEGER NOT NULL,
        exercise_order INTEGER DEFAULT 1,
        superset_group TEXT DEFAULT NULL,
        sets_prescribed INTEGER NOT NULL,
        reps_prescribed TEXT NOT NULL,
        intensity_type TEXT DEFAULT 'rpe' CHECK(intensity_type IN ('rpe','rir','percent_rm','rpe_range')),
        intensity_value TEXT NOT NULL,
        rest_seconds INTEGER DEFAULT 120,
        tempo TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        FOREIGN KEY (session_id) REFERENCES program_sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (exercise_id) REFERENCES exercises(id)
    );

    CREATE TABLE IF NOT EXISTS workout_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id INTEGER NOT NULL,
        program_id INTEGER,
        session_id INTEGER,
        date TEXT NOT NULL,
        duration_min INTEGER,
        notes TEXT DEFAULT '',
        session_rpe REAL,
        body_weight REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (athlete_id) REFERENCES athletes(id),
        FOREIGN KEY (program_id) REFERENCES programs(id)
    );

    CREATE TABLE IF NOT EXISTS set_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_log_id INTEGER NOT NULL,
        exercise_id INTEGER NOT NULL,
        set_number INTEGER NOT NULL,
        set_type TEXT DEFAULT 'working' CHECK(set_type IN ('warmup','working','backoff','amrap','drop','cluster')),
        weight REAL,
        reps INTEGER,
        rpe REAL,
        rir INTEGER,
        tempo TEXT DEFAULT '',
        rest_seconds INTEGER,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id) ON DELETE CASCADE,
        FOREIGN KEY (exercise_id) REFERENCES exercises(id)
    );

    CREATE TABLE IF NOT EXISTS one_rep_maxes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id INTEGER NOT NULL,
        exercise_id INTEGER NOT NULL,
        estimated_1rm REAL NOT NULL,
        method TEXT DEFAULT 'epley',
        source_weight REAL,
        source_reps INTEGER,
        source_rpe REAL,
        date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (athlete_id) REFERENCES athletes(id),
        FOREIGN KEY (exercise_id) REFERENCES exercises(id)
    );

    CREATE TABLE IF NOT EXISTS volume_landmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id INTEGER NOT NULL,
        muscle_group TEXT NOT NULL,
        mev INTEGER DEFAULT 6,
        mav_low INTEGER DEFAULT 10,
        mav_high INTEGER DEFAULT 16,
        mrv INTEGER DEFAULT 20,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (athlete_id) REFERENCES athletes(id),
        UNIQUE(athlete_id, muscle_group)
    );

    CREATE INDEX IF NOT EXISTS idx_set_logs_exercise ON set_logs(exercise_id);
    CREATE INDEX IF NOT EXISTS idx_set_logs_workout ON set_logs(workout_log_id);
    CREATE INDEX IF NOT EXISTS idx_workout_logs_athlete ON workout_logs(athlete_id);
    CREATE INDEX IF NOT EXISTS idx_workout_logs_date ON workout_logs(date);
    CREATE INDEX IF NOT EXISTS idx_one_rep_maxes_athlete_exercise ON one_rep_maxes(athlete_id, exercise_id);
    """)

    db.commit()
    return db


def seed_exercises(db):
    """Seed the exercise taxonomy database with 250+ exercises."""
    count = db.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    if count > 0:
        return

    exercises = [
        # === COMPOUND BARBELL - HORIZONTAL PUSH ===
        ("Barbell Bench Press", "compound", "horizontal_push", "chest,anterior_deltoid,triceps", "serratus_anterior", "barbell", 1, 2, 4, 6, 22),
        ("Close-Grip Bench Press", "compound", "horizontal_push", "triceps,chest", "anterior_deltoid", "barbell", 1, 2, 3, 6, 20),
        ("Wide-Grip Bench Press", "compound", "horizontal_push", "chest,anterior_deltoid", "triceps", "barbell", 1, 3, 4, 6, 20),
        ("Paused Bench Press", "compound", "horizontal_push", "chest,anterior_deltoid,triceps", "serratus_anterior", "barbell", 1, 3, 4, 6, 20),
        ("Spoto Press", "compound", "horizontal_push", "chest,triceps", "anterior_deltoid", "barbell", 1, 3, 4, 6, 18),
        ("Floor Press", "compound", "horizontal_push", "triceps,chest", "anterior_deltoid", "barbell", 1, 2, 3, 6, 18),
        ("Larsen Press", "compound", "horizontal_push", "chest,anterior_deltoid,triceps", "core", "barbell", 1, 3, 4, 6, 18),
        ("Board Press", "compound", "horizontal_push", "triceps,chest", "anterior_deltoid", "barbell", 1, 3, 3, 6, 18),
        ("Incline Barbell Press", "compound", "horizontal_push", "upper_chest,anterior_deltoid,triceps", "serratus_anterior", "barbell", 1, 2, 4, 6, 20),
        ("Decline Barbell Press", "compound", "horizontal_push", "lower_chest,triceps", "anterior_deltoid", "barbell", 1, 2, 3, 6, 18),

        # === COMPOUND BARBELL - VERTICAL PUSH ===
        ("Overhead Press", "compound", "vertical_push", "anterior_deltoid,lateral_deltoid,triceps", "upper_chest,core", "barbell", 1, 2, 4, 6, 18),
        ("Push Press", "compound", "vertical_push", "anterior_deltoid,triceps", "quads,glutes,core", "barbell", 1, 3, 4, 6, 16),
        ("Behind-the-Neck Press", "compound", "vertical_push", "lateral_deltoid,anterior_deltoid,triceps", "upper_traps", "barbell", 1, 4, 4, 4, 14),
        ("Z-Press", "compound", "vertical_push", "anterior_deltoid,lateral_deltoid,triceps", "core", "barbell", 1, 4, 4, 6, 16),
        ("Pin Press (Overhead)", "compound", "vertical_push", "anterior_deltoid,triceps", "lateral_deltoid", "barbell", 1, 3, 3, 6, 16),
        ("Viking Press", "compound", "vertical_push", "anterior_deltoid,triceps", "lateral_deltoid,core", "machine", 1, 2, 3, 6, 18),
        ("Barbell Thruster", "compound", "vertical_push", "quads,anterior_deltoid,triceps", "glutes,core", "barbell", 1, 3, 5, 6, 16),
        ("Strict Press (Military)", "compound", "vertical_push", "anterior_deltoid,lateral_deltoid,triceps", "core,upper_chest", "barbell", 1, 2, 4, 6, 18),

        # === COMPOUND BARBELL - SQUAT PATTERN ===
        ("Back Squat", "compound", "squat", "quads,glutes", "hamstrings,erectors,core", "barbell", 1, 2, 5, 6, 20),
        ("Front Squat", "compound", "squat", "quads,core", "glutes,upper_back", "barbell", 1, 3, 5, 6, 18),
        ("Safety Bar Squat", "compound", "squat", "quads,glutes", "hamstrings,upper_back,core", "barbell", 1, 2, 4, 6, 20),
        ("Paused Back Squat", "compound", "squat", "quads,glutes", "hamstrings,core", "barbell", 1, 3, 5, 6, 18),
        ("Pin Squat", "compound", "squat", "quads,glutes", "hamstrings,core", "barbell", 1, 3, 4, 6, 16),
        ("Box Squat", "compound", "squat", "quads,glutes,hamstrings", "core,erectors", "barbell", 1, 3, 4, 6, 18),
        ("Tempo Squat", "compound", "squat", "quads,glutes", "hamstrings,core", "barbell", 1, 3, 5, 6, 18),
        ("Anderson Squat", "compound", "squat", "quads,glutes", "core,erectors", "barbell", 1, 4, 4, 6, 16),
        ("Zercher Squat", "compound", "squat", "quads,glutes,core", "biceps,upper_back", "barbell", 1, 4, 5, 6, 16),
        ("Overhead Squat", "compound", "squat", "quads,glutes,core", "shoulders,upper_back", "barbell", 1, 5, 4, 4, 14),

        # === COMPOUND BARBELL - HIP HINGE ===
        ("Conventional Deadlift", "compound", "hip_hinge", "hamstrings,glutes,erectors", "quads,lats,traps,forearms", "barbell", 1, 2, 5, 4, 16),
        ("Sumo Deadlift", "compound", "hip_hinge", "glutes,quads,hamstrings", "erectors,adductors", "barbell", 1, 3, 5, 4, 16),
        ("Romanian Deadlift", "compound", "hip_hinge", "hamstrings,glutes", "erectors,core", "barbell", 1, 2, 3, 6, 18),
        ("Stiff-Leg Deadlift", "compound", "hip_hinge", "hamstrings,glutes,erectors", "core", "barbell", 1, 2, 4, 6, 18),
        ("Deficit Deadlift", "compound", "hip_hinge", "hamstrings,glutes,quads", "erectors,lats", "barbell", 1, 3, 5, 4, 16),
        ("Block Pull / Rack Pull", "compound", "hip_hinge", "erectors,glutes,traps", "hamstrings,lats", "barbell", 1, 3, 4, 4, 16),
        ("Trap Bar Deadlift", "compound", "hip_hinge", "quads,glutes,hamstrings", "erectors,traps", "barbell", 1, 2, 4, 6, 18),
        ("Paused Deadlift", "compound", "hip_hinge", "hamstrings,glutes,erectors", "quads,lats", "barbell", 1, 3, 5, 4, 16),
        ("Snatch-Grip Deadlift", "compound", "hip_hinge", "upper_back,hamstrings,glutes", "erectors,traps", "barbell", 1, 4, 5, 4, 16),
        ("Good Morning", "compound", "hip_hinge", "hamstrings,erectors,glutes", "core", "barbell", 1, 3, 4, 6, 16),
        ("Seated Good Morning", "compound", "hip_hinge", "hamstrings,erectors", "glutes,core", "barbell", 1, 3, 3, 6, 14),

        # === COMPOUND - HORIZONTAL PULL ===
        ("Barbell Row (Bent-Over)", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps,erectors", "barbell", 1, 2, 3, 6, 20),
        ("Pendlay Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps,erectors", "barbell", 1, 3, 4, 6, 18),
        ("Seal Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps", "barbell", 1, 2, 2, 6, 20),
        ("T-Bar Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps,erectors", "barbell", 1, 2, 3, 6, 20),
        ("Meadows Row", "compound", "horizontal_pull", "lats,rear_deltoid", "biceps,rhomboids", "barbell", 0, 3, 3, 6, 18),
        ("Chest-Supported Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps", "dumbbell", 1, 1, 2, 6, 22),
        ("Kroc Row", "compound", "horizontal_pull", "lats,rhomboids", "biceps,forearms,rear_deltoid", "dumbbell", 0, 2, 3, 6, 18),
        ("Cable Row (Seated)", "compound", "horizontal_pull", "lats,rhomboids", "biceps,rear_deltoid", "cable", 1, 1, 2, 6, 22),
        ("Single-Arm Cable Row", "compound", "horizontal_pull", "lats,rhomboids", "biceps,rear_deltoid,core", "cable", 0, 2, 2, 6, 20),
        ("Machine Row", "compound", "horizontal_pull", "lats,rhomboids", "biceps,rear_deltoid", "machine", 1, 1, 2, 6, 22),
        ("Helms Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps", "dumbbell", 1, 2, 2, 6, 20),

        # === COMPOUND - VERTICAL PULL ===
        ("Pull-Up", "compound", "vertical_pull", "lats,biceps", "rhomboids,rear_deltoid,forearms", "bodyweight", 1, 2, 3, 6, 20),
        ("Chin-Up", "compound", "vertical_pull", "lats,biceps", "rhomboids,forearms", "bodyweight", 1, 2, 3, 6, 20),
        ("Neutral-Grip Pull-Up", "compound", "vertical_pull", "lats,biceps,brachialis", "rhomboids,rear_deltoid", "bodyweight", 1, 2, 3, 6, 20),
        ("Weighted Pull-Up", "compound", "vertical_pull", "lats,biceps", "rhomboids,rear_deltoid,forearms", "bodyweight", 1, 3, 4, 6, 18),
        ("Weighted Chin-Up", "compound", "vertical_pull", "lats,biceps", "rhomboids,forearms", "bodyweight", 1, 3, 4, 6, 18),
        ("Lat Pulldown", "compound", "vertical_pull", "lats,biceps", "rhomboids,rear_deltoid", "cable", 1, 1, 2, 6, 22),
        ("Close-Grip Lat Pulldown", "compound", "vertical_pull", "lats,biceps,brachialis", "rhomboids", "cable", 1, 1, 2, 6, 22),
        ("Wide-Grip Lat Pulldown", "compound", "vertical_pull", "lats,rear_deltoid", "biceps,rhomboids", "cable", 1, 1, 2, 6, 22),
        ("Behind-the-Neck Lat Pulldown", "compound", "vertical_pull", "lats,rear_deltoid,rhomboids", "biceps", "cable", 1, 2, 2, 6, 18),
        ("Single-Arm Lat Pulldown", "compound", "vertical_pull", "lats", "biceps,rear_deltoid", "cable", 0, 2, 2, 6, 20),
        ("Assisted Pull-Up", "compound", "vertical_pull", "lats,biceps", "rhomboids,rear_deltoid", "machine", 1, 1, 2, 6, 22),
        ("One-Arm Chin-Up (OAC)", "compound", "vertical_pull", "lats,biceps", "forearms,core,rear_deltoid", "bodyweight", 0, 5, 5, 4, 12),
        ("1.25 Neutral Chin-Up", "compound", "vertical_pull", "lats,biceps,brachialis", "rhomboids", "bodyweight", 1, 4, 4, 6, 16),
        ("Pulley-Assisted OAC", "compound", "vertical_pull", "lats,biceps", "forearms,core", "cable", 0, 5, 4, 4, 14),

        # === DUMBBELL - PUSH ===
        ("Dumbbell Bench Press", "compound", "horizontal_push", "chest,anterior_deltoid,triceps", "serratus_anterior", "dumbbell", 1, 1, 3, 6, 22),
        ("Incline Dumbbell Press", "compound", "horizontal_push", "upper_chest,anterior_deltoid", "triceps", "dumbbell", 1, 1, 3, 6, 22),
        ("Decline Dumbbell Press", "compound", "horizontal_push", "lower_chest,triceps", "anterior_deltoid", "dumbbell", 1, 1, 3, 6, 20),
        ("Dumbbell Overhead Press", "compound", "vertical_push", "anterior_deltoid,lateral_deltoid,triceps", "core", "dumbbell", 1, 2, 3, 6, 20),
        ("Seated Dumbbell Press", "compound", "vertical_push", "anterior_deltoid,lateral_deltoid,triceps", "", "dumbbell", 1, 1, 3, 6, 20),
        ("Arnold Press", "compound", "vertical_push", "anterior_deltoid,lateral_deltoid,triceps", "upper_chest", "dumbbell", 1, 2, 3, 6, 18),
        ("Dumbbell Floor Press", "compound", "horizontal_push", "triceps,chest", "anterior_deltoid", "dumbbell", 1, 1, 3, 6, 18),
        ("Incline Smith Machine Press", "compound", "horizontal_push", "upper_chest,anterior_deltoid,triceps", "", "machine", 1, 1, 3, 6, 22),
        ("Range Press", "compound", "horizontal_push", "chest,anterior_deltoid", "triceps", "dumbbell", 1, 3, 3, 6, 18),
        ("JM Press", "compound", "horizontal_push", "triceps,chest", "anterior_deltoid", "barbell", 1, 3, 3, 6, 16),

        # === DUMBBELL - LOWER ===
        ("Dumbbell Goblet Squat", "compound", "squat", "quads,glutes", "core", "dumbbell", 1, 1, 2, 6, 20),
        ("Dumbbell Lunge", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 1, 3, 6, 20),
        ("Dumbbell Romanian Deadlift", "compound", "hip_hinge", "hamstrings,glutes", "erectors", "dumbbell", 1, 1, 3, 6, 20),
        ("Dumbbell Step-Up", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 2, 3, 6, 18),
        ("Dumbbell Split Squat", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 2, 3, 6, 18),
        ("Dumbbell Bulgarian Split Squat", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 2, 4, 6, 18),
        ("Goblet Cyclic Squat", "compound", "squat", "quads,glutes", "core,calves", "dumbbell", 1, 2, 3, 6, 18),

        # === BARBELL - LUNGE / UNILATERAL ===
        ("Barbell Walking Lunge", "compound", "lunge", "quads,glutes", "hamstrings,core", "barbell", 0, 2, 4, 6, 18),
        ("Barbell Reverse Lunge", "compound", "lunge", "quads,glutes", "hamstrings,core", "barbell", 0, 2, 3, 6, 18),
        ("Barbell Bulgarian Split Squat", "compound", "lunge", "quads,glutes", "hamstrings,core", "barbell", 0, 3, 4, 6, 16),
        ("Zercher Reverse Lunge", "compound", "lunge", "quads,glutes,core", "hamstrings,biceps", "barbell", 0, 4, 4, 6, 16),
        ("Barbell Step-Up", "compound", "lunge", "quads,glutes", "hamstrings", "barbell", 0, 2, 3, 6, 18),
        ("Front Foot Elevated Split Squat", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 2, 3, 6, 18),
        ("Kickstand RDL", "compound", "hip_hinge", "hamstrings,glutes", "erectors,core", "dumbbell", 0, 2, 3, 6, 18),
        ("Single-Leg RDL", "compound", "hip_hinge", "hamstrings,glutes", "erectors,core", "dumbbell", 0, 3, 3, 6, 16),
        ("Smith Machine Pistol Squat", "compound", "squat", "quads,glutes", "core", "machine", 0, 3, 3, 6, 16),

        # === MACHINE - LOWER ===
        ("Leg Press", "compound", "squat", "quads,glutes", "hamstrings", "machine", 1, 1, 3, 6, 22),
        ("Hack Squat", "compound", "squat", "quads,glutes", "hamstrings", "machine", 1, 1, 3, 6, 22),
        ("Belt Squat", "compound", "squat", "quads,glutes", "core", "machine", 1, 1, 3, 6, 22),
        ("Pendulum Squat", "compound", "squat", "quads,glutes", "", "machine", 1, 1, 3, 6, 22),
        ("Smith Machine Squat", "compound", "squat", "quads,glutes", "hamstrings", "machine", 1, 1, 3, 6, 22),
        ("V-Squat", "compound", "squat", "quads,glutes", "hamstrings", "machine", 1, 1, 3, 6, 22),

        # === ISOLATION - QUADS ===
        ("Leg Extension", "isolation", "knee_extension", "quads", "", "machine", 1, 1, 1, 8, 24),
        ("Single-Leg Extension", "isolation", "knee_extension", "quads", "", "machine", 0, 1, 1, 8, 24),
        ("Sissy Squat", "isolation", "knee_extension", "quads", "core", "bodyweight", 1, 3, 2, 6, 18),
        ("Reverse Nordic Curl", "isolation", "knee_extension", "quads", "", "bodyweight", 1, 3, 2, 6, 16),
        ("Spanish Squat", "isolation", "knee_extension", "quads", "", "band", 1, 2, 2, 8, 20),

        # === ISOLATION - HAMSTRINGS ===
        ("Lying Leg Curl", "isolation", "knee_flexion", "hamstrings", "", "machine", 1, 1, 1, 8, 24),
        ("Seated Leg Curl", "isolation", "knee_flexion", "hamstrings", "", "machine", 1, 1, 1, 8, 24),
        ("Nordic Curl", "isolation", "knee_flexion", "hamstrings", "", "bodyweight", 1, 4, 4, 6, 16),
        ("Razor Curl", "isolation", "knee_flexion", "hamstrings", "", "bodyweight", 1, 3, 3, 6, 18),
        ("Glute-Ham Raise", "compound", "knee_flexion", "hamstrings,glutes", "erectors", "bodyweight", 1, 3, 3, 6, 18),
        ("Slider Leg Curl", "isolation", "knee_flexion", "hamstrings", "glutes", "bodyweight", 1, 2, 2, 8, 20),
        ("Single-Leg Lying Curl", "isolation", "knee_flexion", "hamstrings", "", "machine", 0, 1, 1, 8, 24),
        ("Standing Leg Curl", "isolation", "knee_flexion", "hamstrings", "", "machine", 0, 1, 1, 8, 24),

        # === ISOLATION - GLUTES ===
        ("Hip Thrust", "compound", "hip_extension", "glutes", "hamstrings", "barbell", 1, 2, 3, 6, 20),
        ("Single-Leg Hip Thrust", "compound", "hip_extension", "glutes", "hamstrings,core", "bodyweight", 0, 2, 2, 6, 20),
        ("Barbell Glute Bridge", "compound", "hip_extension", "glutes", "hamstrings", "barbell", 1, 1, 2, 6, 22),
        ("Cable Pull-Through", "compound", "hip_extension", "glutes,hamstrings", "erectors", "cable", 1, 1, 2, 8, 22),
        ("Hip Abduction Machine", "isolation", "hip_abduction", "glute_medius,glute_minimus", "", "machine", 1, 1, 1, 8, 24),
        ("Cable Kickback", "isolation", "hip_extension", "glutes", "", "cable", 0, 1, 1, 8, 22),
        ("Frog Pump", "isolation", "hip_extension", "glutes", "", "bodyweight", 1, 1, 1, 8, 22),
        ("Reverse Hyperextension", "compound", "hip_extension", "glutes,hamstrings,erectors", "", "machine", 1, 1, 2, 8, 22),
        ("45-Degree Back Extension", "compound", "hip_extension", "erectors,glutes,hamstrings", "", "bodyweight", 1, 1, 2, 8, 22),

        # === ISOLATION - CHEST ===
        ("Cable Fly (Mid)", "isolation", "horizontal_push", "chest", "anterior_deltoid", "cable", 1, 1, 1, 8, 24),
        ("Cable Fly (Low-to-High)", "isolation", "horizontal_push", "upper_chest", "anterior_deltoid", "cable", 1, 1, 1, 8, 24),
        ("Cable Fly (High-to-Low)", "isolation", "horizontal_push", "lower_chest", "anterior_deltoid", "cable", 1, 1, 1, 8, 24),
        ("Dumbbell Fly", "isolation", "horizontal_push", "chest", "anterior_deltoid", "dumbbell", 1, 1, 2, 8, 22),
        ("Incline Dumbbell Fly", "isolation", "horizontal_push", "upper_chest", "anterior_deltoid", "dumbbell", 1, 1, 2, 8, 22),
        ("Pec Deck", "isolation", "horizontal_push", "chest", "anterior_deltoid", "machine", 1, 1, 1, 8, 24),
        ("Machine Chest Press", "compound", "horizontal_push", "chest,anterior_deltoid,triceps", "", "machine", 1, 1, 2, 6, 22),
        ("Machine Incline Press", "compound", "horizontal_push", "upper_chest,anterior_deltoid", "triceps", "machine", 1, 1, 2, 6, 22),

        # === ISOLATION - SHOULDERS ===
        ("Lateral Raise (Dumbbell)", "isolation", "lateral_raise", "lateral_deltoid", "", "dumbbell", 1, 1, 1, 10, 25),
        ("Cable Lateral Raise", "isolation", "lateral_raise", "lateral_deltoid", "", "cable", 0, 1, 1, 10, 25),
        ("Machine Lateral Raise", "isolation", "lateral_raise", "lateral_deltoid", "", "machine", 1, 1, 1, 10, 25),
        ("Leaning Lateral Raise", "isolation", "lateral_raise", "lateral_deltoid", "", "dumbbell", 0, 2, 1, 10, 25),
        ("Upright Row", "compound", "lateral_raise", "lateral_deltoid,upper_traps", "anterior_deltoid,biceps", "barbell", 1, 2, 2, 8, 20),
        ("Cable Upright Row", "compound", "lateral_raise", "lateral_deltoid,upper_traps", "anterior_deltoid", "cable", 1, 2, 2, 8, 20),
        ("Face Pull", "isolation", "horizontal_pull", "rear_deltoid,rhomboids", "external_rotators", "cable", 1, 1, 1, 10, 25),
        ("Reverse Pec Deck", "isolation", "horizontal_pull", "rear_deltoid", "rhomboids", "machine", 1, 1, 1, 10, 25),
        ("Rear Delt Fly (Dumbbell)", "isolation", "horizontal_pull", "rear_deltoid", "rhomboids", "dumbbell", 1, 1, 1, 10, 25),
        ("Cable Rear Delt Fly", "isolation", "horizontal_pull", "rear_deltoid", "rhomboids", "cable", 1, 1, 1, 10, 25),
        ("Band Pull-Apart", "isolation", "horizontal_pull", "rear_deltoid,rhomboids", "external_rotators", "band", 1, 1, 1, 10, 25),
        ("Lu Raise", "isolation", "lateral_raise", "lateral_deltoid,anterior_deltoid", "", "dumbbell", 1, 3, 2, 8, 18),
        ("Y-Raise", "isolation", "vertical_push", "lower_traps,rear_deltoid", "", "dumbbell", 1, 1, 1, 10, 25),

        # === ISOLATION - TRICEPS ===
        ("Tricep Pushdown (Rope)", "isolation", "elbow_extension", "triceps", "", "cable", 1, 1, 1, 10, 25),
        ("Tricep Pushdown (Bar)", "isolation", "elbow_extension", "triceps", "", "cable", 1, 1, 1, 10, 25),
        ("Overhead Tricep Extension (Cable)", "isolation", "elbow_extension", "triceps_long_head", "", "cable", 1, 1, 1, 10, 25),
        ("Overhead Tricep Extension (Dumbbell)", "isolation", "elbow_extension", "triceps_long_head", "", "dumbbell", 1, 1, 1, 10, 25),
        ("Skull Crusher", "isolation", "elbow_extension", "triceps", "", "barbell", 1, 2, 2, 8, 22),
        ("Dumbbell Skull Crusher", "isolation", "elbow_extension", "triceps", "", "dumbbell", 1, 2, 2, 8, 22),
        ("Dip", "compound", "vertical_push", "triceps,chest,anterior_deltoid", "", "bodyweight", 1, 2, 3, 6, 20),
        ("Weighted Dip", "compound", "vertical_push", "triceps,chest,anterior_deltoid", "", "bodyweight", 1, 3, 4, 6, 18),
        ("Kickback (Cable)", "isolation", "elbow_extension", "triceps", "", "cable", 0, 1, 1, 10, 25),
        ("Diamond Push-Up", "compound", "horizontal_push", "triceps,chest", "anterior_deltoid", "bodyweight", 1, 2, 2, 8, 20),
        ("French Press", "isolation", "elbow_extension", "triceps_long_head", "", "barbell", 1, 2, 2, 8, 22),
        ("Butcher Block Tricep Extension", "isolation", "elbow_extension", "triceps", "", "dumbbell", 1, 2, 2, 8, 20),

        # === ISOLATION - BICEPS ===
        ("Barbell Curl", "isolation", "elbow_flexion", "biceps", "brachialis,forearms", "barbell", 1, 1, 1, 10, 25),
        ("EZ-Bar Curl", "isolation", "elbow_flexion", "biceps", "brachialis", "barbell", 1, 1, 1, 10, 25),
        ("Dumbbell Curl", "isolation", "elbow_flexion", "biceps", "brachialis", "dumbbell", 1, 1, 1, 10, 25),
        ("Alternating Dumbbell Curl", "isolation", "elbow_flexion", "biceps", "brachialis", "dumbbell", 0, 1, 1, 10, 25),
        ("Seated Alternating DB Curl", "isolation", "elbow_flexion", "biceps", "brachialis", "dumbbell", 0, 1, 1, 10, 25),
        ("Incline Dumbbell Curl", "isolation", "elbow_flexion", "biceps_long_head", "brachialis", "dumbbell", 1, 1, 1, 10, 25),
        ("Hammer Curl", "isolation", "elbow_flexion", "brachialis,biceps", "forearms", "dumbbell", 1, 1, 1, 10, 25),
        ("Cable Curl", "isolation", "elbow_flexion", "biceps", "brachialis", "cable", 1, 1, 1, 10, 25),
        ("High Cable Curl", "isolation", "elbow_flexion", "biceps", "", "cable", 0, 1, 1, 10, 25),
        ("Preacher Curl", "isolation", "elbow_flexion", "biceps_short_head", "brachialis", "barbell", 1, 1, 1, 10, 25),
        ("Concentration Curl", "isolation", "elbow_flexion", "biceps", "", "dumbbell", 0, 1, 1, 10, 25),
        ("Spider Curl", "isolation", "elbow_flexion", "biceps_short_head", "", "dumbbell", 1, 1, 1, 10, 25),
        ("Reverse Curl", "isolation", "elbow_flexion", "brachioradialis,brachialis", "biceps", "barbell", 1, 1, 1, 10, 25),
        ("Bayesian Curl", "isolation", "elbow_flexion", "biceps_long_head", "", "cable", 0, 2, 1, 10, 25),

        # === ISOLATION - CALVES ===
        ("Standing Calf Raise (Machine)", "isolation", "ankle_plantar_flexion", "gastrocnemius", "soleus", "machine", 1, 1, 1, 10, 25),
        ("Seated Calf Raise", "isolation", "ankle_plantar_flexion", "soleus", "gastrocnemius", "machine", 1, 1, 1, 10, 25),
        ("Leg Press Calf Raise", "isolation", "ankle_plantar_flexion", "gastrocnemius,soleus", "", "machine", 1, 1, 1, 10, 25),
        ("Single-Leg Calf Raise", "isolation", "ankle_plantar_flexion", "gastrocnemius,soleus", "", "bodyweight", 0, 1, 1, 10, 25),
        ("Donkey Calf Raise", "isolation", "ankle_plantar_flexion", "gastrocnemius", "soleus", "machine", 1, 1, 1, 10, 25),
        ("Smith Machine Calf Raise", "isolation", "ankle_plantar_flexion", "gastrocnemius,soleus", "", "machine", 1, 1, 1, 10, 25),

        # === CORE / ABS ===
        ("Hanging Leg Raise", "isolation", "spinal_flexion", "rectus_abdominis,hip_flexors", "obliques", "bodyweight", 1, 2, 2, 8, 22),
        ("Hanging Knee Raise", "isolation", "spinal_flexion", "rectus_abdominis,hip_flexors", "obliques", "bodyweight", 1, 1, 2, 8, 22),
        ("Cable Crunch", "isolation", "spinal_flexion", "rectus_abdominis", "obliques", "cable", 1, 1, 1, 10, 25),
        ("Ab Wheel Rollout", "isolation", "anti_extension", "rectus_abdominis,core", "lats,shoulders", "bodyweight", 1, 3, 3, 8, 20),
        ("Pallof Press", "isolation", "anti_rotation", "obliques,core", "", "cable", 0, 1, 1, 10, 25),
        ("Dragon Flag", "isolation", "anti_extension", "rectus_abdominis,core", "", "bodyweight", 1, 4, 3, 6, 16),
        ("Decline Sit-Up", "isolation", "spinal_flexion", "rectus_abdominis", "hip_flexors", "bodyweight", 1, 1, 2, 10, 22),
        ("Weighted Decline Sit-Up", "isolation", "spinal_flexion", "rectus_abdominis", "hip_flexors", "bodyweight", 1, 2, 2, 10, 22),
        ("Plank", "isolation", "anti_extension", "core,rectus_abdominis", "obliques", "bodyweight", 1, 1, 1, 10, 25),
        ("Side Plank", "isolation", "anti_lateral_flexion", "obliques,core", "", "bodyweight", 0, 1, 1, 10, 25),
        ("Copenhagen Plank", "isolation", "anti_lateral_flexion", "obliques,adductors", "core", "bodyweight", 0, 3, 2, 8, 18),
        ("Copenhagen Dip", "isolation", "anti_lateral_flexion", "adductors,obliques", "core", "bodyweight", 0, 3, 2, 8, 18),
        ("Incline Side Bend", "isolation", "lateral_flexion", "obliques", "core", "bodyweight", 0, 1, 1, 10, 25),
        ("Woodchop (Cable)", "isolation", "rotation", "obliques,core", "", "cable", 0, 1, 1, 10, 25),
        ("Dead Bug", "isolation", "anti_extension", "core,rectus_abdominis", "hip_flexors", "bodyweight", 1, 1, 1, 10, 25),
        ("Bird Dog", "isolation", "anti_extension", "core,erectors", "glutes", "bodyweight", 0, 1, 1, 10, 25),
        ("L-Sit Hold", "isolation", "anti_extension", "core,hip_flexors", "rectus_abdominis", "bodyweight", 1, 3, 2, 6, 18),
        ("GHD Sit-Up", "isolation", "spinal_flexion", "rectus_abdominis,hip_flexors", "", "machine", 1, 2, 2, 8, 20),
        ("Suitcase Carry", "compound", "anti_lateral_flexion", "obliques,core,forearms", "traps", "dumbbell", 0, 1, 2, 8, 22),
        ("Farmer Carry", "compound", "loaded_carry", "forearms,traps,core", "erectors", "dumbbell", 1, 1, 2, 8, 22),

        # === TRAPS / UPPER BACK ===
        ("Barbell Shrug", "isolation", "scapular_elevation", "upper_traps", "", "barbell", 1, 1, 1, 10, 25),
        ("Dumbbell Shrug", "isolation", "scapular_elevation", "upper_traps", "", "dumbbell", 1, 1, 1, 10, 25),
        ("Trap Bar Shrug", "isolation", "scapular_elevation", "upper_traps", "", "barbell", 1, 1, 1, 10, 25),
        ("Cable Shrug", "isolation", "scapular_elevation", "upper_traps", "", "cable", 1, 1, 1, 10, 25),
        ("Snatch-Grip High Pull", "compound", "scapular_elevation", "upper_traps,rear_deltoid", "erectors,biceps", "barbell", 1, 4, 4, 6, 16),

        # === FOREARMS / GRIP ===
        ("Wrist Curl (Barbell)", "isolation", "wrist_flexion", "forearm_flexors", "", "barbell", 1, 1, 1, 12, 25),
        ("Reverse Wrist Curl", "isolation", "wrist_extension", "forearm_extensors", "", "barbell", 1, 1, 1, 12, 25),
        ("Plate Pinch Hold", "isolation", "grip", "forearms", "", "other", 1, 1, 1, 8, 25),
        ("Fat Grip Curl", "isolation", "elbow_flexion", "biceps,forearms", "", "dumbbell", 1, 2, 2, 10, 22),
        ("Dead Hang", "isolation", "grip", "forearms,lats", "", "bodyweight", 1, 1, 1, 8, 25),

        # === OLYMPIC LIFTING / POWER ===
        ("Power Clean", "compound", "olympic", "quads,glutes,hamstrings,traps", "erectors,shoulders,core", "barbell", 1, 5, 5, 4, 14),
        ("Hang Clean", "compound", "olympic", "quads,glutes,traps", "hamstrings,core", "barbell", 1, 4, 5, 4, 14),
        ("Clean & Jerk", "compound", "olympic", "quads,glutes,hamstrings,shoulders,traps", "core,triceps", "barbell", 1, 5, 5, 4, 12),
        ("Power Snatch", "compound", "olympic", "quads,glutes,hamstrings,traps,shoulders", "core,erectors", "barbell", 1, 5, 5, 4, 12),
        ("Hang Snatch", "compound", "olympic", "quads,glutes,traps,shoulders", "core", "barbell", 1, 5, 5, 4, 12),
        ("Clean Pull", "compound", "olympic", "hamstrings,glutes,erectors,traps", "quads", "barbell", 1, 4, 4, 4, 16),
        ("Snatch Pull", "compound", "olympic", "hamstrings,glutes,erectors,traps", "quads", "barbell", 1, 4, 4, 4, 16),
        ("Muscle Snatch", "compound", "olympic", "traps,shoulders,triceps", "erectors,core", "barbell", 1, 4, 4, 4, 14),

        # === PLYOMETRICS / POWER ===
        ("Box Jump", "compound", "plyometric", "quads,glutes", "calves,core", "bodyweight", 1, 2, 3, 6, 18),
        ("Depth Jump", "compound", "plyometric", "quads,glutes,calves", "core", "bodyweight", 1, 4, 4, 4, 14),
        ("Kneeling Jump", "compound", "plyometric", "quads,glutes,hip_flexors", "core", "bodyweight", 1, 3, 3, 6, 16),
        ("Broad Jump", "compound", "plyometric", "quads,glutes", "hamstrings,calves", "bodyweight", 1, 2, 3, 6, 18),
        ("Plyo Push-Up", "compound", "plyometric", "chest,triceps", "anterior_deltoid", "bodyweight", 1, 3, 3, 6, 16),
        ("Medicine Ball Slam", "compound", "plyometric", "lats,core,anterior_deltoid", "triceps", "other", 1, 2, 3, 8, 18),
        ("Kettlebell Swing", "compound", "hip_hinge", "glutes,hamstrings", "core,erectors", "kettlebell", 1, 2, 3, 8, 20),
        ("Kettlebell Clean", "compound", "olympic", "glutes,hamstrings,forearms", "core,shoulders", "kettlebell", 0, 3, 3, 6, 18),

        # === BODYWEIGHT ===
        ("Push-Up", "compound", "horizontal_push", "chest,triceps,anterior_deltoid", "core", "bodyweight", 1, 1, 1, 10, 25),
        ("Pike Push-Up", "compound", "vertical_push", "anterior_deltoid,triceps", "upper_chest", "bodyweight", 1, 2, 2, 8, 22),
        ("Handstand Push-Up", "compound", "vertical_push", "anterior_deltoid,triceps", "traps,core", "bodyweight", 1, 4, 4, 4, 14),
        ("Inverted Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps,core", "bodyweight", 1, 1, 2, 8, 22),
        ("Ring Row", "compound", "horizontal_pull", "lats,rhomboids", "biceps,rear_deltoid,core", "bodyweight", 1, 2, 2, 8, 20),
        ("Ring Dip", "compound", "vertical_push", "chest,triceps,anterior_deltoid", "core", "bodyweight", 1, 3, 4, 6, 16),
        ("Muscle-Up", "compound", "vertical_pull", "lats,chest,triceps", "biceps,core", "bodyweight", 1, 5, 5, 4, 12),
        ("Pistol Squat", "compound", "squat", "quads,glutes", "core,hip_flexors", "bodyweight", 0, 3, 3, 6, 16),
        ("Archer Push-Up", "compound", "horizontal_push", "chest,triceps", "anterior_deltoid,core", "bodyweight", 0, 3, 2, 8, 18),
        ("Ring Push-Up", "compound", "horizontal_push", "chest,triceps,anterior_deltoid", "core", "bodyweight", 1, 2, 2, 8, 20),

        # === MACHINE - UPPER ===
        ("Machine Shoulder Press", "compound", "vertical_push", "anterior_deltoid,triceps", "lateral_deltoid", "machine", 1, 1, 2, 6, 22),
        ("Cable Pullover", "isolation", "vertical_pull", "lats", "chest,triceps_long_head", "cable", 1, 1, 1, 8, 24),
        ("Machine Pullover", "isolation", "vertical_pull", "lats", "chest", "machine", 1, 1, 1, 8, 24),
        ("Machine Bicep Curl", "isolation", "elbow_flexion", "biceps", "", "machine", 1, 1, 1, 10, 25),
        ("Machine Tricep Extension", "isolation", "elbow_extension", "triceps", "", "machine", 1, 1, 1, 10, 25),
        ("Machine Rear Delt Fly", "isolation", "horizontal_pull", "rear_deltoid", "rhomboids", "machine", 1, 1, 1, 10, 25),

        # === MOBILITY / PREHAB ===
        ("T-Spine Pull-Over", "isolation", "thoracic_extension", "lats,chest", "core", "dumbbell", 1, 1, 1, 10, 25),
        ("Kneeling T-Spine Rotation", "isolation", "thoracic_rotation", "obliques,core", "erectors", "bodyweight", 0, 1, 1, 10, 25),
        ("Band Dislocate", "isolation", "shoulder_mobility", "rotator_cuff,rear_deltoid", "", "band", 1, 1, 1, 10, 25),
        ("External Rotation (Cable)", "isolation", "shoulder_mobility", "external_rotators", "", "cable", 0, 1, 1, 10, 25),
        ("Internal Rotation (Cable)", "isolation", "shoulder_mobility", "internal_rotators", "", "cable", 0, 1, 1, 10, 25),
        ("Hip 90/90 Stretch", "isolation", "hip_mobility", "hip_flexors,glutes", "", "bodyweight", 0, 1, 1, 10, 25),
        ("Banded Hip Flexor Stretch", "isolation", "hip_mobility", "hip_flexors", "", "band", 0, 1, 1, 10, 25),
        ("Wall Slide", "isolation", "shoulder_mobility", "lower_traps,serratus_anterior", "", "bodyweight", 1, 1, 1, 10, 25),
        ("Cat-Cow", "isolation", "spinal_mobility", "erectors,core", "", "bodyweight", 1, 1, 1, 10, 25),
        ("World's Greatest Stretch", "compound", "hip_mobility", "hip_flexors,hamstrings,core", "shoulders", "bodyweight", 0, 1, 1, 10, 25),

        # === ADDITIONAL COMPOUND / SPECIALTY ===
        ("Landmine Press", "compound", "vertical_push", "anterior_deltoid,upper_chest", "triceps,core", "barbell", 0, 2, 2, 6, 20),
        ("Landmine Row", "compound", "horizontal_pull", "lats,rhomboids", "biceps,rear_deltoid", "barbell", 0, 2, 2, 6, 20),
        ("Landmine Squat", "compound", "squat", "quads,glutes", "core", "barbell", 1, 2, 2, 6, 20),
        ("Dumbbell Pullover", "isolation", "vertical_pull", "lats,chest", "triceps_long_head,serratus_anterior", "dumbbell", 1, 1, 2, 8, 22),
        ("Cable Crossover", "isolation", "horizontal_push", "chest", "anterior_deltoid", "cable", 1, 1, 1, 8, 24),
        ("Hip Adduction Machine", "isolation", "hip_adduction", "adductors", "", "machine", 1, 1, 1, 10, 25),
        ("Leg Press (Single Leg)", "compound", "squat", "quads,glutes", "hamstrings", "machine", 0, 1, 2, 6, 22),
        ("Chest-Supported Dumbbell Row", "compound", "horizontal_pull", "lats,rhomboids,rear_deltoid", "biceps", "dumbbell", 1, 1, 2, 6, 22),
        ("Cable Lateral Raise (Behind)", "isolation", "lateral_raise", "lateral_deltoid", "", "cable", 0, 2, 1, 10, 25),
        ("Prone Y-T-W Raise", "isolation", "scapular_retraction", "lower_traps,rear_deltoid,rhomboids", "", "dumbbell", 1, 1, 1, 10, 25),
        ("Sled Push", "compound", "loaded_carry", "quads,glutes,calves", "core", "other", 1, 2, 3, 8, 18),
        ("Sled Pull", "compound", "loaded_carry", "hamstrings,glutes,calves", "core,lats", "other", 1, 2, 3, 8, 18),

        # === ADDITIONAL EXERCISES TO REACH 250+ ===
        ("Deficit Push-Up", "compound", "horizontal_push", "chest,triceps", "anterior_deltoid", "bodyweight", 1, 2, 2, 8, 22),
        ("Feet-Elevated Push-Up", "compound", "horizontal_push", "upper_chest,triceps", "anterior_deltoid,core", "bodyweight", 1, 2, 2, 8, 22),
        ("Svend Press", "isolation", "horizontal_push", "chest", "anterior_deltoid", "other", 1, 1, 1, 10, 25),
        ("Decline Cable Fly", "isolation", "horizontal_push", "lower_chest", "anterior_deltoid", "cable", 1, 1, 1, 8, 24),
        ("Cable Curl (Single-Arm)", "isolation", "elbow_flexion", "biceps", "", "cable", 0, 1, 1, 10, 25),
        ("Zottman Curl", "isolation", "elbow_flexion", "biceps,brachioradialis", "forearms", "dumbbell", 1, 2, 1, 10, 22),
        ("Overhead Cable Curl", "isolation", "elbow_flexion", "biceps", "", "cable", 1, 1, 1, 10, 25),
        ("Cross-Body Hammer Curl", "isolation", "elbow_flexion", "brachialis,biceps", "", "dumbbell", 0, 1, 1, 10, 25),
        ("Tate Press", "isolation", "elbow_extension", "triceps", "chest", "dumbbell", 1, 2, 2, 8, 22),
        ("Overhead EZ-Bar Extension", "isolation", "elbow_extension", "triceps_long_head", "", "barbell", 1, 2, 2, 8, 22),
        ("Single-Arm Overhead Extension", "isolation", "elbow_extension", "triceps_long_head", "", "dumbbell", 0, 1, 1, 10, 25),
        ("Bench Dip", "compound", "vertical_push", "triceps", "chest,anterior_deltoid", "bodyweight", 1, 1, 2, 8, 22),
        ("Dumbbell Lateral Raise (Seated)", "isolation", "lateral_raise", "lateral_deltoid", "", "dumbbell", 1, 1, 1, 10, 25),
        ("Front Raise (Dumbbell)", "isolation", "shoulder_flexion", "anterior_deltoid", "", "dumbbell", 0, 1, 1, 10, 25),
        ("Front Raise (Cable)", "isolation", "shoulder_flexion", "anterior_deltoid", "", "cable", 0, 1, 1, 10, 25),
        ("Barbell Front Raise", "isolation", "shoulder_flexion", "anterior_deltoid", "", "barbell", 1, 1, 1, 10, 25),
        ("Machine Lateral Raise (Single Arm)", "isolation", "lateral_raise", "lateral_deltoid", "", "machine", 0, 1, 1, 10, 25),
        ("OAC ISO Hold (Top)", "isolation", "vertical_pull", "lats,biceps", "forearms", "bodyweight", 0, 5, 4, 4, 14),
        ("Typewriter Pull-Up", "compound", "vertical_pull", "lats,biceps", "rear_deltoid,core", "bodyweight", 0, 4, 4, 4, 14),
        ("Commando Pull-Up", "compound", "vertical_pull", "lats,biceps", "obliques,core", "bodyweight", 0, 3, 3, 6, 16),
        ("Negative Pull-Up", "compound", "vertical_pull", "lats,biceps", "rhomboids", "bodyweight", 1, 2, 3, 6, 20),
        ("Chest-to-Bar Pull-Up", "compound", "vertical_pull", "lats,biceps,rhomboids", "rear_deltoid", "bodyweight", 1, 3, 4, 6, 16),
        ("Supinated Barbell Row", "compound", "horizontal_pull", "lats,biceps,rhomboids", "rear_deltoid", "barbell", 1, 2, 3, 6, 20),
        ("Single-Arm Dumbbell Row", "compound", "horizontal_pull", "lats,rhomboids", "biceps,rear_deltoid", "dumbbell", 0, 1, 2, 6, 22),
        ("Pause Squat (Front)", "compound", "squat", "quads,core", "glutes", "barbell", 1, 3, 5, 6, 16),
        ("Hatfield Squat", "compound", "squat", "quads,glutes", "hamstrings", "barbell", 1, 2, 3, 6, 20),
        ("Chain Squat", "compound", "squat", "quads,glutes", "hamstrings,core", "barbell", 1, 3, 4, 6, 18),
        ("Band Squat", "compound", "squat", "quads,glutes", "hamstrings,core", "barbell", 1, 3, 4, 6, 18),
        ("Sumo Squat", "compound", "squat", "quads,glutes,adductors", "hamstrings", "barbell", 1, 2, 3, 6, 20),
        ("Hip Belt Squat", "compound", "squat", "quads,glutes", "core", "machine", 1, 1, 2, 6, 22),
        ("Jefferson Deadlift", "compound", "hip_hinge", "quads,glutes,hamstrings", "core,erectors", "barbell", 0, 4, 4, 4, 14),
        ("Reeves Deadlift", "compound", "hip_hinge", "hamstrings,glutes,forearms", "erectors,traps", "barbell", 1, 5, 4, 4, 12),
        ("Touch-and-Go Deadlift", "compound", "hip_hinge", "hamstrings,glutes,erectors", "quads,lats", "barbell", 1, 2, 4, 6, 18),
        ("Single-Leg Leg Press", "compound", "squat", "quads,glutes", "hamstrings", "machine", 0, 1, 2, 6, 22),
        ("Walking Lunge (Dumbbell)", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 1, 3, 6, 20),
        ("Curtsy Lunge", "compound", "lunge", "quads,glutes,adductors", "core", "dumbbell", 0, 2, 3, 6, 18),
        ("Reverse Lunge (Dumbbell)", "compound", "lunge", "quads,glutes", "hamstrings,core", "dumbbell", 0, 1, 3, 6, 20),
    ]

    db.executemany("""
        INSERT OR IGNORE INTO exercises (name, category, movement_pattern, primary_muscles, secondary_muscles,
        equipment, bilateral, complexity, fatigue_rating, mev_sets_per_week, mrv_sets_per_week)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, exercises)
    db.commit()


# =============================================
# CALCULATION ENGINE
# =============================================

def estimate_1rm(weight, reps, rpe=10):
    """
    Estimate 1RM using Epley formula with RPE adjustment.
    Uses the Tuchscherer RPE-to-percentage table for accurate mapping.
    """
    if reps <= 0 or weight <= 0:
        return 0

    # RPE to RIR conversion
    rir = 10 - rpe if rpe else 0

    # Effective reps = actual reps + reps in reserve
    effective_reps = reps + rir

    if effective_reps <= 1:
        return weight

    # Epley formula: 1RM = weight * (1 + reps/30)
    e1rm = weight * (1 + effective_reps / 30.0)

    return round(e1rm, 1)


def rpe_to_percentage(rpe, reps):
    """
    Tuchscherer RPE chart - maps RPE and rep count to %1RM.
    Based on NSCA and RTS standards.
    """
    chart = {
        10:  {1: 100, 2: 95.5, 3: 92.2, 4: 89.2, 5: 86.3, 6: 83.7, 7: 81.1, 8: 78.6, 9: 76.2, 10: 73.9, 12: 69.4},
        9.5: {1: 97.8, 2: 93.9, 3: 90.7, 4: 87.8, 5: 85.0, 6: 82.4, 7: 79.9, 8: 77.4, 9: 75.1, 10: 72.3, 12: 68.0},
        9:   {1: 95.5, 2: 92.2, 3: 89.2, 4: 86.3, 5: 83.7, 6: 81.1, 7: 78.6, 8: 76.2, 9: 73.9, 10: 71.0, 12: 66.7},
        8.5: {1: 93.9, 2: 90.7, 3: 87.8, 4: 85.0, 5: 82.4, 6: 79.9, 7: 77.4, 8: 75.1, 9: 72.3, 10: 69.4, 12: 65.3},
        8:   {1: 92.2, 2: 89.2, 3: 86.3, 4: 83.7, 5: 81.1, 6: 78.6, 7: 76.2, 8: 73.9, 9: 71.0, 10: 68.0, 12: 64.0},
        7.5: {1: 90.7, 2: 87.8, 3: 85.0, 4: 82.4, 5: 79.9, 6: 77.4, 7: 75.1, 8: 72.3, 9: 69.4, 10: 66.7, 12: 62.6},
        7:   {1: 89.2, 2: 86.3, 3: 83.7, 4: 81.1, 5: 78.6, 6: 76.2, 7: 73.9, 8: 71.0, 9: 68.0, 10: 65.3, 12: 61.3},
        6.5: {1: 87.8, 2: 85.0, 3: 82.4, 4: 79.9, 5: 77.4, 6: 75.1, 7: 72.3, 8: 69.4, 9: 66.7, 10: 64.0, 12: 60.0},
        6:   {1: 86.3, 2: 83.7, 3: 81.1, 4: 78.6, 5: 76.2, 6: 73.9, 7: 71.0, 8: 68.0, 9: 65.3, 10: 62.6, 12: 58.8},
    }

    rpe_key = max(6, min(10, round(rpe * 2) / 2))
    rep_key = min(12, max(1, reps))

    if rpe_key in chart and rep_key in chart[rpe_key]:
        return chart[rpe_key][rep_key]
    return 75.0


def calculate_training_weight(e1rm, rpe, reps):
    """Calculate recommended training weight from e1RM, target RPE, and rep count."""
    pct = rpe_to_percentage(rpe, reps) / 100.0
    return round(e1rm * pct, 1)


def calculate_volume_load(sets_data):
    """Calculate total volume load (sets × reps × weight) from set logs."""
    total = 0
    for s in sets_data:
        w = s.get('weight', 0) or 0
        r = s.get('reps', 0) or 0
        total += w * r
    return round(total, 1)


def calculate_e1rm_trend(db, athlete_id, exercise_id, days=90):
    """Get e1RM trend over time for an exercise."""
    rows = db.execute("""
        SELECT estimated_1rm, date FROM one_rep_maxes
        WHERE athlete_id = ? AND exercise_id = ?
        AND date >= date('now', ?)
        ORDER BY date ASC
    """, [athlete_id, exercise_id, f'-{days} days']).fetchall()
    return [{"e1rm": r["estimated_1rm"], "date": r["date"]} for r in rows]


def get_progressive_overload_recommendation(db, athlete_id, exercise_id):
    """
    Analyze recent performance and recommend progressive overload strategy.
    Returns recommendation dict with suggested weight, reps, and rationale.
    """
    # Get last 4 workout instances of this exercise
    recent = db.execute("""
        SELECT sl.weight, sl.reps, sl.rpe, sl.set_type, wl.date
        FROM set_logs sl
        JOIN workout_logs wl ON sl.workout_log_id = wl.id
        WHERE wl.athlete_id = ? AND sl.exercise_id = ? AND sl.set_type = 'working'
        ORDER BY wl.date DESC, sl.set_number DESC
        LIMIT 20
    """, [athlete_id, exercise_id]).fetchall()

    if len(recent) < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 logged sessions"}

    # Group by date
    sessions = {}
    for r in recent:
        d = r["date"]
        if d not in sessions:
            sessions[d] = []
        sessions[d].append(dict(r))

    dates = sorted(sessions.keys(), reverse=True)
    last_session = sessions[dates[0]]
    prev_session = sessions[dates[1]] if len(dates) > 1 else []

    # Calculate averages
    last_avg_weight = sum(s["weight"] for s in last_session if s["weight"]) / max(1, len(last_session))
    last_avg_reps = sum(s["reps"] for s in last_session if s["reps"]) / max(1, len(last_session))
    last_avg_rpe = sum(s["rpe"] for s in last_session if s["rpe"]) / max(1, len([s for s in last_session if s["rpe"]]))

    # Get current e1RM
    e1rm_row = db.execute("""
        SELECT estimated_1rm FROM one_rep_maxes
        WHERE athlete_id = ? AND exercise_id = ?
        ORDER BY date DESC LIMIT 1
    """, [athlete_id, exercise_id]).fetchone()

    current_e1rm = e1rm_row["estimated_1rm"] if e1rm_row else estimate_1rm(last_avg_weight, last_avg_reps, last_avg_rpe)

    recommendation = {
        "current_e1rm": current_e1rm,
        "last_session": {
            "avg_weight": round(last_avg_weight, 1),
            "avg_reps": round(last_avg_reps, 1),
            "avg_rpe": round(last_avg_rpe, 1)
        }
    }

    if last_avg_rpe < 7:
        # Under-recovered or too light - bump weight
        new_weight = round(last_avg_weight * 1.05, 1)
        recommendation["action"] = "increase_load"
        recommendation["suggested_weight"] = new_weight
        recommendation["suggested_reps"] = round(last_avg_reps)
        recommendation["rationale"] = f"RPE {last_avg_rpe} indicates capacity for heavier loading. Increase by ~5%."
    elif last_avg_rpe < 8.5:
        # Sweet spot - small increment
        new_weight = round(last_avg_weight * 1.025, 1)
        recommendation["action"] = "micro_load"
        recommendation["suggested_weight"] = new_weight
        recommendation["suggested_reps"] = round(last_avg_reps)
        recommendation["rationale"] = f"RPE {last_avg_rpe} is in productive range. Micro-load 2.5% for sustained progression."
    elif last_avg_rpe >= 9.5:
        # Near maximal - increase reps or deload
        recommendation["action"] = "add_reps_or_deload"
        recommendation["suggested_weight"] = round(last_avg_weight, 1)
        recommendation["suggested_reps"] = round(last_avg_reps) + 1
        recommendation["rationale"] = f"RPE {last_avg_rpe} is near-maximal. Add 1 rep at same weight or consider deload."
    else:
        # RPE 8.5-9.5 - standard progression
        new_weight = round(last_avg_weight + 2.5, 1)
        recommendation["action"] = "standard_progression"
        recommendation["suggested_weight"] = new_weight
        recommendation["suggested_reps"] = round(last_avg_reps)
        recommendation["rationale"] = f"RPE {last_avg_rpe} supports linear load increase. Add 2.5 lbs/1.25 kg."

    return recommendation


def generate_phase_config(goal, phase, experience, weeks=4):
    """
    Generate phase-specific programming parameters based on NSCA guidelines.
    Returns intensity, volume, and rep ranges for the given phase/goal.
    """
    configs = {
        "strength": {
            "accumulation": {
                "compound_sets": (3, 5), "compound_reps": (5, 8), "compound_rpe": (7, 8),
                "isolation_sets": (2, 4), "isolation_reps": (8, 12), "isolation_rpe": (7, 8.5),
                "rest_compound": 180, "rest_isolation": 90,
                "volume_progression": "linear", "intensity_start_pct": 70, "intensity_end_pct": 80
            },
            "intensification": {
                "compound_sets": (4, 6), "compound_reps": (2, 5), "compound_rpe": (8, 9.5),
                "isolation_sets": (2, 3), "isolation_reps": (6, 10), "isolation_rpe": (8, 9),
                "rest_compound": 240, "rest_isolation": 120,
                "volume_progression": "undulating", "intensity_start_pct": 80, "intensity_end_pct": 92
            },
            "realization": {
                "compound_sets": (3, 5), "compound_reps": (1, 3), "compound_rpe": (9, 10),
                "isolation_sets": (1, 2), "isolation_reps": (6, 8), "isolation_rpe": (7, 8),
                "rest_compound": 300, "rest_isolation": 120,
                "volume_progression": "taper", "intensity_start_pct": 90, "intensity_end_pct": 100
            },
            "deload": {
                "compound_sets": (2, 3), "compound_reps": (3, 5), "compound_rpe": (6, 7),
                "isolation_sets": (1, 2), "isolation_reps": (8, 10), "isolation_rpe": (6, 7),
                "rest_compound": 120, "rest_isolation": 60,
                "volume_progression": "reduced", "intensity_start_pct": 60, "intensity_end_pct": 70
            }
        },
        "hypertrophy": {
            "accumulation": {
                "compound_sets": (3, 4), "compound_reps": (8, 12), "compound_rpe": (7, 8.5),
                "isolation_sets": (3, 4), "isolation_reps": (10, 15), "isolation_rpe": (7, 9),
                "rest_compound": 120, "rest_isolation": 60,
                "volume_progression": "linear", "intensity_start_pct": 62, "intensity_end_pct": 72
            },
            "intensification": {
                "compound_sets": (3, 5), "compound_reps": (6, 10), "compound_rpe": (8, 9),
                "isolation_sets": (2, 4), "isolation_reps": (8, 12), "isolation_rpe": (8, 9.5),
                "rest_compound": 150, "rest_isolation": 75,
                "volume_progression": "step", "intensity_start_pct": 70, "intensity_end_pct": 82
            },
            "realization": {
                "compound_sets": (3, 4), "compound_reps": (4, 8), "compound_rpe": (8.5, 9.5),
                "isolation_sets": (2, 3), "isolation_reps": (6, 10), "isolation_rpe": (8, 9),
                "rest_compound": 180, "rest_isolation": 90,
                "volume_progression": "taper", "intensity_start_pct": 78, "intensity_end_pct": 88
            },
            "deload": {
                "compound_sets": (2, 3), "compound_reps": (8, 10), "compound_rpe": (5, 7),
                "isolation_sets": (1, 2), "isolation_reps": (10, 12), "isolation_rpe": (5, 7),
                "rest_compound": 90, "rest_isolation": 60,
                "volume_progression": "reduced", "intensity_start_pct": 55, "intensity_end_pct": 65
            }
        },
        "power": {
            "accumulation": {
                "compound_sets": (3, 5), "compound_reps": (3, 6), "compound_rpe": (7, 8),
                "isolation_sets": (2, 3), "isolation_reps": (6, 10), "isolation_rpe": (7, 8),
                "rest_compound": 180, "rest_isolation": 90,
                "volume_progression": "linear", "intensity_start_pct": 65, "intensity_end_pct": 78
            },
            "intensification": {
                "compound_sets": (4, 6), "compound_reps": (1, 3), "compound_rpe": (8, 9.5),
                "isolation_sets": (2, 3), "isolation_reps": (3, 6), "isolation_rpe": (8, 9),
                "rest_compound": 300, "rest_isolation": 150,
                "volume_progression": "undulating", "intensity_start_pct": 82, "intensity_end_pct": 95
            },
            "realization": {
                "compound_sets": (3, 5), "compound_reps": (1, 2), "compound_rpe": (9, 10),
                "isolation_sets": (1, 2), "isolation_reps": (3, 5), "isolation_rpe": (7, 8),
                "rest_compound": 360, "rest_isolation": 180,
                "volume_progression": "taper", "intensity_start_pct": 92, "intensity_end_pct": 100
            },
            "deload": {
                "compound_sets": (2, 3), "compound_reps": (2, 3), "compound_rpe": (6, 7),
                "isolation_sets": (1, 2), "isolation_reps": (6, 8), "isolation_rpe": (6, 7),
                "rest_compound": 120, "rest_isolation": 60,
                "volume_progression": "reduced", "intensity_start_pct": 55, "intensity_end_pct": 65
            }
        },
        "endurance": {
            "accumulation": {
                "compound_sets": (2, 3), "compound_reps": (12, 20), "compound_rpe": (6, 8),
                "isolation_sets": (2, 3), "isolation_reps": (15, 25), "isolation_rpe": (6, 8),
                "rest_compound": 60, "rest_isolation": 45,
                "volume_progression": "linear", "intensity_start_pct": 45, "intensity_end_pct": 60
            },
            "intensification": {
                "compound_sets": (3, 4), "compound_reps": (10, 15), "compound_rpe": (7, 9),
                "isolation_sets": (2, 3), "isolation_reps": (12, 20), "isolation_rpe": (7, 9),
                "rest_compound": 45, "rest_isolation": 30,
                "volume_progression": "step", "intensity_start_pct": 55, "intensity_end_pct": 68
            },
            "realization": {
                "compound_sets": (2, 3), "compound_reps": (8, 12), "compound_rpe": (8, 9),
                "isolation_sets": (2, 3), "isolation_reps": (10, 15), "isolation_rpe": (8, 9),
                "rest_compound": 60, "rest_isolation": 45,
                "volume_progression": "taper", "intensity_start_pct": 62, "intensity_end_pct": 72
            },
            "deload": {
                "compound_sets": (1, 2), "compound_reps": (10, 15), "compound_rpe": (5, 6),
                "isolation_sets": (1, 2), "isolation_reps": (12, 15), "isolation_rpe": (5, 6),
                "rest_compound": 60, "rest_isolation": 45,
                "volume_progression": "reduced", "intensity_start_pct": 40, "intensity_end_pct": 50
            }
        }
    }

    goal_key = goal if goal in configs else "strength"
    phase_key = phase if phase in configs[goal_key] else "accumulation"
    return configs[goal_key][phase_key]


# =============================================
# REQUEST ROUTER
# =============================================

def handle_request():
    db = init_db()
    seed_exercises(db)

    method = os.environ.get("REQUEST_METHOD", "GET")
    query_string = os.environ.get("QUERY_STRING", "")
    params = parse_qs(query_string)

    # Get the action parameter
    action = params.get("action", [""])[0]

    # Read body for POST/PUT
    body = {}
    if method in ("POST", "PUT", "PATCH"):
        content_length = int(os.environ.get("CONTENT_LENGTH", 0))
        if content_length > 0:
            raw = sys.stdin.read(content_length)
            try:
                body = json.loads(raw)
            except:
                body = {}

    try:
        if action == "get_exercises":
            return get_exercises(db, params)
        elif action == "get_exercise":
            return get_exercise(db, params)
        elif action == "search_exercises":
            return search_exercises(db, params)
        elif action == "get_athlete":
            return get_athlete(db, params)
        elif action == "save_athlete":
            return save_athlete(db, body)
        elif action == "get_programs":
            return get_programs(db, params)
        elif action == "get_program":
            return get_program_detail(db, params)
        elif action == "generate_program":
            return generate_program(db, body)
        elif action == "save_workout":
            return save_workout(db, body)
        elif action == "get_workouts":
            return get_workouts(db, params)
        elif action == "get_workout_detail":
            return get_workout_detail(db, params)
        elif action == "get_e1rm":
            return get_e1rm(db, params)
        elif action == "get_overload_rec":
            return get_overload_rec(db, params)
        elif action == "get_analytics":
            return get_analytics(db, params)
        elif action == "get_volume_landmarks":
            return get_volume_landmarks(db, params)
        elif action == "save_volume_landmarks":
            return save_volume_landmarks(db, body)
        elif action == "get_phase_config":
            return get_phase_config(db, params)
        elif action == "delete_workout":
            return delete_workout(db, params)
        elif action == "get_dashboard":
            return get_dashboard(db, params)
        elif action == "get_movement_patterns":
            return get_movement_patterns(db)
        elif action == "get_muscle_groups":
            return get_muscle_groups(db)
        else:
            return json_response({"error": "Unknown action", "available_actions": [
                "get_exercises", "get_exercise", "search_exercises",
                "get_athlete", "save_athlete",
                "get_programs", "get_program", "generate_program",
                "save_workout", "get_workouts", "get_workout_detail", "delete_workout",
                "get_e1rm", "get_overload_rec", "get_analytics",
                "get_volume_landmarks", "save_volume_landmarks",
                "get_phase_config", "get_dashboard",
                "get_movement_patterns", "get_muscle_groups"
            ]}, 400)
    except Exception as e:
        return json_response({"error": str(e)}, 500)
    finally:
        db.close()


# =============================================
# API HANDLERS
# =============================================

def get_exercises(db, params):
    pattern = params.get("pattern", [""])[0]
    category = params.get("category", [""])[0]
    equipment = params.get("equipment", [""])[0]
    muscle = params.get("muscle", [""])[0]

    query = "SELECT * FROM exercises WHERE 1=1"
    args = []

    if pattern:
        query += " AND movement_pattern = ?"
        args.append(pattern)
    if category:
        query += " AND category = ?"
        args.append(category)
    if equipment:
        query += " AND equipment = ?"
        args.append(equipment)
    if muscle:
        query += " AND (primary_muscles LIKE ? OR secondary_muscles LIKE ?)"
        args.extend([f"%{muscle}%", f"%{muscle}%"])

    query += " ORDER BY name"
    rows = db.execute(query, args).fetchall()
    return json_response([dict(r) for r in rows])


def get_exercise(db, params):
    eid = params.get("id", [""])[0]
    if not eid:
        return json_response({"error": "id required"}, 400)
    row = db.execute("SELECT * FROM exercises WHERE id = ?", [eid]).fetchone()
    if not row:
        return json_response({"error": "not found"}, 404)
    return json_response(dict(row))


def search_exercises(db, params):
    q = params.get("q", [""])[0]
    if not q:
        return json_response([])
    rows = db.execute("""
        SELECT * FROM exercises
        WHERE name LIKE ? OR primary_muscles LIKE ? OR movement_pattern LIKE ? OR equipment LIKE ?
        ORDER BY name LIMIT 50
    """, [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]).fetchall()
    return json_response([dict(r) for r in rows])


def get_athlete(db, params):
    aid = params.get("id", ["1"])[0]
    row = db.execute("SELECT * FROM athletes WHERE id = ?", [aid]).fetchone()
    if not row:
        return json_response({"id": None})
    return json_response(dict(row))


def save_athlete(db, body):
    existing = db.execute("SELECT id FROM athletes WHERE id = ?", [body.get("id", 1)]).fetchone()
    if existing:
        db.execute("""
            UPDATE athletes SET name=?, age=?, body_weight=?, body_fat_pct=?,
            training_age=?, experience_level=?, primary_goal=?,
            training_days_per_week=?, session_duration_min=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, [body.get("name"), body.get("age"), body.get("body_weight"),
              body.get("body_fat_pct"), body.get("training_age"),
              body.get("experience_level", "intermediate"),
              body.get("primary_goal", "strength"),
              body.get("training_days_per_week", 4),
              body.get("session_duration_min", 75),
              existing["id"]])
        db.commit()
        return json_response({"id": existing["id"], "status": "updated"})
    else:
        cur = db.execute("""
            INSERT INTO athletes (name, age, body_weight, body_fat_pct, training_age,
            experience_level, primary_goal, training_days_per_week, session_duration_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [body.get("name", "Athlete"), body.get("age"), body.get("body_weight"),
              body.get("body_fat_pct"), body.get("training_age", 0),
              body.get("experience_level", "intermediate"),
              body.get("primary_goal", "strength"),
              body.get("training_days_per_week", 4),
              body.get("session_duration_min", 75)])
        db.commit()
        return json_response({"id": cur.lastrowid, "status": "created"}, 201)


def get_programs(db, params):
    aid = params.get("athlete_id", ["1"])[0]
    rows = db.execute("""
        SELECT * FROM programs WHERE athlete_id = ? ORDER BY created_at DESC
    """, [aid]).fetchall()
    return json_response([dict(r) for r in rows])


def get_program_detail(db, params):
    pid = params.get("id", [""])[0]
    if not pid:
        return json_response({"error": "id required"}, 400)

    program = db.execute("SELECT * FROM programs WHERE id = ?", [pid]).fetchone()
    if not program:
        return json_response({"error": "not found"}, 404)

    sessions = db.execute("""
        SELECT * FROM program_sessions WHERE program_id = ? ORDER BY day_number, session_order
    """, [pid]).fetchall()

    result = dict(program)
    result["sessions"] = []
    for sess in sessions:
        s = dict(sess)
        exercises = db.execute("""
            SELECT pe.*, e.name as exercise_name, e.movement_pattern, e.category,
                   e.primary_muscles, e.equipment
            FROM program_exercises pe
            JOIN exercises e ON pe.exercise_id = e.id
            WHERE pe.session_id = ?
            ORDER BY pe.exercise_order
        """, [sess["id"]]).fetchall()
        s["exercises"] = [dict(ex) for ex in exercises]
        result["sessions"].append(s)

    return json_response(result)


def generate_program(db, body):
    """Generate a periodized program based on athlete profile and goals."""
    athlete_id = body.get("athlete_id", 1)
    goal = body.get("goal", "strength")
    phase = body.get("phase", "accumulation")
    split = body.get("split", "upper_lower")
    weeks = body.get("weeks", 4)
    days_per_week = body.get("days_per_week", 4)
    program_name = body.get("name", f"{goal.title()} - {phase.title()} Block")

    athlete = db.execute("SELECT * FROM athletes WHERE id = ?", [athlete_id]).fetchone()
    experience = athlete["experience_level"] if athlete else "intermediate"
    config = generate_phase_config(goal, phase, experience, weeks)

    # Create program
    cur = db.execute("""
        INSERT INTO programs (athlete_id, name, phase, goal, mesocycle_weeks, config)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [athlete_id, program_name, phase, goal, weeks, json.dumps(config)])
    program_id = cur.lastrowid

    if split == "upper_lower":
        _generate_upper_lower(db, program_id, config, goal, days_per_week)
    elif split == "push_pull_legs":
        _generate_ppl(db, program_id, config, goal, days_per_week)
    elif split == "full_body":
        _generate_full_body(db, program_id, config, goal, days_per_week)

    db.commit()

    return json_response({"id": program_id, "name": program_name, "status": "generated"}, 201)


def _generate_upper_lower(db, program_id, config, goal, days):
    """Generate upper/lower split program."""
    sessions = []
    if days >= 4:
        sessions = [
            (1, "Upper A - Strength Focus", "upper_strength"),
            (2, "Lower A - Strength Focus", "lower_strength"),
            (3, "Upper B - Volume Focus", "upper_volume"),
            (4, "Lower B - Volume Focus", "lower_volume")
        ]
    elif days == 3:
        sessions = [
            (1, "Upper A", "upper_strength"),
            (2, "Lower A", "lower_strength"),
            (3, "Full Body B", "full_body")
        ]
    else:
        sessions = [
            (1, "Upper", "upper_strength"),
            (2, "Lower", "lower_strength")
        ]

    for day_num, name, focus in sessions:
        cur = db.execute("""
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
        """, [program_id, day_num, name, focus])
        session_id = cur.lastrowid
        _populate_session(db, session_id, focus, config, goal)


def _generate_ppl(db, program_id, config, goal, days):
    """Generate push/pull/legs split."""
    sessions = [
        (1, "Push", "push"),
        (2, "Pull", "pull"),
        (3, "Legs", "legs")
    ]
    if days >= 6:
        sessions.extend([
            (4, "Push B", "push_volume"),
            (5, "Pull B", "pull_volume"),
            (6, "Legs B", "legs_volume")
        ])

    for day_num, name, focus in sessions:
        cur = db.execute("""
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
        """, [program_id, day_num, name, focus])
        session_id = cur.lastrowid
        _populate_session(db, session_id, focus, config, goal)


def _generate_full_body(db, program_id, config, goal, days):
    """Generate full body split."""
    for d in range(1, min(days + 1, 5)):
        focus = "full_body" if d % 2 == 1 else "full_body_b"
        cur = db.execute("""
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
        """, [program_id, d, f"Full Body Day {d}", focus])
        session_id = cur.lastrowid
        _populate_session(db, session_id, focus, config, goal)


def _populate_session(db, session_id, focus, config, goal):
    """Populate a session with exercises from the taxonomy based on focus."""
    c_sets = config["compound_sets"]
    c_reps = config["compound_reps"]
    c_rpe = config["compound_rpe"]
    i_sets = config["isolation_sets"]
    i_reps = config["isolation_reps"]
    i_rpe = config["isolation_rpe"]

    order = 1

    if focus in ("upper_strength", "push"):
        # Main compound push
        _add_exercise_by_pattern(db, session_id, "horizontal_push", "compound", "barbell",
                                 c_sets[1], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
                                 config["rest_compound"], order, "A"); order += 1
        # Secondary push
        _add_exercise_by_pattern(db, session_id, "vertical_push", "compound", None,
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Horizontal pull (superset)
        _add_exercise_by_pattern(db, session_id, "horizontal_pull", "compound", None,
                                 c_sets[0], f"{c_reps[0]+1}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Triceps isolation
        _add_exercise_by_pattern(db, session_id, "elbow_extension", "isolation", None,
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
                                 config["rest_isolation"], order, "C"); order += 1
        # Lateral raise (superset)
        _add_exercise_by_pattern(db, session_id, "lateral_raise", "isolation", None,
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
                                 config["rest_isolation"], order, "C"); order += 1

    elif focus in ("lower_strength", "legs"):
        # Main squat
        _add_exercise_by_pattern(db, session_id, "squat", "compound", "barbell",
                                 c_sets[1], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
                                 config["rest_compound"], order, "A"); order += 1
        # Hip hinge
        _add_exercise_by_pattern(db, session_id, "hip_hinge", "compound", "barbell",
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Unilateral
        _add_exercise_by_pattern(db, session_id, "lunge", "compound", None,
                                 c_sets[0], f"{c_reps[0]+1}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "C"); order += 1
        # Leg curl
        _add_exercise_by_pattern(db, session_id, "knee_flexion", "isolation", None,
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
                                 config["rest_isolation"], order, "D"); order += 1
        # Calf raise
        _add_exercise_by_pattern(db, session_id, "ankle_plantar_flexion", "isolation", None,
                                 i_sets[0], f"{i_reps[0]}-{i_reps[1]+3}", "rir", "1",
                                 config["rest_isolation"], order, "D"); order += 1

    elif focus in ("upper_volume", "push_volume"):
        # Incline press
        _add_exercise_by_pattern(db, session_id, "horizontal_push", "compound", "dumbbell",
                                 c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "A"); order += 1
        # Vertical pull
        _add_exercise_by_pattern(db, session_id, "vertical_pull", "compound", None,
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Cable fly (superset)
        _add_exercise_by_pattern(db, session_id, "horizontal_push", "isolation", "cable",
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
                                 config["rest_isolation"], order, "C"); order += 1
        # Biceps
        _add_exercise_by_pattern(db, session_id, "elbow_flexion", "isolation", None,
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
                                 config["rest_isolation"], order, "C"); order += 1
        # Rear delt
        _add_exercise_by_pattern(db, session_id, "horizontal_pull", "isolation", None,
                                 i_sets[0], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
                                 config["rest_isolation"], order, "D"); order += 1

    elif focus in ("lower_volume", "legs_volume"):
        # Front squat or hack squat
        _add_exercise_by_pattern(db, session_id, "squat", "compound", "machine",
                                 c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "A"); order += 1
        # RDL
        _add_exercise_by_pattern(db, session_id, "hip_hinge", "compound", "dumbbell",
                                 c_sets[0], f"{c_reps[0]+1}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Hip extension
        _add_exercise_by_pattern(db, session_id, "hip_extension", "compound", None,
                                 c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "C"); order += 1
        # Leg extension
        _add_exercise_by_pattern(db, session_id, "knee_extension", "isolation", None,
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
                                 config["rest_isolation"], order, "D"); order += 1
        # Calf
        _add_exercise_by_pattern(db, session_id, "ankle_plantar_flexion", "isolation", None,
                                 i_sets[0], f"{i_reps[0]}-{i_reps[1]+3}", "rir", "1",
                                 config["rest_isolation"], order, "D"); order += 1

    elif focus in ("pull", "pull_volume"):
        # Heavy row
        _add_exercise_by_pattern(db, session_id, "horizontal_pull", "compound", "barbell",
                                 c_sets[1], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
                                 config["rest_compound"], order, "A"); order += 1
        # Vertical pull
        _add_exercise_by_pattern(db, session_id, "vertical_pull", "compound", None,
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Cable row
        _add_exercise_by_pattern(db, session_id, "horizontal_pull", "compound", "cable",
                                 c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "C"); order += 1
        # Biceps
        _add_exercise_by_pattern(db, session_id, "elbow_flexion", "isolation", None,
                                 i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
                                 config["rest_isolation"], order, "D"); order += 1
        # Rear delt
        _add_exercise_by_pattern(db, session_id, "horizontal_pull", "isolation", None,
                                 i_sets[0], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
                                 config["rest_isolation"], order, "D"); order += 1

    elif focus in ("full_body", "full_body_b"):
        # Squat
        _add_exercise_by_pattern(db, session_id, "squat", "compound", "barbell",
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
                                 config["rest_compound"], order, "A"); order += 1
        # Press
        _add_exercise_by_pattern(db, session_id, "horizontal_push", "compound", None,
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Pull
        _add_exercise_by_pattern(db, session_id, "vertical_pull", "compound", None,
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "B"); order += 1
        # Hinge
        _add_exercise_by_pattern(db, session_id, "hip_hinge", "compound", None,
                                 c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
                                 config["rest_compound"], order, "C"); order += 1


def _add_exercise_by_pattern(db, session_id, pattern, category, equipment, sets, reps, intensity_type, intensity_value, rest, order, superset_group):
    """Find a matching exercise and add it to the session."""
    query = "SELECT id FROM exercises WHERE movement_pattern = ? AND category = ?"
    args = [pattern, category]
    if equipment:
        query += " AND equipment = ?"
        args.append(equipment)
    query += " ORDER BY RANDOM() LIMIT 1"

    row = db.execute(query, args).fetchone()
    if not row:
        # Fallback without equipment filter
        row = db.execute("SELECT id FROM exercises WHERE movement_pattern = ? ORDER BY RANDOM() LIMIT 1", [pattern]).fetchone()

    if row:
        db.execute("""
            INSERT INTO program_exercises (session_id, exercise_id, exercise_order, superset_group,
            sets_prescribed, reps_prescribed, intensity_type, intensity_value, rest_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [session_id, row["id"], order, superset_group, sets, reps, intensity_type, intensity_value, rest])


def save_workout(db, body):
    """Save a complete workout log with all sets."""
    athlete_id = body.get("athlete_id", 1)
    program_id = body.get("program_id")
    session_id = body.get("session_id")
    date = body.get("date", datetime.now().strftime("%Y-%m-%d"))
    duration = body.get("duration_min")
    notes = body.get("notes", "")
    session_rpe = body.get("session_rpe")
    body_weight = body.get("body_weight")
    sets = body.get("sets", [])

    cur = db.execute("""
        INSERT INTO workout_logs (athlete_id, program_id, session_id, date, duration_min, notes, session_rpe, body_weight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [athlete_id, program_id, session_id, date, duration, notes, session_rpe, body_weight])
    workout_id = cur.lastrowid

    for s in sets:
        db.execute("""
            INSERT INTO set_logs (workout_log_id, exercise_id, set_number, set_type,
            weight, reps, rpe, rir, tempo, rest_seconds, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [workout_id, s["exercise_id"], s.get("set_number", 1), s.get("set_type", "working"),
              s.get("weight"), s.get("reps"), s.get("rpe"), s.get("rir"),
              s.get("tempo", ""), s.get("rest_seconds"), s.get("notes", "")])

        # Auto-calculate and store e1RM for working sets
        if s.get("weight") and s.get("reps") and s.get("set_type", "working") == "working":
            rpe = s.get("rpe", 10)
            e1rm = estimate_1rm(s["weight"], s["reps"], rpe)
            if e1rm > 0:
                db.execute("""
                    INSERT INTO one_rep_maxes (athlete_id, exercise_id, estimated_1rm, method,
                    source_weight, source_reps, source_rpe, date)
                    VALUES (?, ?, ?, 'epley', ?, ?, ?, ?)
                """, [athlete_id, s["exercise_id"], e1rm, s["weight"], s["reps"], rpe, date])

    db.commit()
    return json_response({"id": workout_id, "status": "saved", "sets_logged": len(sets)}, 201)


def get_workouts(db, params):
    aid = params.get("athlete_id", ["1"])[0]
    limit = int(params.get("limit", ["20"])[0])
    offset = int(params.get("offset", ["0"])[0])

    rows = db.execute("""
        SELECT wl.*, COUNT(sl.id) as total_sets,
               SUM(CASE WHEN sl.set_type = 'working' THEN 1 ELSE 0 END) as working_sets,
               ROUND(SUM(sl.weight * sl.reps), 1) as total_volume
        FROM workout_logs wl
        LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id
        WHERE wl.athlete_id = ?
        GROUP BY wl.id
        ORDER BY wl.date DESC, wl.created_at DESC
        LIMIT ? OFFSET ?
    """, [aid, limit, offset]).fetchall()
    return json_response([dict(r) for r in rows])


def get_workout_detail(db, params):
    wid = params.get("id", [""])[0]
    if not wid:
        return json_response({"error": "id required"}, 400)

    workout = db.execute("SELECT * FROM workout_logs WHERE id = ?", [wid]).fetchone()
    if not workout:
        return json_response({"error": "not found"}, 404)

    sets = db.execute("""
        SELECT sl.*, e.name as exercise_name, e.movement_pattern, e.category
        FROM set_logs sl
        JOIN exercises e ON sl.exercise_id = e.id
        WHERE sl.workout_log_id = ?
        ORDER BY sl.exercise_id, sl.set_number
    """, [wid]).fetchall()

    result = dict(workout)
    result["sets"] = [dict(s) for s in sets]

    # Group sets by exercise for display
    grouped = {}
    for s in result["sets"]:
        eid = s["exercise_id"]
        if eid not in grouped:
            grouped[eid] = {
                "exercise_id": eid,
                "exercise_name": s["exercise_name"],
                "movement_pattern": s["movement_pattern"],
                "category": s["category"],
                "sets": []
            }
        grouped[eid]["sets"].append(s)
    result["exercises"] = list(grouped.values())

    return json_response(result)


def delete_workout(db, params):
    wid = params.get("id", [""])[0]
    if not wid:
        return json_response({"error": "id required"}, 400)
    db.execute("DELETE FROM set_logs WHERE workout_log_id = ?", [wid])
    db.execute("DELETE FROM workout_logs WHERE id = ?", [wid])
    db.commit()
    return json_response({"status": "deleted"})


def get_e1rm(db, params):
    aid = params.get("athlete_id", ["1"])[0]
    eid = params.get("exercise_id", [""])[0]
    days = int(params.get("days", ["90"])[0])

    if eid:
        trend = calculate_e1rm_trend(db, aid, eid, days)
        current = db.execute("""
            SELECT estimated_1rm FROM one_rep_maxes
            WHERE athlete_id = ? AND exercise_id = ?
            ORDER BY date DESC LIMIT 1
        """, [aid, eid]).fetchone()
        return json_response({
            "current_e1rm": current["estimated_1rm"] if current else None,
            "trend": trend
        })
    else:
        # Get all current e1RMs
        rows = db.execute("""
            SELECT orm.exercise_id, e.name, orm.estimated_1rm, orm.date
            FROM one_rep_maxes orm
            JOIN exercises e ON orm.exercise_id = e.id
            WHERE orm.athlete_id = ?
            AND orm.id = (
                SELECT id FROM one_rep_maxes
                WHERE athlete_id = orm.athlete_id AND exercise_id = orm.exercise_id
                ORDER BY date DESC LIMIT 1
            )
            ORDER BY e.name
        """, [aid]).fetchall()
        return json_response([dict(r) for r in rows])


def get_overload_rec(db, params):
    aid = params.get("athlete_id", ["1"])[0]
    eid = params.get("exercise_id", [""])[0]
    if not eid:
        return json_response({"error": "exercise_id required"}, 400)
    rec = get_progressive_overload_recommendation(db, aid, eid)
    return json_response(rec)


def get_analytics(db, params):
    aid = params.get("athlete_id", ["1"])[0]
    days = int(params.get("days", ["30"])[0])
    metric = params.get("metric", ["volume"])[0]

    if metric == "volume":
        rows = db.execute("""
            SELECT wl.date, SUM(sl.weight * sl.reps) as volume,
                   COUNT(DISTINCT sl.exercise_id) as exercises_performed,
                   COUNT(sl.id) as total_sets
            FROM workout_logs wl
            JOIN set_logs sl ON sl.workout_log_id = wl.id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY wl.date
            ORDER BY wl.date
        """, [aid, f"-{days} days"]).fetchall()
        return json_response([dict(r) for r in rows])

    elif metric == "frequency":
        rows = db.execute("""
            SELECT e.movement_pattern, COUNT(DISTINCT wl.date) as session_count,
                   COUNT(sl.id) as total_sets
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            JOIN exercises e ON sl.exercise_id = e.id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY e.movement_pattern
            ORDER BY total_sets DESC
        """, [aid, f"-{days} days"]).fetchall()
        return json_response([dict(r) for r in rows])

    elif metric == "muscle_volume":
        rows = db.execute("""
            SELECT e.primary_muscles, COUNT(sl.id) as total_sets,
                   SUM(sl.weight * sl.reps) as total_volume
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            JOIN exercises e ON sl.exercise_id = e.id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY e.primary_muscles
            ORDER BY total_sets DESC
        """, [aid, f"-{days} days"]).fetchall()
        return json_response([dict(r) for r in rows])

    return json_response([])


def get_volume_landmarks(db, params):
    aid = params.get("athlete_id", ["1"])[0]
    rows = db.execute("""
        SELECT * FROM volume_landmarks WHERE athlete_id = ? ORDER BY muscle_group
    """, [aid]).fetchall()

    if not rows:
        # Return defaults
        defaults = [
            ("chest", 8, 12, 18, 22), ("back", 8, 12, 18, 22),
            ("quads", 6, 10, 16, 20), ("hamstrings", 6, 10, 14, 18),
            ("glutes", 4, 8, 14, 18), ("shoulders", 8, 12, 18, 22),
            ("biceps", 6, 10, 16, 20), ("triceps", 6, 8, 14, 18),
            ("calves", 8, 10, 16, 20), ("core", 4, 8, 12, 16),
        ]
        return json_response([
            {"muscle_group": d[0], "mev": d[1], "mav_low": d[2], "mav_high": d[3], "mrv": d[4]}
            for d in defaults
        ])

    return json_response([dict(r) for r in rows])


def save_volume_landmarks(db, body):
    aid = body.get("athlete_id", 1)
    landmarks = body.get("landmarks", [])
    for lm in landmarks:
        db.execute("""
            INSERT OR REPLACE INTO volume_landmarks (athlete_id, muscle_group, mev, mav_low, mav_high, mrv, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [aid, lm["muscle_group"], lm["mev"], lm["mav_low"], lm["mav_high"], lm["mrv"]])
    db.commit()
    return json_response({"status": "saved", "count": len(landmarks)})


def get_phase_config(db, params):
    goal = params.get("goal", ["strength"])[0]
    phase = params.get("phase", ["accumulation"])[0]
    experience = params.get("experience", ["intermediate"])[0]
    config = generate_phase_config(goal, phase, experience)
    return json_response(config)


def get_dashboard(db, params):
    aid = params.get("athlete_id", ["1"])[0]

    # Recent workouts
    recent = db.execute("""
        SELECT wl.id, wl.date, wl.duration_min, wl.session_rpe,
               COUNT(sl.id) as total_sets,
               ROUND(SUM(sl.weight * sl.reps), 0) as volume_load
        FROM workout_logs wl
        LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id AND sl.set_type = 'working'
        WHERE wl.athlete_id = ?
        GROUP BY wl.id
        ORDER BY wl.date DESC
        LIMIT 7
    """, [aid]).fetchall()

    # Streak
    streak = 0
    dates = db.execute("""
        SELECT DISTINCT date FROM workout_logs WHERE athlete_id = ? ORDER BY date DESC LIMIT 60
    """, [aid]).fetchall()
    if dates:
        today = datetime.now().date()
        for i, row in enumerate(dates):
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            expected = today - timedelta(days=i)
            if d == expected or (today - d).days <= 2:
                streak += 1
            else:
                break

    # Total stats
    totals = db.execute("""
        SELECT COUNT(DISTINCT wl.id) as total_workouts,
               COUNT(sl.id) as total_sets,
               ROUND(SUM(sl.weight * sl.reps), 0) as total_volume
        FROM workout_logs wl
        LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id AND sl.set_type = 'working'
        WHERE wl.athlete_id = ?
    """, [aid]).fetchone()

    # PRs (top e1RM per exercise, last 30 days)
    prs = db.execute("""
        SELECT e.name, MAX(orm.estimated_1rm) as best_e1rm, orm.date
        FROM one_rep_maxes orm
        JOIN exercises e ON orm.exercise_id = e.id
        WHERE orm.athlete_id = ? AND orm.date >= date('now', '-30 days')
        GROUP BY orm.exercise_id
        ORDER BY orm.estimated_1rm DESC
        LIMIT 5
    """, [aid]).fetchall()

    # Active program
    program = db.execute("""
        SELECT * FROM programs WHERE athlete_id = ? AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
    """, [aid]).fetchone()

    return json_response({
        "recent_workouts": [dict(r) for r in recent],
        "streak": streak,
        "totals": dict(totals) if totals else {},
        "recent_prs": [dict(r) for r in prs],
        "active_program": dict(program) if program else None
    })


def get_movement_patterns(db):
    rows = db.execute("""
        SELECT DISTINCT movement_pattern, COUNT(*) as count
        FROM exercises GROUP BY movement_pattern ORDER BY movement_pattern
    """).fetchall()
    return json_response([dict(r) for r in rows])


def get_muscle_groups(db):
    rows = db.execute("SELECT DISTINCT primary_muscles FROM exercises ORDER BY primary_muscles").fetchall()
    # Parse comma-separated muscles
    muscles = set()
    for r in rows:
        for m in r["primary_muscles"].split(","):
            muscles.add(m.strip())
    return json_response(sorted(list(muscles)))


def json_response(data, status=200):
    if status != 200:
        print(f"Status: {status}")
    print("Content-Type: application/json")
    print()
    print(json.dumps(data))


if __name__ == "__main__":
    handle_request()
