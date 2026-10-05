from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

OPTIONS_PER_QUESTION = 4


class Phase(str, Enum):
    LOBBY = 'lobby'
    QUESTION_OPEN = 'question_open'
    QUESTION_REVEALED = 'question_revealed'
    BREAK_IT_OPEN = 'break_it_open'
    BREAK_IT_CLOSED = 'break_it_closed'
    RACE_PODIUM = 'race_podium'
    BONUS = 'bonus'
    FINALE = 'finale'


class GameError(Exception):
    """A client action that is not allowed; the message is shown to that client."""


@dataclass(frozen=True)
class Verdict:
    layer: str
    message: str


@dataclass(frozen=True)
class Question:
    copilot_prompt: str
    text: str
    concept: str
    options: tuple[str, ...]
    correct_index: int


@dataclass
class Player:
    id: str
    token: str
    name: str
    predict_points: int = 0
    hack_points: int = 0
    race_points: int = 0
    demo_points: int = 0
    streak: int = 0
    attacks_scored: int = 0
    last_attack_at: float | None = None
    race_finished_at: float | None = None
    kicked: bool = False
    takeaway_status: str | None = None   # queued | sent | failed | saved (collected, mail not configured)
    takeaway_hint: str | None = None     # masked address only; the full address lives in the takeaway CSV

    @property
    def total(self) -> int:
        return self.predict_points + self.hack_points + self.race_points + self.demo_points


@dataclass
class Answer:
    option: int
    elapsed: float
    points: int = 0


@dataclass
class Attack:
    id: str
    player_id: str
    text: str
    layer: str
    message: str
    starred: bool = False


@dataclass
class BonusQuestion:
    id: str
    player_id: str
    text: str
    voters: list[str] = field(default_factory=list)


@dataclass
class GameState:
    phase: Phase = Phase.LOBBY
    question_index: int = -1
    question_opened_at: float | None = None
    answers: dict[int, dict[str, Answer]] = field(default_factory=dict)
    copilot_results: dict[int, dict[str, Any]] = field(default_factory=dict)
    race_started_at: float | None = None
    race_finishers: list[str] = field(default_factory=list)
    attacks: list[Attack] = field(default_factory=list)
    bonus_questions: list[BonusQuestion] = field(default_factory=list)
    bonus_answer: dict[str, Any] | None = None
    players: dict[str, Player] = field(default_factory=dict)
    hands_mode: bool = False
    takeaway_broadcast: dict[str, Any] | None = None   # {'status': sending|sent|failed, 'count', 'detail'}
