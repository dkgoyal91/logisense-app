from __future__ import annotations

QUESTION_WINDOW_SECONDS = 20
MAX_PREDICTION_POINTS = 1000
SPEED_PENALTY_RANGE = 500
STREAK_THRESHOLD = 3
STREAK_BONUS = 200
ATTACK_POINTS = 50
MAX_SCORED_ATTACKS = 5
STAR_ATTACK_POINTS = 1000
RACE_PLACE_POINTS = (3000, 2000, 1000)
RACE_FINISH_POINTS = 500
DEMO_POINTS = 500


def prediction_points(elapsed: float) -> int:
    clamped = min(max(elapsed, 0.0), QUESTION_WINDOW_SECONDS)
    return MAX_PREDICTION_POINTS - round(SPEED_PENALTY_RANGE * clamped / QUESTION_WINDOW_SECONDS)


def streak_bonus(streak: int) -> int:
    return STREAK_BONUS if streak >= STREAK_THRESHOLD else 0


def race_points(place: int) -> int:
    if place <= len(RACE_PLACE_POINTS):
        return RACE_PLACE_POINTS[place - 1]
    return RACE_FINISH_POINTS
