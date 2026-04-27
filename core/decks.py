"""Deck abstractions and concrete deck presets."""

from abc import ABC
from random import shuffle

import core.cards as cards
from core.errors import NoCardsLeft


class Deck(ABC):
    """Абстрактный класс для колод."""

    def __init__(self) -> None:
        self.index = 0
        self.cards: list[cards.Card] = []

    def shuffle(self) -> None:
        """Перемешивает колоду."""
        shuffle(self.cards)
        self.index = 0

    def empty(self) -> bool:
        """Проверяет пустоту колоды."""
        return self.index >= len(self.cards)

    def draw(self) -> cards.Card:
        """Вытягивает следующую карту из колоды."""
        if self.empty():
            raise NoCardsLeft("Cannot draw a card from an empty deck.")

        drawn_card = self.cards[self.index]
        self.index += 1
        return drawn_card

    def _append_cards(
        self,
        suits: tuple[cards.Suit, ...],
        *,
        copies: int = 1,
        min_rank: cards.Rank = cards.Rank.TWO,
    ) -> None:
        """
        Добавляет карты в колоду.

        Карты каждой масти из ``suits``,
        ранга от ``min_rank`` до туза,
        в количестве ``copies`` штук.
        """
        for suit in suits:
            for rank in cards.Rank:
                if rank >= min_rank:
                    for _ in range(copies):
                        self.cards.append(cards.Card(rank, suit))


class StandardDeck(Deck):
    """Стандартная колода из 52 карт."""

    def __init__(self) -> None:
        super().__init__()
        self._append_cards(tuple(cards.Suit))


class ShortDeck(Deck):
    """Укороченная колода из 36 карт."""

    def __init__(self) -> None:
        super().__init__()
        self._append_cards(tuple(cards.Suit), min_rank=cards.Rank.SIX)


class HeartsSpadesDeck(Deck):
    """Колода только из ``♥`` и ``♠``."""

    def __init__(self) -> None:
        super().__init__()
        self._append_cards((cards.Suit.HEARTS, cards.Suit.SPADES), copies=2)


DECK_TYPES: dict[str, type[Deck]] = {
    "Standard Deck": StandardDeck,
    "Short Deck": ShortDeck,
    "Hearts & Spades Deck": HeartsSpadesDeck,
}


def get_deck_type(deck_name: str) -> type[Deck]:
    """Получает тип нужной колоды по имени."""
    try:
        return DECK_TYPES[deck_name]
    except KeyError as exc:
        raise KeyError(f"Unknown deck name: {deck_name}") from exc
