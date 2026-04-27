"""Файл, описывающий комбинации карт и действия с картами в руке."""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

import core.cards as cards
from core.cards import Card
from core.decks import Deck
from core.errors import SelectionError


@dataclass(slots=True)
class HandScore:
    """Базовые фишки и множитель комбинации."""

    chips: int = 0
    mult: int = 0


class PlayedHand:
    """Сыгранный набор карт с вычисленной комбинацией."""

    def __init__(self, played_cards: tuple[Card, ...]) -> None:
        self.played_cards = played_cards
        self.rank_groups = self._init_rank_groups()
        self.is_straight = self._init_is_straight()
        self.is_flush = (
            len(played_cards) == 5
            and all(card.suit == played_cards[0].suit for card in played_cards)
        )

        self.combination_name = ""
        self.combination_score = HandScore()
        self.score_indices: tuple[int, ...] = ()

        self.check()

    def _init_rank_groups(self) -> list[tuple[int, ...]]:
        grouped: dict[cards.Rank, list[int]] = defaultdict(list)
        for index, card in enumerate(self.played_cards):
            grouped[card.rank].append(index)

        return [
            tuple(indices)
            for _, indices in sorted(
                grouped.items(),
                key=lambda item: (len(item[1]), int(item[0])),
                reverse=True,
            )
        ]

    def _init_is_straight(self) -> bool:
        if len(self.played_cards) < 5:
            return False

        sorted_ranks = sorted(card.rank for card in self.played_cards)

        if sorted_ranks == [
            cards.Rank.TWO,
            cards.Rank.THREE,
            cards.Rank.FOUR,
            cards.Rank.FIVE,
            cards.Rank.ACE,
        ]:
            return True

        return all(
            sorted_ranks[index] + 1 == sorted_ranks[index + 1]
            for index in range(len(sorted_ranks) - 1)
        )

    def check(self) -> None:
        """Определяет старшую подходящую комбинацию."""
        for combination in ALL_COMBINATIONS:
            indices = combination.indices(self)
            if indices:
                self.combination_name = combination.name
                self.combination_score = combination.base_score
                self.score_indices = indices
                return

    def has_group_sizes(self, *sizes: int) -> bool:
        """Проверяет размеры групп карт одного ранга."""
        return len(self.rank_groups) >= len(sizes) and all(
            len(self.rank_groups[index]) == size
            for index, size in enumerate(sizes)
        )

    @property
    def scored_cards(self) -> tuple[Card, ...]:
        """Возвращает карты, участвующие в подсчете очков."""
        return tuple(self.played_cards[index] for index in self.score_indices)

    @property
    def base_score(self) -> HandScore:
        """Возвращает базовые очки найденной комбинации."""
        return self.combination_score

    @property
    def chips(self) -> int:
        """Возвращает количество фишек с учетом карт комбинации."""
        return self.combination_score.chips + sum(card.chips for card in self.scored_cards)

    @property
    def mult(self) -> int:
        """Возвращает множитель найденной комбинации."""
        return self.combination_score.mult

    @property
    def score(self) -> int:
        """Возвращает счет комбинации."""
        return self.chips * self.mult


class BaseHandCombination(ABC):
    """Абстрактный класс для комбинации карт."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Отображаемое имя комбинации."""
        raise NotImplementedError

    @property
    @abstractmethod
    def base_score(self) -> HandScore:
        """Базовые очки и множитель."""
        raise NotImplementedError

    @abstractmethod
    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        """Индексы карт, участвующих в комбинации."""
        raise NotImplementedError


class HighCard(BaseHandCombination):
    @property
    def name(self) -> str:
        return "High Card"

    @property
    def base_score(self) -> HandScore:
        return HandScore(5, 1)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        if not played_hand.played_cards:
            return tuple()

        best_index = max(
            range(len(played_hand.played_cards)),
            key=lambda i: int(played_hand.played_cards[i].rank),
        )
        return (best_index,)


