SCHEMA = """
CREATE TABLE IF NOT EXISTS athletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    body_weight REAL,
    body_fat_pct REAL,
    training_age INTEGER DEFAULT 0,
    experience_level TEXT DEFAULT 'intermediate'
        CHECK(experience_level IN ('beginner','intermediate','advanced','elite')),
    primary_goal TEXT DEFAULT 'strength'
        CHECK(primary_goal IN ('strength','hypertrophy','power','endurance','general')),
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

CREATE TABLE IF NOT EXISTS exercise_muscles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER NOT NULL,
    muscle_group TEXT NOT NULL,
    is_primary INTEGER DEFAULT 1,
    contribution REAL DEFAULT 0.5,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    UNIQUE(exercise_id, muscle_group)
);

CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phase TEXT NOT NULL
        CHECK(phase IN ('accumulation','intensification','realization','deload','transition')),
    goal TEXT NOT NULL
        CHECK(goal IN ('strength','hypertrophy','power','endurance','general')),
    mesocycle_weeks INTEGER DEFAULT 4,
    current_week INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active'
        CHECK(status IN ('active','completed','paused')),
    config TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS program_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    phase_order INTEGER NOT NULL,
    phase_type TEXT NOT NULL
        CHECK(phase_type IN ('accumulation','intensification','realization','deload')),
    duration_weeks INTEGER DEFAULT 4,
    volume_multiplier REAL DEFAULT 1.0,
    intensity_target REAL,
    rpe_target REAL,
    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
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
    intensity_type TEXT DEFAULT 'rpe'
        CHECK(intensity_type IN ('rpe','rir','percent_rm','rpe_range')),
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
    set_type TEXT DEFAULT 'working'
        CHECK(set_type IN ('warmup','working','backoff','amrap','drop','cluster')),
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

CREATE INDEX IF NOT EXISTS idx_exercise_muscles_exercise
    ON exercise_muscles(exercise_id);
CREATE INDEX IF NOT EXISTS idx_program_phases_program
    ON program_phases(program_id);
CREATE INDEX IF NOT EXISTS idx_set_logs_exercise
    ON set_logs(exercise_id);
CREATE INDEX IF NOT EXISTS idx_set_logs_workout
    ON set_logs(workout_log_id);
CREATE INDEX IF NOT EXISTS idx_workout_logs_athlete
    ON workout_logs(athlete_id);
CREATE INDEX IF NOT EXISTS idx_workout_logs_date
    ON workout_logs(date);
CREATE INDEX IF NOT EXISTS idx_one_rep_maxes_athlete_exercise
    ON one_rep_maxes(athlete_id, exercise_id);
"""


def init_schema(db):
    db.executescript(SCHEMA)
    db.commit()
