"""Основной модуль приложения PyGame."""

import pygame

from core.cards import Card
from core.game import GameSession
from core.errors import InvalidMove
from ui.assets import AppAssets
from ui.config import AppConfig
from ui.enums import AppMode, PopupKind, RoundPhase
from ui.layout import RectFactory
from ui.profiles import ProfileRepository
from ui.views import GameView


class App:
    """Главный объект приложения и координатор игрового цикла."""

    def __init__(self) -> None:
        pygame.init()

        self.config = AppConfig()
        pygame.display.set_caption(self.config.window.caption)

        self.screen = pygame.display.set_mode(self.config.window.size)
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = AppAssets.load(self.config)
        self.rects = RectFactory(self.config)
        self.view = GameView(self.screen, self.config, self.assets, self.rects)
        self.profiles = ProfileRepository(
            self.config.paths.profiles_csv,
            self.config.layout.max_profiles,
        )

        self.selected_profile_index: int | None = None

        self.session = GameSession()
        self.mode = AppMode.MENU
        self.popup_kind = PopupKind.NONE
        self.plays_left = self.config.gameplay.starting_plays
        self.discards_left = self.config.gameplay.starting_discards

        self.bottom_card_positions: list[pygame.Vector2] = []
        self.animated_played_positions: list[pygame.Vector2] = []
        self.animated_discard_cards: list[Card] = []
        self.animated_discard_positions: list[pygame.Vector2] = []

        self.round_phase = RoundPhase.IDLE
        self.center_move_active = False
        self.score_delay_timer = 0.0
        self.score_step_index = 0
        self.score_step_timer = 0.0
        self.score_final_fade_timer = 0.0

    def run(self) -> None:
        """Запускает основной цикл приложения."""
        while self.running:
            dt = self.clock.tick(self.config.window.fps) / 1000.0
            self._handle_events()
            self._update(dt)
            self.view.render(self)
            pygame.display.flip()

        pygame.quit()

    def profile_slot_kind(self, index: int) -> str:
        """Возвращает тип слота профиля в меню."""
        if index < self.profiles.count():
            return "created"
        if index == self.profiles.count() and self.profiles.count() < self.profiles.max_profiles:
            return "plus"
        return "inactive"

    def play_button_enabled(self) -> bool:
        """Можно ли нажать Play."""
        return (
            self.mode == AppMode.GAME
            and self.popup_kind == PopupKind.NONE
            and self.round_phase == RoundPhase.IDLE
            and self.plays_left > 0
            and self.session.can_play
        )

    def discard_button_enabled(self) -> bool:
        """Можно ли нажать Discard."""
        return (
            self.mode == AppMode.GAME
            and self.popup_kind == PopupKind.NONE
            and self.round_phase == RoundPhase.IDLE
            and self.discards_left > 0
            and self.session.can_discard
        )

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode == AppMode.MENU:
                    self._handle_menu_click(event.pos)
                    continue

                if self.popup_kind != PopupKind.NONE:
                    if self.rects.popup_primary_button_rect().collidepoint(event.pos):
                        self._start_game_for_selected_profile()
                    elif self.rects.popup_secondary_button_rect().collidepoint(event.pos):
                        self._back_to_menu()
                    continue

                self._handle_game_click(event.pos)

    def _handle_menu_click(self, mouse_pos: tuple[int, int]) -> None:
        for index, rect in enumerate(self.rects.profile_slot_rects()):
            if not rect.collidepoint(mouse_pos):
                continue

            kind = self.profile_slot_kind(index)

            if kind == "created" and self.rects.profile_delete_rect(rect).collidepoint(mouse_pos):
                self._delete_profile(index)
                return

            if kind == "inactive":
                return

            if kind == "plus":
                self._create_profile()
                return

            if self.selected_profile_index == index:
                self._start_game_for_selected_profile()
            else:
                self.selected_profile_index = index
            return

    def _handle_game_click(self, mouse_pos: tuple[int, int]) -> None:
        if self.rects.play_button_rect().collidepoint(mouse_pos):
            if self.play_button_enabled():
                self.plays_left -= 1
                self._start_play_animation()
            return

        if self.rects.discard_button_rect().collidepoint(mouse_pos):
            if self.discard_button_enabled():
                self.discards_left -= 1
                self._start_discard_animation()
            return

        if self.round_phase != RoundPhase.IDLE:
            return

        card_rects = self.rects.bottom_hitbox_rects(self.bottom_card_positions)
        for index in range(len(card_rects) - 1, -1, -1):
            if card_rects[index].collidepoint(mouse_pos):
                try:
                    self.session.toggle_card_selection(index)
                except InvalidMove:
                    pass
                return

    def _create_profile(self) -> None:
        new_index = self.profiles.create_profile()
        if new_index is not None:
            self.selected_profile_index = new_index

    def _delete_profile(self, index: int) -> None:
        self.profiles.delete_profile(index)

        if self.selected_profile_index is None:
            return
        if self.selected_profile_index == index:
            self.selected_profile_index = None
        elif self.selected_profile_index > index:
            self.selected_profile_index -= 1

    def _start_game_for_selected_profile(self) -> None:
        if self.selected_profile_index is None or not self.profiles.exists(self.selected_profile_index):
            return

        self.session = GameSession()
        self.session.start_new_game()

        self.mode = AppMode.GAME
        self.popup_kind = PopupKind.NONE
        self.plays_left = self.config.gameplay.starting_plays
        self.discards_left = self.config.gameplay.starting_discards

        self.bottom_card_positions.clear()
        self.animated_played_positions.clear()
        self.animated_discard_cards.clear()
        self.animated_discard_positions.clear()

        self.round_phase = RoundPhase.IDLE
        self.center_move_active = False
        self.score_delay_timer = 0.0
        self.score_step_index = 0
        self.score_step_timer = 0.0
        self.score_final_fade_timer = 0.0

        self._reset_bottom_card_positions()

    def _back_to_menu(self) -> None:
        self.mode = AppMode.MENU
        self.popup_kind = PopupKind.NONE

        self.animated_played_positions.clear()
        self.animated_discard_cards.clear()
        self.animated_discard_positions.clear()
        self.round_phase = RoundPhase.IDLE

    def _finish_win_round(self) -> None:
        if self.selected_profile_index is None or not self.profiles.exists(self.selected_profile_index):
            return

        self.profiles.increment_current_round(self.selected_profile_index)
        self.popup_kind = PopupKind.WIN

    def _finish_loss_round(self) -> None:
        if self.selected_profile_index is not None and self.profiles.exists(self.selected_profile_index):
            self.profiles.reset_current_round(self.selected_profile_index)

        self.popup_kind = PopupKind.LOSS

    def _update(self, dt: float) -> None:
        if self.mode != AppMode.GAME:
            return

        if self.popup_kind != PopupKind.NONE:
            return

        self._update_bottom_hand_animation(dt)
        self._update_played_hand_animation(dt)
        self._update_discard_animation(dt)
        self._update_round_phase(dt)
        self._check_round_end_conditions()

    def _check_round_end_conditions(self) -> None:
        if self.popup_kind != PopupKind.NONE:
            return
        if self.round_phase != RoundPhase.IDLE:
            return
        if self.session.state.total_chips >= self.config.gameplay.win_score:
            self._finish_win_round()
            return
        if self.plays_left <= 0:
            self._finish_loss_round()

    def _start_play_animation(self) -> None:
        start_rects = self.rects.bottom_target_rects(
            hand_count=len(self.session.state.hand),
            selected_indices=self.session.state.selected_indices,
            round_phase=self.round_phase,
        )
        selected_indices = sorted(self.session.state.selected_indices)

        try:
            self.session.play_selected()
        except InvalidMove:
            self.plays_left += 1
            return

        self.animated_played_positions = [
            pygame.Vector2(start_rects[index].x, start_rects[index].y)
            for index in selected_indices
        ]
        self.round_phase = RoundPhase.MOVING_TO_CENTER
        self.center_move_active = True
        self.score_delay_timer = 0.0
        self.score_step_index = 0
        self.score_step_timer = 0.0
        self.score_final_fade_timer = 0.0

    def _start_discard_animation(self) -> None:
        selected_indices = sorted(self.session.state.selected_indices)

        self.animated_discard_cards = [
            self.session.state.hand[index]
            for index in selected_indices
        ]
        self.animated_discard_positions = [
            pygame.Vector2(
                self.bottom_card_positions[index].x,
                self.bottom_card_positions[index].y,
            )
            for index in selected_indices
        ]
        self.round_phase = RoundPhase.DISCARD_EXITING

    def _update_bottom_hand_animation(self, dt: float) -> None:
        target_rects = self.rects.bottom_target_rects(
            hand_count=len(self.session.state.hand),
            selected_indices=self.session.state.selected_indices,
            round_phase=self.round_phase,
        )
        if len(self.bottom_card_positions) != len(target_rects):
            self._reset_bottom_card_positions()
            return

        factor = min(1.0, self.config.animation.move_speed * dt)

        for position, target_rect in zip(self.bottom_card_positions, target_rects):
            target = pygame.Vector2(target_rect.x, target_rect.y)
            position.update(position.lerp(target, factor))
            if position.distance_to(target) <= 1.0:
                position.update(target)

    def _update_played_hand_animation(self, dt: float) -> None:
        if not self.animated_played_positions:
            return

        if self.round_phase == RoundPhase.MOVING_TO_CENTER:
            target_rects = self.rects.center_played_card_rects(len(self.session.state.played_cards))
            all_reached = self._move_vectors_to_rects(
                self.animated_played_positions,
                target_rects,
                dt,
                self.config.animation.move_speed,
            )
            self.center_move_active = not all_reached
            return

        if self.round_phase == RoundPhase.EXITING_PLAYED:
            target_rects = self.rects.exit_played_card_rects(len(self.session.state.played_cards))
            all_reached = self._move_vectors_to_rects(
                self.animated_played_positions,
                target_rects,
                dt,
                self.config.animation.played_exit_speed,
            )
            if all_reached:
                self._begin_refill_animation()

    def _update_discard_animation(self, dt: float) -> None:
        if self.round_phase != RoundPhase.DISCARD_EXITING:
            return
        if not self.animated_discard_positions:
            return

        target_rects = self.rects.exit_discard_card_rects(self.animated_discard_positions)
        all_reached = self._move_vectors_to_rects(
            self.animated_discard_positions,
            target_rects,
            dt,
            self.config.animation.played_exit_speed,
        )
        if all_reached:
            self._begin_discard_refill_animation()

    def _update_round_phase(self, dt: float) -> None:
        if self.round_phase == RoundPhase.IDLE:
            return

        if self.round_phase == RoundPhase.MOVING_TO_CENTER:
            if not self.center_move_active:
                self.round_phase = RoundPhase.SCORE_DELAY
                self.score_delay_timer = 0.0
            return

        if self.round_phase == RoundPhase.SCORE_DELAY:
            self.score_delay_timer += dt
            if self.score_delay_timer >= self.config.animation.score_start_delay:
                self.round_phase = RoundPhase.SCORE_SEQUENCE
                self.score_step_index = 0
                self.score_step_timer = 0.0
            return

        if self.round_phase == RoundPhase.SCORE_SEQUENCE:
            scoring_indices = self.session.state.scoring_card_indices
            if not scoring_indices:
                self.session.commit_play_score()
                self.round_phase = RoundPhase.EXITING_PLAYED
                return

            self.score_step_timer += dt
            if self.score_step_timer >= self.config.animation.score_step_duration:
                self.session.apply_next_card_bonus()
                self.score_step_index += 1
                self.score_step_timer = 0.0

                if self.score_step_index >= len(scoring_indices):
                    self.round_phase = RoundPhase.SCORE_FINAL_FADE
                    self.score_final_fade_timer = 0.0
            return

        if self.round_phase == RoundPhase.SCORE_FINAL_FADE:
            self.score_final_fade_timer += dt
            if self.score_final_fade_timer >= self.config.animation.score_final_fade_duration:
                self.session.commit_play_score()
                self.round_phase = RoundPhase.EXITING_PLAYED
            return

        if self.round_phase == RoundPhase.REFILLING:
            if self._bottom_positions_match_targets():
                self.round_phase = RoundPhase.IDLE

    def _begin_refill_animation(self) -> None:
        selected_indices = set(self.session.state.selected_indices)

        remaining_positions = [
            pygame.Vector2(position.x, position.y)
            for index, position in enumerate(self.bottom_card_positions)
            if index not in selected_indices
        ]

        drawn_cards = self.session.finish_played_hand()
        spawn_positions = [
            pygame.Vector2(rect.x, rect.y)
            for rect in (self.rects.new_card_spawn_rect(index) for index in range(len(drawn_cards)))
        ]

        self.bottom_card_positions = remaining_positions + spawn_positions
        self.animated_played_positions.clear()
        self.round_phase = RoundPhase.REFILLING

    def _begin_discard_refill_animation(self) -> None:
        selected_indices = set(self.session.state.selected_indices)

        remaining_positions = [
            pygame.Vector2(position.x, position.y)
            for index, position in enumerate(self.bottom_card_positions)
            if index not in selected_indices
        ]

        drawn_cards = self.session.discard_selected()
        spawn_positions = [
            pygame.Vector2(rect.x, rect.y)
            for rect in (self.rects.new_card_spawn_rect(index) for index in range(len(drawn_cards)))
        ]

        self.bottom_card_positions = remaining_positions + spawn_positions
        self.animated_discard_cards.clear()
        self.animated_discard_positions.clear()
        self.round_phase = RoundPhase.REFILLING

    def _move_vectors_to_rects(
        self,
        positions: list[pygame.Vector2],
        target_rects: list[pygame.Rect],
        dt: float,
        speed: float,
    ) -> bool:
        all_reached = True
        factor = min(1.0, speed * dt)

        for position, target_rect in zip(positions, target_rects):
            target = pygame.Vector2(target_rect.x, target_rect.y)
            position.update(position.lerp(target, factor))
            if position.distance_to(target) > 1.0:
                all_reached = False
            else:
                position.update(target)

        return all_reached

    def _bottom_positions_match_targets(self) -> bool:
        target_rects = self.rects.bottom_target_rects(
            hand_count=len(self.session.state.hand),
            selected_indices=self.session.state.selected_indices,
            round_phase=self.round_phase,
        )
        if len(target_rects) != len(self.bottom_card_positions):
            return False

        for position, target_rect in zip(self.bottom_card_positions, target_rects):
            target = pygame.Vector2(target_rect.x, target_rect.y)
            if position.distance_to(target) > 1.0:
                return False

        return True

    def _reset_bottom_card_positions(self) -> None:
        target_rects = self.rects.bottom_target_rects(
            hand_count=len(self.session.state.hand),
            selected_indices=self.session.state.selected_indices,
            round_phase=self.round_phase,
        )
        self.bottom_card_positions = [
            pygame.Vector2(rect.x, rect.y)
            for rect in target_rects
        ]
