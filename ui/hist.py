"""Построение простой гистограммы статистики профиля через matplotlib."""

import pygame
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from profiles.profiles import HAND_NAME_TO_STAT_FIELD, ProfileStats


class ProfileHistogram:
    """Строит и кеширует изображение гистограммы для выбранного профиля."""

    def __init__(self) -> None:
        self._cache_key: tuple[tuple[str, int], tuple[int, int]] | None = None
        self._cache_surface: pygame.Surface | None = None

    def render(
        self,
        profile: ProfileStats,
        size: tuple[int, int],
        *,
        background_color: tuple[int, int, int],
        bar_color: tuple[int, int, int],
        text_color: tuple[int, int, int],
        grid_color: tuple[int, int, int],
    ) -> pygame.Surface:
        """Возвращает готовую поверхность с гистограммой."""
        stats_items = tuple(
            (hand_name, profile.hand_stats.get(field_name, 0))
            for hand_name, field_name in HAND_NAME_TO_STAT_FIELD.items()
        )
        cache_key = (stats_items, size)

        if self._cache_key == cache_key and self._cache_surface is not None:
            return self._cache_surface

        width, height = size
        figure = Figure(figsize=(width / 100, height / 100), dpi=100)
        figure.patch.set_facecolor(self._normalize_color(background_color))

        axes = figure.add_subplot(111)
        axes.set_facecolor(self._normalize_color(background_color))

        labels = [item[0] for item in stats_items]
        values = [item[1] for item in stats_items]
        x_positions = list(range(len(labels)))

        axes.bar(
            x_positions,
            values,
            color=self._normalize_color(bar_color),
            width=0.7,
        )

        axes.set_xticks(x_positions)
        axes.set_xticklabels(labels, rotation=35, ha="right", color=self._normalize_color(text_color))
        axes.tick_params(axis="y", colors=self._normalize_color(text_color))
        axes.tick_params(axis="x", colors=self._normalize_color(text_color))

        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.spines["left"].set_color(self._normalize_color(grid_color))
        axes.spines["bottom"].set_color(self._normalize_color(grid_color))

        axes.grid(axis="y", color=self._normalize_color(grid_color), alpha=0.35, linewidth=1)
        axes.set_axisbelow(True)

        max_value = max(values, default=0)
        axes.set_ylim(0, max(1, max_value + 1))

        figure.subplots_adjust(left=0.07, right=0.985, top=0.96, bottom=0.24)

        canvas = FigureCanvasAgg(figure)
        canvas.draw()

        raw_data = canvas.buffer_rgba()
        surface = pygame.image.frombuffer(raw_data, canvas.get_width_height(), "RGBA").convert_alpha()

        self._cache_key = cache_key
        self._cache_surface = surface
        return surface

    @staticmethod
    def _normalize_color(color: tuple[int, int, int]) -> tuple[float, float, float]:
        """Преобразует RGB 0..255 в формат matplotlib 0..1."""
        return tuple(channel / 255 for channel in color)
