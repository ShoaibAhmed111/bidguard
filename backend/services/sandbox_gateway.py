from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from models.schemas import (
    DebarmentCheckResponse,
    EnterpriseCategory,
    RegistrationStatus,
    TaxpayerVerificationResponse,
    UdyamVerificationResponse,
)
from services.gateway_interface import IVerificationGateway, VerificationNotFoundError

MOCK_DATA_PATH = Path(__file__).resolve().parent.parent / "mock_data" / "taxpayers.json"


@lru_cache(maxsize=1)
def _load_taxpayers() -> list[dict[str, Any]]:
    with MOCK_DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("taxpayers.json must contain a JSON array")
    return payload


def _norm(value: str) -> str:
    return value.strip().upper()


class SandboxVerificationGateway(IVerificationGateway):
    """Resolves GSTN / Udyam / PAN checks against seeded mock taxpayers."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self._records = records if records is not None else _load_taxpayers()

    def _find(self, field: str, value: str) -> dict[str, Any]:
        needle = _norm(value)
        for record in self._records:
            candidate = record.get(field)
            if isinstance(candidate, str) and _norm(candidate) == needle:
                return record
        raise VerificationNotFoundError(f"No sandbox taxpayer found for {field}={value}")

    async def verify_gstin(self, gstin: str) -> TaxpayerVerificationResponse:
        record = self._find("gstin", gstin)
        return TaxpayerVerificationResponse(
            gstin=record["gstin"],
            legal_name=record["legal_name"],
            pan=record["pan"],
            status=RegistrationStatus(record["status"]),
            annual_turnover_cr=float(record["annual_turnover_cr"]),
            filing_compliant=bool(record["filing_compliant"]),
            last_return_filed_date=record.get("last_return_filed_date"),
        )

    async def verify_udyam(self, udyam_no: str) -> UdyamVerificationResponse:
        record = self._find("udyam_no", udyam_no)
        return UdyamVerificationResponse(
            udyam_no=record["udyam_no"],
            enterprise_name=record["legal_name"],
            category=EnterpriseCategory(record["enterprise_category"]),
            is_valid=bool(record["is_valid"]),
            valid_upto=record.get("valid_upto"),
        )

    async def check_debarment(self, pan: str) -> DebarmentCheckResponse:
        record = self._find("pan", pan)
        return DebarmentCheckResponse(
            pan=record["pan"],
            is_blacklisted=bool(record["is_blacklisted"]),
            gazette_order_ref=record.get("gazette_order_ref"),
            debarment_reason=record.get("debarment_reason"),
            debarred_until=record.get("debarred_until"),
        )
