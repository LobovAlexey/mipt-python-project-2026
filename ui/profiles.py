"""Классы для хранения и загрузки игровых профилей."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from core.errors import ProfileStorageError

DEFAULT_DECK_NAME = "standart"
AVAILABLE_DECK_NAMES = ("standart", "short", "hearts-spades")

STAT_FIELDS: tuple[str, ...] = (
    "high_card_cnt",
    "pair_cnt",
    "two_pair_cnt",
    "three_of_a_kind_cnt",
    "straight_cnt",
    "flush_cnt",
    "full_house_cnt",
    "four_of_a_kind_cnt",
    "straight_flush_cnt",
    "five_of_a_kind_cnt",
    "flush_house_cnt",
    "flush_five_cnt",
)

HAND_NAME_TO_STAT_FIELD: dict[str, str] = {
    "High Card": "high_card_cnt",
    "Pair": "pair_cnt",
    "Two Pair": "two_pair_cnt",
    "Three of a Kind": "three_of_a_kind_cnt",
    "Straight": "straight_cnt",
    "Flush": "flush_cnt",
    "Full House": "full_house_cnt",
    "Four of a Kind": "four_of_a_kind_cnt",
    "Straight Flush": "straight_flush_cnt",
    "Five of a Kind": "five_of_a_kind_cnt",
    "Flush House": "flush_house_cnt",
    "Flush Five": "flush_five_cnt",
}


def default_hand_stats() -> dict[str, int]:
    """Возвращает словарь со статистикой комбинаций по умолчанию."""
    return {field_name: 0 for field_name in STAT_FIELDS}


@dataclass(slots=True)
class ProfileStats:
    """Статистика одного игрового профиля."""

    current_rounds: int = 0
    record_rounds: int = 0
    deck_name: str = DEFAULT_DECK_NAME
    hand_stats: dict[str, int] = field(default_factory=default_hand_stats)

    def normalize(self) -> None:
        """Приводит значения статистики к корректному виду."""
        self.current_rounds = max(0, self.current_rounds)
        self.record_rounds = max(0, self.record_rounds)
        if self.current_rounds > self.record_rounds:
            self.record_rounds = self.current_rounds
        if self.deck_name not in AVAILABLE_DECK_NAMES:
            self.deck_name = DEFAULT_DECK_NAME

        normalized_stats = default_hand_stats()
        for field_name in STAT_FIELDS:
            normalized_stats[field_name] = max(0, int(self.hand_stats.get(field_name, 0)))
        self.hand_stats = normalized_stats


class ProfileRepository:
    """CSV-хранилище профилей."""

    CSV_HEADER: tuple[str, ...] = ("current", "record", "deck", *STAT_FIELDS)

    def __init__(self, file_path: Path, max_profiles: int) -> None:
        self.file_path = file_path
        self.max_profiles = max_profiles
        self.profiles: list[ProfileStats] = []
        self.load()

    def count(self) -> int:
        """Возвращает количество сохраненных профилей."""
        return len(self.profiles)

    def exists(self, index: int) -> bool:
        """Проверяет существование профиля по индексу."""
        return 0 <= index < len(self.profiles)

    def get(self, index: int) -> ProfileStats:
        """Возвращает профиль по индексу."""
        if not self.exists(index):
            raise ProfileStorageError(f"Profile index out of range: {index}")
        return self.profiles[index]

    def create_profile(self) -> int | None:
        """Создает новый профиль и возвращает его индекс."""
        if len(self.profiles) >= self.max_profiles:
            return None

        self.profiles.append(ProfileStats())
        self.save()
        return len(self.profiles) - 1

    def delete_profile(self, index: int) -> None:
        """Удаляет профиль по индексу."""
        if not self.exists(index):
            return

        self.profiles.pop(index)
        self.save()

    def increment_current_round(self, index: int) -> None:
        """Увеличивает текущий прогресс профиля на один раунд."""
        profile = self.get(index)
        profile.current_rounds += 1
        profile.normalize()
        self.save()

    def reset_current_round(self, index: int) -> None:
        """Сбрасывает текущий прогресс профиля."""
        profile = self.get(index)
        profile.current_rounds = 0
        profile.normalize()
        self.save()

    def set_deck_name(self, index: int, deck_name: str) -> None:
        """Сохраняет выбранную рубашку колоды."""
        profile = self.get(index)
        profile.deck_name = deck_name
        profile.normalize()
        self.save()

    def increment_hand_stat(self, index: int, hand_name: str) -> None:
        """Увеличивает счетчик сыгранной комбинации."""
        stat_field = HAND_NAME_TO_STAT_FIELD.get(hand_name)
        if stat_field is None:
            return

        profile = self.get(index)
        profile.hand_stats[stat_field] = profile.hand_stats.get(stat_field, 0) + 1
        profile.normalize()
        self.save()

    def save(self) -> None:
        """Сохраняет профили в CSV-файл."""
        try:
            with self.file_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(self.CSV_HEADER)
                for profile in self.profiles[: self.max_profiles]:
                    writer.writerow(
                        (
                            profile.current_rounds,
                            profile.record_rounds,
                            profile.deck_name,
                            *(profile.hand_stats[field_name] for field_name in STAT_FIELDS),
                        )
                    )
        except OSError as exc:
            raise ProfileStorageError(f"Cannot write profiles file: {self.file_path}") from exc

    def load(self) -> None:
        """Загружает профили из CSV-файла."""
        self.profiles = []
        try:
            with self.file_path.open("r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None:
                    return

                for row in reader:
                    if len(self.profiles) >= self.max_profiles:
                        break
                    if not row:
                        continue

                    profile = ProfileStats(
                        current_rounds=self._parse_int(row.get("current")),
                        record_rounds=self._parse_int(row.get("record")),
                        deck_name=(row.get("deck") or DEFAULT_DECK_NAME).strip() or DEFAULT_DECK_NAME,
                        hand_stats={
                            field_name: self._parse_int(row.get(field_name))
                            for field_name in STAT_FIELDS
                        },
                    )
                    profile.normalize()
                    self.profiles.append(profile)
        except OSError as exc:
            raise ProfileStorageError(f"Cannot read profiles file: {self.file_path}") from exc

    @staticmethod
    def _parse_int(value: str | None) -> int:
        """Преобразует строку в неотрицательное целое число."""
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0