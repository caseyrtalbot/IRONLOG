# tests/test_volume_budget.py
from server.algorithms.volume_budget import calculate_projected_volume, audit_volume


def test_calculate_projected_volume():
    """Project weekly volume from program exercises and muscle contributions."""
    program_exercises = [
        {"sets_prescribed": 4, "muscles": [
            {"muscle_group": "chest", "contribution": 1.0},
            {"muscle_group": "front_delts", "contribution": 0.5},
            {"muscle_group": "triceps", "contribution": 0.5},
        ]},
        {"sets_prescribed": 4, "muscles": [
            {"muscle_group": "upper_back", "contribution": 1.0},
            {"muscle_group": "lats", "contribution": 0.75},
            {"muscle_group": "rear_delts", "contribution": 0.5},
            {"muscle_group": "biceps", "contribution": 0.5},
        ]},
    ]
    result = calculate_projected_volume(program_exercises)
    assert result["chest"] == 4.0
    assert result["front_delts"] == 2.0
    assert result["triceps"] == 2.0
    assert result["upper_back"] == 4.0
    assert result["lats"] == 3.0
    assert result["biceps"] == 2.0


def test_audit_volume_flags_red_issues():
    """Audit should flag muscles below MEV (red) or above MRV (red)."""
    projected = {"chest": 4.0, "side_delts": 0.0, "quads": 25.0}
    landmarks = {
        "chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22},
        "side_delts": {"mev": 8, "mav_low": 14, "mav_high": 22, "mrv": 28},
        "quads": {"mev": 6, "mav_low": 10, "mav_high": 16, "mrv": 20},
    }
    audit = audit_volume(projected, landmarks)
    assert any(a["muscle"] == "chest" and a["issue"] == "below_mev" for a in audit)
    assert any(a["muscle"] == "side_delts" and a["issue"] == "below_mev" for a in audit)
    assert any(a["muscle"] == "quads" and a["issue"] == "above_mrv" for a in audit)


def test_audit_volume_flags_yellow_issues():
    """Audit should flag muscles below MAV-low (yellow) or above MAV-high (yellow)."""
    projected = {"chest": 9.0, "quads": 19.0}
    landmarks = {
        "chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22},
        "quads": {"mev": 6, "mav_low": 10, "mav_high": 16, "mrv": 20},
    }
    audit = audit_volume(projected, landmarks)
    assert any(a["muscle"] == "chest" and a["issue"] == "below_mav" for a in audit)
    assert any(a["muscle"] == "quads" and a["issue"] == "above_mav" for a in audit)


def test_audit_volume_within_range():
    """Muscles within MAV range should have no issues."""
    projected = {"chest": 14.0}
    landmarks = {"chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22}}
    audit = audit_volume(projected, landmarks)
    assert len(audit) == 0
