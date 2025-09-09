from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.models.schemas import Alert, AlertCreate, AlertStatus, RiskLevel
from app.database.connection import get_database, DatabaseManager
from loguru import logger
import json
from datetime import datetime

router = APIRouter()


@router.post("/alerts", response_model=Alert, status_code=status.HTTP_201_CREATED)
async def create_alert(alert: AlertCreate, db: DatabaseManager = Depends(get_database)):
    """
    Create a new alert
    """
    try:
        # Verify patient exists
        patient_result = await db.execute_query(
            "SELECT id FROM patients WHERE patient_id = ?", [alert.patient_id]
        )

        if not patient_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        # Insert alert
        await db.execute_query(
            """
            INSERT INTO alerts (
                patient_id, alert_type, severity, message, 
                triggered_by, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            [
                alert.patient_id,
                alert.alert_type,
                alert.severity.value,
                alert.message,
                alert.triggered_by,
                json.dumps(alert.metadata) if alert.metadata else None,
                datetime.utcnow(),
            ],
        )

        # Get the created alert
        result = await db.execute_query(
            """
            SELECT * FROM alerts 
            WHERE patient_id = ? AND created_at = (
                SELECT MAX(created_at) FROM alerts WHERE patient_id = ?
            )
        """,
            [alert.patient_id, alert.patient_id],
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create alert",
            )

        alert_data = result[0]

        logger.info(f"Created alert for patient: {alert.patient_id}")

        return Alert(
            id=alert_data[0],
            patient_id=alert_data[1],
            alert_type=alert_data[2],
            severity=RiskLevel(alert_data[3]),
            message=alert_data[4],
            triggered_by=alert_data[5],
            status=AlertStatus(alert_data[6]),
            metadata=json.loads(alert_data[7]) if alert_data[7] else {},
            created_at=alert_data[8],
            acknowledged_at=alert_data[9],
            acknowledged_by=alert_data[10],
            resolved_at=alert_data[11],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/alerts", response_model=List[Alert])
async def list_alerts(
    status_filter: Optional[AlertStatus] = None,
    severity_filter: Optional[RiskLevel] = None,
    patient_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: DatabaseManager = Depends(get_database),
):
    """
    List alerts with optional filters
    """
    try:
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter.value)

        if severity_filter:
            query += " AND severity = ?"
            params.append(severity_filter.value)

        if patient_id:
            query += " AND patient_id = ?"
            params.append(patient_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        result = await db.execute_query(query, params)

        alerts = []
        for alert_data in result:
            alerts.append(
                Alert(
                    id=alert_data[0],
                    patient_id=alert_data[1],
                    alert_type=alert_data[2],
                    severity=RiskLevel(alert_data[3]),
                    message=alert_data[4],
                    triggered_by=alert_data[5],
                    status=AlertStatus(alert_data[6]),
                    metadata=json.loads(alert_data[7]) if alert_data[7] else {},
                    created_at=alert_data[8],
                    acknowledged_at=alert_data[9],
                    acknowledged_by=alert_data[10],
                    resolved_at=alert_data[11],
                )
            )

        return alerts

    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int, acknowledged_by: str, db: DatabaseManager = Depends(get_database)
):
    """
    Acknowledge an alert
    """
    try:
        # Check if alert exists
        result = await db.execute_query(
            "SELECT id FROM alerts WHERE id = ?", [alert_id]
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )

        # Update alert status
        await db.execute_query(
            """
            UPDATE alerts 
            SET status = 'acknowledged', acknowledged_at = ?, acknowledged_by = ?
            WHERE id = ?
        """,
            [datetime.utcnow(), acknowledged_by, alert_id],
        )

        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")

        return {"message": "Alert acknowledged successfully", "alert_id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: DatabaseManager = Depends(get_database)):
    """
    Resolve an alert
    """
    try:
        # Check if alert exists
        result = await db.execute_query(
            "SELECT id FROM alerts WHERE id = ?", [alert_id]
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )

        # Update alert status
        await db.execute_query(
            """
            UPDATE alerts 
            SET status = 'resolved', resolved_at = ?
            WHERE id = ?
        """,
            [datetime.utcnow(), alert_id],
        )

        logger.info(f"Alert {alert_id} resolved")

        return {"message": "Alert resolved successfully", "alert_id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/alerts/active/count")
async def get_active_alerts_count(db: DatabaseManager = Depends(get_database)):
    """
    Get count of active alerts by severity
    """
    try:
        result = await db.execute_query(
            """
            SELECT severity, COUNT(*) as count
            FROM alerts 
            WHERE status = 'active'
            GROUP BY severity
        """
        )

        alert_counts = {}
        for row in result:
            severity, count = row
            alert_counts[severity] = count

        return {
            "active_alerts": alert_counts,
            "total_active": sum(alert_counts.values()),
        }

    except Exception as e:
        logger.error(f"Failed to get active alerts count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
