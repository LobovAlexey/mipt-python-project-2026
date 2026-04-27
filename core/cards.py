"""Файл, описывающий структуру карт."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, IntEnum


class Suit(Enum):
    """Масть карты."""

    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    SPADES = "spades"
    CLUBS = "clubs"


SUIT_SORT_ORDER: dict[Suit, int] = {
    Suit.SPADES: 3,
    Suit.CLUBS: 2,
    Suit.HEARTS: 1,
    Suit.DIAMONDS: 0,
}


class Rank(IntEnum):
    """Ранг карты."""

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@dataclass(frozen=True, slots=True)
class Card:
    """Игровая карта (иммутабельный объект)."""

    rank: Rank
    suit: Suit

    @property
    def chips(self) -> int:
        """Return the chip value of the card."""
        if self.rank < Rank.JACK:
            return int(self.rank)
        if self.rank < Rank.ACE:
            return 10
        return 11

    @property
    def file_name(self) -> str:
        """Return the image file name for the card."""
        if self.rank < Rank.JACK:
            spelled_rank: str | int = int(self.rank)
        else:
            spelled_rank = ("jack", "queen", "king", "ace")[int(self.rank) - int(Rank.JACK)]
        return f"{spelled_rank}_of_{self.suit.value}.png"


def hand_sort_key(card: Card) -> tuple[int, int]:
    """The key function for sorting cards by rank."""
    return int(card.rank), SUIT_SORT_ORDER[card.suit]


def sort_cards(cards: Iterable[Card]) -> list[Card]:
    """Sorts the cards by rank."""
    return sorted(cards, key=hand_sort_key, reverse=True)
