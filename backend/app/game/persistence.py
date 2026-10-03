"""Write the game to a JSON snapshot after every change so a restart can resume mid-show."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.game.models import Answer, Attack, BonusQuestion, GameState, Phase, Player

logger = logging.getLogger(__name__)


class SnapshotStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, state: GameState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state_to_dict(state)), encoding='utf-8')
        os.replace(temporary, self._path)

    def load(self) -> GameState | None:
        if not self._path.is_file():
            return None
        try:
            return state_from_dict(json.loads(self._path.read_text(encoding='utf-8')))
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning('Ignoring unreadable game snapshot %s: %s', self._path, exc)
            return None


def state_to_dict(state: GameState) -> dict[str, Any]:
    data = asdict(state)
    data['phase'] = state.phase.value
    return data


def state_from_dict(data: dict[str, Any]) -> GameState:
    return GameState(
        phase=Phase(data['phase']),
        question_index=data['question_index'],
        question_opened_at=data['question_opened_at'],
        answers=_answers_from(data['answers']),
        copilot_results={int(index): result for index, result in data['copilot_results'].items()},
        race_started_at=data['race_started_at'],
        race_finishers=list(data['race_finishers']),
        attacks=[Attack(**attack) for attack in data['attacks']],
        bonus_questions=[BonusQuestion(**question) for question in data['bonus_questions']],
        bonus_answer=data['bonus_answer'],
        players={player_id: Player(**player) for player_id, player in data['players'].items()},
        hands_mode=data['hands_mode'],
    )


def _answers_from(raw: dict[str, dict[str, dict[str, Any]]]) -> dict[int, dict[str, Answer]]:
    return {
        int(index): {player_id: Answer(**answer) for player_id, answer in by_player.items()}
        for index, by_player in raw.items()
    }
