"""Risk prediction API routes."""
import json
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger

from app.database.connection import DatabaseManager, get_database
from app.models.schemas import (RiskLevel, RiskPredictionInput,
                                RiskPredictionResponse, RiskScore)
from app.services.ml_service import MLService

router = APIRouter()


@router.post("/predictions", response_model=RiskPredictionResponse)
async def predict_patient_risk(
    prediction_input: RiskPredictionInput,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_database),
):
    """
    Generate risk predictions for a patient
    """
    try:
        # Verify patient exists
        patient_result = await db.execute_query(
            "SELECT id FROM patients WHERE patient_id = ?",
            [prediction_input.patient_id],
        )

        if not patient_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        prediction_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Initialize ML service
        ml_service = MLService()

        # Generate risk predictions
        risk_scores = await ml_service.predict_risks(prediction_input)

        # Store predictions in database
        for risk_score in risk_scores:
            # Get next ID for risk_predictions
            next_id_result = await db.execute_query(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM risk_predictions"
            )
            next_id = next_id_result[0][0] if next_id_result else 1

            # Generate unique prediction_id for each risk score
            individual_prediction_id = f"{prediction_id}_{risk_score.risk_type}"

            await db.execute_query(
                """
                INSERT INTO risk_predictions (
                    id, prediction_id, patient_id, risk_type, risk_score,
                    risk_level, confidence, contributing_factors,
                    recommendations, created_at, next_review_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    next_id,
                    individual_prediction_id,
                    prediction_input.patient_id,
                    risk_score.risk_type,
                    risk_score.score,
                    risk_score.risk_level.value,
                    risk_score.confidence,
                    json.dumps(risk_score.contributing_factors),
                    json.dumps([]),
                    # Recommendations will be generated separately
                    timestamp,
                    timestamp + timedelta(days=7),  # Review in 7 days
                ],
            )

        # Generate care recommendations
        recommendations = await ml_service.generate_recommendations(risk_scores)

        # Check for high-risk alerts
        high_risk_scores = [
            rs
            for rs in risk_scores
            if rs.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
        if high_risk_scores:
            background_tasks.add_task(
                create_risk_alerts, prediction_input.patient_id, high_risk_scores, db
            )

        logger.info(
            f"Generated risk predictions for patient: {prediction_input.patient_id}"
        )

        return RiskPredictionResponse(
            patient_id=prediction_input.patient_id,
            prediction_id=prediction_id,
            timestamp=timestamp,
            risk_scores=risk_scores,
            recommendations=recommendations,
            next_review_date=timestamp + timedelta(days=7),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to generate predictions for patient "
            f"{prediction_input.patient_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/predictions/{patient_id}", response_model=List[RiskPredictionResponse])
async def get_patient_predictions(
    patient_id: str, limit: int = 10, db: DatabaseManager = Depends(get_database)
):
    """
    Get recent risk predictions for a patient
    """
    try:
        # Get predictions
        result = await db.execute_query(
            """
            SELECT prediction_id, patient_id, created_at, next_review_date
            FROM risk_predictions
            WHERE patient_id = ?
            GROUP BY prediction_id, patient_id, created_at, next_review_date
            ORDER BY created_at DESC
            LIMIT ?
        """,
            [patient_id, limit],
        )

        predictions = []
        for row in result:
            prediction_id, patient_id, created_at, next_review_date = row

            # Get risk scores for this prediction
            scores_result = await db.execute_query(
                """
                SELECT risk_type, risk_score, risk_level, confidence,
                       contributing_factors
                FROM risk_predictions
                WHERE prediction_id = ?
            """,
                [prediction_id],
            )

            risk_scores = []
            for score_row in scores_result:
                risk_type, score, level, confidence, factors = score_row
                risk_scores.append(
                    RiskScore(
                        risk_type=risk_type,
                        score=score,
                        risk_level=RiskLevel(level),
                        confidence=confidence,
                        contributing_factors=json.loads(factors) if factors else [],
                    )
                )

            predictions.append(
                RiskPredictionResponse(
                    patient_id=patient_id,
                    prediction_id=prediction_id,
                    timestamp=created_at,
                    risk_scores=risk_scores,
                    recommendations=[],  # Could be loaded separately if needed
                    next_review_date=next_review_date,
                )
            )

        return predictions

    except Exception as e:
        logger.error(f"Error retrieving predictions for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/predictions/high-risk")
async def get_high_risk_patients(db: DatabaseManager = Depends(get_database)):
    """
    Get patients with high or critical risk scores
    """
    try:
        result = await db.execute_query(
            """
            SELECT DISTINCT p.patient_id, p.age, p.gender,
                   rp.risk_type, rp.risk_score, rp.risk_level, rp.created_at
            FROM patients p
            JOIN risk_predictions rp ON p.patient_id = rp.patient_id
            WHERE rp.risk_level IN ('high', 'critical')
            AND rp.created_at >= CURRENT_DATE - INTERVAL 7 DAYS
            ORDER BY rp.risk_score DESC, rp.created_at DESC
        """
        )

        high_risk_patients = []
        for row in result:
            patient_id, age, gender, risk_type, risk_score, risk_level, created_at = row
            high_risk_patients.append(
                {
                    "patient_id": patient_id,
                    "age": age,
                    "gender": gender,
                    "risk_type": risk_type,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "last_assessment": created_at,
                }
            )

        return {"high_risk_patients": high_risk_patients}

    except Exception as e:
        logger.error(f"Error creating risk prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


async def create_risk_alerts(
    patient_id: str, risk_scores: List[RiskScore], db: DatabaseManager
):
    """
    Background task to create alerts for high-risk patients
    """
    try:
        for risk_score in risk_scores:
            if risk_score.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await db.execute_query(
                    """
                    INSERT INTO alerts (
                        patient_id, alert_type, severity, message,
                        triggered_by, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    [
                        patient_id,
                        f"{risk_score.risk_type}_risk",
                        risk_score.risk_level.value,
                        f"High {risk_score.risk_type} risk detected "
                        f"(score: {risk_score.score:.2f})",
                        "risk_prediction_model",
                        json.dumps(
                            {
                                "risk_score": risk_score.score,
                                "confidence": risk_score.confidence,
                                "contributing_factors": risk_score.contributing_factors,
                            }
                        ),
                        datetime.utcnow(),
                    ],
                )

        logger.info(f"Created risk alerts for patient: {patient_id}")

    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Failed to create risk alerts for patient {patient_id}: {e}")
    except (ConnectionError, RuntimeError, AttributeError) as e:
        logger.error(
            f"Unexpected error creating risk alerts for patient {patient_id}: {e}"
        )
