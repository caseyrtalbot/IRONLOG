# tests/test_progression.py
from server.algorithms.progression import (
    calculate_weekly_progression,
    prescribe_weight,
)


def test_linear_progression_4_weeks():
    result = calculate_weekly_progression(
        base_sets=3, weeks=4, progression_type="linear",
        intensity_start=70, intensity_end=80,
        rpe_start=7.0, rpe_end=8.0,
    )
    assert len(result) == 4
    assert result[0]["week"] == 1
    assert result[0]["intensity_pct"] == 70.0
    assert result[3]["intensity_pct"] == 80.0
    # Volume should ramp: at least one week has more sets than base
    assert any(w["sets"] > 3 for w in result)


def test_undulating_progression():
    result = calculate_weekly_progression(
        base_sets=3, weeks=4, progression_type="undulating",
        intensity_start=70, intensity_end=80,
        rpe_start=7.0, rpe_end=8.0,
    )
    # Undulating should alternate
    sets_sequence = [w["sets"] for w in result]
    assert sets_sequence != sorted(sets_sequence), "Undulating should not be monotonic"


def test_reduced_progression_deload():
    result = calculate_weekly_progression(
        base_sets=4, weeks=4, progression_type="reduced",
        intensity_start=55, intensity_end=65,
        rpe_start=5.0, rpe_end=7.0,
    )
    # All weeks should have fewer sets than base
    for w in result:
        assert w["sets"] <= 4


def test_taper_progression():
    result = calculate_weekly_progression(
        base_sets=4, weeks=4, progression_type="taper",
        intensity_start=90, intensity_end=100,
        rpe_start=9.0, rpe_end=10.0,
    )
    # Sets should decrease toward end
    assert result[-1]["sets"] <= result[0]["sets"]


def test_prescribe_weight_basic():
    # 315 e1RM at 75% intensity
    # 315 * 0.75 = 236.25 → round(236.25 / 2.5) = round(94.5) = 94 → 94 * 2.5 = 235.0
    weight = prescribe_weight(315, 75.0)
    assert weight == 235.0


def test_prescribe_weight_rounds_to_2_5():
    weight = prescribe_weight(300, 72.0)
    # 300 * 0.72 = 216.0 → already multiple of 2.5 (86.4 * 2.5 = 216)
    assert weight % 2.5 == 0


def test_prescribe_weight_none_without_e1rm():
    assert prescribe_weight(None, 75.0) is None
    assert prescribe_weight(0, 75.0) is None
