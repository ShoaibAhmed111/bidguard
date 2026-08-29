from __future__ import annotations

from typing import Any

import httpx

from config import settings
from models.schemas import (
    DebarmentCheckResponse,
    EnterpriseCategory,
    RegistrationStatus,
    TaxpayerVerificationResponse,
    UdyamVerificationResponse,
)
from services.gateway_interface import (
    IVerificationGateway,
    VerificationGatewayError,
    VerificationNotFoundError,
)

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class ApiSetuLiveGateway(IVerificationGateway):
    """Production skeleton for API Setu GSTN / Udyam / debarment lookups."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.API_SETU_BASE_URL.rstrip("/"),
            timeout=_TIMEOUT,
        )

    def _headers(self) -> dict[str, str]:
        if not settings.API_SETU_CLIENT_ID or not settings.API_SETU_CLIENT_SECRET:
            raise VerificationGatewayError(
                "API Setu credentials are not configured (API_SETU_CLIENT_ID / API_SETU_CLIENT_SECRET)",
                status_code=503,
            )
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Client-Id": settings.API_SETU_CLIENT_ID,
            "X-Client-Secret": settings.API_SETU_CLIENT_SECRET,
        }

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                path,
                headers=self._headers(),
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise VerificationGatewayError(
                f"API Setu request failed: {exc}",
                status_code=502,
            ) from exc

        if response.status_code == 404:
            raise VerificationNotFoundError(f"API Setu resource not found: {path}")

        if response.status_code >= 400:
            detail = response.text[:500]
            raise VerificationGatewayError(
                f"API Setu error {response.status_code}: {detail}",
                status_code=502,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise VerificationGatewayError(
                "API Setu returned a non-JSON response",
                status_code=502,
            ) from exc

        if not isinstance(payload, dict):
            raise VerificationGatewayError("API Setu returned an unexpected payload", status_code=502)
        return payload

    async def verify_gstin(self, gstin: str) -> TaxpayerVerificationResponse:
        payload = await self._request("GET", f"/gstn/{gstin}")
        try:
            return TaxpayerVerificationResponse(
                gstin=str(payload.get("gstin", gstin)),
                legal_name=str(payload["legal_name"]),
                pan=str(payload["pan"]),
                status=RegistrationStatus(str(payload["status"]).upper()),
                annual_turnover_cr=float(payload["annual_turnover_cr"]),
                filing_compliant=bool(payload["filing_compliant"]),
                last_return_filed_date=payload.get("last_return_filed_date"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise VerificationGatewayError(
                f"API Setu GSTN payload could not be mapped: {exc}",
                status_code=502,
            ) from exc

    async def verify_udyam(self, udyam_no: str) -> UdyamVerificationResponse:
        payload = await self._request("GET", f"/udyam/{udyam_no}")
        try:
            return UdyamVerificationResponse(
                udyam_no=str(payload.get("udyam_no", udyam_no)),
                enterprise_name=str(payload.get("enterprise_name") or payload["legal_name"]),
                category=EnterpriseCategory(str(payload["category"]).upper()),
                is_valid=bool(payload["is_valid"]),
                valid_upto=payload.get("valid_upto"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise VerificationGatewayError(
                f"API Setu Udyam payload could not be mapped: {exc}",
                status_code=502,
            ) from exc

    async def check_debarment(self, pan: str) -> DebarmentCheckResponse:
        payload = await self._request("GET", f"/debarment/{pan}")
        try:
            return DebarmentCheckResponse(
                pan=str(payload.get("pan", pan)),
                is_blacklisted=bool(payload["is_blacklisted"]),
                gazette_order_ref=payload.get("gazette_order_ref"),
                debarment_reason=payload.get("debarment_reason"),
                debarred_until=payload.get("debarred_until"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise VerificationGatewayError(
                f"API Setu debarment payload could not be mapped: {exc}",
                status_code=502,
            ) from exc
