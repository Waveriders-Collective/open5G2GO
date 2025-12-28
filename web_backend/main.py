"""
Main FastAPI application for Open5G2GO Web Backend.

Exposes REST API endpoints for Open5GS subscriber management,
providing browser-based access to the openSurfControl functionality.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"MongoDB URI: {settings.mongodb_uri}")
    logger.info(f"API prefix: {settings.api_prefix}")
    logger.info(f"Debug mode: {settings.debug}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API for Open5GS mobile core management. "
        "Provides browser-based access to subscriber management, "
        "system monitoring, and network configuration for private 4G networks."
    ),
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint - provides basic API information.
    """
    return JSONResponse({
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs",
        "health": f"{settings.api_prefix}/health"
    })


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


def main():
    """Entry point for running the web backend server."""
    import uvicorn

    uvicorn.run(
        "web_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )


if __name__ == "__main__":
    main()
