from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import (
    CartorioException,
    cartorio_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.interfaces.api.v1.router import router as v1_router

setup_logging()
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # O esquema do banco é gerenciado exclusivamente pelo Alembic.
    # Nenhuma operação de DDL deve acontecer aqui.
    logger.info("Iniciando %s v%s", settings.app_name, settings.app_version)
    yield
    logger.info("Encerrando aplicação.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_exception_handler(CartorioException, cartorio_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

app.include_router(v1_router, prefix=settings.api_prefix)
