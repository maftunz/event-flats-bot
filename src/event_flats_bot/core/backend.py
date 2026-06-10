"""Thin async client around the Event Flats backend API.

Holds a single JWT token: the bot logs in once at startup as a service
account and re-uses the same token for all subsequent reads. On 401, the
client transparently re-logs-in and retries the original request once.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BackendClient:
    def __init__(
        self,
        base_url: str,
        login: str,
        password: str,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._login = login
        self._password = password
        self._token: str | None = None
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _login_call(self) -> None:
        r = await self._client.post(
            "/auth/login/access-token",
            json={"email": self._login, "password": self._password},
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        logger.info("Backend login succeeded")

    async def _ensure_token(self) -> str:
        if self._token is None:
            await self._login_call()
        assert self._token is not None
        return self._token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}
        r = await self._client.request(method, path, params=params, headers=headers)
        if r.status_code == 401:
            # Token expired / revoked — login once more and retry.
            self._token = None
            token = await self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            r = await self._client.request(method, path, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    async def list_addresses(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/addresses")

    async def search_flats(
        self,
        *,
        district: int | None = None,
        rooms_start: int | None = None,
        rooms_end: int | None = None,
        price_start: int | None = None,
        price_end: int | None = None,
        repair: str | None = None,
        page: int = 1,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page": page,
            "order_by": "created_at:desc",
            "sold": 0,
        }
        if district is not None:
            params["district"] = district
        if rooms_start is not None:
            params["rooms_start"] = rooms_start
        if rooms_end is not None:
            params["rooms_end"] = rooms_end
        if price_start is not None:
            params["price_start"] = price_start
        if price_end is not None:
            params["price_end"] = price_end
        if repair is not None:
            params["repair"] = repair
        return await self._request("GET", "/flats", params=params)
