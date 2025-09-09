import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import torch.nn as nn
from typing import List, Dict
import joblib
from pathlib import Path
from loguru import logger

from app.models.schemas import RiskPredictionInput, RiskScore, RiskLevel
from config.settings import settings


class RiskPredictionModel(nn.Module):
    """PyTorch neural network for risk prediction"""

    def __init__(self, input_size: int, hidden_size: int = 128, num_classes: int = 4):
        super(RiskPredictionModel, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, num_classes)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return self.softmax(x)


class MLService:
    """Machine Learning service for patient risk prediction"""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.model_path = Path(settings.model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)

        # Initialize models
        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models for different risk types"""
        try:
            # Load existing models or create new ones
            self._load_or_create_readmission_model()
            self._load_or_create_medication_adherence_model()
            self._load_or_create_disease_progression_model()

            logger.info("ML models initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ML models: {e}")
            # Create default models
            self._create_default_models()

    def _load_or_create_readmission_model(self):
        """Load or create hospital readmission prediction model"""
        model_file = self.model_path / "readmission_model.joblib"
        scaler_file = self.model_path / "readmission_scaler.joblib"

        if model_file.exists() and scaler_file.exists():
            self.models["readmission"] = joblib.load(model_file)
            self.scalers["readmission"] = joblib.load(scaler_file)
            logger.info("Loaded existing readmission model")
        else:
            # Create and train a basic model with synthetic data
            self._create_readmission_model()

    def _create_readmission_model(self):
        """Create and train readmission prediction model"""
        # Generate synthetic training data
        np.random.seed(42)
        n_samples = 1000

        # Features: age, length_of_stay, num_diagnoses, num_medications, emergency_visits
        X = np.random.rand(n_samples, 5)
        X[:, 0] = np.random.normal(65, 15, n_samples)  # age
        X[:, 1] = np.random.exponential(5, n_samples)  # length_of_stay
        X[:, 2] = np.random.poisson(3, n_samples)  # num_diagnoses
        X[:, 3] = np.random.poisson(5, n_samples)  # num_medications
        X[:, 4] = np.random.poisson(2, n_samples)  # emergency_visits

        # Target: readmission risk (higher for older patients, longer stays, more conditions)
        risk_score = (
            X[:, 0] / 100 + X[:, 1] / 20 + X[:, 2] / 10 + X[:, 3] / 15 + X[:, 4] / 5
        )
        y = (risk_score > np.percentile(risk_score, 75)).astype(int)

        # Train model
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        auc_score = roc_auc_score(y_test, y_prob)

        logger.info(f"Readmission model trained with AUC: {auc_score:.3f}")

        # Save model
        self.models["readmission"] = model
        self.scalers["readmission"] = scaler

        joblib.dump(model, self.model_path / "readmission_model.joblib")
        joblib.dump(scaler, self.model_path / "readmission_scaler.joblib")

    def _load_or_create_medication_adherence_model(self):
        """Load or create medication adherence prediction model"""
        model_file = self.model_path / "medication_adherence_model.joblib"
        scaler_file = self.model_path / "medication_adherence_scaler.joblib"

        if model_file.exists() and scaler_file.exists():
            self.models["medication_adherence"] = joblib.load(model_file)
            self.scalers["medication_adherence"] = joblib.load(scaler_file)
            logger.info("Loaded existing medication adherence model")
        else:
            self._create_medication_adherence_model()

    def _create_medication_adherence_model(self):
        """Create medication adherence prediction model"""
        np.random.seed(42)
        n_samples = 1000

        # Features: age, num_medications, complexity_score, socioeconomic_factor, previous_adherence
        X = np.random.rand(n_samples, 5)
        X[:, 0] = np.random.normal(60, 20, n_samples)  # age
        X[:, 1] = np.random.poisson(4, n_samples)  # num_medications
        X[:, 2] = np.random.uniform(1, 10, n_samples)  # complexity_score
        X[:, 3] = np.random.uniform(0, 1, n_samples)  # socioeconomic_factor
        X[:, 4] = np.random.uniform(0, 1, n_samples)  # previous_adherence

        # Non-adherence risk (higher for more medications, lower socioeconomic status)
        risk_score = X[:, 1] / 10 + (1 - X[:, 3]) + X[:, 2] / 10 + (1 - X[:, 4])
        y = (risk_score > np.percentile(risk_score, 70)).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)

        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        auc_score = roc_auc_score(y_test, y_prob)

        logger.info(f"Medication adherence model trained with AUC: {auc_score:.3f}")

        self.models["medication_adherence"] = model
        self.scalers["medication_adherence"] = scaler

        joblib.dump(model, self.model_path / "medication_adherence_model.joblib")
        joblib.dump(scaler, self.model_path / "medication_adherence_scaler.joblib")

    def _load_or_create_disease_progression_model(self):
        """Load or create disease progression prediction model"""
        model_file = self.model_path / "disease_progression_model.joblib"
        scaler_file = self.model_path / "disease_progression_scaler.joblib"

        if model_file.exists() and scaler_file.exists():
            self.models["disease_progression"] = joblib.load(model_file)
            self.scalers["disease_progression"] = joblib.load(scaler_file)
            logger.info("Loaded existing disease progression model")
        else:
            self._create_disease_progression_model()

    def _create_disease_progression_model(self):
        """Create disease progression prediction model"""
        np.random.seed(42)
        n_samples = 1000

        # Features: age, hba1c, bp_systolic, bmi, duration_of_disease
        X = np.random.rand(n_samples, 5)
        X[:, 0] = np.random.normal(65, 12, n_samples)  # age
        X[:, 1] = np.random.normal(7.5, 1.5, n_samples)  # hba1c
        X[:, 2] = np.random.normal(140, 20, n_samples)  # bp_systolic
        X[:, 3] = np.random.normal(28, 5, n_samples)  # bmi
        X[:, 4] = np.random.exponential(5, n_samples)  # duration_of_disease

        # Progression risk (higher for poor control, older age)
        risk_score = (
            (X[:, 1] - 7) / 3
            + (X[:, 2] - 120) / 40
            + (X[:, 3] - 25) / 10
            + X[:, 4] / 10
        )
        y = (risk_score > np.percentile(risk_score, 75)).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)

        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        auc_score = roc_auc_score(y_test, y_prob)

        logger.info(f"Disease progression model trained with AUC: {auc_score:.3f}")

        self.models["disease_progression"] = model
        self.scalers["disease_progression"] = scaler

        joblib.dump(model, self.model_path / "disease_progression_model.joblib")
        joblib.dump(scaler, self.model_path / "disease_progression_scaler.joblib")

    def _create_default_models(self):
        """Create default models if loading fails"""
        logger.warning("Creating default models")
        self._create_readmission_model()
        self._create_medication_adherence_model()
        self._create_disease_progression_model()

    def _extract_features(
        self, prediction_input: RiskPredictionInput
    ) -> Dict[str, np.ndarray]:
        """Extract features from prediction input for different models"""
        features = {}

        # Common features
        base_features = []

        # Vital signs features
        if prediction_input.vital_signs:
            vitals = prediction_input.vital_signs
            base_features.extend(
                [
                    vitals.systolic_bp or 120,
                    vitals.diastolic_bp or 80,
                    vitals.heart_rate or 70,
                    vitals.temperature or 98.6,
                    vitals.respiratory_rate or 16,
                    vitals.oxygen_saturation or 98,
                    vitals.weight or 70,
                    vitals.height or 170,
                ]
            )
        else:
            base_features.extend([120, 80, 70, 98.6, 16, 98, 70, 170])  # Default values

        # Lab results features
        lab_features = [
            0,
            0,
            0,
        ]  # Default: normal glucose, normal cholesterol, normal hba1c
        if prediction_input.lab_results:
            for lab in prediction_input.lab_results:
                if "glucose" in lab.test_name.lower():
                    lab_features[0] = lab.value
                elif "cholesterol" in lab.test_name.lower():
                    lab_features[1] = lab.value
                elif "hba1c" in lab.test_name.lower():
                    lab_features[2] = lab.value

        # Medical history features
        history_features = [0, 0, 0]  # num_diagnoses, num_medications, num_allergies
        if prediction_input.medical_history:
            history = prediction_input.medical_history
            history_features = [
                len(history.diagnoses),
                len(history.medications),
                len(history.allergies),
            ]

        # Readmission model features
        features["readmission"] = np.array(
            [
                base_features[0] / 10,  # age proxy from systolic BP
                len(prediction_input.lab_results)
                if prediction_input.lab_results
                else 3,  # length of stay proxy
                history_features[0],  # num_diagnoses
                history_features[1],  # num_medications
                1 if history_features[0] > 3 else 0,  # emergency_visits proxy
            ]
        ).reshape(1, -1)

        # Medication adherence features
        features["medication_adherence"] = np.array(
            [
                base_features[0] / 2,  # age proxy
                history_features[1],  # num_medications
                min(history_features[1] * 2, 10),  # complexity_score
                0.7,  # socioeconomic_factor (default)
                0.8,  # previous_adherence (default)
            ]
        ).reshape(1, -1)

        # Disease progression features
        features["disease_progression"] = np.array(
            [
                base_features[0] / 2,  # age proxy
                lab_features[2] if lab_features[2] > 0 else 7.0,  # hba1c
                base_features[0],  # bp_systolic
                (base_features[6] / ((base_features[7] / 100) ** 2))
                if base_features[6] > 0 and base_features[7] > 0
                else 25,  # BMI
                max(history_features[0], 1),  # duration_of_disease proxy
            ]
        ).reshape(1, -1)

        return features

    async def predict_risks(
        self, prediction_input: RiskPredictionInput
    ) -> List[RiskScore]:
        """Generate risk predictions for a patient"""
        try:
            features = self._extract_features(prediction_input)
            risk_scores = []

            for risk_type in [
                "readmission",
                "medication_adherence",
                "disease_progression",
            ]:
                if risk_type not in self.models:
                    continue

                model = self.models[risk_type]
                scaler = self.scalers[risk_type]

                # Scale features
                features_scaled = scaler.transform(features[risk_type])

                # Get prediction
                risk_prob = model.predict_proba(features_scaled)[0, 1]
                confidence = max(model.predict_proba(features_scaled)[0])

                # Determine risk level
                if risk_prob >= settings.risk_threshold_high:
                    risk_level = (
                        RiskLevel.HIGH if risk_prob < 0.9 else RiskLevel.CRITICAL
                    )
                elif risk_prob >= settings.risk_threshold_medium:
                    risk_level = RiskLevel.MEDIUM
                else:
                    risk_level = RiskLevel.LOW

                # Get contributing factors (simplified)
                contributing_factors = self._get_contributing_factors(
                    risk_type, features[risk_type][0]
                )

                risk_scores.append(
                    RiskScore(
                        risk_type=risk_type,
                        score=float(risk_prob),
                        risk_level=risk_level,
                        confidence=float(confidence),
                        contributing_factors=contributing_factors,
                    )
                )

            return risk_scores

        except Exception as e:
            logger.error(f"Failed to generate risk predictions: {e}")
            # Return default low-risk scores
            return [
                RiskScore(
                    risk_type="readmission",
                    score=0.2,
                    risk_level=RiskLevel.LOW,
                    confidence=0.5,
                    contributing_factors=["insufficient_data"],
                )
            ]

    def _get_contributing_factors(
        self, risk_type: str, features: np.ndarray
    ) -> List[str]:
        """Get contributing factors for risk prediction"""
        factors = []

        if risk_type == "readmission":
            if features[0] > 7:  # high age proxy
                factors.append("advanced_age")
            if features[2] > 5:  # many diagnoses
                factors.append("multiple_comorbidities")
            if features[3] > 8:  # many medications
                factors.append("polypharmacy")

        elif risk_type == "medication_adherence":
            if features[1] > 6:  # many medications
                factors.append("complex_medication_regimen")
            if features[2] > 8:  # high complexity
                factors.append("high_treatment_complexity")

        elif risk_type == "disease_progression":
            if features[1] > 8:  # high HbA1c
                factors.append("poor_glycemic_control")
            if features[2] > 140:  # high BP
                factors.append("uncontrolled_hypertension")
            if features[3] > 30:  # high BMI
                factors.append("obesity")

        return factors if factors else ["standard_risk_factors"]

    async def generate_recommendations(
        self, patient_id: str, risk_scores: List[RiskScore]
    ) -> List[str]:
        """Generate care recommendations based on risk scores"""
        recommendations = []

        for risk_score in risk_scores:
            if risk_score.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                if risk_score.risk_type == "readmission":
                    recommendations.extend(
                        [
                            "Schedule follow-up appointment within 7 days",
                            "Consider home health services",
                            "Review medication reconciliation",
                        ]
                    )
                elif risk_score.risk_type == "medication_adherence":
                    recommendations.extend(
                        [
                            "Provide medication adherence counseling",
                            "Consider pill organizer or medication synchronization",
                            "Schedule pharmacist consultation",
                        ]
                    )
                elif risk_score.risk_type == "disease_progression":
                    recommendations.extend(
                        [
                            "Intensify disease management protocols",
                            "Increase monitoring frequency",
                            "Consider specialist referral",
                        ]
                    )

        return list(set(recommendations))  # Remove duplicates
