"""
Advanced Analytics & Business Intelligence Module
Real-time dashboards, reports, and predictive insights
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics
import sqlite3

logger = logging.getLogger(__name__)


class AdvancedAnalytics:
    """Advanced analytics engine for business intelligence"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        """Initialize analytics engine"""
        self.db_path = db_path
        logger.info("AdvancedAnalytics initialized")
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_engagement_insights(self, org_id: str, days: int = 7) -> Dict:
        """
        Get engagement insights and trends
        
        Args:
            org_id: Organization ID
            days: Number of days to analyze
            
        Returns:
            Engagement insights dictionary
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Get daily engagement trends
            cursor.execute('''
                SELECT
                    DATE(event_timestamp) as date,
                    AVG(CAST(JSON_EXTRACT(details, '$.engagement_level') AS REAL)) as avg_engagement,
                    COUNT(CASE WHEN event_type = 'sleeping' THEN 1 END) as sleep_events,
                    COUNT(CASE WHEN event_type = 'idle' THEN 1 END) as idle_events,
                    COUNT(CASE WHEN event_type = 'active' THEN 1 END) as active_events
                FROM behavior_events
                WHERE org_id = ? AND event_timestamp > ?
                GROUP BY DATE(event_timestamp)
                ORDER BY date DESC
            ''', (org_id, cutoff_date))
            
            daily_data = [dict(row) for row in cursor.fetchall()]
            
            # Get per-person engagement
            cursor.execute('''
                SELECT
                    name,
                    AVG(CAST(JSON_EXTRACT(details, '$.engagement_level') AS REAL)) as avg_engagement,
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN event_type = 'sleeping' THEN 1 END) as sleep_count,
                    COUNT(CASE WHEN event_type = 'idle' THEN 1 END) as idle_count
                FROM behavior_events
                WHERE org_id = ? AND event_timestamp > ?
                GROUP BY name
                ORDER BY avg_engagement DESC
            ''', (org_id, cutoff_date))
            
            person_data = [dict(row) for row in cursor.fetchall()]
            
            # Calculate metrics
            all_engagement_scores = [row['avg_engagement'] for row in daily_data if row['avg_engagement']]
            
            insights = {
                "period_days": days,
                "analysis_date": datetime.now().isoformat(),
                "overall_average_engagement": round(statistics.mean(all_engagement_scores), 2) if all_engagement_scores else 0,
                "engagement_trend": self._calculate_trend(all_engagement_scores),
                "peak_engagement_day": max(daily_data, key=lambda x: x['avg_engagement'] or 0)['date'] if daily_data else None,
                "low_engagement_day": min(daily_data, key=lambda x: x['avg_engagement'] or 100)['date'] if daily_data else None,
                "total_sleep_events": sum(row['sleep_events'] or 0 for row in daily_data),
                "total_idle_events": sum(row['idle_events'] or 0 for row in daily_data),
                "daily_breakdown": daily_data,
                "top_engaged_persons": person_data[:5],
                "lowest_engaged_persons": sorted(person_data, key=lambda x: x['avg_engagement'] or 100)[:5]
            }
            
            conn.close()
            
            return insights
        
        except Exception as e:
            logger.error(f"Error calculating engagement insights: {e}")
            return {}
    
    def get_attendance_insights(self, org_id: str, days: int = 30) -> Dict:
        """
        Get attendance analytics and patterns
        
        Args:
            org_id: Organization ID
            days: Number of days to analyze
            
        Returns:
            Attendance insights dictionary
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Daily attendance summary
            cursor.execute('''
                SELECT
                    DATE(check_in) as date,
                    COUNT(DISTINCT name) as unique_present,
                    COUNT(*) as total_checkins,
                    CAST(COUNT(DISTINCT name) AS FLOAT) / (
                        SELECT COUNT(DISTINCT name) FROM persons WHERE org_id = ?
                    ) * 100 as attendance_rate
                FROM attendance
                WHERE org_id = ? AND DATE(check_in) > ?
                GROUP BY DATE(check_in)
                ORDER BY date DESC
            ''', (org_id, org_id, cutoff_date))
            
            daily_attendance = [dict(row) for row in cursor.fetchall()]
            
            # Person attendance frequency
            cursor.execute('''
                SELECT
                    name,
                    COUNT(*) as total_days_present,
                    MIN(check_in) as first_appearance,
                    MAX(check_in) as last_appearance,
                    AVG(CAST(duration_seconds AS FLOAT)) / 3600 as avg_session_hours
                FROM attendance
                WHERE org_id = ? AND DATE(check_in) > ?
                GROUP BY name
                ORDER BY total_days_present DESC
            ''', (org_id, cutoff_date))
            
            person_attendance = [dict(row) for row in cursor.fetchall()]
            
            # Calculate statistics
            total_days = len(set(row['date'] for row in daily_attendance))
            avg_daily_attendance = statistics.mean([r['unique_present'] for r in daily_attendance]) if daily_attendance else 0
            
            insights = {
                "period_days": days,
                "analysis_date": datetime.now().isoformat(),
                "total_monitoring_days": total_days,
                "avg_daily_attendance": round(avg_daily_attendance, 1),
                "highest_attendance_day": max(daily_attendance, key=lambda x: x['unique_present'])['date'] if daily_attendance else None,
                "lowest_attendance_day": min(daily_attendance, key=lambda x: x['unique_present'])['date'] if daily_attendance else None,
                "attendance_consistency": self._calculate_consistency([r['attendance_rate'] for r in daily_attendance]),
                "daily_breakdown": daily_attendance,
                "most_frequent_attendees": person_attendance[:10],
                "irregular_attendees": sorted(person_attendance, key=lambda x: x['total_days_present'] or 0)[:5]
            }
            
            conn.close()
            
            return insights
        
        except Exception as e:
            logger.error(f"Error calculating attendance insights: {e}")
            return {}
    
    def get_alert_analytics(self, org_id: str, days: int = 30) -> Dict:
        """
        Get alert patterns and trends
        
        Args:
            org_id: Organization ID
            days: Number of days to analyze
            
        Returns:
            Alert analytics dictionary
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Alert summary by type
            cursor.execute('''
                SELECT
                    alert_type,
                    severity,
                    COUNT(*) as count,
                    COUNT(CASE WHEN acknowledged = 1 THEN 1 END) as acknowledged_count
                FROM alerts
                WHERE org_id = ? AND DATE(alert_timestamp) > ? AND alert_timestamp IS NOT NULL
                GROUP BY alert_type, severity
            ''', (org_id, cutoff_date))
            
            alert_summary = [dict(row) for row in cursor.fetchall()]
            
            # Daily alert trends
            cursor.execute('''
                SELECT
                    DATE(alert_timestamp) as date,
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN alert_type = 'sleep' THEN 1 END) as sleep_alerts,
                    COUNT(CASE WHEN alert_type = 'idle' THEN 1 END) as idle_alerts,
                    COUNT(CASE WHEN alert_type = 'unknown' THEN 1 END) as unknown_alerts
                FROM alerts
                WHERE org_id = ? AND DATE(alert_timestamp) > ?
                GROUP BY DATE(alert_timestamp)
                ORDER BY date DESC
            ''', (org_id, cutoff_date))
            
            daily_alerts = [dict(row) for row in cursor.fetchall()]
            
            # Person-specific alerts
            cursor.execute('''
                SELECT
                    name,
                    COUNT(*) as total_alerts,
                    COUNT(CASE WHEN alert_type = 'sleep' THEN 1 END) as sleep_alerts,
                    COUNT(CASE WHEN alert_type = 'idle' THEN 1 END) as idle_alerts,
                    COUNT(CASE WHEN acknowledged = 0 THEN 1 END) as unacknowledged
                FROM alerts
                WHERE org_id = ? AND DATE(alert_timestamp) > ?
                GROUP BY name
                ORDER BY total_alerts DESC
            ''', (org_id, cutoff_date))
            
            person_alerts = [dict(row) for row in cursor.fetchall()]
            
            total_alerts = sum(row['total_alerts'] for row in daily_alerts)
            total_acknowledged = sum(row['acknowledged_count'] or 0 for row in alert_summary)
            
            insights = {
                "period_days": days,
                "analysis_date": datetime.now().isoformat(),
                "total_alerts": total_alerts,
                "total_acknowledged": total_acknowledged,
                "acknowledgment_rate": round((total_acknowledged / total_alerts * 100), 1) if total_alerts > 0 else 0,
                "alert_summary": alert_summary,
                "daily_trends": daily_alerts,
                "high_alert_persons": person_alerts[:5],
                "alert_severity_distribution": self._get_severity_distribution(alert_summary)
            }
            
            conn.close()
            
            return insights
        
        except Exception as e:
            logger.error(f"Error calculating alert analytics: {e}")
            return {}
    
    def get_predictive_insights(self, org_id: str) -> Dict:
        """
        Get predictive insights based on patterns
        
        Args:
            org_id: Organization ID
            
        Returns:
            Predictive insights dictionary
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Identify high-risk persons for sleep/idle
            cursor.execute('''
                SELECT
                    name,
                    COUNT(CASE WHEN event_type = 'sleeping' THEN 1 END) as sleep_count,
                    COUNT(CASE WHEN event_type = 'idle' THEN 1 END) as idle_count,
                    (COUNT(CASE WHEN event_type = 'sleeping' THEN 1 END) + 
                     COUNT(CASE WHEN event_type = 'idle' THEN 1 END)) as risk_score
                FROM behavior_events
                WHERE org_id = ? AND event_timestamp > DATE('now', '-7 days')
                GROUP BY name
                HAVING risk_score > 0
                ORDER BY risk_score DESC
                LIMIT 10
            ''', (org_id,))
            
            high_risk_persons = [dict(row) for row in cursor.fetchall()]
            
            # Identify time periods with high alert rates
            cursor.execute('''
                SELECT
                    strftime('%H', alert_timestamp) as hour_of_day,
                    COUNT(*) as alert_count
                FROM alerts
                WHERE org_id = ? AND alert_timestamp > DATE('now', '-7 days')
                GROUP BY hour_of_day
                ORDER BY alert_count DESC
                LIMIT 3
            ''', (org_id,))
            
            peak_alert_hours = [dict(row) for row in cursor.fetchall()]
            
            # Forecast next week based on patterns
            cursor.execute('''
                SELECT
                    strftime('%w', alert_timestamp) as day_of_week,
                    COUNT(*) as alert_count
                FROM alerts
                WHERE org_id = ? AND alert_timestamp > DATE('now', '-28 days')
                GROUP BY day_of_week
            ''', (org_id,))
            
            day_patterns = [dict(row) for row in cursor.fetchall()]
            
            predictions = {
                "analysis_date": datetime.now().isoformat(),
                "high_risk_persons": high_risk_persons,
                "peak_alert_hours": peak_alert_hours,
                "recommended_actions": self._generate_recommendations(high_risk_persons, peak_alert_hours),
                "forecast": {
                    "expected_alerts_next_week": self._forecast_alerts(day_patterns),
                    "recommended_monitoring_times": peak_alert_hours
                }
            }
            
            conn.close()
            
            return predictions
        
        except Exception as e:
            logger.error(f"Error calculating predictive insights: {e}")
            return {}
    
    def _calculate_trend(self, values: List[float], window: int = 3) -> str:
        """Calculate trend direction"""
        if len(values) < window:
            return "insufficient_data"
        
        recent = statistics.mean(values[:window])
        older = statistics.mean(values[-window:])
        
        if recent > older + 5:
            return "improving"
        elif recent < older - 5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_consistency(self, values: List[float]) -> float:
        """Calculate consistency score (inverse of std dev)"""
        if not values:
            return 0
        
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        return max(0, 100 - std_dev)
    
    def _get_severity_distribution(self, alerts: List[Dict]) -> Dict:
        """Get distribution of alert severities"""
        distribution = defaultdict(int)
        for alert in alerts:
            distribution[alert['severity']] += alert['count']
        
        return dict(distribution)
    
    def _generate_recommendations(self, risk_persons: List[Dict], peak_hours: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if risk_persons and risk_persons[0]['risk_score'] > 10:
            recommendations.append(f"Increased monitoring recommended for {risk_persons[0]['name']} (Risk Score: {risk_persons[0]['risk_score']})")
        
        if peak_hours:
            hour = peak_hours[0]['hour_of_day']
            recommendations.append(f"Plan additional support during {hour}:00 hours (peak alert time)")
        
        if len(risk_persons) > 5:
            recommendations.append("Consider group intervention program for multiple low-engagement persons")
        
        return recommendations
    
    def _forecast_alerts(self, patterns: List[Dict]) -> int:
        """Forecast next week's alert count"""
        if not patterns:
            return 0
        
        avg_alerts = statistics.mean([p['alert_count'] for p in patterns])
        return round(avg_alerts * 7)


