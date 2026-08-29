from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rapidfuzz import fuzz

from config import settings
from models.schemas import (
    BidComplianceReport,
    BoundingBox,
    ClauseAuditResult,
    ClauseStatus,
    ExtractedBidData,
    RegistrationStatus,
    RiskTier,
    TaxpayerVerificationResponse,
)
from services.gateway_interface import (
    IVerificationGateway,
    VerificationGatewayError,
    VerificationNotFoundError,
)

CLAUSE_DEBARMENT = "PAN-DEBARMENT"
CLAUSE_GSTIN = "GSTIN-STATUS"
CLAUSE_TURNOVER = "TURNOVER-RECON"
CLAUSE_UDYAM = "UDYAM-MSME"
CLAUSE_LOCAL_CONTENT = "MII-LOCAL-CONTENT"

PENALTY_DEBARMENT = 100.0
PENALTY_GSTIN = 20.0
PENALTY_TURNOVER = 25.0
PENALTY_UDYAM = 15.0
PENALTY_LOCAL_CONTENT = 20.0
PENALTY_NAME_WARNING = 5.0
PENALTY_NAME_FAIL = 10.0
PENALTY_GST_FILING = 10.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _box(extracted: ExtractedBidData, key: str) -> BoundingBox | None:
    return extracted.bounding_boxes.get(key)


