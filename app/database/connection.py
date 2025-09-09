import duckdb
from pathlib import Path
from loguru import logger


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.db_path = Path("./data/healthcare.db")

    async def connect(self):
        """Initialize DuckDB connection"""
        try:
            # Ensure data directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            self.connection = duckdb.connect(str(self.db_path))
            logger.info(f"Connected to DuckDB at {self.db_path}")

            # Create tables
            await self.create_tables()

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def create_tables(self):
        """Create necessary tables for the healthcare platform"""
        try:
            # Patients table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY,
                    patient_id VARCHAR UNIQUE NOT NULL,
                    age INTEGER NOT NULL,
                    gender VARCHAR NOT NULL,
                    medical_record_number VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """
            )

            # Risk predictions table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_predictions (
                    id INTEGER PRIMARY KEY,
                    prediction_id VARCHAR UNIQUE NOT NULL,
                    patient_id VARCHAR NOT NULL,
                    risk_type VARCHAR NOT NULL,
                    risk_score FLOAT NOT NULL,
                    risk_level VARCHAR NOT NULL,
                    confidence FLOAT NOT NULL,
                    contributing_factors JSON,
                    recommendations JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    next_review_date TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
                )
            """
            )

            # Alerts table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY,
                    patient_id VARCHAR NOT NULL,
                    alert_type VARCHAR NOT NULL,
                    severity VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    triggered_by VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'active',
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by VARCHAR,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
                )
            """
            )

            # Medical records table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS medical_records (
                    id INTEGER PRIMARY KEY,
                    patient_id VARCHAR NOT NULL,
                    record_type VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    processed_content JSON,
                    embeddings FLOAT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
                )
            """
            )

            # Lab results table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_results (
                    id INTEGER PRIMARY KEY,
                    patient_id VARCHAR NOT NULL,
                    test_name VARCHAR NOT NULL,
                    value FLOAT NOT NULL,
                    unit VARCHAR NOT NULL,
                    reference_range VARCHAR,
                    is_abnormal BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
                )
            """
            )

            # Vital signs table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vital_signs (
                    id INTEGER PRIMARY KEY,
                    patient_id VARCHAR NOT NULL,
                    systolic_bp FLOAT,
                    diastolic_bp FLOAT,
                    heart_rate FLOAT,
                    temperature FLOAT,
                    respiratory_rate FLOAT,
                    oxygen_saturation FLOAT,
                    weight FLOAT,
                    height FLOAT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
                )
            """
            )

            # Care recommendations table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS care_recommendations (
                    id INTEGER PRIMARY KEY,
                    recommendation_id VARCHAR UNIQUE NOT NULL,
                    patient_id VARCHAR NOT NULL,
                    recommendation_type VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    description TEXT NOT NULL,
                    priority VARCHAR NOT NULL,
                    evidence_level VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    due_date TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
                )
            """
            )

            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def execute_query(self, query: str, params=None):
        """Execute a query with optional parameters"""
        try:
            if params:
                result = self.connection.execute(query, params).fetchall()
            else:
                result = self.connection.execute(query).fetchall()
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager()


async def init_database():
    """Initialize database connection"""
    await db_manager.connect()


async def get_database():
    """Dependency to get database connection"""
    return db_manager
