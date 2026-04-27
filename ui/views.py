"""Классы для отрисовки интерфейса игры."""

from dataclasses import dataclass

import pygame

from core.cards import Card
from ui.assets import AppAssets
from ui.config import AppConfig
from ui.enums import AppMode, PopupKind, RoundPhase
from ui.layout import RectFactory


@dataclass(frozen=True, slots=True)
class FontSet:
    """Набор шрифтов, используемых в интерфейсе."""

    title: pygame.font.Font
    label: pygame.font.Font
    value: pygame.font.Font
    small: pygame.font.Font
    tiny: pygame.font.Font
    button: pygame.font.Font
    deck_badge: pygame.font.Font
    score_badge: pygame.font.Font
    profile_delete: pygame.font.Font

    @classmethod
    def create(cls) -> "FontSet":
        """Создает стандартный набор шрифтов приложения."""
        return cls(
            title=pygame.font.SysFont("arial", 34, bold=True),
            label=pygame.font.SysFont("arial", 24, bold=True),
            value=pygame.font.SysFont("arial", 40, bold=True),
            small=pygame.font.SysFont("arial", 22),
            tiny=pygame.font.SysFont("arial", 20),
            button=pygame.font.SysFont("arial", 26, bold=True),
            deck_badge=pygame.font.SysFont("arial", 28, bold=True),
            score_badge=pygame.font.SysFont("arial", 28, bold=True),
            profile_delete=pygame.font.SysFont("arial", 22, bold=True),
        )


