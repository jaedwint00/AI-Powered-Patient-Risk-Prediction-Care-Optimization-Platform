# Quick Start Guide

This guide provides the essential steps to run and stop the AI-Powered Patient Risk Prediction & Care Optimization Platform.

## Prerequisites

- Python 3.11+
- Git (for cloning the repository)

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AI-Powered-Patient-Risk-Prediction-Care-Optimization-Platform
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Setup (Optional)
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings (optional for demo)
# nano .env
```

## Running the Application

### Start the Platform
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXX] using WatchFiles
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Access the Platform
- **Main Application**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## Testing the Platform

### Run API Endpoint Tests
```bash
python scripts/test_endpoints.py
```

### Run Realistic Demo
```bash
PYTHONPATH=$(pwd) python scripts/realistic_demo.py
```

## Stopping the Application

### Method 1: Keyboard Interrupt
Press `Ctrl+C` in the terminal where the server is running.

### Method 2: Kill Process by Port
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Method 3: Kill by Process Name
```bash
# Kill all uvicorn processes
pkill -f uvicorn
```

### Method 4: Kill Specific Python Process
```bash
# Find the process
ps aux | grep "python.*uvicorn"

# Kill by PID (replace XXXX with actual PID)
kill -9 XXXX
```

## Verification Commands

### Check if Server is Running
```bash
# Check port 8000
netstat -an | grep :8000

# Check process
ps aux | grep uvicorn
```

### Test Database Connection
```bash
python -c "from app.database.connection import DatabaseManager; db = DatabaseManager(); print('✅ Database: OK')"
```

### Test ML Services
```bash
python -c "from app.services.ml_service import MLService; ml = MLService(); print('✅ ML Service: OK')"
```

### Test NLP Services
```bash
python -c "from app.services.nlp_service import NLPService; nlp = NLPService(); print('✅ NLP Service: OK')"
```

## Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
lsof -ti:8000 | xargs kill -9
```

**Missing Dependencies:**
```bash
pip install -r requirements.txt
```

**Module Import Errors:**
```bash
# Set Python path for scripts
export PYTHONPATH=$(pwd)
```

**Permission Errors:**
```bash
# Check file permissions
ls -la data/
chmod 755 data/
```

## Quick Commands Summary

| Action | Command |
|--------|---------|
| **Start Server** | `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload` |
| **Stop Server** | `Ctrl+C` or `lsof -ti:8000 \| xargs kill -9` |
| **Test APIs** | `python scripts/test_endpoints.py` |
| **Run Demo** | `PYTHONPATH=$(pwd) python scripts/realistic_demo.py` |
| **Check Status** | `netstat -an \| grep :8000` |
| **View Docs** | Open http://localhost:8000/docs |

## Development Mode

For development with auto-reload:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## Production Mode

For production deployment:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

**Need Help?** Check the main [README.md](README.md) for detailed documentation or [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for advanced deployment options.
