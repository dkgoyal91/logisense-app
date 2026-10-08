from app.game.scoring import prediction_points, race_points, streak_bonus


def test_prediction_points_scale_with_speed_and_clamp() -> None:
    assert prediction_points(0) == 1000
    assert prediction_points(10) == 750
    assert prediction_points(20) == 500
    assert prediction_points(35) == 500
    assert prediction_points(-1) == 1000


def test_streak_bonus_starts_at_third_correct_answer() -> None:
    assert [streak_bonus(streak) for streak in range(5)] == [0, 0, 0, 200, 200]


def test_race_points_by_finishing_place() -> None:
    assert [race_points(place) for place in (1, 2, 3, 4, 50)] == [3000, 2000, 1000, 500, 500]
