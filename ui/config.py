"""Настройки интерфейса."""

from dataclasses import dataclass, field
from pathlib import Path

Color = tuple[int, int, int]
ColorA = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class WindowConfig:
    size: tuple[int, int] = (1365, 768)
    fps: int = 60
    caption: str = "Card Game (Beta)"


@dataclass(frozen=True, slots=True)
class GameplayConfig:
    base_win_score: int = 300
    win_score_step: int = 20
    starting_plays: int = 5
    starting_discards: int = 5


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    sidebar_width: int = 300
    card_size: tuple[int, int] = (110, 160)
    card_gap: int = 12
    selected_card_offset: int = 28
    played_card_gap: int = 18

    hand_area_height: int = 176
    hand_area_margin_x: int = 36
    hand_area_margin_bottom: int = 28

    badge_size: int = 58

    action_box_size: tuple[int, int] = (136, 112)
    action_button_height: int = 60
    action_top: int = 494

    profile_box_size: tuple[int, int] = (300, 170)
    profile_cols: int = 3
    profile_rows: int = 2
    profile_gap_x: int = 26
    profile_gap_y: int = 26
    profile_delete_size: int = 34

    @property
    def max_profiles(self) -> int:
        return self.profile_cols * self.profile_rows


@dataclass(frozen=True, slots=True)
class AnimationConfig:
    move_speed: float = 12.0
    score_start_delay: float = 0.1
    score_step_duration: float = 0.3
    score_final_fade_duration: float = 0.3
    played_exit_speed: float = 14.0


@dataclass(frozen=True, slots=True)
class PathsConfig:
    profiles_csv: Path = Path("data/profiles.csv")
    card_images_dir: Path = Path("images/card_images")
    background_image: Path = Path("images/background.png")


@dataclass(frozen=True, slots=True)
class ColorTheme:
    bg_fallback: Color = (34, 110, 76)
    panel_bg: Color = (28, 37, 43)
    panel_border: Color = (18, 24, 28)
    panel_accent: Color = (74, 104, 93)
    action_panel: Color = (28, 56, 96)
    info_button: Color = (166, 114, 15)

    text_main: Color = (248, 248, 248)
    text_muted: Color = (210, 214, 216)
    text_gold: Color = (255, 202, 76)
    text_blue: Color = (78, 181, 255)
    text_red: Color = (255, 92, 92)
    text_dark: Color = (24, 28, 32)

    selected_border: Color = (255, 230, 120)

    play_disabled: Color = (110, 116, 124)
    play_enabled: Color = (54, 144, 255)
    play_enabled_text: Color = (255, 255, 255)
    discard_disabled: Color = (105, 105, 105)

    profile_created: Color = (144, 152, 162)
    profile_available: Color = (186, 190, 196)
    profile_inactive: Color = (96, 99, 104)
    profile_selected: Color = (54, 144, 255)
    profile_border: Color = (32, 38, 44)
    profile_delete_fill: Color = (178, 68, 68)
    profile_settings_fill: Color = (54, 144, 255)

    hand_box_fill: ColorA = (0, 0, 0, 70)
    hand_box_border: ColorA = (255, 255, 255, 210)

    deck_badge_fill: Color = (242, 242, 242)
    deck_badge_border: Color = (30, 30, 30)
    deck_selected_badge_fill: Color = (72, 176, 88)
    deck_selected_badge_border: Color = (24, 96, 36)
    score_badge_fill: Color = (54, 144, 255)
    score_badge_border: Color = (20, 40, 90)
    deck_fallback_fill: Color = (90, 50, 110)

    popup_fill: Color = (40, 50, 58)
    overlay_fill: ColorA = (0, 0, 0, 150)


@dataclass(frozen=True, slots=True)
class AppConfig:
    window: WindowConfig = field(default_factory=WindowConfig)
    gameplay: GameplayConfig = field(default_factory=GameplayConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    colors: ColorTheme = field(default_factory=ColorTheme)