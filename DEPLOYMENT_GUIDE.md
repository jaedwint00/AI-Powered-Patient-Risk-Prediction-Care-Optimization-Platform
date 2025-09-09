# AI-Powered Patient Risk Prediction Platform - Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose (optional)
- 8GB+ RAM (for ML models)

### Local Development Setup

1. **Clone and Setup Environment**
```bash
cd AI-Powered-Patient-Risk-Prediction-Care-Optimization-Platform
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start the Platform**
```bash
# Recommended: Direct FastAPI startup
python main.py

# Alternative: Using uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

4. **Test the Platform**
```bash
# Run realistic healthcare demo (5 patients with AI processing)
python scripts/realistic_demo.py

# Test API endpoints (requires server running)
python scripts/test_endpoints.py

# Access API documentation (debug mode enabled)
# http://localhost:8000/docs
```

### Docker Deployment

1. **Build and Run with Docker Compose**
```bash
docker-compose up --build
```

2. **Access the Platform**
- API: http://localhost:8000/api/v1/
- Documentation: http://localhost:8000/docs (debug mode enabled)
- Health Check: http://localhost:8000/api/v1/health

## 🏗️ Architecture Overview

### Core Components

1. **FastAPI Application** (`main.py`)
   - RESTful API endpoints
   - Automatic OpenAPI documentation
   - CORS middleware
   - Lifecycle management

2. **Database Layer** (`app/database/`)
   - DuckDB for analytics and storage
   - Async connection management
   - Automatic schema creation

3. **ML Services** (`app/services/ml_service.py`)
   - Hospital readmission prediction
   - Medication adherence modeling
   - Disease progression analysis
   - PyTorch and Scikit-learn models

4. **NLP Services** (`app/services/nlp_service.py`)
   - Medical entity extraction
   - Clinical text summarization
   - Semantic search capabilities
   - Simplified rule-based implementation (no external dependencies)

5. **Alert System** (`app/services/alert_service.py`)
   - Real-time risk monitoring
   - Configurable alert rules
   - Async notification system

6. **Authentication** (`app/services/auth_service.py`)
   - JWT token management
   - Role-based access control
   - HIPAA-compliant audit logging

### API Endpoints

#### Health & Monitoring
- `GET /api/v1/health` - System health check
- `GET /api/v1/health/detailed` - Detailed system metrics

#### Patient Management
- `POST /api/v1/patients` - Create patient
- `GET /api/v1/patients/{patient_id}` - Get patient details
- `GET /api/v1/patients` - List patients
- `POST /api/v1/patients/{patient_id}/vitals` - Add vital signs
- `POST /api/v1/patients/{patient_id}/labs` - Add lab results

#### Risk Predictions
- `POST /api/v1/predictions` - Generate risk predictions
- `GET /api/v1/predictions/{patient_id}` - Get patient predictions
- `GET /api/v1/predictions/high-risk` - List high-risk patients

#### Alerts
- `POST /api/v1/alerts` - Create alert
- `GET /api/v1/alerts` - List alerts (with filters)
- `PUT /api/v1/alerts/{alert_id}/acknowledge` - Acknowledge alert
- `PUT /api/v1/alerts/{alert_id}/resolve` - Resolve alert

#### NLP Processing
- `POST /api/v1/nlp/process` - Process medical text
- `POST /api/v1/nlp/extract-entities` - Extract entities
- `POST /api/v1/nlp/summarize` - Summarize text
- `POST /api/v1/nlp/search` - Semantic search

#### Authentication
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - User logout

## 🔒 Security & HIPAA Compliance

### Security Features
- JWT-based authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Rate limiting via nginx
- Security headers
- Audit logging for all actions

### HIPAA Compliance
- Encrypted data transmission (HTTPS)
- Access controls and user authentication
- Audit trails for all data access
- Secure session management
- Data minimization principles
- Regular security monitoring

### Environment Variables
```env
# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=duckdb:///data/healthcare.db

# ML/NLP Models
MODEL_PATH=./data/models/
HUGGINGFACE_CACHE_DIR=./data/models/huggingface/

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
ENABLE_AUDIT_LOGGING=true
```

