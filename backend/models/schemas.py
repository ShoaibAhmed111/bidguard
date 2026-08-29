from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClauseStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class EnterpriseCategory(str, Enum):
    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class RegistrationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ymin: float
    xmin: float
    ymax: float
    xmax: float
    page: int = Field(ge=1)


class ExtractedBidData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: str
    pan: str | None = None
    gstin: str | None = None
    udyam_no: str | None = None
    declared_turnover_inr_cr: float | None = Field(default=None, ge=0)
    make_in_india_local_content_pct: float | None = Field(default=None, ge=0, le=100)
    submission_date: date | None = None
    document_issue_dates: dict[str, date] = Field(default_factory=dict)
    bounding_boxes: dict[str, BoundingBox] = Field(default_factory=dict)


class TaxpayerVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gstin: str
    legal_name: str
    pan: str
    status: RegistrationStatus
    annual_turnover_cr: float = Field(ge=0)
    filing_compliant: bool
    last_return_filed_date: date | None = None


class UdyamVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    udyam_no: str
    enterprise_name: str
    category: EnterpriseCategory
    is_valid: bool
    valid_upto: date | None = None


class DebarmentCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pan: str
    is_blacklisted: bool
    gazette_order_ref: str | None = None
    debarment_reason: str | None = None
    debarred_until: date | None = None


class ClauseAuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clause_id: str
    clause_title: str
    is_mandatory: bool
    status: ClauseStatus
    extracted_value: str | None = None
    expected_value: str | None = None
    visual_evidence: BoundingBox | None = None
    discrepancy_notes: str | None = None
    risk_penalty: float = Field(default=0.0, ge=0)


class BidComplianceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tender_id: str
    bidder_name: str
    compliance_score: float = Field(ge=0, le=100)
    risk_tier: RiskTier
    is_debarred: bool
    evaluated_at: datetime
    clause_results: list[ClauseAuditResult] = Field(default_factory=list)
    executive_summary: str
    recommended_action: str
