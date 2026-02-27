from server.db.connection import get_connection


def get_db():
    db = get_connection()
    try:
        yield db
    finally:
        db.close()