def _fmt(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _name_similarity(left: str, right: str) -> float:
    if not left.strip() or not right.strip():
        return 0.0
    return float(fuzz.token_sort_ratio(left, right)) / 100.0


def _risk_tier(
    score: float,
    *,
    is_debarred: bool,
    gst_inactive: bool,
    turnover_inflated: bool,
) -> RiskTier:
    if is_debarred:
        return RiskTier.CRITICAL
    if score >= 85:
        tier = RiskTier.LOW
    elif score >= 65:
        tier = RiskTier.MEDIUM
    elif score >= 40:
        tier = RiskTier.HIGH
    else:
        tier = RiskTier.CRITICAL
    # Statutory red flags must not be masked by otherwise high residual scores.
    if (gst_inactive or turnover_inflated) and tier in {RiskTier.LOW, RiskTier.MEDIUM}:
        return RiskTier.HIGH
    return tier


def _recommend(*, is_debarred: bool, tier: RiskTier, failed: list[str]) -> str:
    if is_debarred:
        return (
            "Reject this bid immediately. The bidder is debarred/blacklisted. "
            "Escalate to the Vigilance Officer and do not proceed with technical evaluation."
        )
    if tier == RiskTier.CRITICAL:
        return (
            "Do not award. Critical compliance failures remain unresolved: "
            + "; ".join(failed)
            + ". Require a fresh compliant bid or initiate disqualification."
        )
    if tier == RiskTier.HIGH:
        return (
            "Do not award until discrepancies are closed. Seek certified clarifications "
            "from the bidder and re-verify against GSTN/Udyam/GeM before opening financials."
        )
    if tier == RiskTier.MEDIUM:
        return (
            "Proceed only with conditions: obtain supporting certificates for warning/fail "
            "clauses and record residual risk in the procurement file."
        )
    return (
        "Bid is substantially compliant. Procurement Officer may proceed to the next "
        "evaluation stage under standard GeM due-diligence."
    )


def _summary(
    bidder: str,
    score: float,
    tier: RiskTier,
    clauses: list[ClauseAuditResult],
) -> str:
    passed = [c.clause_title for c in clauses if c.status == ClauseStatus.PASS]
    failed = [c.clause_title for c in clauses if c.status == ClauseStatus.FAIL]
    warnings = [c.clause_title for c in clauses if c.status == ClauseStatus.WARNING]
    parts = [
        f"{bidder} scored {score:.1f}/100 ({tier.value} risk).",
        f"Passed: {len(passed)} clause(s)" + (f" ({', '.join(passed)})" if passed else "") + ".",
        f"Failed: {len(failed)} clause(s)" + (f" ({', '.join(failed)})" if failed else "") + ".",
    ]
    if warnings:
        parts.append(f"Warnings: {', '.join(warnings)}.")
    return " ".join(parts)


class BidComplianceAuditEngine:
    """Deterministic statutory + tender-criteria auditor for GeM bids."""

    def __init__(self, gateway: IVerificationGateway) -> None:
        self.gateway = gateway

    async def audit_bid(
        self,
        extracted_data: ExtractedBidData,
        tender_criteria: dict[str, Any],
    ) -> BidComplianceReport:
        clauses: list[ClauseAuditResult] = []
        is_debarred = False
        gst_inactive = False
        turnover_inflated = False
        taxpayer: TaxpayerVerificationResponse | None = None

        debar_clause, is_debarred = await self._audit_debarment(extracted_data)
        clauses.append(debar_clause)

        gst_clause, taxpayer, gst_inactive = await self._audit_gstin(extracted_data)
        clauses.append(gst_clause)

        turn_clause, turnover_inflated = self._audit_turnover(extracted_data, taxpayer)
        clauses.append(turn_clause)

        clauses.append(await self._audit_udyam(extracted_data))
        clauses.append(self._audit_local_content(extracted_data, tender_criteria))

        total_penalties = sum(item.risk_penalty for item in clauses)
        score = max(0.0, 100.0 - total_penalties)
        if is_debarred:
            score = 0.0

        tier = _risk_tier(
            score,
            is_debarred=is_debarred,
            gst_inactive=gst_inactive,
            turnover_inflated=turnover_inflated,
        )
        failed_titles = [c.clause_title for c in clauses if c.status == ClauseStatus.FAIL]
        tender_id = str(tender_criteria.get("tender_id") or "UNSPECIFIED")

        return BidComplianceReport(
            tender_id=tender_id,
            bidder_name=extracted_data.legal_name,
            compliance_score=round(score, 2),
            risk_tier=tier,
            is_debarred=is_debarred,
            evaluated_at=_now(),
            clause_results=clauses,
            executive_summary=_summary(extracted_data.legal_name, score, tier, clauses),
            recommended_action=_recommend(is_debarred=is_debarred, tier=tier, failed=failed_titles),
        )

    async def _audit_debarment(
        self, extracted: ExtractedBidData
    ) -> tuple[ClauseAuditResult, bool]:
        if not extracted.pan:
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_DEBARMENT,
                    clause_title="PAN & Debarment Check",
                    is_mandatory=True,
                    status=ClauseStatus.FAIL,
                    extracted_value=None,
                    expected_value="Valid PAN; not blacklisted",
                    visual_evidence=_box(extracted, "pan"),
                    discrepancy_notes="PAN was not extracted; debarment could not be verified.",
                    risk_penalty=PENALTY_GSTIN,
                ),
                False,
            )

        try:
            result = await self.gateway.check_debarment(extracted.pan)
        except VerificationNotFoundError:
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_DEBARMENT,
                    clause_title="PAN & Debarment Check",
                    is_mandatory=True,
                    status=ClauseStatus.WARNING,
                    extracted_value=extracted.pan,
                    expected_value="PAN found in debarment registry (or confirmed absent)",
                    visual_evidence=_box(extracted, "pan"),
                    discrepancy_notes="PAN was not found in the debarment dataset; treat as unverified.",
                    risk_penalty=PENALTY_NAME_WARNING,
                ),
                False,
            )
        except VerificationGatewayError as exc:
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_DEBARMENT,
                    clause_title="PAN & Debarment Check",
                    is_mandatory=True,
                    status=ClauseStatus.FAIL,
                    extracted_value=extracted.pan,
                    expected_value="Debarment service available",
                    visual_evidence=_box(extracted, "pan"),
                    discrepancy_notes=f"Debarment gateway error: {exc.message}",
                    risk_penalty=PENALTY_GSTIN,
                ),
                False,
            )

        if result.is_blacklisted:
            refs = [
                part
                for part in (
                    result.gazette_order_ref,
                    result.debarment_reason,
                    f"until {result.debarred_until}" if result.debarred_until else None,
                )
                if part
            ]
            note = "Bidder is blacklisted/debarred. " + "; ".join(refs)
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_DEBARMENT,
                    clause_title="PAN & Debarment Check",
                    is_mandatory=True,
                    status=ClauseStatus.FAIL,
                    extracted_value=extracted.pan,
                    expected_value="Not debarred / not blacklisted",
                    visual_evidence=_box(extracted, "pan"),
                    discrepancy_notes=note,
                    risk_penalty=PENALTY_DEBARMENT,
                ),
                True,
            )

        return (
            ClauseAuditResult(
                clause_id=CLAUSE_DEBARMENT,
                clause_title="PAN & Debarment Check",
                is_mandatory=True,
                status=ClauseStatus.PASS,
                extracted_value=extracted.pan,
                expected_value="Not debarred / not blacklisted",
                visual_evidence=_box(extracted, "pan"),
                discrepancy_notes=None,
                risk_penalty=0.0,
            ),
            False,
        )

    async def _audit_gstin(
        self, extracted: ExtractedBidData
    ) -> tuple[ClauseAuditResult, TaxpayerVerificationResponse | None, bool]:
        if not extracted.gstin:
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_GSTIN,
                    clause_title="GSTIN Status & Name Matching",
                    is_mandatory=True,
                    status=ClauseStatus.FAIL,
                    extracted_value=None,
                    expected_value="ACTIVE GSTIN with filing-compliant returns",
                    visual_evidence=_box(extracted, "gstin"),
                    discrepancy_notes="GSTIN was not extracted from the bid documents.",
                    risk_penalty=PENALTY_GSTIN,
                ),
                None,
                True,
            )

        try:
            taxpayer = await self.gateway.verify_gstin(extracted.gstin)
        except (VerificationNotFoundError, VerificationGatewayError) as exc:
            message = getattr(exc, "message", str(exc))
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_GSTIN,
                    clause_title="GSTIN Status & Name Matching",
                    is_mandatory=True,
                    status=ClauseStatus.FAIL,
                    extracted_value=extracted.gstin,
                    expected_value="ACTIVE GSTIN with filing-compliant returns",
                    visual_evidence=_box(extracted, "gstin"),
                    discrepancy_notes=f"GSTIN verification failed: {message}",
                    risk_penalty=PENALTY_GSTIN,
                ),
                None,
                True,
            )

        notes: list[str] = []
        penalty = 0.0
        status = ClauseStatus.PASS
        gst_inactive = taxpayer.status != RegistrationStatus.ACTIVE

        if gst_inactive:
            status = ClauseStatus.FAIL
            penalty += PENALTY_GSTIN
            notes.append(
                f"GST registration is {taxpayer.status.value}, expected ACTIVE."
            )
        if not taxpayer.filing_compliant:
            status = ClauseStatus.FAIL
            if gst_inactive:
                penalty += PENALTY_GST_FILING
                notes.append("GST returns are not filing-compliant.")
            else:
                penalty += PENALTY_GSTIN
                notes.append("GST returns are not filing-compliant.")

        similarity = _name_similarity(extracted.legal_name, taxpayer.legal_name)
        threshold = settings.MIN_NAME_MATCH_SIMILARITY
        notes.append(
            f"Legal-name similarity {similarity:.0%} "
            f"(bid '{extracted.legal_name}' vs GSTN '{taxpayer.legal_name}')."
        )
        if similarity < threshold:
            if similarity < 0.70:
                status = ClauseStatus.FAIL
                penalty += PENALTY_NAME_FAIL
            else:
                if status == ClauseStatus.PASS:
                    status = ClauseStatus.WARNING
                penalty += PENALTY_NAME_WARNING
            notes.append(
                f"Name match is below the {threshold:.0%} statutory threshold."
            )

        return (
            ClauseAuditResult(
                clause_id=CLAUSE_GSTIN,
                clause_title="GSTIN Status & Name Matching",
                is_mandatory=True,
                status=status,
                extracted_value=extracted.gstin,
                expected_value="ACTIVE, filing-compliant, name match ≥ 85%",
                visual_evidence=_box(extracted, "gstin"),
                discrepancy_notes=" ".join(notes) if notes else None,
                risk_penalty=round(penalty, 2),
            ),
            taxpayer,
            gst_inactive or not taxpayer.filing_compliant,
        )

    def _audit_turnover(
        self,
        extracted: ExtractedBidData,
        taxpayer: TaxpayerVerificationResponse | None,
    ) -> tuple[ClauseAuditResult, bool]:
        declared = extracted.declared_turnover_inr_cr
        verified = taxpayer.annual_turnover_cr if taxpayer is not None else None
        tolerance = settings.TURNOVER_TOLERANCE_PCT

        if declared is None or verified is None:
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_TURNOVER,
                    clause_title="Turnover Reconciliation",
                    is_mandatory=True,
                    status=ClauseStatus.WARNING,
                    extracted_value=_fmt(declared),
                    expected_value="Declared turnover within 10% of GSTN annual turnover",
                    visual_evidence=_box(extracted, "declared_turnover_inr_cr"),
                    discrepancy_notes="Turnover could not be reconciled; declared or portal value is missing.",
                    risk_penalty=PENALTY_NAME_FAIL,
                ),
                False,
            )

        if verified <= 0:
            inflated = declared > 0
            excess_pct = 1.0 if inflated else 0.0
        else:
            excess_pct = (declared - verified) / verified
            inflated = excess_pct > tolerance

        if inflated:
            return (
                ClauseAuditResult(
                    clause_id=CLAUSE_TURNOVER,
                    clause_title="Turnover Reconciliation",
                    is_mandatory=True,
                    status=ClauseStatus.FAIL,
                    extracted_value=f"{declared:.2f} Cr",
                    expected_value=f"≤ {verified * (1 + tolerance):.2f} Cr (portal {verified:.2f} Cr + {tolerance:.0%})",
                    visual_evidence=_box(extracted, "declared_turnover_inr_cr"),
                    discrepancy_notes=(
                        f"Declared turnover ({declared:.2f} Cr) exceeds GSTN/portal turnover "
                        f"({verified:.2f} Cr) by {excess_pct:.1%}, which is above the "
                        f"{tolerance:.0%} inflation tolerance. Treat as possible turnover inflation."
                    ),
                    risk_penalty=PENALTY_TURNOVER,
                ),
                True,
            )

        return (
            ClauseAuditResult(
                clause_id=CLAUSE_TURNOVER,
                clause_title="Turnover Reconciliation",
                is_mandatory=True,
                status=ClauseStatus.PASS,
                extracted_value=f"{declared:.2f} Cr",
                expected_value=f"Portal {verified:.2f} Cr (±{tolerance:.0%})",
                visual_evidence=_box(extracted, "declared_turnover_inr_cr"),
                discrepancy_notes=None,
                risk_penalty=0.0,
            ),
            False,
        )

    async def _audit_udyam(self, extracted: ExtractedBidData) -> ClauseAuditResult:
        if not extracted.udyam_no:
            return ClauseAuditResult(
                clause_id=CLAUSE_UDYAM,
                clause_title="Udyam / MSME Validation",
                is_mandatory=False,
                status=ClauseStatus.WARNING,
                extracted_value=None,
                expected_value="Valid Udyam registration (if MSME benefits claimed)",
                visual_evidence=_box(extracted, "udyam_no"),
                discrepancy_notes="No Udyam number was declared on the bid.",
                risk_penalty=0.0,
            )

        try:
            udyam = await self.gateway.verify_udyam(extracted.udyam_no)
        except (VerificationNotFoundError, VerificationGatewayError) as exc:
            message = getattr(exc, "message", str(exc))
            return ClauseAuditResult(
                clause_id=CLAUSE_UDYAM,
                clause_title="Udyam / MSME Validation",
                is_mandatory=True,
                status=ClauseStatus.FAIL,
                extracted_value=extracted.udyam_no,
                expected_value="Valid, in-force Udyam registration",
                visual_evidence=_box(extracted, "udyam_no"),
                discrepancy_notes=f"Udyam verification failed: {message}",
                risk_penalty=PENALTY_UDYAM,
            )

        if not udyam.is_valid:
            return ClauseAuditResult(
                clause_id=CLAUSE_UDYAM,
                clause_title="Udyam / MSME Validation",
                is_mandatory=True,
                status=ClauseStatus.FAIL,
                extracted_value=extracted.udyam_no,
                expected_value="Valid Udyam (is_valid=true)",
                visual_evidence=_box(extracted, "udyam_no"),
                discrepancy_notes=(
                    f"Udyam {udyam.udyam_no} is not valid"
                    + (f" (valid_upto {udyam.valid_upto})" if udyam.valid_upto else "")
                    + f". Recorded category: {udyam.category.value}."
                ),
                risk_penalty=PENALTY_UDYAM,
            )

        return ClauseAuditResult(
            clause_id=CLAUSE_UDYAM,
            clause_title="Udyam / MSME Validation",
            is_mandatory=True,
            status=ClauseStatus.PASS,
            extracted_value=f"{udyam.udyam_no} ({udyam.category.value})",
            expected_value="Valid Udyam registration",
            visual_evidence=_box(extracted, "udyam_no"),
            discrepancy_notes=f"Enterprise '{udyam.enterprise_name}' category {udyam.category.value}.",
            risk_penalty=0.0,
        )

    def _audit_local_content(
        self,
        extracted: ExtractedBidData,
        tender_criteria: dict[str, Any],
    ) -> ClauseAuditResult:
        minimum = float(tender_criteria.get("min_local_content_pct", 50.0))
        declared = extracted.make_in_india_local_content_pct

        if declared is None:
            return ClauseAuditResult(
                clause_id=CLAUSE_LOCAL_CONTENT,
                clause_title="Make in India / Local Content",
                is_mandatory=True,
                status=ClauseStatus.FAIL,
                extracted_value=None,
                expected_value=f">= {minimum:.1f}% local content",
                visual_evidence=_box(extracted, "make_in_india_local_content_pct"),
                discrepancy_notes="Local content / Make in India percentage was not declared.",
                risk_penalty=PENALTY_LOCAL_CONTENT,
            )

        if declared + 1e-9 < minimum:
            return ClauseAuditResult(
                clause_id=CLAUSE_LOCAL_CONTENT,
                clause_title="Make in India / Local Content",
                is_mandatory=True,
                status=ClauseStatus.FAIL,
                extracted_value=f"{declared:.1f}%",
                expected_value=f">= {minimum:.1f}%",
                visual_evidence=_box(extracted, "make_in_india_local_content_pct"),
                discrepancy_notes=(
                    f"Declared local content {declared:.1f}% is below the tender minimum of {minimum:.1f}%."
                ),
                risk_penalty=PENALTY_LOCAL_CONTENT,
            )

        return ClauseAuditResult(
            clause_id=CLAUSE_LOCAL_CONTENT,
            clause_title="Make in India / Local Content",
            is_mandatory=True,
            status=ClauseStatus.PASS,
            extracted_value=f"{declared:.1f}%",
            expected_value=f">= {minimum:.1f}%",
            visual_evidence=_box(extracted, "make_in_india_local_content_pct"),
            discrepancy_notes=None,
            risk_penalty=0.0,
        )
