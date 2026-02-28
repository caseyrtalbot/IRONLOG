from server.algorithms.e1rm import estimate_1rm, rpe_to_percentage


def test_estimate_1rm_basic():
    # 225 lbs x 5 reps @ RPE 10 -> Epley: 225 * (1 + 5/30) = 262.5
    assert estimate_1rm(225, 5, 10) == 262.5


def test_estimate_1rm_with_rpe_adjustment():
    # 225 lbs x 5 reps @ RPE 8 -> effective reps = 5 + 2 = 7
    # 225 * (1 + 7/30) = 277.5
    assert estimate_1rm(225, 5, 8) == 277.5


def test_estimate_1rm_single_rep():
    # 1 rep @ RPE 10 -> effective_reps = 1, return weight
    assert estimate_1rm(315, 1, 10) == 315


def test_estimate_1rm_zero_weight():
    assert estimate_1rm(0, 5, 8) == 0


def test_estimate_1rm_zero_reps():
    assert estimate_1rm(225, 0, 8) == 0


def test_rpe_to_percentage_known_values():
    assert rpe_to_percentage(10, 1) == 100
    assert rpe_to_percentage(8, 5) == 81.1
    assert rpe_to_percentage(6, 10) == 62.6
