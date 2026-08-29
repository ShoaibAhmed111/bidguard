from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services.gateway_interface import VerificationGatewayError, VerificationNotFoundError
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
