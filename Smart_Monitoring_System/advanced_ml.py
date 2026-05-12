"""
Advanced Machine Learning & Anomaly Detection Module
Real-time predictions, anomaly detection, and intelligent insights
"""

import logging
import json
import sqlite3
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import pickle
import os

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalous behavior patterns using Isolation Forest"""
    
    def __init__(self, contamination: float = 0.1):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of anomalies (0-1)
        """
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = [
            'engagement_level', 'movement_speed', 'head_pose_variance',
            'eye_closure_duration', 'idle_time_percent', 'alert_frequency'
        ]
    
    def train(self, features: np.ndarray) -> bool:
        """
        Train anomaly detector on historical data
        
        Args:
            features: Array of shape (n_samples, n_features)
            
        Returns:
            True if training successful
        """
        try:
            # Normalize features
            features_scaled = self.scaler.fit_transform(features)
            
            # Train model
            self.model.fit(features_scaled)
            self.is_trained = True
            
            logger.info(f"Trained anomaly detector on {len(features)} samples")
            return True
        
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}")
            return False
    
    def detect(self, features: Dict) -> Tuple[bool, float]:
        """
        Detect if behavior is anomalous
        
        Args:
            features: Dictionary of behavior features
            
        Returns:
            Tuple of (is_anomaly, confidence)
        """
        try:
            if not self.is_trained:
                # Train on default model if not trained
                self.train(np.random.rand(100, len(self.feature_names)))
            
            # Convert to feature vector
            feature_vector = np.array([
                features.get(name, 0.5) for name in self.feature_names
            ]).reshape(1, -1)
            
            # Scale
            feature_scaled = self.scaler.transform(feature_vector)
            
            # Predict
            anomaly_score = self.model.score_samples(feature_scaled)[0]
            is_anomaly = self.model.predict(feature_scaled)[0] == -1
            
            # Confidence is based on how far from decision boundary
            confidence = abs(anomaly_score) / 10.0  # Normalize
            confidence = min(1.0, confidence)
            
            return is_anomaly, confidence
        
        except Exception as e:
            logger.error(f"Error detecting anomaly: {e}")
            return False, 0.0
    
    def save(self, path: str):
        """Save trained model"""
        try:
            with open(path, 'wb') as f:
                pickle.dump({'model': self.model, 'scaler': self.scaler}, f)
            logger.info(f"Saved anomaly detector to {path}")
        except Exception as e:
            logger.error(f"Error saving anomaly detector: {e}")
    
    def load(self, path: str) -> bool:
        """Load trained model"""
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.scaler = data['scaler']
                    self.is_trained = True
                logger.info(f"Loaded anomaly detector from {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading anomaly detector: {e}")
            return False


