from fastapi import HTTPException


def require_found(result, resource: str = "Resource"):
    """Raise 404 if result is None, otherwise return result."""
    if result is None:
        raise HTTPException(status_code=404, detail=f"{resource} not found")
    return result
