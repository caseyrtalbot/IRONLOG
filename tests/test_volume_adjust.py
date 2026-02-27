# tests/test_volume_adjust.py
from server.algorithms.volume_budget import calculate_projected_volume, audit_volume


def test_audit_identifies_deficit():
    """Verify the audit correctly flags below_mev issues."""
    projected = {"chest": 10, "lats": 3, "biceps": 2}
    landmarks = {
        "chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22},
        "lats": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22},
        "biceps": {"mev": 6, "mav_low": 10, "mav_high": 16, "mrv": 20},
    }
    issues = audit_volume(projected, landmarks)
    below_mev = [i for i in issues if i["issue"] == "below_mev"]
    assert len(below_mev) == 2  # lats and biceps
    muscles_flagged = {i["muscle"] for i in below_mev}
    assert "lats" in muscles_flagged
    assert "biceps" in muscles_flagged
