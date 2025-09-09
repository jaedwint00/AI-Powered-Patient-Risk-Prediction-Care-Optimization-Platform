"""
Health monitoring API endpoints for the AI-Powered Patient Risk Prediction platform.

Provides system health checks, database status monitoring, and resource utilization
metrics.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends
from loguru import logger
import psutil

from app.database.connection import DatabaseManager, get_database
from app.models.schemas import HealthMetrics

router = APIRouter()

start_time = time.time()


@router.get("/health", response_model=HealthMetrics)
async def health_check(db: DatabaseManager = Depends(get_database)):
    """
    Health check endpoint for monitoring system status
    """
    try:
        # Get system metrics
        uptime = time.time() - start_time

        # Database health check
        try:
            await db.execute_query("SELECT 1")
            db_status = "healthy"
        except (ConnectionError, TimeoutError, Exception) as e:
            logger.warning(f"Database health check failed: {e}")
            db_status = "unhealthy"

        # Get patient statistics
        try:
            total_patients_result = await db.execute_query(
                "SELECT COUNT(*) FROM patients"
            )
            total_patients = total_patients_result[0][0] if total_patients_result else 0

            high_risk_result = await db.execute_query(
                """
                SELECT COUNT(DISTINCT patient_id) FROM risk_predictions
                WHERE risk_level IN ('high', 'critical')
                AND created_at >= CURRENT_DATE
            """
            )
            high_risk_patients = high_risk_result[0][0] if high_risk_result else 0

            active_alerts_result = await db.execute_query(
                """
                SELECT COUNT(*) FROM alerts WHERE status = 'active'
            """
            )
            active_alerts = active_alerts_result[0][0] if active_alerts_result else 0

            predictions_today_result = await db.execute_query(
                """
                SELECT COUNT(*) FROM risk_predictions
                WHERE CAST(created_at AS DATE) = CURRENT_DATE
            """
            )
            predictions_today = (
                predictions_today_result[0][0] if predictions_today_result else 0
            )

        except (ValueError, TypeError, ConnectionError) as e:
            logger.warning(f"Could not fetch database metrics: {e}")
            total_patients = 0
            high_risk_patients = 0
            active_alerts = 0
            predictions_today = 0

        return HealthMetrics(
            total_patients=total_patients,
            high_risk_patients=high_risk_patients,
            active_alerts=active_alerts,
            predictions_today=predictions_today,
            system_uptime=uptime,
            database_status=db_status,
        )

    except (ValueError, TypeError, ConnectionError) as e:
        logger.error(f"Health check failed: {e}")
        return HealthMetrics(
            total_patients=0,
            high_risk_patients=0,
            active_alerts=0,
            predictions_today=0,
            system_uptime=time.time() - start_time,
            database_status="error",
        )
    except Exception as e:
        logger.error(f"Unexpected error in health check: {e}")
        return HealthMetrics(
            total_patients=0,
            high_risk_patients=0,
            active_alerts=0,
            predictions_today=0,
            system_uptime=uptime,
            database_status="error",
        )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with system resources
    """
    try:
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "uptime_seconds": time.time() - start_time,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
            },
        }
    except (OSError, ValueError) as e:
        logger.error(f"System resource check failed: {e}")
        return {"status": "error", "timestamp": datetime.utcnow(), "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in detailed health check: {e}")
        return {"status": "error", "timestamp": datetime.utcnow(), "error": str(e)}
