"""UI enums."""

from enum import StrEnum


class AppMode(StrEnum):
    """Режим приложения"""
    MENU = "menu"
    GAME = "game"


class PopupKind(StrEnum):
    """Тип всплывающего окна."""
    NONE = "none"
    WIN = "win"
    LOSS = "loss"


class RoundPhase(StrEnum):
    """Стадия раунда."""
    IDLE = "idle"
    MOVING_TO_CENTER = "moving_to_center"
    SCORE_DELAY = "score_delay"
    SCORE_SEQUENCE = "score_sequence"
    SCORE_FINAL_FADE = "score_final_fade"
    EXITING_PLAYED = "exiting_played"
    DISCARD_EXITING = "discard_exiting"
    REFILLING = "refilling"