class GameView:
    """Отрисовывает экраны и элементы интерфейса игры."""

    def __init__(
        self,
        screen: pygame.Surface,
        config: AppConfig,
        assets: AppAssets,
        rects: RectFactory,
    ) -> None:
        self.screen = screen
        self.config = config
        self.assets = assets
        self.rects = rects
        self.fonts = FontSet.create()

    def render(self, app: "App") -> None:
        """Отрисовывает текущий экран приложения."""
        self.draw_background()

        if app.mode == AppMode.MENU:
            self.draw_profile_menu(app)
            return

        self.draw_left_sidebar(app)
        self.draw_bottom_hand_area(app)

        if app.session.state.has_played_hand:
            self.draw_played_hand_preview(app)
        if app.round_phase == RoundPhase.DISCARD_EXITING:
            self.draw_discard_exiting_cards(app)
        if app.popup_kind != PopupKind.NONE:
            self.draw_round_popup(app)

    def draw_profile_menu(self, app: "App") -> None:
        """Отрисовывает меню выбора профиля."""
        colors = self.config.colors

        title_rect = pygame.Rect(0, 44, self.config.window.size[0], 50)
        subtitle_rect = pygame.Rect(0, 100, self.config.window.size[0], 32)

        self.draw_centered_text("Choose Profile", self.fonts.title, colors.text_main, title_rect)
        self.draw_centered_text("Click + to create a profile. Click a selected profile to start.", self.fonts.small,
                                colors.text_muted, subtitle_rect)

        profiles = app.profiles.profiles
        for index, rect in enumerate(self.rects.profile_slot_rects()):
            kind = app.profile_slot_kind(index)

            if kind == "inactive":
                fill = colors.profile_inactive
            elif kind == "plus":
                fill = colors.profile_available
            elif app.selected_profile_index == index:
                fill = colors.profile_selected
            else:
                fill = colors.profile_created

            pygame.draw.rect(self.screen, fill, rect, border_radius=18)
            pygame.draw.rect(self.screen, colors.profile_border, rect, width=4, border_radius=18)

            if kind == "inactive":
                continue

            if kind == "plus":
                plus_surface = self.fonts.value.render("+", True, colors.text_main)
                plus_rect = plus_surface.get_rect(center=rect.center)
                self.screen.blit(plus_surface, plus_rect)
                continue

            delete_rect = self.rects.profile_delete_rect(rect)
            pygame.draw.rect(self.screen, colors.profile_delete_fill, delete_rect, border_radius=10)
            pygame.draw.rect(self.screen, colors.profile_border, delete_rect, width=2, border_radius=10)
            delete_surface = self.fonts.profile_delete.render("x", True, colors.text_main)
            delete_text_rect = delete_surface.get_rect(center=delete_rect.center)
            self.screen.blit(delete_surface, delete_text_rect)

            profile = profiles[index]
            text_x = rect.x + 20
            self.draw_text(f"Profile {index + 1}", self.fonts.label, colors.text_main, text_x, rect.y + 24)
            self.draw_text(f"Record: {profile.record_rounds} rounds", self.fonts.small, colors.text_main, text_x,
                           rect.y + 72)
            self.draw_text(f"Current: {profile.current_rounds} rounds", self.fonts.small, colors.text_main, text_x,
                           rect.y + 108)

    def draw_round_popup(self, app: "App") -> None:
        """Отрисовывает всплывающее окно завершения раунда."""
        colors = self.config.colors

        overlay = pygame.Surface(self.config.window.size, pygame.SRCALPHA)
        overlay.fill(colors.overlay_fill)
        self.screen.blit(overlay, (0, 0))

        popup = self.rects.round_popup_rect()
        self.draw_panel(popup, fill=colors.popup_fill)

        title_rect = pygame.Rect(popup.x, popup.y + 18, popup.width, 44)
        line1 = pygame.Rect(popup.x, popup.y + 82, popup.width, 28)
        line2 = pygame.Rect(popup.x, popup.y + 116, popup.width, 28)
        line3 = pygame.Rect(popup.x, popup.y + 150, popup.width, 28)

        if app.popup_kind == PopupKind.WIN:
            title = "Round complete!"
            primary_label = "Next round"
        else:
            title = "You lost"
            primary_label = "Retry round"

        self.draw_centered_text(title, self.fonts.title, colors.text_main, title_rect)

        if app.selected_profile_index is not None and app.profiles.exists(app.selected_profile_index):
            profile = app.profiles.get(app.selected_profile_index)
            self.draw_centered_text(f"Profile {app.selected_profile_index + 1}", self.fonts.label, colors.text_main,
                                    line1)
            self.draw_centered_text(f"Record: {profile.record_rounds} rounds", self.fonts.small, colors.text_muted,
                                    line2)
            self.draw_centered_text(f"Current: {profile.current_rounds} rounds", self.fonts.small, colors.text_muted,
                                    line3)

        self.draw_button(self.rects.popup_primary_button_rect(), primary_label, colors.play_enabled,
                         colors.play_enabled_text)
        self.draw_button(self.rects.popup_secondary_button_rect(), "Back to menu", colors.profile_created,
                         colors.text_main)

    def draw_background(self) -> None:
        """Отрисовывает фон приложения."""
        if self.assets.background is not None:
            self.screen.blit(self.assets.background, (0, 0))
        else:
            self.screen.fill(self.config.colors.bg_fallback)

    def draw_left_sidebar(self, app: "App") -> None:
        """Отрисовывает левую боковую панель."""
        colors = self.config.colors

        sidebar_rect = pygame.Rect(0, 0, self.config.layout.sidebar_width, self.config.window.size[1])
        pygame.draw.rect(self.screen, colors.panel_bg, sidebar_rect)

        title_rect = self.rects.title_rect()
        self.draw_panel(title_rect, fill=colors.info_button)

        profile_label = "Profile"
        if app.selected_profile_index is not None:
            profile_label = f"Profile {app.selected_profile_index + 1}"
        self.draw_centered_text(profile_label, self.fonts.title, colors.text_main, title_rect)

        total_chips_rect = self.rects.total_chips_rect()
        self.draw_panel(total_chips_rect)
        self.draw_text("Total Chips", self.fonts.label, colors.text_muted, total_chips_rect.x + 18,
                       total_chips_rect.y + 16)
        self.draw_text(str(app.session.state.total_chips), self.fonts.value, colors.text_gold, total_chips_rect.x + 18,
                       total_chips_rect.y + 56)

        chips_rect = self.rects.chips_rect()
        self.draw_panel(chips_rect)
        self.draw_text("Chips", self.fonts.label, colors.text_muted, chips_rect.x + 18, chips_rect.y + 14)
        self.draw_text(str(app.session.state.current_chips), self.fonts.value, colors.text_blue, chips_rect.x + 18,
                       chips_rect.y + 42)

        mult_rect = self.rects.mult_rect()
        self.draw_panel(mult_rect)
        self.draw_text("Mult", self.fonts.label, colors.text_muted, mult_rect.x + 18, mult_rect.y + 14)
        self.draw_text(str(app.session.state.current_mult), self.fonts.value, colors.text_red, mult_rect.x + 18,
                       mult_rect.y + 42)

        self.draw_button(self.rects.info_button_rect(), "Info", colors.info_button, colors.text_main)

        self.draw_action_boxes(app)
        self.draw_sidebar_deck(app)

    def draw_action_boxes(self, app: "App") -> None:
        """Отрисовывает панели действий Play и Discard."""
        self.draw_action_box(
            panel_rect=self.rects.play_box_rect(),
            button_rect=self.rects.play_button_rect(),
            counter_rect=self.rects.play_counter_rect(),
            label="Play",
            count=app.plays_left,
            enabled=app.play_button_enabled(),
        )
        self.draw_action_box(
            panel_rect=self.rects.discard_box_rect(),
            button_rect=self.rects.discard_button_rect(),
            counter_rect=self.rects.discard_counter_rect(),
            label="Discard",
            count=app.discards_left,
            enabled=app.discard_button_enabled(),
        )

    def draw_action_box(
        self,
        *,
        panel_rect: pygame.Rect,
        button_rect: pygame.Rect,
        counter_rect: pygame.Rect,
        label: str,
        count: int,
        enabled: bool,
    ) -> None:
        """Отрисовывает одну панель действия с кнопкой и счетчиком."""
        colors = self.config.colors

        pygame.draw.rect(self.screen, colors.action_panel, panel_rect, border_radius=18)
        pygame.draw.rect(self.screen, colors.panel_border, panel_rect, width=4, border_radius=18)

        button_fill = colors.play_enabled if enabled else colors.play_disabled
        button_text = colors.play_enabled_text if enabled else colors.text_muted
        self.draw_button(button_rect, label, button_fill, button_text)

        counter_label = self.fonts.small.render(f"{count} left", True, colors.text_main)
        counter_label_rect = counter_label.get_rect(center=counter_rect.center)
        self.screen.blit(counter_label, counter_label_rect)

    def draw_sidebar_deck(self, app: "App") -> None:
        """Отрисовывает колоду и счетчик оставшихся карт."""
        colors = self.config.colors
        deck_rect = self.rects.sidebar_deck_rect()

        if self.assets.deck_back_image is not None:
            self.screen.blit(self.assets.deck_back_image, deck_rect.topleft)
        else:
            pygame.draw.rect(self.screen, colors.deck_fallback_fill, deck_rect, border_radius=12)
            pygame.draw.rect(self.screen, colors.panel_border, deck_rect, width=3, border_radius=12)

        badge_rect = pygame.Rect(0, 0, self.config.layout.badge_size, self.config.layout.badge_size)
        badge_rect.center = deck_rect.center

        pygame.draw.rect(self.screen, colors.deck_badge_fill, badge_rect, border_radius=10)
        pygame.draw.rect(self.screen, colors.deck_badge_border, badge_rect, width=2, border_radius=10)

        badge_text = self.fonts.deck_badge.render(str(app.session.cards_remaining), True, colors.text_dark)
        badge_text_rect = badge_text.get_rect(center=badge_rect.center)
        self.screen.blit(badge_text, badge_text_rect)

    def draw_bottom_hand_area(self, app: "App") -> None:
        """Отрисовывает нижнюю область руки игрока."""
        colors = self.config.colors

        hand_area_rect = self.rects.hand_area_rect()
        self.draw_rounded_overlay(hand_area_rect, fill_rgba=colors.hand_box_fill, border_rgba=colors.hand_box_border,
                                  border_width=2, radius=16)

        hand = app.session.state.hand
        for index, card in enumerate(hand):
            if app.session.state.has_played_hand and index in app.session.state.selected_indices:
                continue
            if app.round_phase == RoundPhase.DISCARD_EXITING and index in app.session.state.selected_indices:
                continue

            position = app.bottom_card_positions[index]
            draw_rect = pygame.Rect(
                round(position.x),
                round(position.y),
                self.config.layout.card_size[0],
                self.config.layout.card_size[1],
            )
            self.screen.blit(self.assets.card_images.get(card), draw_rect.topleft)

            if app.round_phase == RoundPhase.IDLE and index in app.session.state.selected_indices:
                pygame.draw.rect(
                    self.screen,
                    colors.selected_border,
                    draw_rect.inflate(6, 6),
                    width=3,
                    border_radius=10,
                )

    def draw_played_hand_preview(self, app: "App") -> None:
        """Отрисовывает сыгранные карты и название комбинации."""
        played_cards = app.session.state.played_cards
        if not played_cards:
            return

        label_surface = self.fonts.title.render(app.session.state.played_hand_label, True, self.config.colors.text_main)
        label_rect = label_surface.get_rect(
            center=(
                self.config.layout.sidebar_width
                + (self.config.window.size[0] - self.config.layout.sidebar_width) // 2,
                220,
            )
        )
        self.screen.blit(label_surface, label_rect)

        fallback_rects = self.rects.center_played_card_rects(len(played_cards))
        positions = app.animated_played_positions
        if len(positions) != len(played_cards):
            positions = [pygame.Vector2(rect.x, rect.y) for rect in fallback_rects]

        for index, (card, position) in enumerate(zip(played_cards, positions)):
            card_rect = pygame.Rect(
                round(position.x),
                round(position.y),
                self.config.layout.card_size[0],
                self.config.layout.card_size[1],
            )
            self.screen.blit(self.assets.card_images.get(card), card_rect.topleft)
            self.draw_score_badge_for_card(app, index, card, card_rect)

    def draw_score_badge_for_card(
        self,
        app: "App",
        played_card_index: int,
        card: Card,
        card_rect: pygame.Rect,
    ) -> None:
        """Отрисовывает бейдж очков для сыгранной карты."""
        alpha = self.badge_alpha_for_played_card(app, played_card_index)
        if alpha <= 0:
            return

        badge_rect = pygame.Rect(0, 0, self.config.layout.badge_size, self.config.layout.badge_size)
        badge_rect.center = card_rect.center

        self.draw_alpha_badge(badge_rect=badge_rect, text=str(card.chips), alpha=alpha,
                              fill_color=self.config.colors.score_badge_fill,
                              border_color=self.config.colors.score_badge_border,
                              text_color=self.config.colors.play_enabled_text)

    def badge_alpha_for_played_card(self, app: "App", played_card_index: int) -> int:
        """Возвращает прозрачность бейджа для сыгранной карты."""
        scoring_indices = app.session.state.scoring_card_indices
        if played_card_index not in scoring_indices:
            return 0

        ordered_index = scoring_indices.index(played_card_index)

        if app.round_phase in {
            RoundPhase.IDLE,
            RoundPhase.MOVING_TO_CENTER,
            RoundPhase.SCORE_DELAY,
            RoundPhase.REFILLING,
            RoundPhase.DISCARD_EXITING,
        }:
            return 0

        if app.round_phase == RoundPhase.SCORE_SEQUENCE:
            progress = min(1.0, app.score_step_timer / self.config.animation.score_step_duration)
            if ordered_index == app.score_step_index:
                return round(255 * progress)
            if ordered_index == app.score_step_index - 1:
                return round(255 * (1.0 - progress))
            return 0

        if app.round_phase == RoundPhase.SCORE_FINAL_FADE:
            if ordered_index != len(scoring_indices) - 1:
                return 0
            progress = min(1.0, app.score_final_fade_timer / self.config.animation.score_final_fade_duration)
            return round(255 * (1.0 - progress))

        return 0

    def draw_discard_exiting_cards(self, app: "App") -> None:
        """Отрисовывает карты во время анимации сброса."""
        for card, position in zip(app.animated_discard_cards, app.animated_discard_positions):
            rect = pygame.Rect(
                round(position.x),
                round(position.y),
                self.config.layout.card_size[0],
                self.config.layout.card_size[1],
            )
            self.screen.blit(self.assets.card_images.get(card), rect.topleft)

    def draw_button(
        self,
        rect: pygame.Rect,
        text: str,
        fill_color: tuple[int, int, int],
        text_color: tuple[int, int, int],
    ) -> None:
        """Отрисовывает кнопку с текстом."""
        pygame.draw.rect(self.screen, fill_color, rect, border_radius=14)
        pygame.draw.rect(self.screen, self.config.colors.panel_border, rect, width=3, border_radius=14)
        label = self.fonts.button.render(text, True, text_color)
        label_rect = label.get_rect(center=rect.center)
        self.screen.blit(label, label_rect)

    def draw_panel(
        self,
        rect: pygame.Rect,
        *,
        fill: tuple[int, int, int] | None = None,
    ) -> None:
        """Отрисовывает стандартную панель интерфейса."""
        pygame.draw.rect(
            self.screen,
            fill or self.config.colors.panel_accent,
            rect,
            border_radius=18,
        )
        pygame.draw.rect(
            self.screen,
            self.config.colors.panel_border,
            rect,
            width=4,
            border_radius=18,
        )

    def draw_rounded_overlay(
        self,
        rect: pygame.Rect,
        *,
        fill_rgba: tuple[int, int, int, int],
        border_rgba: tuple[int, int, int, int],
        border_width: int,
        radius: int,
    ) -> None:
        """Отрисовывает полупрозрачную скругленную подложку."""
        surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        local_rect = surface.get_rect()
        pygame.draw.rect(surface, fill_rgba, local_rect, border_radius=radius)
        pygame.draw.rect(surface, border_rgba, local_rect, width=border_width, border_radius=radius)
        self.screen.blit(surface, rect.topleft)

    def draw_alpha_badge(
        self,
        *,
        badge_rect: pygame.Rect,
        text: str,
        alpha: int,
        fill_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
        text_color: tuple[int, int, int],
    ) -> None:
        """Отрисовывает бейдж с настраиваемой прозрачностью."""
        badge_surface = pygame.Surface((badge_rect.width, badge_rect.height), pygame.SRCALPHA)
        local_rect = badge_surface.get_rect()

        pygame.draw.rect(badge_surface, (*fill_color, alpha), local_rect, border_radius=10)
        pygame.draw.rect(badge_surface, (*border_color, alpha), local_rect, width=2, border_radius=10)

        text_surface = self.fonts.score_badge.render(text, True, text_color)
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect(center=local_rect.center)
        badge_surface.blit(text_surface, text_rect)

        self.screen.blit(badge_surface, badge_rect.topleft)

    def draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
    ) -> None:
        """Отрисовывает текст по заданным координатам."""
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def draw_centered_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
    ) -> None:
        """Отрисовывает текст по центру прямоугольной области."""
        surface = font.render(text, True, color)
        surface_rect = surface.get_rect(center=rect.center)
        self.screen.blit(surface, surface_rect)
