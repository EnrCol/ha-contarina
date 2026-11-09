"""Strictly read-only client for private, undocumented SOL GET endpoints."""
from __future__ import annotations
import asyncio
import json
import re
from datetime import date
from typing import Any
from urllib.parse import quote
import aiohttp
from .const import API_BASE, MAX_PAGES, PDF_MAX_BYTES, REQUEST_TIMEOUT_SECONDS
from .models import ResponseShapeError, parse_balance, required_list

class ContarinaAuthError(Exception):
    """Authentication has been rejected or expired."""

class ContarinaConnectionError(Exception):
    """Service is unavailable or response is unusable."""

def _safe_segment(value: str | int) -> str:
    value = str(value)
    if not re.fullmatch(r"[\w-]{1,100}", value, flags=re.ASCII):
        raise ContarinaConnectionError("Unexpected remote identifier")
    return quote(value, safe="")

class ContarinaApi:
    """All calls are GET; never log request URLs, bodies or tokens."""
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._limit = asyncio.Semaphore(2)

    async def get(self, path: str, token: str, params: dict[str, Any] | None = None) -> Any:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            async with self._limit:
                async with self._session.get(
                    API_BASE + path, params=params, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
                    allow_redirects=False,
                ) as response:
                    if response.status in (401, 403):
                        raise ContarinaAuthError("SOL authentication required")
                    if response.status != 200:
                        raise ContarinaConnectionError(f"SOL HTTP {response.status}")
                    if response.content_type == "application/pdf":
                        raise ContarinaConnectionError("Unexpected PDF response")
                    raw = await response.text()
        except ContarinaAuthError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise ContarinaConnectionError("SOL connection failed") from exc
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ContarinaConnectionError("Invalid SOL JSON response") from exc
        if isinstance(payload, dict) and {"Code", "Message"} <= payload.keys():
            raise ContarinaConnectionError("SOL reported an application error")
        return payload

    async def get_contracts(self, token: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        params: dict[str, Any] = {"active": "all"}
        seen_pages: set[int] = set()
        first_page: int | None = None
        for _ in range(MAX_PAGES):
            data = await self.get("/api/contracts", token, params)
            if not isinstance(data, dict) or not isinstance(data.get("contracts"), list):
                raise ContarinaConnectionError("Invalid contracts response")
            result.extend(x for x in data["contracts"] if isinstance(x, dict))
            current_page = data.get("page")
            total_pages = data.get("totalPages")
            if not isinstance(current_page, int) or not isinstance(total_pages, int):
                return result
            if current_page in seen_pages:
                raise ContarinaConnectionError("Contracts pagination loop")
            seen_pages.add(current_page)
            if first_page is None:
                first_page = current_page
            if current_page >= total_pages - 1 + first_page:
                return result
            params = {"active": "all", "page": current_page + 1}
        raise ContarinaConnectionError("Contracts pagination exceeded safety limit")

    async def contract_detail(self, ref: str, token: str) -> dict[str, Any]:
        data = await self.get(f"/api/contracts/{_safe_segment(ref)}", token)
        if not isinstance(data, dict):
            raise ContarinaConnectionError("Invalid contract detail")
        return data

    async def areas(self, ref: str, token: str) -> list[dict[str, Any]]:
        return required_list(await self.get(f"/api/users/areas/{_safe_segment(ref)}", token))

    async def ecocalendars(self, token: str) -> list[dict[str, Any]]:
        return required_list(await self.get("/api/sol/ecocalendars", token))

    async def waste_types(self, token: str) -> list[dict[str, Any]]:
        return required_list(await self.get("/api/sol/emptying-types", token))

    async def collections(self, calendar_id: str, start: date, end: date, token: str) -> list[dict[str, Any]]:
        return required_list(await self.get("/api/sol/ecocalendar-emptyings", token, {
            "ecocalendario_id": calendar_id, "start_date": start.isoformat(), "end_date": end.isoformat(),
        }))

    async def equipment(self, ref: str, token: str) -> list[dict[str, Any]]:
        return required_list(await self.get(
            f"/api/services/equipment/contract/{_safe_segment(ref)}", token,
            {"active": "all", "rsuOnly": "false"},
        ))

    async def emptyings(self, ref: str, container: str, start: str, end: str, token: str) -> list[dict[str, Any]]:
        return required_list(await self.get(
            f"/api/users/{_safe_segment(ref)}/emptyings/{_safe_segment(container)}",
            token, {"from": start, "to": end},
        ))

    async def accounting(self, ref: str, token: str) -> list[dict[str, Any]]:
        data = await self.get(f"/api/users/{_safe_segment(ref)}/accounting", token)
        if not isinstance(data, dict):
            raise ContarinaConnectionError("Invalid accounting response")
        return required_list(data.get("fatture"))

    async def check_balance(self, ref: str, token: str) -> bool:
        return parse_balance(await self.get(f"/api/users/{_safe_segment(ref)}/check-balance", token))

    async def refresh(self, token: str) -> str:
        data = await self.get("/api/users/refresh-token", token)
        if not isinstance(data, dict) or not isinstance(data.get("access_token"), str):
            raise ContarinaConnectionError("Invalid refresh response")
        return data["access_token"]

    async def invoice_pdf(self, ref: str, invoice_id: str, token: str) -> bytes:
        """GET one invoice PDF (read-only). Size, type and signature are enforced."""
        path = f"/api/contracts/{_safe_segment(ref)}/bill/{_safe_segment(invoice_id)}/file"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/pdf"}
        try:
            async with self._limit:
                async with self._session.get(
                    API_BASE + path, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS * 2),
                    allow_redirects=False,
                ) as response:
                    if response.status in (401, 403):
                        raise ContarinaAuthError("SOL authentication required")
                    if response.status != 200:
                        raise ContarinaConnectionError(f"SOL HTTP {response.status}")
                    if response.content_type != "application/pdf":
                        raise ContarinaConnectionError("SOL did not return a PDF")
                    if response.content_length is not None and response.content_length > PDF_MAX_BYTES:
                        raise ContarinaConnectionError("Invoice PDF too large")
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        if len(data) + len(chunk) > PDF_MAX_BYTES:
                            raise ContarinaConnectionError("Invoice PDF too large")
                        data.extend(chunk)
        except (ContarinaAuthError, ContarinaConnectionError):
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError):
            # aiohttp errors may embed the request URL: never chain them into messages.
            raise ContarinaConnectionError("SOL connection failed") from None
        if bytes(data[:5]) != b"%PDF-":
            raise ContarinaConnectionError("Invalid PDF signature")
        return bytes(data)
