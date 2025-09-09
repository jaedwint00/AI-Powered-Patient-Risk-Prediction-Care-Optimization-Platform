"""Patient management API routes."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status
from loguru import logger

from app.models.schemas import Patient, PatientCreate, VitalSigns, LabResult
from app.database.connection import get_database, DatabaseManager

router = APIRouter()


@router.post("/patients", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient: PatientCreate, db: DatabaseManager = Depends(get_database)
):
    """
    Create a new patient record
    """
    try:
        # Check if patient already exists
        existing = await db.execute_query(
            "SELECT id FROM patients WHERE patient_id = ?", [patient.patient_id]
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient with this ID already exists",
            )

        # Get next ID
        next_id_result = await db.execute_query(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM patients"
        )
        next_id = next_id_result[0][0] if next_id_result else 1

        # Insert new patient
        await db.execute_query(
            """
            INSERT INTO patients (
                id, patient_id, age, gender, medical_record_number, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            [
                next_id,
                patient.patient_id,
                patient.age,
                patient.gender.value,
                patient.medical_record_number,
                datetime.utcnow(),
            ],
        )

        # Fetch the created patient
        result = await db.execute_query(
            "SELECT * FROM patients WHERE patient_id = ?", [patient.patient_id]
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create patient",
            )

        patient_data = result[0]

        logger.info(f"Created patient: {patient.patient_id}")

        return Patient(
            id=patient_data[0],
            patient_id=patient_data[1],
            age=patient_data[2],
            gender=patient_data[3],
            medical_record_number=patient_data[4],
            created_at=patient_data[5],
            updated_at=patient_data[6],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/patients/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str, db: DatabaseManager = Depends(get_database)):
    """
    Get patient by ID
    """
    try:
        result = await db.execute_query(
            "SELECT * FROM patients WHERE patient_id = ?", [patient_id]
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        patient_data = result[0]

        return Patient(
            id=patient_data[0],
            patient_id=patient_data[1],
            age=patient_data[2],
            gender=patient_data[3],
            medical_record_number=patient_data[4],
            created_at=patient_data[5],
            updated_at=patient_data[6],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/patients", response_model=List[Patient])
async def list_patients(
    skip: int = 0, limit: int = 100, db: DatabaseManager = Depends(get_database)
):
    """
    List patients with pagination
    """
    try:
        result = await db.execute_query(
            "SELECT * FROM patients ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [limit, skip],
        )

        patients = []
        for patient_data in result:
            patients.append(
                Patient(
                    id=patient_data[0],
                    patient_id=patient_data[1],
                    age=patient_data[2],
                    gender=patient_data[3],
                    medical_record_number=patient_data[4],
                    created_at=patient_data[5],
                    updated_at=patient_data[6],
                )
            )

        return patients

    except Exception as e:
        logger.error(f"Error retrieving patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post("/patients/{patient_id}/vitals")
async def add_vital_signs(
    patient_id: str, vitals: VitalSigns, db: DatabaseManager = Depends(get_database)
):
    """
    Add vital signs for a patient
    """
    try:
        # Verify patient exists
        patient_result = await db.execute_query(
            "SELECT id FROM patients WHERE patient_id = ?", [patient_id]
        )

        if not patient_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        # Generate unique ID for vital signs
        id_result = await db.execute_query(
            "SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM vital_signs"
        )
        next_id = id_result[0][0] if id_result else 1

        # Insert vital signs
        await db.execute_query(
            """
            INSERT INTO vital_signs (
                id, patient_id, systolic_bp, diastolic_bp, heart_rate,
                temperature, respiratory_rate, oxygen_saturation,
                weight, height, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                next_id,
                patient_id,
                vitals.systolic_bp,
                vitals.diastolic_bp,
                vitals.heart_rate,
                vitals.temperature,
                vitals.respiratory_rate,
                vitals.oxygen_saturation,
                vitals.weight,
                vitals.height,
                datetime.utcnow(),
            ],
        )

        logger.info(f"Added vital signs for patient: {patient_id}")

        return {"message": "Vital signs added successfully", "patient_id": patient_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding vital signs for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post("/patients/{patient_id}/labs")
async def add_lab_results(
    patient_id: str,
    lab_results: List[LabResult],
    db: DatabaseManager = Depends(get_database),
):
    """
    Add lab results for a patient
    """
    try:
        # Verify patient exists
        patient_result = await db.execute_query(
            "SELECT id FROM patients WHERE patient_id = ?", [patient_id]
        )

        if not patient_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        # Insert lab results
        for lab in lab_results:
            # Generate unique ID for lab result
            id_result = await db.execute_query(
                "SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM lab_results"
            )
            next_id = id_result[0][0] if id_result else 1

            await db.execute_query(
                """
                INSERT INTO lab_results (
                    id, patient_id, test_name, value, unit,
                    reference_range, is_abnormal, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    next_id,
                    patient_id,
                    lab.test_name,
                    lab.value,
                    lab.unit,
                    lab.reference_range,
                    lab.is_abnormal,
                    lab.timestamp,
                ],
            )

        logger.info(f"Added {len(lab_results)} lab results for patient: {patient_id}")

        return {
            "message": f"Added {len(lab_results)} lab results successfully",
            "patient_id": patient_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding lab results for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
