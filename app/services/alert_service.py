import asyncio
from typing import List, Dict, Any, Callable
from datetime import datetime, timedelta
import json
from loguru import logger
from dataclasses import dataclass
from enum import Enum

from app.models.schemas import AlertCreate, RiskLevel
from app.database.connection import DatabaseManager
from config.settings import settings


class AlertType(str, Enum):
    RISK_THRESHOLD = "risk_threshold"
    LAB_ABNORMAL = "lab_abnormal"
    VITAL_CRITICAL = "vital_critical"
    MEDICATION_DUE = "medication_due"
    APPOINTMENT_REMINDER = "appointment_reminder"


@dataclass
class AlertRule:
    """Alert rule configuration"""

    rule_id: str
    alert_type: AlertType
    condition: Callable
    severity: RiskLevel
    message_template: str
    cooldown_minutes: int = 60  # Prevent spam


class AlertService:
    """Real-time alerting service using asyncio"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, datetime] = {}  # Track cooldowns
        self.alert_subscribers: List[Callable] = []
        self.running = False

        # Initialize alert rules
        self._initialize_alert_rules()

    def _initialize_alert_rules(self):
        """Initialize predefined alert rules"""

        # High risk score alert
        self.alert_rules.append(
            AlertRule(
                rule_id="high_risk_readmission",
                alert_type=AlertType.RISK_THRESHOLD,
                condition=lambda data: (
                    data.get("risk_type") == "readmission"
                    and data.get("risk_score", 0) >= settings.risk_threshold_high
                ),
                severity=RiskLevel.HIGH,
                message_template="High readmission risk detected for patient {patient_id} (score: {risk_score:.2f})",
                cooldown_minutes=120,
            )
        )

        # Critical vital signs alert
        self.alert_rules.append(
            AlertRule(
                rule_id="critical_vitals",
                alert_type=AlertType.VITAL_CRITICAL,
                condition=lambda data: (
                    data.get("systolic_bp", 0) > 180
                    or data.get("systolic_bp", 0) < 90
                    or data.get("heart_rate", 0) > 120
                    or data.get("oxygen_saturation", 100) < 90
                ),
                severity=RiskLevel.CRITICAL,
                message_template="Critical vital signs detected for patient {patient_id}",
                cooldown_minutes=30,
            )
        )

        # Abnormal lab results alert
        self.alert_rules.append(
            AlertRule(
                rule_id="abnormal_labs",
                alert_type=AlertType.LAB_ABNORMAL,
                condition=lambda data: data.get("is_abnormal", False),
                severity=RiskLevel.MEDIUM,
                message_template="Abnormal lab result: {test_name} = {value} {unit} for patient {patient_id}",
                cooldown_minutes=60,
            )
        )

        logger.info(f"Initialized {len(self.alert_rules)} alert rules")

    async def start_monitoring(self):
        """Start the alert monitoring service"""
        if self.running:
            logger.warning("Alert service is already running")
            return

        self.running = True
        logger.info("Starting alert monitoring service")

        # Start background tasks
        tasks = [
            asyncio.create_task(self._monitor_risk_predictions()),
            asyncio.create_task(self._monitor_vital_signs()),
            asyncio.create_task(self._monitor_lab_results()),
            asyncio.create_task(self._cleanup_old_alerts()),
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Alert monitoring service error: {e}")
        finally:
            self.running = False

    async def stop_monitoring(self):
        """Stop the alert monitoring service"""
        self.running = False
        logger.info("Stopping alert monitoring service")

    async def _monitor_risk_predictions(self):
        """Monitor for new high-risk predictions"""
        while self.running:
            try:
                # Check for recent high-risk predictions
                recent_predictions = await self.db.execute_query(
                    """
                    SELECT patient_id, risk_type, risk_score, risk_level, created_at
                    FROM risk_predictions 
                    WHERE created_at >= ? AND risk_level IN ('high', 'critical')
                """,
                    [datetime.utcnow() - timedelta(minutes=5)],
                )

                for prediction in recent_predictions:
                    (
                        patient_id,
                        risk_type,
                        risk_score,
                        risk_level,
                        created_at,
                    ) = prediction

                    await self._evaluate_alert_rules(
                        {
                            "patient_id": patient_id,
                            "risk_type": risk_type,
                            "risk_score": risk_score,
                            "risk_level": risk_level,
                            "timestamp": created_at,
                        }
                    )

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error monitoring risk predictions: {e}")
                await asyncio.sleep(60)

    async def _monitor_vital_signs(self):
        """Monitor for critical vital signs"""
        while self.running:
            try:
                # Check for recent critical vitals
                recent_vitals = await self.db.execute_query(
                    """
                    SELECT patient_id, systolic_bp, diastolic_bp, heart_rate, 
                           oxygen_saturation, recorded_at
                    FROM vital_signs 
                    WHERE recorded_at >= ?
                """,
                    [datetime.utcnow() - timedelta(minutes=10)],
                )

                for vital in recent_vitals:
                    (
                        patient_id,
                        systolic_bp,
                        diastolic_bp,
                        heart_rate,
                        o2_sat,
                        recorded_at,
                    ) = vital

                    await self._evaluate_alert_rules(
                        {
                            "patient_id": patient_id,
                            "systolic_bp": systolic_bp or 0,
                            "diastolic_bp": diastolic_bp or 0,
                            "heart_rate": heart_rate or 0,
                            "oxygen_saturation": o2_sat or 100,
                            "timestamp": recorded_at,
                        }
                    )

                await asyncio.sleep(120)  # Check every 2 minutes

            except Exception as e:
                logger.error(f"Error monitoring vital signs: {e}")
                await asyncio.sleep(120)

    async def _monitor_lab_results(self):
        """Monitor for abnormal lab results"""
        while self.running:
            try:
                # Check for recent abnormal labs
                recent_labs = await self.db.execute_query(
                    """
                    SELECT patient_id, test_name, value, unit, is_abnormal, timestamp
                    FROM lab_results 
                    WHERE timestamp >= ? AND is_abnormal = true
                """,
                    [datetime.utcnow() - timedelta(minutes=30)],
                )

                for lab in recent_labs:
                    patient_id, test_name, value, unit, is_abnormal, timestamp = lab

                    await self._evaluate_alert_rules(
                        {
                            "patient_id": patient_id,
                            "test_name": test_name,
                            "value": value,
                            "unit": unit,
                            "is_abnormal": is_abnormal,
                            "timestamp": timestamp,
                        }
                    )

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Error monitoring lab results: {e}")
                await asyncio.sleep(300)

    async def _evaluate_alert_rules(self, data: Dict[str, Any]):
        """Evaluate data against alert rules"""
        patient_id = data.get("patient_id")
        if not patient_id:
            return

        for rule in self.alert_rules:
            try:
                # Check cooldown
                cooldown_key = f"{rule.rule_id}:{patient_id}"
                if cooldown_key in self.active_alerts:
                    last_alert = self.active_alerts[cooldown_key]
                    if datetime.utcnow() - last_alert < timedelta(
                        minutes=rule.cooldown_minutes
                    ):
                        continue

                # Evaluate condition
                if rule.condition(data):
                    await self._create_alert(rule, data)
                    self.active_alerts[cooldown_key] = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule.rule_id}: {e}")

    async def _create_alert(self, rule: AlertRule, data: Dict[str, Any]):
        """Create and store an alert"""
        try:
            patient_id = data["patient_id"]
            message = rule.message_template.format(**data)

            # Create alert in database
            await self.db.execute_query(
                """
                INSERT INTO alerts (
                    patient_id, alert_type, severity, message, 
                    triggered_by, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    patient_id,
                    rule.alert_type.value,
                    rule.severity.value,
                    message,
                    f"alert_service:{rule.rule_id}",
                    json.dumps(data),
                    datetime.utcnow(),
                ],
            )

            # Notify subscribers
            await self._notify_subscribers(
                {
                    "patient_id": patient_id,
                    "alert_type": rule.alert_type.value,
                    "severity": rule.severity.value,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": data,
                }
            )

            logger.info(f"Created alert for patient {patient_id}: {message}")

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")

    async def _cleanup_old_alerts(self):
        """Clean up old alert cooldowns"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                expired_keys = []

                for key, timestamp in self.active_alerts.items():
                    if current_time - timestamp > timedelta(hours=24):
                        expired_keys.append(key)

                for key in expired_keys:
                    del self.active_alerts[key]

                if expired_keys:
                    logger.debug(
                        f"Cleaned up {len(expired_keys)} expired alert cooldowns"
                    )

                await asyncio.sleep(3600)  # Clean up every hour

            except Exception as e:
                logger.error(f"Error during alert cleanup: {e}")
                await asyncio.sleep(3600)

    def subscribe_to_alerts(self, callback: Callable):
        """Subscribe to real-time alerts"""
        self.alert_subscribers.append(callback)
        logger.info("New alert subscriber registered")

    def unsubscribe_from_alerts(self, callback: Callable):
        """Unsubscribe from alerts"""
        if callback in self.alert_subscribers:
            self.alert_subscribers.remove(callback)
            logger.info("Alert subscriber removed")

    async def _notify_subscribers(self, alert_data: Dict[str, Any]):
        """Notify all subscribers of new alerts"""
        for callback in self.alert_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Error notifying alert subscriber: {e}")

    async def trigger_manual_alert(self, alert_create: AlertCreate) -> bool:
        """Manually trigger an alert"""
        try:
            await self.db.execute_query(
                """
                INSERT INTO alerts (
                    patient_id, alert_type, severity, message, 
                    triggered_by, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    alert_create.patient_id,
                    alert_create.alert_type,
                    alert_create.severity.value,
                    alert_create.message,
                    alert_create.triggered_by,
                    json.dumps(alert_create.metadata)
                    if alert_create.metadata
                    else None,
                    datetime.utcnow(),
                ],
            )

            # Notify subscribers
            await self._notify_subscribers(
                {
                    "patient_id": alert_create.patient_id,
                    "alert_type": alert_create.alert_type,
                    "severity": alert_create.severity.value,
                    "message": alert_create.message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": alert_create.metadata or {},
                }
            )

            logger.info(f"Manual alert triggered for patient {alert_create.patient_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to trigger manual alert: {e}")
            return False

    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            # Active alerts by severity
            active_by_severity = await self.db.execute_query(
                """
                SELECT severity, COUNT(*) as count
                FROM alerts 
                WHERE status = 'active'
                GROUP BY severity
            """
            )

            # Alerts in last 24 hours
            recent_alerts = await self.db.execute_query(
                """
                SELECT COUNT(*) FROM alerts 
                WHERE created_at >= ?
            """,
                [datetime.utcnow() - timedelta(hours=24)],
            )

            # Most common alert types
            common_types = await self.db.execute_query(
                """
                SELECT alert_type, COUNT(*) as count
                FROM alerts 
                WHERE created_at >= ?
                GROUP BY alert_type
                ORDER BY count DESC
                LIMIT 5
            """,
                [datetime.utcnow() - timedelta(days=7)],
            )

            return {
                "active_by_severity": dict(active_by_severity),
                "alerts_last_24h": recent_alerts[0][0] if recent_alerts else 0,
                "common_alert_types": dict(common_types),
                "total_rules": len(self.alert_rules),
                "active_cooldowns": len(self.active_alerts),
                "subscribers": len(self.alert_subscribers),
            }

        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {}
