import os

DB_PATH = os.environ.get("IRONLOG_DB", "ironlog.db")
CORS_ORIGINS = os.environ.get("IRONLOG_CORS", "*").split(",")
