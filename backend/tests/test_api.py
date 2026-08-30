from __future__ import annotations

from collections.abc import AsyncIterator

import fitz
import httpx
import pytest
import pytest_asyncio

from main import app

APEX_NAME = "Apex Petrochem Pvt Ltd"
APEX_PAN = "AABCA1234F"
APEX_GSTIN = "33AABCA1234F1Z5"
APEX_UDYAM = "UDYAM-TN-01-0012345"


def _build_apex_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), APEX_NAME, fontsize=24)
    page.insert_text((72, 130), f"PAN: {APEX_PAN}", fontsize=11)
    page.insert_text((72, 155), f"GSTIN: {APEX_GSTIN}", fontsize=11)
    page.insert_text((72, 180), f"Udyam No: {APEX_UDYAM}", fontsize=11)
    page.insert_text((72, 205), "Annual turnover: Rs. 25.00 Crore", fontsize=11)
    page.insert_text((72, 230), "Make in India local content: 65%", fontsize=11)
    payload = document.tobytes()
    document.close()
    return payload


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "bidguard-ai"


@pytest.mark.asyncio
async def test_mock_gstn_returns_apex(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/mock/gstn/{APEX_GSTIN}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["legal_name"] == APEX_NAME
    assert payload["pan"] == APEX_PAN
    assert payload["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_mock_gstn_unknown_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/mock/gstn/33ZZZZZ9999Z1Z9")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_tender_compliant_bid(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tenders/evaluate",
        files={"file": ("apex_bid.pdf", _build_apex_pdf(), "application/pdf")},
        data={"tender_id": "GEM-2026-CPCL-001", "min_local_content_pct": "50.0"},
    )

    assert response.status_code == 200
    report = response.json()
    assert report["tender_id"] == "GEM-2026-CPCL-001"
    assert report["bidder_name"] == APEX_NAME
    assert report["compliance_score"] >= 90
    assert report["risk_tier"] == "LOW"
    assert report["is_debarred"] is False


@pytest.mark.asyncio
async def test_evaluate_tender_rejects_non_pdf(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tenders/evaluate",
        files={"file": ("bid.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_evaluate_tender_unreadable_pdf(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tenders/evaluate",
        files={"file": ("empty.pdf", b"%PDF-1.4 garbage", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unable to extract readable text from PDF"
