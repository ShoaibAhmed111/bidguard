from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.schemas import BidComplianceReport
from services.audit_engine import BidComplianceAuditEngine
from services.gateway_interface import (
    VerificationGatewayError,
    VerificationNotFoundError,
    get_gateway,
)
from services.parser import BidDocumentParser
from services.sandbox_gateway import SandboxVerificationGateway

app = FastAPI(
    title="BidGuard AI",
    description="SIH26100 — GeM Bid Compliance Platform (verification gateway + mock APIs)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sandbox_gateway = SandboxVerificationGateway()
gateway = get_gateway()
parser = BidDocumentParser()
audit_engine = BidComplianceAuditEngine(gateway=gateway)


def _raise_gateway_error(exc: VerificationGatewayError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "bidguard-ai",
        "env": settings.APP_ENV,
    }


@app.get("/api/v1/mock/gstn/{gstin}")
async def mock_gstn(gstin: str):
    try:
        return await sandbox_gateway.verify_gstin(gstin)
    except VerificationNotFoundError as exc:
        _raise_gateway_error(exc)
    except VerificationGatewayError as exc:
        _raise_gateway_error(exc)


@app.get("/api/v1/mock/udyam/{udyam_no}")
async def mock_udyam(udyam_no: str):
    try:
        return await sandbox_gateway.verify_udyam(udyam_no)
    except VerificationNotFoundError as exc:
        _raise_gateway_error(exc)
    except VerificationGatewayError as exc:
        _raise_gateway_error(exc)


@app.get("/api/v1/mock/debarment/{pan}")
async def mock_debarment(pan: str):
    try:
        return await sandbox_gateway.check_debarment(pan)
    except VerificationNotFoundError as exc:
        _raise_gateway_error(exc)
    except VerificationGatewayError as exc:
        _raise_gateway_error(exc)


@app.post("/api/v1/tenders/evaluate", response_model=BidComplianceReport)
async def evaluate_tender(
    file: UploadFile = File(...),
    tender_id: str = Form("GEM-2026-CPCL-001"),
    min_local_content_pct: float = Form(50.0),
) -> BidComplianceReport:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF bid documents are supported",
        )

    file_bytes = await file.read()
    extracted_data = await parser.parse_pdf(file_bytes)
    if not extracted_data.legal_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to extract readable text from PDF",
        )

    return await audit_engine.audit_bid(
        extracted_data,
        tender_criteria={
            "tender_id": tender_id,
            "min_local_content_pct": min_local_content_pct,
        },
    )
