#!/usr/bin/env python3
"""
API Endpoint Testing Script
Tests key API endpoints with sample data to validate platform functionality
"""

import time

import requests  # type: ignore

BASE_URL = "http://localhost:8000/api/v1"


def test_health_endpoint():
    """Test health check endpoint"""
    print("🔍 Testing Health Check Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Status: {data.get('status', 'Unknown')}")
            print(f"   Uptime: {data.get('uptime', 'Unknown')}")
            db_status = data.get('database_status') == 'connected'
            status_text = 'Connected' if db_status else 'Disconnected'
            print(f"   Database: {status_text}")
            return True
        print(f"❌ Health check failed: {response.status_code}")
        return False
    except requests.RequestException as e:
        print(f"❌ Health check error: {e}")
        return False


def test_patient_creation():
    """Test patient creation endpoint"""
    print("\n👤 Testing Patient Creation...")

    patient_data = {
        "patient_id": "TEST001",
        "age": 45,
        "gender": "female",
        "medical_record_number": "MRN_TEST_001",
    }

    try:
        response = requests.post(
            f"{BASE_URL}/patients", json=patient_data, timeout=30
        )
        if response.status_code == 201:
            print("✅ Patient created successfully")
            return response.json()
        if response.status_code == 409:
            print("ℹ️ Patient already exists")
            # Get existing patient
            response = requests.get(
                f"{BASE_URL}/patients/TEST001", timeout=30
            )
            return response.json() if response.status_code == 200 else None
        print(
            f"❌ Patient creation failed: {response.status_code} - "
            f"{response.text}"
        )
        return None
    except requests.RequestException as e:
        print(f"❌ Patient creation error: {e}")
        return None


def test_vital_signs():
    """Test adding vital signs"""
    print("\n📊 Testing Vital Signs...")

    vitals_data = {
        "patient_id": "TEST001",
        "systolic_bp": 140,
        "diastolic_bp": 90,
        "heart_rate": 85,
        "temperature": 98.6,
        "respiratory_rate": 18,
        "oxygen_saturation": 97,
        "weight": 70.5,
        "height": 165,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/patients/TEST001/vitals", json=vitals_data, timeout=30
        )
        if response.status_code == 200:
            print("✅ Vital signs recorded successfully")
            return True
        print(
            f"❌ Vital signs failed: {response.status_code} - {response.text}"
        )
        return False
    except requests.RequestException as e:
        print(f"❌ Vital signs error: {e}")
        return False


def test_lab_results():
    """Test adding lab results"""
    print("\n🧪 Testing Lab Results...")

    lab_data = [
        {
            "test_name": "HbA1c",
            "value": 7.5,
            "unit": "%",
            "reference_range": "< 7.0%",
            "is_abnormal": True,
            "timestamp": "2025-09-09T15:47:00Z",
        }
    ]

    try:
        response = requests.post(
            f"{BASE_URL}/patients/TEST001/labs", json=lab_data, timeout=30
        )
        if response.status_code == 200:
            print("✅ Lab results recorded successfully")
            return True
        print(
            f"❌ Lab results failed: {response.status_code} - {response.text}"
        )
        return False
    except requests.RequestException as e:
        print(f"❌ Lab results error: {e}")
        return False


def test_risk_prediction():
    """Test ML risk prediction"""
    print("\n🔮 Testing Risk Prediction...")

    prediction_data = {
        "patient_id": "TEST001",
        "vital_signs": {
            "systolic_bp": 140,
            "diastolic_bp": 90,
            "heart_rate": 85,
            "temperature": 98.6,
            "oxygen_saturation": 97,
            "weight": 70.5,
            "height": 165,
        },
        "medical_history": {
            "diagnoses": ["Type 2 Diabetes", "Hypertension"],
            "medications": ["Metformin", "Lisinopril"],
            "allergies": ["Penicillin"],
        },
        "clinical_notes": (
            "Patient presents for routine diabetes follow-up. "
            "Blood pressure elevated at 140/90."
        ),
    }

    try:
        response = requests.post(
            f"{BASE_URL}/predictions", json=prediction_data, timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ Risk prediction generated successfully")
            for risk in data.get("risk_scores", []):
                risk_level = risk.get("risk_level", "unknown").upper()
                risk_type = (
                    risk.get("risk_type", "unknown")
                    .replace("_", " ")
                    .title()
                )
                score = risk.get("score", 0) * 100
                print(f"   • {risk_type}: {score:.1f}% ({risk_level})")
            return True
        print(
            f"❌ Risk prediction failed: {response.status_code} - "
            f"{response.text}"
        )
        return False
    except requests.RequestException as e:
        print(f"❌ Risk prediction error: {e}")
        return False


def test_nlp_processing():
    """Test NLP text processing"""
    print("\n📝 Testing NLP Processing...")

    nlp_data = {
        "text": (
            "Patient presents with chest pain and shortness of breath. "
            "Taking metformin for diabetes. "
            "Blood pressure elevated at 150/95 mmHg."
        ),
        "task": "extract_entities",
        "patient_id": "TEST001",
    }

    try:
        response = requests.post(
            f"{BASE_URL}/nlp/process",
            json=nlp_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ NLP processing completed successfully")
            entities = data.get("categorized", {})
            if entities.get("medications"):
                medications = ', '.join(entities['medications'])
                print(f"   💊 Medications: {medications}")
            if entities.get("conditions"):
                print(f"   🏥 Conditions: {', '.join(entities['conditions'])}")
            if entities.get("symptoms"):
                print(f"   🩺 Symptoms: {', '.join(entities['symptoms'])}")
            return True
        print(
            f"❌ NLP processing failed: {response.status_code} - "
            f"{response.text}"
        )
        return False
    except requests.RequestException as e:
        print(f"❌ NLP processing error: {e}")
        return False


def test_patient_list():
    """Test patient listing"""
    print("\n📋 Testing Patient List...")

    try:
        response = requests.get(f"{BASE_URL}/patients", timeout=30)
        if response.status_code == 200:
            patients = response.json()
            print(f"✅ Retrieved {len(patients)} patients")
            return True
        print(
            f"❌ Patient list failed: {response.status_code} - {response.text}"
        )
        return False
    except requests.RequestException as e:
        print(f"❌ Patient list error: {e}")
        return False


def main():
    """Run all API endpoint tests"""
    print("🧪 AI Healthcare Platform - API Endpoint Testing")
    print("=" * 60)

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding. Please start the server first:")
            print("   python main.py")
            return
    except requests.RequestException:
        print("❌ Server not accessible. Please start the server first:")
        print("   python main.py")
        return

    # Run tests
    tests = [
        test_health_endpoint,
        test_patient_creation,
        test_vital_signs,
        test_lab_results,
        test_risk_prediction,
        test_nlp_processing,
        test_patient_list,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        time.sleep(0.5)  # Brief pause between tests

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All API endpoints are working correctly!")
        print("\n🌐 Platform Access:")
        print("   📊 Live Server: http://localhost:8000/")
        print("   📚 API Documentation: http://localhost:8000/docs")
        print("   🔍 Health Dashboard: http://localhost:8000/api/v1/health")
    else:
        print("⚠️ Some tests failed. Check server logs for details.")


if __name__ == "__main__":
    main()
