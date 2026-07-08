"""Spreadconnect (SPOD) API client."""

from __future__ import annotations

from typing import Any

import httpx

SPREADCONNECT_LIVE = "https://api.spreadconnect.app"
SPREADCONNECT_STAGING = "https://rest.spreadconnect-staging.app"


class SpreadconnectAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class SpreadconnectClient:
    def __init__(self, api_key: str, *, staging: bool = False, timeout: float = 60.0):
        self._api_key = api_key
        self._base = SPREADCONNECT_STAGING if staging else SPREADCONNECT_LIVE
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-SPOD-ACCESS-TOKEN": self._api_key, "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.request(
                method, url, headers=self._headers(), params=params, json=json
            )
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            message = resp.text
            if isinstance(data, dict):
                message = str(data.get("message") or data.get("error") or resp.text)
            raise SpreadconnectAPIError(message, status_code=resp.status_code, body=data)
        return data

    async def list_product_types(self) -> Any:
        return await self._request("GET", "/productTypes")

    async def get_product_type(self, product_type_id: str) -> Any:
        return await self._request("GET", f"/productTypes/{product_type_id}")

    async def list_stocks(self) -> Any:
        return await self._request("GET", "/stocks")

    async def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request("POST", "/orders", json=payload)
        return data if isinstance(data, dict) else {"result": data}

    async def confirm_order(self, order_id: str) -> dict[str, Any]:
        data = await self._request("POST", f"/orders/{order_id}/confirm")
        return data if isinstance(data, dict) else {"result": data}

    async def get_order(self, order_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/orders/{order_id}")
        return data if isinstance(data, dict) else {"result": data}
