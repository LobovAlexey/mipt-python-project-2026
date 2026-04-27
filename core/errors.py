"""Файл для исключений."""

class ProjectError(Exception):
    """Базовое исключение."""


class CoreError(ProjectError):
    """Базовое исключение для ошибок ядра игры."""


class NoCardsLeft(CoreError):
    """Вызывается при попытке получить карту из пустой колоды."""


class InvalidMove(CoreError):
    """Вызывается при попытке сделать недопустимое действие."""


class SelectionError(CoreError):
    """Вызывается при неудачном выборе карты."""


class UIError(ProjectError):
    """Базовое исключение для ошибок интерфейса игры."""


class AssetLoadError(UIError):
    """Вызывается, когда необходимый файл не был найден."""


class ProfileStorageError(UIError):
    """Вызывается при неуспешной попытке получения/записи данных профилей."""
