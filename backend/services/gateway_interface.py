from abc import ABC, abstractmethod

from config import settings
from models.schemas import (
    DebarmentCheckResponse,
    TaxpayerVerificationResponse,
    UdyamVerificationResponse,
)


class VerificationGatewayError(Exception):
    """Raised when a verification provider cannot complete a request."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class VerificationNotFoundError(VerificationGatewayError):
    """Raised when the identifier is unknown to the provider."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class IVerificationGateway(ABC):
    """Contract for GSTN, Udyam, and debarment verification backends."""

    @abstractmethod
    async def verify_gstin(self, gstin: str) -> TaxpayerVerificationResponse:
        raise NotImplementedError

    @abstractmethod
    async def verify_udyam(self, udyam_no: str) -> UdyamVerificationResponse:
        raise NotImplementedError

    @abstractmethod
    async def check_debarment(self, pan: str) -> DebarmentCheckResponse:
        raise NotImplementedError


def get_gateway() -> IVerificationGateway:
    """Return the sandbox or live API Setu gateway based on APP_ENV."""
    if settings.APP_ENV == "PRODUCTION":
        from services.apisetu_gateway import ApiSetuLiveGateway

        return ApiSetuLiveGateway()

    from services.sandbox_gateway import SandboxVerificationGateway

    return SandboxVerificationGateway()
