"""Классы для хранения и загрузки игровых профилей."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from core.decks import get_deck_types
from core.errors import ProfileStorageError
from core.hands import ALL_COMBINATIONS, HAND_NAME_IND

AVAILABLE_DECK_NAMES = tuple(deck_type.deck_name for deck_type in get_deck_types())
DECK_NAME_TO_INDEX = {name: index for index, name in enumerate(AVAILABLE_DECK_NAMES)}

STAT_FIELDS = tuple(i.stat_field_name for i in ALL_COMBINATIONS)
HAND_NAME_TO_STAT_FIELD = {i: ALL_COMBINATIONS[HAND_NAME_IND[i]].stat_field_name for i in HAND_NAME_IND}


def _default_hand_stats() -> dict[str, int]:
    """Возвращает словарь со статистикой комбинаций по умолчанию."""
    return {field_name: 0 for field_name in STAT_FIELDS}


@dataclass(slots=True)
class ProfileStats:
    """Статистика одного игрового профиля."""

    current_rounds: int = 0
    record_rounds: int = 0
    deck: int = 0
    hand_stats: dict[str, int] = field(default_factory=_default_hand_stats)

    @property
    def deck_name(self) -> str:
        """Возвращает имя колоды по числовому индексу."""
        return AVAILABLE_DECK_NAMES[self.deck]

    def normalize(self) -> None:
        """Приводит значения статистики к корректному виду."""
        self.current_rounds = max(0, int(self.current_rounds))
        self.record_rounds = max(0, int(self.record_rounds))
        if self.current_rounds > self.record_rounds:
            self.record_rounds = self.current_rounds

        self.deck = max(0, min(int(self.deck), len(AVAILABLE_DECK_NAMES) - 1))

        normalized_stats = _default_hand_stats()
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

    def set_deck(self, index: int, deck: int) -> None:
        """Сохраняет выбранную рубашку колоды."""
        profile = self.get(index)
        profile.deck = deck
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

    def replace_profiles(self, profiles: list[ProfileStats]) -> None:
        """Полностью заменяет содержимое репозитория."""
        copied_profiles: list[ProfileStats] = []
        for profile in profiles[: self.max_profiles]:
            copied_profile = ProfileStats(
                current_rounds=profile.current_rounds,
                record_rounds=profile.record_rounds,
                deck=profile.deck,
                hand_stats=dict(profile.hand_stats),
            )
            copied_profile.normalize()
            copied_profiles.append(copied_profile)

        self.profiles = copied_profiles
        self.save()

    def clear(self) -> None:
        """Очищает репозиторий."""
        self.profiles = []
        self.save()

    def save(self) -> None:
        """Сохраняет профили в CSV-файл."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with self.file_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(self.CSV_HEADER)
                for profile in self.profiles[: self.max_profiles]:
                    writer.writerow(
                        [
                            profile.current_rounds,
                            profile.record_rounds,
                            profile.deck,
                            *(profile.hand_stats[field_name] for field_name in STAT_FIELDS),
                        ]
                    )
        except OSError as exc:
            raise ProfileStorageError(f"Cannot write profiles file: {self.file_path}") from exc

    def load(self) -> None:
        """Загружает профили из CSV-файла."""
        self.profiles = []

        if not self.file_path.exists():
            self.save()
            return

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
                        deck=self._parse_deck(row.get("deck")),
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

    @staticmethod
    def _parse_deck(value: str | None) -> int:
        """Преобразует строку из CSV в индекс колоды."""
        if value is None:
            return 0

        stripped = str(value).strip()
        if not stripped:
            return 0

        if stripped in DECK_NAME_TO_INDEX:
            return DECK_NAME_TO_INDEX[stripped]

        try:
            parsed = int(stripped)
        except (TypeError, ValueError):
            return 0

        return max(0, min(parsed, len(AVAILABLE_DECK_NAMES) - 1))
