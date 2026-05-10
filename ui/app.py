"""Основной модуль приложения PyGame."""

import pygame

from core.cards import Card
from core.decks import get_deck_type, get_deck_types
from core.errors import InvalidMove
from core.game import GameSession
from profiles.cloud import SupabaseProfileClient
from profiles.profiles import ProfileRepository
from ui.assets import AppAssets
from ui.config import AppConfig
from ui.enums import AppMode, PopupKind, RoundPhase
from ui.layout import RectFactory
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

        self.local_profiles = ProfileRepository(self.config.paths.profiles_csv, 3)
        self.cloud_profiles = ProfileRepository(self.config.paths.cloud_profiles_csv, 3)
        self.cloud_client = SupabaseProfileClient(self.config.supabase)

        self.selected_profile_slot: int | None = None

        self.login_popup_open = False
        self.login_input = ""
        self.password_input = ""
        self.active_login_field: str | None = None
        self.logged_in_login: str | None = None
        self.login_error_text: str | None = None

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

        if self.cloud_client.is_logged_in:
            self._logout_from_cloud(sync_only=True)

        pygame.quit()

    def is_cloud_slot(self, slot: int) -> bool:
        """Проверяет, относится ли слот к cloud-профилям."""
        return slot >= 3

    def _repo_index_for_slot(self, slot: int) -> int:
        """Возвращает индекс профиля внутри репозитория."""
        return slot % 3

    def _profile_repository_for_slot(self, slot: int) -> ProfileRepository | None:
        """Возвращает репозиторий для слота меню."""
        if 0 <= slot < 3:
            return self.local_profiles
        if 3 <= slot < 6 and self.logged_in_login is not None:
            return self.cloud_profiles
        return None

    def profile_slot_display_number(self, slot: int) -> int:
        """Возвращает номер профиля внутри локальной или cloud-тройки."""
        return self._repo_index_for_slot(slot) + 1

    def selected_profile_display_number(self) -> int | None:
        """Возвращает номер выбранного профиля внутри своей тройки."""
        if self.selected_profile_slot is None:
            return None
        return self.profile_slot_display_number(self.selected_profile_slot)

    def is_slot_selected(self, slot: int) -> bool:
        """Проверяет, выбран ли слот."""
        return self.selected_profile_slot == slot

    def profile_slot_kind(self, index: int) -> str:
        """Возвращает тип слота профиля в меню."""
        repository = self._profile_repository_for_slot(index)
        if repository is None:
            return "inactive"

        repo_index = self._repo_index_for_slot(index)
        if repo_index < repository.count():
            return "created"
        if repo_index == repository.count() and repository.count() < repository.max_profiles:
            return "plus"
        return "inactive"

    def profile_by_slot(self, slot: int):
        """Возвращает профиль по номеру слота меню."""
        repository = self._profile_repository_for_slot(slot)
        if repository is None:
            return None

        repo_index = self._repo_index_for_slot(slot)
        if not repository.exists(repo_index):
            return None
        return repository.get(repo_index)

    def current_repository(self) -> ProfileRepository | None:
        """Возвращает репозиторий выбранного профиля."""
        if self.selected_profile_slot is None:
            return None
        return self._profile_repository_for_slot(self.selected_profile_slot)

    def current_profile_index(self) -> int | None:
        """Возвращает индекс выбранного профиля внутри репозитория."""
        if self.selected_profile_slot is None:
            return None
        return self._repo_index_for_slot(self.selected_profile_slot)

    def current_profile(self):
        """Возвращает текущий выбранный профиль."""
        repository = self.current_repository()
        profile_index = self.current_profile_index()
        if repository is None or profile_index is None:
            return None
        if not repository.exists(profile_index):
            return None
        return repository.get(profile_index)

    def selected_profile_deck_name(self) -> str:
        """Возвращает название выбранной колоды профиля."""
        profile = self.current_profile()
        if profile is None:
            return get_deck_types()[0].deck_name
        return profile.deck_name

    def current_win_score(self) -> int:
        """Возвращает цель по фишкам для победы."""
        profile = self.current_profile()
        current_rounds = 0 if profile is None else profile.current_rounds
        return self.config.gameplay.base_win_score + self.config.gameplay.win_score_step * current_rounds

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
                continue

            if event.type == pygame.KEYDOWN and self.login_popup_open:
                self._handle_login_keydown(event)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode == AppMode.MENU:
                    if self.login_popup_open:
                        self._handle_login_popup_click(event.pos)
                    else:
                        self._handle_menu_click(event.pos)
                    continue

                if self.mode == AppMode.PROFILE_SETTINGS:
                    self._handle_profile_settings_click(event.pos)
                    continue

                if self.popup_kind != PopupKind.NONE:
                    if self.rects.popup_primary_button_rect().collidepoint(event.pos):
                        self._start_game_for_selected_profile()
                    elif self.rects.popup_secondary_button_rect().collidepoint(event.pos):
                        self._back_to_menu()
                    continue

                self._handle_game_click(event.pos)

    def _handle_menu_click(self, mouse_pos: tuple[int, int]) -> None:
        if self.rects.menu_auth_button_rect().collidepoint(mouse_pos):
            if self.logged_in_login is None:
                self.login_popup_open = True
                self.active_login_field = "login"
                self.login_error_text = None
            else:
                self._logout_from_cloud()
            return

        for index, rect in enumerate(self.rects.profile_slot_rects()):
            if not rect.collidepoint(mouse_pos):
                continue

            kind = self.profile_slot_kind(index)

            if kind == "created" and self.rects.profile_delete_rect(rect).collidepoint(mouse_pos):
                self._delete_profile(index)
                return

            if kind == "created" and self.rects.profile_settings_rect(rect).collidepoint(mouse_pos):
                self.selected_profile_slot = index
                self.mode = AppMode.PROFILE_SETTINGS
                return

            if kind == "inactive":
                return

            if kind == "plus":
                self._create_profile(index)
                return

            if self.selected_profile_slot == index:
                self._start_game_for_selected_profile()
            else:
                self.selected_profile_slot = index
            return

    def _handle_login_popup_click(self, mouse_pos: tuple[int, int]) -> None:
        if self.rects.login_input_rect().collidepoint(mouse_pos):
            self.active_login_field = "login"
            return

        if self.rects.password_input_rect().collidepoint(mouse_pos):
            self.active_login_field = "password"
            return

        if self.rects.login_submit_button_rect().collidepoint(mouse_pos):
            self._attempt_login()
            return

        if self.rects.login_cancel_button_rect().collidepoint(mouse_pos):
            self._close_login_popup()

    def _handle_login_keydown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._close_login_popup()
            return

        if event.key == pygame.K_TAB:
            self.active_login_field = "password" if self.active_login_field == "login" else "login"
            return

        if event.key == pygame.K_RETURN:
            self._attempt_login()
            return

        if self.active_login_field not in {"login", "password"}:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.active_login_field == "login":
                self.login_input = self.login_input[:-1]
            else:
                self.password_input = self.password_input[:-1]
            return

        if event.unicode and event.unicode.isprintable():
            if self.active_login_field == "login":
                self.login_input += event.unicode
            else:
                self.password_input += event.unicode

    def _attempt_login(self) -> None:
        if not self.login_input or not self.password_input:
            self.login_error_text = "Fill in all fields"
            return

        if not self.cloud_client.login(self.login_input, self.password_input):
            self.login_error_text = "Invalid login data"
            return

        self.login_error_text = None
        self.logged_in_login = self.login_input
        cloud_profiles = self.cloud_client.download_profiles()
        self.cloud_profiles.replace_profiles(cloud_profiles)

        self.login_popup_open = False
        self.active_login_field = None
        self.password_input = ""

    def _close_login_popup(self) -> None:
        self.login_popup_open = False
        self.active_login_field = None
        self.login_error_text = None
        self.login_input = ""
        self.password_input = ""

    def _logout_from_cloud(self, *, sync_only: bool = False) -> None:
        self.cloud_client.upload_profiles(self.cloud_profiles.profiles)
        self.cloud_profiles.clear()
        self.cloud_client.logout()

        self.logged_in_login = None
        self.login_popup_open = False
        self.active_login_field = None
        self.login_input = ""
        self.password_input = ""

        if self.selected_profile_slot is not None and self.is_cloud_slot(self.selected_profile_slot):
            self.selected_profile_slot = None
            if not sync_only:
                self._back_to_menu()

    def profile_slot_label(self, slot: int) -> str:
        """Возвращает отображаемое имя слота профиля."""
        kind = "Cloud" if self.is_cloud_slot(slot) else "Local"
        return f"{kind} {self.profile_slot_display_number(slot)}"

    def selected_profile_label(self) -> str:
        """Возвращает отображаемое имя выбранного профиля."""
        if self.selected_profile_slot is None:
            return "Profile"
        return self.profile_slot_label(self.selected_profile_slot)

    def _handle_profile_settings_click(self, mouse_pos: tuple[int, int]) -> None:
        repository = self.current_repository()
        profile_index = self.current_profile_index()

        if repository is None or profile_index is None or not repository.exists(profile_index):
            self._back_to_menu()
            return

        for deck_index, rect in enumerate(self.rects.settings_deck_rects()):
            if rect.collidepoint(mouse_pos):
                repository.set_deck(profile_index, deck_index)
                return

        if self.rects.settings_back_button_rect().collidepoint(mouse_pos):
            self._back_to_menu()
            return

        if self.rects.settings_play_button_rect().collidepoint(mouse_pos):
            self._start_game_for_selected_profile()

    def _handle_game_click(self, mouse_pos: tuple[int, int]) -> None:
        if self.rects.info_button_rect().collidepoint(mouse_pos):
            self._back_to_menu()
            return

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

    def _create_profile(self, slot: int) -> None:
        repository = self._profile_repository_for_slot(slot)
        if repository is None:
            return

        new_index = repository.create_profile()
        if new_index is not None:
            self.selected_profile_slot = (3 if self.is_cloud_slot(slot) else 0) + new_index

    def _delete_profile(self, slot: int) -> None:
        repository = self._profile_repository_for_slot(slot)
        if repository is None:
            return

        repo_index = self._repo_index_for_slot(slot)
        repository.delete_profile(repo_index)

        if self.selected_profile_slot is None:
            return
        if self.selected_profile_slot == slot:
            self.selected_profile_slot = None
            return

        if self.is_cloud_slot(self.selected_profile_slot) != self.is_cloud_slot(slot):
            return

        selected_repo_index = self._repo_index_for_slot(self.selected_profile_slot)
        if selected_repo_index > repo_index:
            offset = 3 if self.is_cloud_slot(slot) else 0
            self.selected_profile_slot = offset + selected_repo_index - 1

    def _start_game_for_selected_profile(self) -> None:
        profile = self.current_profile()
        if profile is None:
            return

        deck_cls = get_deck_type(profile.deck_name)

        self.session = GameSession()
        self.session.start_new_game(deck_cls)

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
        repository = self.current_repository()
        profile_index = self.current_profile_index()
        if repository is None or profile_index is None or not repository.exists(profile_index):
            return

        repository.increment_current_round(profile_index)
        self.popup_kind = PopupKind.WIN

    def _finish_loss_round(self) -> None:
        repository = self.current_repository()
        profile_index = self.current_profile_index()

        if repository is not None and profile_index is not None and repository.exists(profile_index):
            repository.reset_current_round(profile_index)

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

        if self.session.state.total_chips >= self.current_win_score():
            self._finish_win_round()
            return

        if self.session.cards_remaining <= 0 and not self.session.state.hand:
            self._finish_loss_round()
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

        repository = self.current_repository()
        profile_index = self.current_profile_index()
        if repository is not None and profile_index is not None and repository.exists(profile_index):
            repository.increment_hand_stat(
                profile_index,
                self.session.state.played_hand_label,
            )

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
