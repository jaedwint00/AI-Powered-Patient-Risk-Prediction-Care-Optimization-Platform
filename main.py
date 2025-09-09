"""
AI-Powered Patient Risk Prediction & Care Optimization Platform

Main FastAPI application entry point for the healthcare platform.
Provides HIPAA-compliant AI services for patient risk prediction,
care optimization, and clinical decision support.
"""

import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from loguru import logger

from app.api.routes import (alerts,  # pylint: disable=wrong-import-position
                            auth, health, nlp, patients, predictions)
from app.database.connection import \
    init_database  # pylint: disable=wrong-import-position
from app.utils.logging_config import \
    setup_logging  # pylint: disable=wrong-import-position
from config.settings import settings  # pylint: disable=wrong-import-position

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

# Import after path setup to avoid import errors


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):  # pylint: disable=unused-argument
    """Application lifespan events"""
    # Startup
    logger.info("Starting AI-Powered Patient Risk Prediction Platform")
    setup_logging()
    await init_database()
    logger.info("Database initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down AI-Powered Patient Risk Prediction Platform")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=(
        "HIPAA-compliant AI platform for patient risk prediction and care optimization"
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Security
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["health"])
app.include_router(patients.router, prefix=settings.api_v1_prefix, tags=["patients"])
app.include_router(
    predictions.router, prefix=settings.api_v1_prefix, tags=["predictions"]
)
app.include_router(alerts.router, prefix=settings.api_v1_prefix, tags=["alerts"])
app.include_router(nlp.router, prefix=settings.api_v1_prefix, tags=["nlp"])
app.include_router(auth.router, prefix=settings.api_v1_prefix, tags=["auth"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI-Powered Patient Risk Prediction Platform",
        "version": settings.app_version,
        "status": "operational",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