class PredictiveAnalytics:
    """Predict future behaviors and identify high-risk scenarios"""
    
    def __init__(self, db_path: str = "predictions.db"):
        """
        Initialize predictive analytics
        
        Args:
            db_path: Path to predictions database
        """
        self.db_path = db_path
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.init_database()
    
    def init_database(self):
        """Initialize predictions database"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Predictions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    prediction_type TEXT NOT NULL,
                    predicted_value REAL NOT NULL,
                    confidence REAL NOT NULL,
                    prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actual_outcome TEXT,
                    validated_at TIMESTAMP,
                    accuracy REAL
                )
            ''')
            
            # Behavioral patterns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS behavioral_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_observed TIMESTAMP,
                    risk_level TEXT DEFAULT 'low'
                )
            ''')
            
            # Risk scores
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    risk_factors TEXT NOT NULL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recommendation TEXT
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_person ON predictions(person_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_person ON behavioral_patterns(person_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_person ON risk_scores(person_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("Predictions database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing predictions database: {e}")
    
    def predict_next_behavior(self, org_id: str, person_id: str) -> Dict:
        """
        Predict next likely behavior for person
        
        Args:
            org_id: Organization ID
            person_id: Person ID
            
        Returns:
            Prediction dictionary
        """
        try:
            # Get recent behavior history
            conn = sqlite3.connect(f"attendance_{org_id}.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Query last 50 behavior events
            cursor.execute('''
                SELECT event_type, details, event_timestamp
                FROM behavior_events
                WHERE person_id = ?
                ORDER BY event_timestamp DESC
                LIMIT 50
            ''', (person_id,))
            
            events = cursor.fetchall()
            conn.close()
            
            if not events:
                return {"prediction": "unknown", "confidence": 0.0}
            
            # Analyze pattern
            event_types = [e['event_type'] for e in events]
            sleep_count = event_types.count('sleeping')
            idle_count = event_types.count('idle')
            active_count = event_types.count('active')
            
            # Predict based on frequency
            predictions = {
                'sleeping': sleep_count / len(events),
                'idle': idle_count / len(events),
                'active': active_count / len(events)
            }
            
            predicted_state = max(predictions, key=predictions.get)
            confidence = predictions[predicted_state]
            
            # Store prediction
            self.store_prediction(org_id, person_id, "next_behavior", predicted_state, confidence)
            
            return {
                "prediction": predicted_state,
                "confidence": confidence,
                "alternatives": sorted(
                    [(k, v) for k, v in predictions.items() if k != predicted_state],
                    key=lambda x: x[1],
                    reverse=True
                )
            }
        
        except Exception as e:
            logger.error(f"Error predicting behavior: {e}")
            return {"prediction": "unknown", "confidence": 0.0}
    
    def calculate_risk_score(self, org_id: str, person_id: str) -> Dict:
        """
        Calculate individual risk score (0-100)
        
        Args:
            org_id: Organization ID
            person_id: Person ID
            
        Returns:
            Risk assessment dictionary
        """
        try:
            conn = sqlite3.connect(f"attendance_{org_id}.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get statistics for person
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN event_type = 'sleeping' THEN 1 END) as sleep_count,
                    COUNT(CASE WHEN event_type = 'idle' THEN 1 END) as idle_count,
                    COUNT(*) as total_events
                FROM behavior_events
                WHERE person_id = ? AND event_timestamp > datetime('now', '-7 days')
            ''', (person_id,))
            
            stats = cursor.fetchone()
            
            # Get attendance
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT DATE(entry_time)) as days_present,
                    COUNT(DISTINCT DATE(entry_time)) as total_recorded_days
                FROM attendance
                WHERE person_id = ? AND entry_time > datetime('now', '-7 days')
            ''', (person_id,))
            
            attendance = cursor.fetchone()
            conn.close()
            
            # Calculate risk factors
            risk_score = 0.0
            risk_factors = []
            
            # Sleep factor (each sleep event = 10 points)
            if stats and stats['sleep_count'] > 0:
                sleep_risk = min(50, stats['sleep_count'] * 10)
                risk_score += sleep_risk
                risk_factors.append(f"Sleep events: {stats['sleep_count']}")
            
            # Idle factor (excessive idleness)
            if stats and stats['idle_count'] > 20:
                idle_risk = min(30, (stats['idle_count'] - 20) * 2)
                risk_score += idle_risk
                risk_factors.append(f"Idle events: {stats['idle_count']}")
            
            # Attendance factor
            if attendance and attendance['days_present'] < 3:
                attendance_risk = 20
                risk_score += attendance_risk
                risk_factors.append("Low attendance this week")
            
            # Normalize to 0-100
            risk_score = min(100, risk_score)
            
            # Determine risk level
            if risk_score >= 70:
                risk_level = "critical"
            elif risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 30:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Generate recommendation
            recommendation = self._generate_recommendation(risk_level, risk_factors)
            
            # Store risk score
            self.store_risk_score(org_id, person_id, risk_score, risk_factors, recommendation)
            
            return {
                "person_id": person_id,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "recommendation": recommendation
            }
        
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return {"risk_score": 0, "risk_level": "unknown"}
    
    def store_prediction(self, org_id: str, person_id: str, pred_type: str, predicted_value: str, confidence: float):
        """Store prediction in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO predictions (person_id, org_id, prediction_type, predicted_value, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (person_id, org_id, pred_type, predicted_value, confidence))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
    
    def store_risk_score(self, org_id: str, person_id: str, risk_score: float, risk_factors: List[str], recommendation: str):
        """Store risk score in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_scores (person_id, org_id, risk_score, risk_factors, recommendation)
                VALUES (?, ?, ?, ?, ?)
            ''', (person_id, org_id, risk_score, json.dumps(risk_factors), recommendation))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing risk score: {e}")
    
    @staticmethod
    def _generate_recommendation(risk_level: str, risk_factors: List[str]) -> str:
        """Generate recommendation based on risk level"""
        recommendations = {
            "critical": "Immediate intervention required. Contact student and parents immediately.",
            "high": "Close monitoring recommended. Schedule meeting with student.",
            "medium": "Regular check-ins recommended. Monitor for patterns.",
            "low": "Continue normal monitoring. No intervention needed."
        }
        return recommendations.get(risk_level, "Unable to determine")


class BehaviorClustering:
    """Group students into behavioral clusters for targeted interventions"""
    
    def __init__(self, n_clusters: int = 4):
        """
        Initialize behavior clustering
        
        Args:
            n_clusters: Number of clusters to create
        """
        self.n_clusters = n_clusters
        self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train_clusters(self, org_id: str, db_path: str) -> Dict:
        """
        Train clustering model on organization data
        
        Args:
            org_id: Organization ID
            db_path: Path to database
            
        Returns:
            Cluster assignments and centroids
        """
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all persons and their statistics
            cursor.execute('''
                SELECT p.id,
                       COUNT(CASE WHEN be.event_type = 'sleeping' THEN 1 END) as sleep_events,
                       COUNT(CASE WHEN be.event_type = 'idle' THEN 1 END) as idle_events,
                       COUNT(CASE WHEN be.event_type = 'active' THEN 1 END) as active_events,
                       AVG(CAST(JSON_EXTRACT(be.details, '$.engagement_level') AS REAL)) as avg_engagement,
                       COUNT(DISTINCT DATE(a.entry_time)) as days_present
                FROM persons p
                LEFT JOIN behavior_events be ON p.id = be.person_id
                LEFT JOIN attendance a ON p.id = a.person_id
                WHERE be.event_timestamp > datetime('now', '-30 days')
                GROUP BY p.id
            ''')
            
            persons = cursor.fetchall()
            conn.close()
            
            if len(persons) < self.n_clusters:
                logger.warning(f"Not enough persons ({len(persons)}) for {self.n_clusters} clusters")
                return {}
            
            # Create feature matrix
            features = np.array([
                [
                    p['sleep_events'] or 0,
                    p['idle_events'] or 0,
                    p['active_events'] or 0,
                    p['avg_engagement'] or 0.5,
                    p['days_present'] or 0
                ]
                for p in persons
            ])
            
            # Normalize and train
            features_scaled = self.scaler.fit_transform(features)
            self.model.fit(features_scaled)
            self.is_trained = True
            
            # Get cluster assignments
            clusters = self.model.labels_
            
            result = {}
            for person, cluster_id in zip(persons, clusters):
                result[person['id']] = {
                    "cluster": int(cluster_id),
                    "cluster_name": self._get_cluster_name(cluster_id),
                    "statistics": {
                        "sleep_events": person['sleep_events'] or 0,
                        "idle_events": person['idle_events'] or 0,
                        "engagement": person['avg_engagement'] or 0.5,
                        "days_present": person['days_present'] or 0
                    }
                }
            
            logger.info(f"Clustered {len(persons)} persons into {self.n_clusters} clusters")
            return result
        
        except Exception as e:
            logger.error(f"Error training clusters: {e}")
            return {}
    
    @staticmethod
    def _get_cluster_name(cluster_id: int) -> str:
        """Get human-readable cluster name"""
        names = {
            0: "High Engagement",
            1: "Moderate Engagement",
            2: "Low Engagement",
            3: "At Risk"
        }
        return names.get(cluster_id, f"Cluster {cluster_id}")


class TimeSeriesForecast:
    """Forecast attendance and engagement trends"""
    
    @staticmethod
    def forecast_attendance(org_id: str, person_id: str, days_ahead: int = 7) -> List[Dict]:
        """
        Forecast attendance for next N days
        
        Args:
            org_id: Organization ID
            person_id: Person ID
            days_ahead: Number of days to forecast
            
        Returns:
            List of daily forecasts
        """
        try:
            conn = sqlite3.connect(f"attendance_{org_id}.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get last 30 days of attendance
            cursor.execute('''
                SELECT DATE(entry_time) as date, COUNT(*) as attended
                FROM attendance
                WHERE person_id = ? AND entry_time > datetime('now', '-30 days')
                GROUP BY DATE(entry_time)
                ORDER BY date
            ''', (person_id,))
            
            history = cursor.fetchall()
            conn.close()
            
            if not history:
                return []
            
            # Calculate attendance rate
            attendance_rate = len(history) / 30
            
            # Generate forecast
            forecast = []
            for i in range(days_ahead):
                forecast_date = datetime.now() + timedelta(days=i+1)
                
                # Simple forecast: based on historical rate
                predicted_attendance = attendance_rate > 0.8  # High probability if rate > 80%
                confidence = min(attendance_rate, 0.95)
                
                forecast.append({
                    "date": forecast_date.date().isoformat(),
                    "predicted_attendance": predicted_attendance,
                    "confidence": confidence,
                    "historical_rate": attendance_rate
                })
            
            return forecast
        
        except Exception as e:
            logger.error(f"Error forecasting: {e}")
            return []


class ModelEvaluation:
    """Evaluate and validate ML model performance"""
    
    @staticmethod
    def calculate_model_accuracy(db_path: str) -> Dict:
        """
        Calculate actual vs predicted accuracy
        
        Args:
            db_path: Path to predictions database
            
        Returns:
            Accuracy metrics
        """
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get predictions with actual outcomes
            cursor.execute('''
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN validated_at IS NOT NULL THEN 1 END) as validated,
                       AVG(CASE WHEN actual_outcome = predicted_value THEN 1 ELSE 0 END) as accuracy
                FROM predictions
                WHERE validated_at IS NOT NULL AND prediction_type = 'next_behavior'
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                "total_predictions": result['total'] or 0,
                "validated_predictions": result['validated'] or 0,
                "accuracy": (result['accuracy'] or 0) * 100
            }
        
        except Exception as e:
            logger.error(f"Error calculating accuracy: {e}")
            return {}
