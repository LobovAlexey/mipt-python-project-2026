"""Классы для хранения и загрузки игровых профилей."""

import csv
from dataclasses import dataclass
from pathlib import Path

from core.errors import ProfileStorageError


@dataclass(slots=True)
class ProfileStats:
    """Статистика одного игрового профиля."""

    current_rounds: int = 0
    record_rounds: int = 0

    def normalize(self) -> None:
        """Приводит значения статистики к корректному виду."""
        self.current_rounds = max(0, self.current_rounds)
        self.record_rounds = max(0, self.record_rounds)
        if self.current_rounds > self.record_rounds:
            self.record_rounds = self.current_rounds


class ProfileRepository:
    """CSV-хранилище профилей."""

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
        self.save()

    def save(self) -> None:
        """Сохраняет профили в CSV-файл."""
        try:
            with self.file_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["current", "record"])
                for profile in self.profiles[: self.max_profiles]:
                    writer.writerow([profile.current_rounds, profile.record_rounds])
        except OSError as exc:
            raise ProfileStorageError(f"Cannot write profiles file: {self.file_path}") from exc

    def load(self) -> None:
        """Загружает профили из CSV-файла."""
        self.profiles = []
        try:
            with self.file_path.open("r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                next(reader, None)
                for row in reader:
                    if len(self.profiles) >= self.max_profiles:
                        break

                    profile = ProfileStats(
                        current_rounds=int(row[0]),
                        record_rounds=int(row[1]),
                    )

                    profile.normalize()
                    self.profiles.append(profile)
        except OSError as exc:
            raise ProfileStorageError(f"Cannot read profiles file: {self.file_path}") from exc
