"""Классы для управления игровой сессией и ее состоянием."""

from dataclasses import dataclass, field

from core.cards import Card, sort_cards
from core.decks import Deck, StandardDeck
from core.errors import InvalidMove
from core.hands import HandScore, PlayedHand


@dataclass(slots=True)
class PendingCards:
    """Временное состояние сыгранных карт до завершения анимаций."""

    selected_indices: tuple[int, ...]
    played_hand: PlayedHand
    applied_scoring_count: int = 0
    score_committed: bool = False

    @property
    def played_cards(self) -> tuple[Card, ...]:
        """Возвращает сыгранные карты."""
        return self.played_hand.played_cards

    @property
    def scoring_card_indices(self) -> tuple[int, ...]:
        """Возвращает индексы карт, участвующих в подсчете очков."""
        return self.played_hand.score_indices

    @property
    def combination_name(self) -> str:
        """Возвращает название найденной комбинации."""
        return self.played_hand.combination_name

    @property
    def hand_score(self) -> HandScore:
        """Возвращает базовые очки сыгранной комбинации."""
        return self.played_hand.base_score

    @property
    def current_chips(self) -> int:
        """Возвращает текущие фишки с учетом уже примененных бонусов."""
        bonus = sum(
            self.played_cards[index].chips
            for index in self.scoring_card_indices[: self.applied_scoring_count]
        )
        return self.hand_score.chips + bonus

    @property
    def score(self) -> int:
        """Возвращает итоговый счет сыгранной руки."""
        return self.current_chips * self.hand_score.mult


@dataclass(slots=True)
class GameState:
    """Текущее состояние игры, доступное интерфейсу."""

    hand: list[Card] = field(default_factory=list)
    selected_indices: set[int] = field(default_factory=set)

    total_chips: int = 0
    current_chips: int = 0
    current_mult: int = 0

    played_cards: tuple[Card, ...] = ()
    played_hand_label: str = ""
    scoring_card_indices: tuple[int, ...] = ()

    @property
    def has_played_hand(self) -> bool:
        """Показывает, есть ли сейчас сыгранная рука для отображения."""
        return bool(self.played_cards)


class GameSession:
    """Управляет игровой сессией, рукой, колодой и подсчетом очков."""

    HAND_SIZE = 8
    MAX_CARDS_TO_PLAY = 5

    def __init__(self) -> None:
        self.deck: Deck | None = None
        self.pending: PendingCards | None = None
        self.state = GameState()

    def start_new_game(self, deck_cls: type[Deck] = StandardDeck) -> None:
        """Запускает новую игру с новой колодой."""
        self.deck = deck_cls()
        self.deck.shuffle()

        self.pending = None
        self.state = GameState()
        self.state.hand.extend(self._draw_up_to_hand_size())
        self.state.hand = sort_cards(self.state.hand)

    @property
    def cards_remaining(self) -> int:
        """Сколько карт осталось в колоде."""
        if self.deck is None:
            return 0
        return len(self.deck.cards) - self.deck.index

    @property
    def can_play(self) -> bool:
        """Проверка: можно ли прямо сейчас нажать Play."""
        return (
                self.pending is None
                and bool(self.state.selected_indices)
                and len(self.state.selected_indices) <= self.MAX_CARDS_TO_PLAY
        )

    @property
    def can_discard(self) -> bool:
        """Проверка: можно ли прямо сейчас нажать Discard."""
        return bool(self.state.selected_indices) and self.pending is None

    def toggle_card_selection(self, index: int) -> None:
        """Переключает состояние карты: выбрана / не выбрана."""
        if self.pending is not None:
            raise InvalidMove("Cannot change selection while a hand is resolving.")

        if not 0 <= index < len(self.state.hand):
            raise InvalidMove("Card index is out of range.")

        if index in self.state.selected_indices:
            self.state.selected_indices.remove(index)
            return

        self.state.selected_indices.add(index)

    def play_selected(self) -> None:
        """Позволяет сыграть руку и создать ``PendingCards``."""
        if self.pending is not None:
            raise InvalidMove("A hand is already resolving.")
        if not self.state.selected_indices:
            raise InvalidMove("Select at least one card first.")
        if len(self.state.selected_indices) > self.MAX_CARDS_TO_PLAY:
            raise InvalidMove(
                f"You can play at most {self.MAX_CARDS_TO_PLAY} cards."
            )

        selected_indices = tuple(sorted(self.state.selected_indices))
        played_cards = tuple(self.state.hand[index] for index in selected_indices)
        played_hand = PlayedHand(played_cards)

        pending = PendingCards(
            selected_indices=selected_indices,
            played_hand=played_hand,
        )

        self.pending = pending
        self.state.played_cards = pending.played_cards
        self.state.played_hand_label = pending.combination_name
        self.state.scoring_card_indices = pending.scoring_card_indices
        self.state.current_chips = pending.hand_score.chips
        self.state.current_mult = pending.hand_score.mult

    def apply_next_card_bonus(self) -> None:
        """Добавляет фишки карты к фишкам сыгранных карт."""
        if self.pending is None:
            raise InvalidMove("There is no active played hand.")

        if self.pending.applied_scoring_count >= len(self.pending.scoring_card_indices):
            raise InvalidMove("All scoring cards have already been processed.")

        index = self.pending.scoring_card_indices[self.pending.applied_scoring_count]
        self.pending.applied_scoring_count += 1
        self.state.current_chips = self.pending.current_chips

    def commit_play_score(self) -> None:
        """Добавляет фишки сыгранных карт к общим."""
        if self.pending is None:
            raise InvalidMove("There is no active played hand.")

        if self.pending.score_committed:
            return

        self.pending.score_committed = True
        self.state.total_chips += self.pending.score

    def finish_played_hand(self) -> tuple[Card, ...]:
        """Завершает ход."""
        if self.pending is None:
            raise InvalidMove("There is no active played hand.")

        self.commit_play_score()

        self.state.hand = [
            card
            for index, card in enumerate(self.state.hand)
            if index not in self.pending.selected_indices
        ]
        self.state.selected_indices.clear()

        drawn_cards = self._draw_up_to_hand_size()
        self.state.hand.extend(drawn_cards)
        self.state.hand = sort_cards(self.state.hand)

        self._clear_play_state()
        return drawn_cards

    def discard_selected(self) -> tuple[Card, ...]:
        """Сбрасывает выбранные карты и добирает замену."""
        if self.pending is not None:
            raise InvalidMove("Cannot discard while a hand is resolving.")
        if not self.state.selected_indices:
            raise InvalidMove("Select at least one card first.")

        discarded_cards = tuple(
            card
            for index, card in enumerate(self.state.hand)
            if index in self.state.selected_indices
        )

        self.state.hand = [
            card
            for index, card in enumerate(self.state.hand)
            if index not in self.state.selected_indices
        ]
        self.state.selected_indices.clear()

        self.state.hand.extend(self._draw_up_to_hand_size())
        self.state.hand = sort_cards(self.state.hand)
        return discarded_cards

    def _draw_up_to_hand_size(self) -> tuple[Card, ...]:
        if self.deck is None:
            return tuple()
        drawn_cards: list[Card] = []
        while len(self.state.hand) + len(drawn_cards) < self.HAND_SIZE and not self.deck.empty():
            drawn_cards.append(self.deck.draw())
        return tuple(drawn_cards)

    def _clear_play_state(self) -> None:
        self.pending = None
        self.state.played_cards = ()
        self.state.played_hand_label = ""
        self.state.scoring_card_indices = ()
        self.state.current_chips = 0
        self.state.current_mult = 0
