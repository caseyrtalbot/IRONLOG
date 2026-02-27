from server.algorithms.overload import recommend_overload


def test_overload_low_rpe_increases_load():
    last = [{"weight": 200, "reps": 5, "rpe": 6.5}]
    prev = [{"weight": 195, "reps": 5, "rpe": 7}]
    rec = recommend_overload(last, prev, 260)
    assert rec["action"] == "increase_load"


def test_overload_moderate_rpe_micro_loads():
    last = [{"weight": 200, "reps": 5, "rpe": 8}]
    prev = [{"weight": 195, "reps": 5, "rpe": 7.5}]
    rec = recommend_overload(last, prev, 260)
    assert rec["action"] == "micro_load"


def test_overload_high_rpe_adds_reps():
    last = [{"weight": 200, "reps": 5, "rpe": 9.5}]
    prev = [{"weight": 200, "reps": 5, "rpe": 9}]
    rec = recommend_overload(last, prev, 260)
    assert rec["action"] == "add_reps_or_deload"
