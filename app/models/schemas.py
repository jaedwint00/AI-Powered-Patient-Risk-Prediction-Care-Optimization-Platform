"""
Pydantic schemas for the AI-Powered Patient Risk Prediction platform.

Defines data models for patients, risk predictions, alerts, NLP processing,
and other core entities used throughout the healthcare platform.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level enumeration for patient risk assessments."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatientGender(str, Enum):
    """Patient gender enumeration."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AlertStatus(str, Enum):
    """Alert status enumeration for tracking alert lifecycle."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class PatientBase(BaseModel):
    """Base patient model with core patient information."""

    patient_id: str = Field(..., description="Unique patient identifier")
    age: int = Field(..., ge=0, le=150, description="Patient age")
    gender: PatientGender
    medical_record_number: str = Field(..., description="Medical record number")


class PatientCreate(PatientBase):
    """Patient creation request model."""


class Patient(PatientBase):
    """Complete patient model with database fields."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration for Patient model."""

        from_attributes = True


class VitalSigns(BaseModel):
    """Patient vital signs measurements."""

    systolic_bp: Optional[float] = Field(None, ge=50, le=300)
    diastolic_bp: Optional[float] = Field(None, ge=30, le=200)
    heart_rate: Optional[float] = Field(None, ge=30, le=250)
    temperature: Optional[float] = Field(None, ge=90, le=110)  # Fahrenheit
    respiratory_rate: Optional[float] = Field(None, ge=5, le=60)
    oxygen_saturation: Optional[float] = Field(None, ge=70, le=100)
    weight: Optional[float] = Field(None, ge=1, le=1000)  # kg
    height: Optional[float] = Field(None, ge=30, le=300)  # cm


class LabResult(BaseModel):
    """Laboratory test result model."""

    test_name: str
    value: float
    unit: str
    reference_range: str
    is_abnormal: bool = False
    timestamp: datetime


class MedicalHistory(BaseModel):
    """Patient medical history information."""

    diagnoses: List[str] = []
    medications: List[str] = []
    allergies: List[str] = []
    surgeries: List[str] = []
    family_history: List[str] = []


class RiskPredictionInput(BaseModel):
    """Input data for ML risk prediction models."""

    patient_id: str
    vital_signs: Optional[VitalSigns] = None
    lab_results: Optional[List[LabResult]] = []
    medical_history: Optional[MedicalHistory] = None
    clinical_notes: Optional[str] = None


class RiskScore(BaseModel):
    """Individual risk score result from ML prediction."""

    risk_type: str  # readmission, medication_adherence, disease_progression
    score: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0, le=1)
    contributing_factors: List[str] = []


class RiskPredictionResponse(BaseModel):
    """Complete risk prediction response with recommendations."""

    patient_id: str
    prediction_id: str
    timestamp: datetime
    risk_scores: List[RiskScore]
    recommendations: List[str] = []
    next_review_date: Optional[datetime] = None


class AlertCreate(BaseModel):
    """Alert creation request model."""

    patient_id: str
    alert_type: str
    severity: RiskLevel
    message: str
    triggered_by: str  # What triggered the alert
    metadata: Optional[Dict[str, Any]] = {}


class Alert(AlertCreate):
    """Complete alert model with database fields."""

    id: int
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration for Alert model."""

        from_attributes = True


class NLPProcessingRequest(BaseModel):
    """Request model for NLP text processing."""

    text: str = Field(..., min_length=1, max_length=10000)
    task: str = Field(..., description="extract_entities, summarize, or search")
    patient_id: Optional[str] = None


class ExtractedEntity(BaseModel):
    """Named entity extracted from clinical text."""

    entity_type: str  # diagnosis, medication, allergy, procedure
    text: str
    confidence: float = Field(..., ge=0, le=1)
    start_pos: int
    end_pos: int


class NLPProcessingResponse(BaseModel):
    """Response model for NLP processing results."""

    request_id: str
    task: str
    patient_id: Optional[str] = None
    processed_at: datetime
    results: Dict[str, Any]  # Flexible structure for different NLP tasks


class CareRecommendation(BaseModel):
    """Clinical care recommendation model."""

    recommendation_id: str
    patient_id: str
    recommendation_type: str  # medication, lifestyle, follow_up, etc.
    title: str
    description: str
    priority: RiskLevel
    evidence_level: str  # A, B, C based on clinical evidence
    created_at: datetime
    due_date: Optional[datetime] = None


class HealthMetrics(BaseModel):
    """System health and performance metrics."""

    total_patients: int
    high_risk_patients: int
    active_alerts: int
    predictions_today: int
    system_uptime: float
    database_status: str
