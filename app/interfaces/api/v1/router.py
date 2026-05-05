from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.audit.findings.router import router as audit_findings_router
from app.modules.finance.router import router as finance_router
from app.modules.lgpd.router import router as lgpd_router

settings = get_settings()

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


router.include_router(finance_router)
router.include_router(audit_findings_router)
router.include_router(lgpd_router)
