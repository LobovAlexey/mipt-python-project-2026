"""Загрузка и выгрузка cloud-профилей в Supabase."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from profiles.profiles import ProfileStats, STAT_FIELDS
from ui.config import SupabaseConfig


class SupabaseProfileClient:
    """Клиент авторизации и синхронизации профилей через Supabase."""

    def __init__(self, config: SupabaseConfig) -> None:
        self.config = config
        self.access_token: str | None = None
        self.user_id: str | None = None

    @property
    def is_logged_in(self) -> bool:
        """Показывает, выполнен ли вход."""
        return bool(self.access_token and self.user_id)

    def login(self, login: str, password: str) -> bool:
        """Выполняет вход; если аккаунта нет, создает его и повторяет вход."""
        if not self.config.anon_key:
            return False

        email = self._normalize_login(login)

        sign_in_data = self._request_json(
            method="POST",
            url=f"{self.config.url}/auth/v1/token?grant_type=password",
            headers={
                "apikey": self.config.anon_key,
                "Content-Type": "application/json",
            },
            body={
                "email": email,
                "password": password,
            },
        )

        if self._apply_auth_response(sign_in_data):
            return True

        signup_data = self._signup(email, password)
        if self._apply_auth_response(signup_data):
            return True

        retry_sign_in_data = self._request_json(
            method="POST",
            url=f"{self.config.url}/auth/v1/token?grant_type=password",
            headers={
                "apikey": self.config.anon_key,
                "Content-Type": "application/json",
            },
            body={
                "email": email,
                "password": password,
            },
        )
        return self._apply_auth_response(retry_sign_in_data)

    def _signup(self, email: str, password: str) -> object | None:
        """Создает нового пользователя Supabase Auth."""
        return self._request_json(
            method="POST",
            url=f"{self.config.url}/auth/v1/signup",
            headers={
                "apikey": self.config.anon_key,
                "Content-Type": "application/json",
            },
            body={
                "email": email,
                "password": password,
            },
        )

    def _apply_auth_response(self, data: object | None) -> bool:
        """Сохраняет данные сессии из ответа auth API."""
        if not isinstance(data, dict):
            return False

        access_token = data.get("access_token")
        user = data.get("user") or {}
        user_id = user.get("id")

        if not access_token or not user_id:
            return False

        self.access_token = str(access_token)
        self.user_id = str(user_id)
        return True

    @staticmethod
    def _normalize_login(login: str) -> str:
        """Преобразует введенный логин в email для Supabase Auth."""
        value = login.strip()
        if "@" in value:
            return value
        return f"{value}@local.game"

    def logout(self) -> None:
        """Сбрасывает локальное состояние входа."""
        self.access_token = None
        self.user_id = None

    def download_profiles(self) -> list[ProfileStats]:
        """Скачивает cloud-профили текущего пользователя."""
        if not self.is_logged_in:
            return []

        user_id = quote(self.user_id or "", safe="-")
        url = (
            f"{self.config.url}/rest/v1/{self.config.table_name}"
            f"?select=*&user_id=eq.{user_id}&order=profile_ind.asc"
        )
        data = self._request_json(
            method="GET",
            url=url,
            headers=self._rest_headers(),
        )
        if not isinstance(data, list):
            return []

        profiles: list[ProfileStats] = []
        for row in data[:3]:
            if not isinstance(row, dict):
                continue

            profile = ProfileStats(
                current_rounds=self._parse_int(row.get("current")),
                record_rounds=self._parse_int(row.get("record")),
                deck=self._parse_int(row.get("deck")),
                hand_stats={
                    field_name: self._parse_int(row.get(field_name))
                    for field_name in STAT_FIELDS
                },
            )
            profile.normalize()
            profiles.append(profile)

        return profiles

    def upload_profiles(self, profiles: list[ProfileStats]) -> bool:
        """Выгружает все cloud-профили текущего пользователя."""
        if not self.is_logged_in:
            return False

        user_id = quote(self.user_id or "", safe="-")
        delete_url = f"{self.config.url}/rest/v1/{self.config.table_name}?user_id=eq.{user_id}"
        delete_result = self._request_json(
            method="DELETE",
            url=delete_url,
            headers={
                **self._rest_headers(),
                "Prefer": "return=minimal",
            },
        )
        if delete_result is None:
            return False

        if not profiles:
            return True

        payload: list[dict[str, int | str]] = []
        for index, profile in enumerate(profiles[:3]):
            row = {
                "user_id": self.user_id,
                "profile_ind": index,
                "current": profile.current_rounds,
                "record": profile.record_rounds,
                "deck": profile.deck,
            }
            for field_name in STAT_FIELDS:
                row[field_name] = int(profile.hand_stats.get(field_name, 0))
            payload.append(row)

        insert_result = self._request_json(
            method="POST",
            url=f"{self.config.url}/rest/v1/{self.config.table_name}",
            headers={
                **self._rest_headers(),
                "Prefer": "return=minimal",
            },
            body=payload,
        )
        return insert_result is not None

    def _rest_headers(self) -> dict[str, str]:
        """Возвращает стандартные заголовки запросов к REST API."""
        return {
            "apikey": self.config.anon_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _parse_int(value: object) -> int:
        """Преобразует значение в неотрицательное целое число."""
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _request_json(
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        body: object | None = None,
    ) -> object | None:
        """Выполняет HTTP-запрос и возвращает JSON-ответ."""
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        request = Request(url=url, data=data, headers=headers, method=method)

        try:
            with urlopen(request, timeout=10) as response:
                raw = response.read().decode("utf-8").strip()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print("SUPABASE HTTP ERROR:", exc.code, body)
            return None
        except (URLError, TimeoutError, ValueError) as exc:
            print("SUPABASE REQUEST ERROR:", repr(exc))
            return None

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