## 📊 Monitoring & Logging

### Health Monitoring
The platform includes comprehensive health monitoring:
- System resource usage (CPU, memory, disk)
- Database connection status
- Patient statistics
- Active alert counts
- ML model status

### Logging
- Structured logging with Loguru
- HIPAA-compliant audit trails
- Configurable log levels
- File and console output
- Log rotation and retention

### Metrics Endpoints
- `/api/v1/health` - Basic health check
- `/api/v1/health/detailed` - Detailed system metrics

## 🧪 Testing

### Available Testing Options
```bash
# Note: Unit test framework not yet implemented
# The tests/ directory is currently empty
# Testing is currently done through functional demos and API testing
```

### API Testing
```bash
# Comprehensive API endpoint testing
python scripts/test_endpoints.py

# Realistic healthcare demo with AI processing
python scripts/realistic_demo.py

# Manual testing with curl
curl -X GET "http://localhost:8000/api/v1/health"

# Interactive API documentation
# Visit http://localhost:8000/docs for full API testing interface
```

### Load Testing
```bash
# Install locust for load testing
pip install locust

# Note: Load test files not yet implemented
# Create custom load test scripts as needed for your use case
```

## 🚢 Production Deployment

### Docker Production Setup
1. Update `docker-compose.yml` for production
2. Configure nginx with SSL certificates
3. Set up proper environment variables
4. Configure log aggregation
5. Set up monitoring and alerting

### Kubernetes Deployment
```yaml
# Example k8s deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healthcare-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: healthcare-api
  template:
    metadata:
      labels:
        app: healthcare-api
    spec:
      containers:
      - name: healthcare-api
        image: healthcare-platform:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### Performance Optimization
- Use Redis for caching
- Implement connection pooling
- Configure async workers
- Set up CDN for static assets
- Optimize ML model loading

## 🔧 Configuration

### ML Model Configuration
```python
# config/ml_config.py
ML_MODELS = {
    "readmission": {
        "model_type": "pytorch",
        "model_path": "./data/models/readmission_model.pth",
        "threshold": 0.7
    },
    "medication_adherence": {
        "model_type": "sklearn",
        "model_path": "./data/models/medication_model.pkl",
        "threshold": 0.6
    }
}
```

### Alert Configuration
```python
# Alert thresholds
ALERT_RULES = {
    "high_risk_prediction": {"threshold": 0.8, "severity": "high"},
    "critical_vitals": {"threshold": 0.9, "severity": "critical"},
    "abnormal_labs": {"threshold": 0.7, "severity": "medium"}
}
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Load balancer configuration
- Database clustering
- Microservices architecture
- Container orchestration

### Vertical Scaling
- Memory optimization for ML models
- CPU allocation for NLP processing
- Storage optimization for patient data

## 🆘 Troubleshooting

### Common Issues

1. **ML Models Not Loading**
   - Check model file paths
   - Verify memory availability
   - Check Python dependencies

2. **Database Connection Issues**
   - Verify DuckDB file permissions
   - Check disk space
   - Review connection settings

3. **Authentication Problems**
   - Verify JWT secret keys
   - Check token expiration
   - Review user permissions

4. **Performance Issues**
   - Monitor system resources
   - Check database query performance
   - Review ML model inference times

### Debug Mode
```bash
# Debug mode is enabled by default in development
# This provides access to:
# - Interactive API documentation at /docs
# - Detailed error messages
# - Enhanced logging

# Start with debug (default)
python main.py

# Access interactive API docs
# http://localhost:8000/docs
```

## 📞 Support

For technical support and questions:
- Check the API documentation at `/docs`
- Review logs in `./logs/`
- Monitor health endpoint `/api/v1/health`
- Check system resources and dependencies

## 🔄 Updates and Maintenance

### Regular Maintenance
- Update ML models with new data
- Review and update alert thresholds
- Monitor system performance
- Update security patches
- Backup patient data regularly

### Version Updates
- Follow semantic versioning
- Test in staging environment
- Plan database migrations
- Update documentation
- Notify users of changes
