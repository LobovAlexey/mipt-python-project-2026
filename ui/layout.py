"""Файл для создания прямоугольников для интерфейса."""

from dataclasses import dataclass

import pygame

from ui.config import AppConfig
from ui.enums import RoundPhase


@dataclass(frozen=True, slots=True)
class RectFactory:
    """Вычисляет прямоугольные области интерфейса по настройкам приложения."""

    config: AppConfig

    @property
    def window_size(self) -> tuple[int, int]:
        """Возвращает размер окна приложения."""
        return self.config.window.size

    def sidebar_inner_rect(self) -> pygame.Rect:
        """Возвращает внутреннюю область боковой панели."""
        return pygame.Rect(20, 20, self.config.layout.sidebar_width - 40, self.window_size[1] - 40)

    def title_rect(self) -> pygame.Rect:
        """Возвращает область заголовка в боковой панели."""
        inner = self.sidebar_inner_rect()
        return pygame.Rect(inner.x, inner.y, inner.width, 72)

    def total_chips_rect(self) -> pygame.Rect:
        """Возвращает область блока общего счета."""
        inner = self.sidebar_inner_rect()
        title = self.title_rect()
        return pygame.Rect(inner.x, title.bottom + 18, inner.width, 130)

    def chips_rect(self) -> pygame.Rect:
        """Возвращает область блока текущих фишек."""
        inner = self.sidebar_inner_rect()
        total = self.total_chips_rect()
        return pygame.Rect(inner.x, total.bottom + 18, inner.width, 100)

    def mult_rect(self) -> pygame.Rect:
        """Возвращает область блока текущего множителя."""
        inner = self.sidebar_inner_rect()
        chips = self.chips_rect()
        return pygame.Rect(inner.x, chips.bottom + 18, inner.width, 100)

    def hand_area_rect(self) -> pygame.Rect:
        """Возвращает область размещения руки игрока."""
        layout = self.config.layout
        x = layout.sidebar_width + layout.hand_area_margin_x
        y = self.window_size[1] - layout.hand_area_height - layout.hand_area_margin_bottom
        width = self.window_size[0] - layout.sidebar_width - 2 * layout.hand_area_margin_x
        return pygame.Rect(x, y, width, layout.hand_area_height)

    def sidebar_deck_rect(self) -> pygame.Rect:
        """Возвращает область колоды в боковой панели."""
        hand_area = self.hand_area_rect()
        inner = self.sidebar_inner_rect()
        rect = pygame.Rect(0, 0, *self.config.layout.card_size)
        rect.right = inner.right
        rect.centery = hand_area.centery
        return rect

    def info_button_rect(self) -> pygame.Rect:
        """Возвращает область кнопки информации."""
        deck = self.sidebar_deck_rect()
        top = self.mult_rect().bottom + 18
        bottom = deck.y - 18
        return pygame.Rect(deck.x, top, deck.width, max(44, bottom - top))

    def play_box_rect(self) -> pygame.Rect:
        """Возвращает область панели действия Play."""
        inner = self.sidebar_inner_rect()
        return pygame.Rect(
            inner.x,
            self.config.layout.action_top,
            self.config.layout.action_box_size[0],
            self.config.layout.action_box_size[1],
        )

    def discard_box_rect(self) -> pygame.Rect:
        """Возвращает область панели действия Discard."""
        play_box = self.play_box_rect()
        deck = self.sidebar_deck_rect()
        return pygame.Rect(
            play_box.x,
            deck.bottom - self.config.layout.action_box_size[1],
            play_box.width,
            self.config.layout.action_box_size[1],
        )

    def play_button_rect(self) -> pygame.Rect:
        """Возвращает область кнопки Play."""
        box = self.play_box_rect()
        return pygame.Rect(box.x + 8, box.y + 10, box.width - 16, self.config.layout.action_button_height)

    def discard_button_rect(self) -> pygame.Rect:
        """Возвращает область кнопки Discard."""
        box = self.discard_box_rect()
        return pygame.Rect(box.x + 8, box.y + 10, box.width - 16, self.config.layout.action_button_height)

    def play_counter_rect(self) -> pygame.Rect:
        """Возвращает область счетчика оставшихся ходов Play."""
        box = self.play_box_rect()
        button = self.play_button_rect()
        return pygame.Rect(box.x + 8, button.bottom + 6, box.width - 16, box.bottom - button.bottom - 10)

    def discard_counter_rect(self) -> pygame.Rect:
        """Возвращает область счетчика оставшихся Discard."""
        box = self.discard_box_rect()
        button = self.discard_button_rect()
        return pygame.Rect(box.x + 8, button.bottom + 6, box.width - 16, box.bottom - button.bottom - 10)

    def round_popup_rect(self) -> pygame.Rect:
        """Возвращает область всплывающего окна конца раунда."""
        rect = pygame.Rect(0, 0, 520, 320)
        rect.center = (self.window_size[0] // 2, self.window_size[1] // 2)
        return rect

    def popup_primary_button_rect(self) -> pygame.Rect:
        """Возвращает область основной кнопки во всплывающем окне."""
        popup = self.round_popup_rect()
        return pygame.Rect(popup.x + 36, popup.bottom - 88, 200, 56)

    def popup_secondary_button_rect(self) -> pygame.Rect:
        """Возвращает область дополнительной кнопки во всплывающем окне."""
        popup = self.round_popup_rect()
        return pygame.Rect(popup.right - 236, popup.bottom - 88, 200, 56)

    def profile_slot_rects(self) -> list[pygame.Rect]:
        """Возвращает области всех слотов профилей."""
        layout = self.config.layout
        width, height = layout.profile_box_size

        total_width = layout.profile_cols * width + (layout.profile_cols - 1) * layout.profile_gap_x
        total_height = layout.profile_rows * height + (layout.profile_rows - 1) * layout.profile_gap_y

        start_x = (self.window_size[0] - total_width) // 2
        start_y = (self.window_size[1] - total_height) // 2 - 10

        rects: list[pygame.Rect] = []
        for row in range(layout.profile_rows):
            for col in range(layout.profile_cols):
                rects.append(
                    pygame.Rect(
                        start_x + col * (width + layout.profile_gap_x),
                        start_y + row * (height + layout.profile_gap_y),
                        width,
                        height,
                    )
                )

        return rects

    def profile_delete_rect(self, profile_rect: pygame.Rect) -> pygame.Rect:
        """Возвращает область кнопки удаления профиля."""
        size = self.config.layout.profile_delete_size
        return pygame.Rect(profile_rect.right - size - 10, profile_rect.y + 10, size, size)

    def profile_settings_rect(self, profile_rect: pygame.Rect) -> pygame.Rect:
        """Возвращает область кнопки настроек профиля."""
        size = self.config.layout.profile_delete_size
        return pygame.Rect(profile_rect.right - size - 10, profile_rect.bottom - size - 10, size, size)

    def settings_deck_rects(self) -> list[pygame.Rect]:
        """Возвращает области трех рубашек колоды в настройках."""
        inner = self.sidebar_inner_rect()
        title = self.title_rect()
        width, height = self.config.layout.card_size

        start_x = inner.centerx - width // 2
        start_y = title.bottom + 18
        gap = 18

        return [
            pygame.Rect(start_x, start_y + index * (height + gap), width, height)
            for index in range(3)
        ]

    def settings_back_button_rect(self) -> pygame.Rect:
        """Возвращает область кнопки Back to menu."""
        inner = self.sidebar_inner_rect()
        width = inner.width
        height = 56
        return pygame.Rect(inner.x, inner.bottom - height * 2 - 10, width, height)

    def settings_play_button_rect(self) -> pygame.Rect:
        """Возвращает область кнопки Play."""
        inner = self.sidebar_inner_rect()
        width = inner.width
        height = 56
        return pygame.Rect(inner.x, inner.bottom - height, width, height)

    def bottom_target_rects(
        self,
        hand_count: int,
        selected_indices: set[int],
        round_phase: RoundPhase,
    ) -> list[pygame.Rect]:
        """Возвращает области клика по картам нижней руки."""
        if hand_count == 0:
            return []

        layout = self.config.layout
        hand_area = self.hand_area_rect()
        total_width = hand_count * layout.card_size[0] + (hand_count - 1) * layout.card_gap
        start_x = hand_area.x + (hand_area.width - total_width) // 2
        centered_y = hand_area.centery - layout.card_size[1] // 2

        rects: list[pygame.Rect] = []
        for index in range(hand_count):
            y = centered_y
            if round_phase == RoundPhase.IDLE and index in selected_indices:
                y -= layout.selected_card_offset

            rects.append(
                pygame.Rect(
                    start_x + index * (layout.card_size[0] + layout.card_gap),
                    y,
                    layout.card_size[0],
                    layout.card_size[1],
                )
            )

        return rects

    def bottom_hitbox_rects(self, positions: list[pygame.Vector2]) -> list[pygame.Rect]:
        """Возвращает области клика по картам нижней руки."""
        width, height = self.config.layout.card_size
        return [pygame.Rect(round(pos.x), round(pos.y), width, height) for pos in positions]

    def center_played_card_rects(self, played_count: int) -> list[pygame.Rect]:
        """Возвращает области сыгранных карт в центре стола."""
        if played_count == 0:
            return []

        layout = self.config.layout
        total_width = played_count * layout.card_size[0] + (played_count - 1) * layout.played_card_gap
        available_width = self.window_size[0] - layout.sidebar_width
        start_x = layout.sidebar_width + (available_width - total_width) // 2
        y = self.window_size[1] // 2 - layout.card_size[1] // 2

        return [
            pygame.Rect(
                start_x + index * (layout.card_size[0] + layout.played_card_gap),
                y,
                layout.card_size[0],
                layout.card_size[1],
            )
            for index in range(played_count)
        ]

    def exit_played_card_rects(self, played_count: int) -> list[pygame.Rect]:
        """Возвращает области выхода сыгранных карт за экран."""
        if played_count == 0:
            return []

        layout = self.config.layout
        y = self.window_size[1] // 2 - layout.card_size[1] // 2
        start_x = self.window_size[0] + 40

        return [
            pygame.Rect(
                start_x + index * (layout.card_size[0] + layout.played_card_gap),
                y,
                layout.card_size[0],
                layout.card_size[1],
            )
            for index in range(played_count)
        ]

    def exit_discard_card_rects(self, positions: list[pygame.Vector2]) -> list[pygame.Rect]:
        """Возвращает области выхода сбрасываемых карт за экран."""
        width, height = self.config.layout.card_size
        return [
            pygame.Rect(self.window_size[0] + 40 + index * 24, round(pos.y), width, height)
            for index, pos in enumerate(positions)
        ]

    def new_card_spawn_rect(self, drawn_index: int) -> pygame.Rect:
        """Возвращает стартовую область появления новой карты."""
        deck = self.sidebar_deck_rect()
        width, height = self.config.layout.card_size
        x = deck.centerx - width // 2 + drawn_index * 6
        y = deck.bottom + 24 + drawn_index * 4
        return pygame.Rect(x, y, width, height)