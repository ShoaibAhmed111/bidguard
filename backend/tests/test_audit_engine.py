import pytest

from models.schemas import (
    ClauseStatus,
    ExtractedBidData,
    RiskTier,
)
from services.audit_engine import CLAUSE_DEBARMENT, CLAUSE_GSTIN, CLAUSE_TURNOVER, BidComplianceAuditEngine
from services.sandbox_gateway import SandboxVerificationGateway

TENDER = {
    "tender_id": "GEM-2026-CPCL-001",
    "min_local_content_pct": 50.0,
}


def _engine() -> BidComplianceAuditEngine:
    return BidComplianceAuditEngine(SandboxVerificationGateway())


def _clause(report, clause_id: str):
    for item in report.clause_results:
        if item.clause_id == clause_id:
            return item
    raise AssertionError(f"missing clause {clause_id}")


@pytest.mark.asyncio
async def test_apex_petrochem_low_risk_high_score() -> None:
    extracted = ExtractedBidData(
        legal_name="Apex Petrochem Pvt Ltd",
        pan="AABCA1234F",
        gstin="33AABCA1234F1Z5",
        udyam_no="UDYAM-TN-01-0012345",
        declared_turnover_inr_cr=25.0,
        make_in_india_local_content_pct=65.0,
    )
    report = await _engine().audit_bid(extracted, TENDER)

    assert report.compliance_score >= 90.0
    assert report.risk_tier == RiskTier.LOW
    assert report.is_debarred is False
    assert all(item.status == ClauseStatus.PASS for item in report.clause_results)
    assert "proceed" in report.recommended_action.lower()


@pytest.mark.asyncio
async def test_bharat_valves_turnover_inflation_high_risk() -> None:
    extracted = ExtractedBidData(
        legal_name="Bharat Valves & Pipes Ltd",
        pan="BBBCB5678K",
        gstin="27BBBCB5678K1Z2",
        udyam_no="UDYAM-MH-02-0098765",
        declared_turnover_inr_cr=20.0,
        make_in_india_local_content_pct=60.0,
    )
    report = await _engine().audit_bid(extracted, TENDER)
    turnover = _clause(report, CLAUSE_TURNOVER)

    assert turnover.status == ClauseStatus.FAIL
    assert turnover.risk_penalty == 25.0
    assert turnover.discrepancy_notes is not None
    assert "inflation" in turnover.discrepancy_notes.lower()
    assert report.is_debarred is False
    assert report.risk_tier == RiskTier.HIGH
    assert report.compliance_score == pytest.approx(75.0)


@pytest.mark.asyncio
async def test_national_industrial_supplies_debarred_critical() -> None:
    extracted = ExtractedBidData(
        legal_name="National Industrial Supplies",
        pan="CCCDC9012M",
        gstin="07CCCDC9012M1Z8",
        udyam_no="UDYAM-DL-03-0054321",
        declared_turnover_inr_cr=18.0,
        make_in_india_local_content_pct=55.0,
    )
    report = await _engine().audit_bid(extracted, TENDER)
    debarment = _clause(report, CLAUSE_DEBARMENT)

    assert report.is_debarred is True
    assert report.compliance_score == 0.0
    assert report.risk_tier == RiskTier.CRITICAL
    assert debarment.status == ClauseStatus.FAIL
    assert debarment.risk_penalty == 100.0
    assert debarment.discrepancy_notes is not None
    assert "CPCL/VIG/2025/112" in debarment.discrepancy_notes
    assert "reject" in report.recommended_action.lower()


@pytest.mark.asyncio
async def test_delta_fluid_tech_suspended_gst_high_risk() -> None:
    extracted = ExtractedBidData(
        legal_name="Delta Fluid Tech",
        pan="DDDDE3456N",
        gstin="29DDDDE3456N1Z9",
        udyam_no="UDYAM-KA-04-0022222",
        declared_turnover_inr_cr=8.5,
        make_in_india_local_content_pct=52.0,
    )
    report = await _engine().audit_bid(extracted, TENDER)
    gst = _clause(report, CLAUSE_GSTIN)

    assert gst.status == ClauseStatus.FAIL
    assert gst.discrepancy_notes is not None
    assert "SUSPENDED" in gst.discrepancy_notes
    assert "filing-compliant" in gst.discrepancy_notes.lower() or "not filing" in gst.discrepancy_notes.lower()
    assert report.is_debarred is False
    assert report.risk_tier == RiskTier.HIGH
    assert report.compliance_score < 65.0