class ReportGenerator:
    """Generates comprehensive reports"""
    
    @staticmethod
    def generate_daily_report(org_id: str, date: str, analytics: AdvancedAnalytics) -> Dict:
        """Generate daily summary report"""
        return {
            "report_type": "daily_summary",
            "organization_id": org_id,
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "engagement_summary": analytics.get_engagement_insights(org_id, days=1),
            "attendance_summary": analytics.get_attendance_insights(org_id, days=1),
            "alert_summary": analytics.get_alert_analytics(org_id, days=1)
        }
    
    @staticmethod
    def generate_weekly_report(org_id: str, analytics: AdvancedAnalytics) -> Dict:
        """Generate weekly comprehensive report"""
        return {
            "report_type": "weekly_summary",
            "organization_id": org_id,
            "week_of": datetime.now().isoformat(),
            "generated_at": datetime.now().isoformat(),
            "engagement_insights": analytics.get_engagement_insights(org_id, days=7),
            "attendance_insights": analytics.get_attendance_insights(org_id, days=7),
            "alert_analytics": analytics.get_alert_analytics(org_id, days=7),
            "predictive_insights": analytics.get_predictive_insights(org_id)
        }
    
    @staticmethod
    def generate_monthly_report(org_id: str, analytics: AdvancedAnalytics) -> Dict:
        """Generate monthly executive report"""
        return {
            "report_type": "monthly_executive_summary",
            "organization_id": org_id,
            "month": datetime.now().strftime("%B %Y"),
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {
                "engagement": analytics.get_engagement_insights(org_id, days=30),
                "attendance": analytics.get_attendance_insights(org_id, days=30),
                "alerts": analytics.get_alert_analytics(org_id, days=30),
                "predictions": analytics.get_predictive_insights(org_id)
            }
        }
