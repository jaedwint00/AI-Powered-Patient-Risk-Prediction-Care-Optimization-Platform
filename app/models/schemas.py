from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatientGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class PatientBase(BaseModel):
    patient_id: str = Field(..., description="Unique patient identifier")
    age: int = Field(..., ge=0, le=150, description="Patient age")
    gender: PatientGender
    medical_record_number: str = Field(..., description="Medical record number")


class PatientCreate(PatientBase):
    pass


class Patient(PatientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VitalSigns(BaseModel):
    systolic_bp: Optional[float] = Field(None, ge=50, le=300)
    diastolic_bp: Optional[float] = Field(None, ge=30, le=200)
    heart_rate: Optional[float] = Field(None, ge=30, le=250)
    temperature: Optional[float] = Field(None, ge=90, le=110)  # Fahrenheit
    respiratory_rate: Optional[float] = Field(None, ge=5, le=60)
    oxygen_saturation: Optional[float] = Field(None, ge=70, le=100)
    weight: Optional[float] = Field(None, ge=1, le=1000)  # kg
    height: Optional[float] = Field(None, ge=30, le=300)  # cm


class LabResult(BaseModel):
    test_name: str
    value: float
    unit: str
    reference_range: str
    is_abnormal: bool = False
    timestamp: datetime


class MedicalHistory(BaseModel):
    diagnoses: List[str] = []
    medications: List[str] = []
    allergies: List[str] = []
    surgeries: List[str] = []
    family_history: List[str] = []


class RiskPredictionInput(BaseModel):
    patient_id: str
    vital_signs: Optional[VitalSigns] = None
    lab_results: Optional[List[LabResult]] = []
    medical_history: Optional[MedicalHistory] = None
    clinical_notes: Optional[str] = None


class RiskScore(BaseModel):
    risk_type: str  # readmission, medication_adherence, disease_progression
    score: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0, le=1)
    contributing_factors: List[str] = []


class RiskPredictionResponse(BaseModel):
    patient_id: str
    prediction_id: str
    timestamp: datetime
    risk_scores: List[RiskScore]
    recommendations: List[str] = []
    next_review_date: Optional[datetime] = None


class AlertCreate(BaseModel):
    patient_id: str
    alert_type: str
    severity: RiskLevel
    message: str
    triggered_by: str  # What triggered the alert
    metadata: Optional[Dict[str, Any]] = {}


class Alert(AlertCreate):
    id: int
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NLPProcessingRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    task: str = Field(..., description="extract_entities, summarize, or search")
    patient_id: Optional[str] = None


class ExtractedEntity(BaseModel):
    entity_type: str  # diagnosis, medication, allergy, procedure
    text: str
    confidence: float = Field(..., ge=0, le=1)
    start_pos: int
    end_pos: int


class NLPProcessingResponse(BaseModel):
    request_id: str
    task: str
    patient_id: Optional[str] = None
    processed_at: datetime
    results: Dict[str, Any]  # Flexible structure for different NLP tasks


class CareRecommendation(BaseModel):
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
    total_patients: int
    high_risk_patients: int
    active_alerts: int
    predictions_today: int
    system_uptime: float
    database_status: str