class Pair(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Pair"

    @property
    def base_score(self) -> HandScore:
        return HandScore(10, 2)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return played_hand.rank_groups[0] if played_hand.has_group_sizes(2) else tuple()


class TwoPair(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Two Pair"

    @property
    def base_score(self) -> HandScore:
        return HandScore(20, 2)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        if played_hand.has_group_sizes(2, 2):
            return played_hand.rank_groups[0] + played_hand.rank_groups[1]
        return tuple()


class ThreeOfAKind(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Three of a Kind"

    @property
    def base_score(self) -> HandScore:
        return HandScore(30, 3)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return played_hand.rank_groups[0] if played_hand.has_group_sizes(3) else tuple()


class Straight(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Straight"

    @property
    def base_score(self) -> HandScore:
        return HandScore(30, 4)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return tuple(range(5)) if played_hand.is_straight else tuple()


class Flush(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Flush"

    @property
    def base_score(self) -> HandScore:
        return HandScore(35, 4)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return tuple(range(5)) if played_hand.is_flush else tuple()


class FullHouse(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Full House"

    @property
    def base_score(self) -> HandScore:
        return HandScore(40, 4)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        if played_hand.has_group_sizes(3, 2):
            return played_hand.rank_groups[0] + played_hand.rank_groups[1]
        return tuple()


class FourOfAKind(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Four of a Kind"

    @property
    def base_score(self) -> HandScore:
        return HandScore(60, 7)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return played_hand.rank_groups[0] if played_hand.has_group_sizes(4) else tuple()


class StraightFlush(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Straight Flush"

    @property
    def base_score(self) -> HandScore:
        return HandScore(100, 8)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return tuple(range(5)) if played_hand.is_straight and played_hand.is_flush else tuple()


class FiveOfAKind(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Five of a Kind"

    @property
    def base_score(self) -> HandScore:
        return HandScore(120, 12)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        return played_hand.rank_groups[0] if played_hand.has_group_sizes(5) else tuple()


class FlushHouse(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Flush House"

    @property
    def base_score(self) -> HandScore:
        return HandScore(140, 14)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        if played_hand.is_flush and played_hand.has_group_sizes(3, 2):
            return played_hand.rank_groups[0] + played_hand.rank_groups[1]
        return tuple()


class FlushFive(BaseHandCombination):
    @property
    def name(self) -> str:
        return "Flush Five"

    @property
    def base_score(self) -> HandScore:
        return HandScore(160, 16)

    def indices(self, played_hand: PlayedHand) -> tuple[int, ...]:
        if played_hand.is_flush and played_hand.has_group_sizes(5):
            return played_hand.rank_groups[0]
        return tuple()


ALL_COMBINATIONS: tuple[BaseHandCombination, ...] = (
    FlushFive(),
    FlushHouse(),
    FiveOfAKind(),
    StraightFlush(),
    FourOfAKind(),
    FullHouse(),
    Flush(),
    Straight(),
    ThreeOfAKind(),
    TwoPair(),
    Pair(),
    HighCard(),
)


class Hand:
    """Рука игрока с картами и текущим выбором."""

    def __init__(self, cards_in_hand: Iterable[Card] = ()) -> None:
        self.cards: list[Card] = list(cards_in_hand)
        self.selected_indices: set[int] = set()

    def fill(self, deck: Deck, target_size: int) -> None:
        """Добирает карты из колоды до нужного размера руки."""
        while len(self.cards) < target_size and not deck.empty():
            self.cards.append(deck.draw())

    def clear_selection(self) -> None:
        """Снимает выделение со всех карт."""
        self.selected_indices.clear()

    def toggle(self, index: int) -> None:
        """Переключает выбор карты по индексу."""
        if not 0 <= index < len(self.cards):
            raise SelectionError("Card index is out of range.")

        if index in self.selected_indices:
            self.selected_indices.remove(index)
            return

        self.selected_indices.add(index)

    @property
    def selected_cards(self) -> tuple[Card, ...]:
        """Возвращает выбранные карты в порядке индексов."""
        return tuple(self.cards[index] for index in sorted(self.selected_indices))

    def preview_selection(self) -> PlayedHand | None:
        """Возвращает предварительный результат выбранных карт."""
        if not self.selected_indices:
            return None
        return PlayedHand(self.selected_cards)

    def _pop_selected_cards(self) -> tuple[Card, ...]:
        removed: list[Card] = []
        for index in sorted(self.selected_indices, reverse=True):
            removed.append(self.cards.pop(index))
        self.selected_indices.clear()
        removed.reverse()
        return tuple(removed)

    def play_selected(self, deck: Deck, target_size: int) -> PlayedHand:
        """Разыгрывает выбранные карты и добирает новые."""
        played_hand = self.preview_selection()
        if played_hand is None:
            raise SelectionError("Select at least one card first.")

        self._pop_selected_cards()
        self.fill(deck, target_size)
        return played_hand

    def discard_selected(self, deck: Deck, target_size: int) -> tuple[Card, ...]:
        """Сбрасывает выбранные карты и добирает новые."""
        if not self.selected_indices:
            raise SelectionError("Select at least one card first.")

        discarded = self._pop_selected_cards()
        self.fill(deck, target_size)
        return discarded
