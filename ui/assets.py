"""Загрузка изображений."""

from dataclasses import dataclass, field
from pathlib import Path

import pygame

from core.cards import Card
from core.errors import AssetLoadError
from ui.config import AppConfig


@dataclass(slots=True)
class CardImageRepository:
    """Загружает и обрабатывает изображения карт."""

    image_dir: Path
    card_size: tuple[int, int]
    cache: dict[str, pygame.Surface] = field(default_factory=dict)

    def get(self, card: Card) -> pygame.Surface:
        file_name = card.file_name

        if file_name not in self.cache:
            image_path = self.image_dir / file_name
            if not image_path.exists():
                raise AssetLoadError(f"Missing card image: {image_path}")

            try:
                image = pygame.image.load(image_path.as_posix()).convert_alpha()
            except pygame.error as exc:
                raise AssetLoadError(f"Cannot load card image: {image_path}") from exc

            image = pygame.transform.smoothscale(image, self.card_size)
            self.cache[file_name] = image

        return self.cache[file_name]


@dataclass(slots=True)
class AppAssets:
    """Загруженные изображения для интерфейса."""

    card_images: CardImageRepository
    background: pygame.Surface
    card_size: tuple[int, int]
    deck_back_cache: dict[str, pygame.Surface] = field(default_factory=dict)

    @classmethod
    def load(cls, config: AppConfig) -> "AppAssets":
        return cls(
            card_images=CardImageRepository(
                image_dir=config.paths.card_images_dir,
                card_size=config.layout.card_size,
            ),
            background=cls._load_surface(
                config.paths.background_image,
                config.window.size,
            ),
            card_size=config.layout.card_size,
        )

    def get_deck_back(self, image_path: Path) -> pygame.Surface:
        """Возвращает изображение рубашки колоды."""
        cache_key = image_path.as_posix()

        if not image_path.exists():
            raise AssetLoadError(f"Missing image: {image_path}")

        if cache_key not in self.deck_back_cache:
            try:
                image = pygame.image.load(cache_key).convert_alpha()
            except pygame.error as exc:
                raise AssetLoadError(f"Cannot load image: {image_path}") from exc

            self.deck_back_cache[cache_key] = pygame.transform.smoothscale(image, self.card_size)

        return self.deck_back_cache[cache_key]

    @staticmethod
    def _load_surface(path: Path, size: tuple[int, int]) -> pygame.Surface:
        try:
            image = pygame.image.load(path.as_posix()).convert()
        except pygame.error as exc:
            raise AssetLoadError(f"Cannot load image: {path}") from exc

        return pygame.transform.smoothscale(image, size)