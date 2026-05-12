"""
Advanced Integrations Module
Third-party service integrations: Slack, Microsoft Teams, Google Calendar, Analytics
"""

import logging
import requests
import json
from typing import Dict, Optional, List
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class IntegrationProvider(Enum):
    """Supported integration providers"""
    SLACK = "slack"
    TEAMS = "teams"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_SHEETS = "google_sheets"
    ZENDESK = "zendesk"
    JIRA = "jira"
    SALESFORCE = "salesforce"
    WEBHOOKS = "webhooks"


class BaseIntegration(ABC):
    """Base class for all integrations"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize integration
        
        Args:
            credentials: Authentication credentials
        """
        self.credentials = credentials
        self.provider = None
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test integration connection"""
        pass
    
    @abstractmethod
    def send_message(self, message: Dict) -> bool:
        """Send message through integration"""
        pass


class SlackIntegration(BaseIntegration):
    """Slack workspace integration"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize Slack integration
        
        Args:
            credentials: {"webhook_url": "...", "bot_token": "..."}
        """
        super().__init__(credentials)
        self.provider = IntegrationProvider.SLACK
        self.webhook_url = credentials.get("webhook_url")
        self.bot_token = credentials.get("bot_token")
    
    def test_connection(self) -> bool:
        """Test Slack connection"""
        try:
            response = requests.post(
                self.webhook_url,
                json={"text": "🧪 Test message from Smart Monitoring System"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False
    
    def send_message(self, message: Dict) -> bool:
        """
        Send message to Slack
        
        Args:
            message: {
                "text": "message text",
                "severity": "info/warning/critical",
                "metadata": {...}
            }
            
        Returns:
            True if successful
        """
        try:
            # Determine color based on severity
            color_map = {
                "info": "#36a64f",
                "warning": "#ff9900",
                "critical": "#ff0000"
            }
            
            color = color_map.get(message.get("severity", "info"), "#36a64f")
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": message.get("title", "Alert"),
                        "text": message.get("text", ""),
                        "fields": [
                            {
                                "title": k,
                                "value": str(v),
                                "short": True
                            }
                            for k, v in message.get("metadata", {}).items()
                        ],
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Message sent to Slack: {message.get('title')}")
                return True
            else:
                logger.error(f"Slack API error: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    def send_alert(self, alert_data: Dict, channel: str = None) -> bool:
        """Send alert to Slack channel"""
        try:
            message = {
                "channel": channel,
                "attachments": [{
                    "color": "danger",
                    "title": f"🚨 Alert: {alert_data.get('alert_type')}",
                    "text": alert_data.get("description", ""),
                    "fields": [
                        {"title": "Person", "value": alert_data.get("person_name", "Unknown"), "short": True},
                        {"title": "Time", "value": datetime.now().isoformat(), "short": True},
                        {"title": "Severity", "value": alert_data.get("severity", "high"), "short": True},
                    ]
                }]
            }
            
            response = requests.post(self.webhook_url, json=message)
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            return False


class TeamsIntegration(BaseIntegration):
    """Microsoft Teams integration"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize Teams integration
        
        Args:
            credentials: {"webhook_url": "..."}
        """
        super().__init__(credentials)
        self.provider = IntegrationProvider.TEAMS
        self.webhook_url = credentials.get("webhook_url")
    
    def test_connection(self) -> bool:
        """Test Teams connection"""
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": "Test Message",
                "themeColor": "0078D4",
                "sections": [{
                    "activityTitle": "🧪 Connection Test",
                    "text": "Smart Monitoring System test message"
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Teams connection test failed: {e}")
            return False
    
    def send_message(self, message: Dict) -> bool:
        """
        Send message to Teams
        
        Args:
            message: Message dictionary
            
        Returns:
            True if successful
        """
        try:
            color_map = {
                "info": "0078D4",
                "warning": "FFB900",
                "critical": "D84315"
            }
            
            severity = message.get("severity", "info")
            color = color_map.get(severity, "0078D4")
            
            payload = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": message.get("title", "Alert"),
                "themeColor": color,
                "sections": [{
                    "activityTitle": message.get("title", "Alert"),
                    "activitySubtitle": message.get("text", ""),
                    "facts": [
                        {"name": k, "value": str(v)}
                        for k, v in message.get("metadata", {}).items()
                    ]
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message sent to Teams: {message.get('title')}")
                return True
            else:
                logger.error(f"Teams API error: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending Teams message: {e}")
            return False


class GoogleSheetsIntegration(BaseIntegration):
    """Google Sheets integration for attendance and reporting"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize Google Sheets integration
        
        Args:
            credentials: {"spreadsheet_id": "...", "sheet_name": "...", "api_key": "..."}
        """
        super().__init__(credentials)
        self.provider = IntegrationProvider.GOOGLE_SHEETS
        self.spreadsheet_id = credentials.get("spreadsheet_id")
        self.sheet_name = credentials.get("sheet_name", "Sheet1")
        self.api_key = credentials.get("api_key")
    
    def test_connection(self) -> bool:
        """Test Google Sheets connection"""
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}"
            params = {"key": self.api_key}
            
            response = requests.get(url, params=params, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Google Sheets connection test failed: {e}")
            return False
    
    def send_message(self, message: Dict) -> bool:
        """
        This method not used for Sheets, use append_data instead
        """
        return False
    
    def append_attendance(self, attendance_data: List[Dict]) -> bool:
        """
        Append attendance records to Google Sheet
        
        Args:
            attendance_data: List of attendance records
            
        Returns:
            True if successful
        """
        try:
            # Format data for Sheets
            values = []
            for record in attendance_data:
                values.append([
                    record.get("date"),
                    record.get("person_name"),
                    record.get("entry_time"),
                    record.get("duration"),
                    record.get("status")
                ])
            
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{self.sheet_name}!A1:append"
            
            payload = {
                "values": values
            }
            
            params = {"key": self.api_key, "insertDataOption": "INSERT_ROWS"}
            
            response = requests.post(url, json=payload, params=params, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"Appended {len(values)} records to Google Sheets")
                return True
            else:
                logger.error(f"Google Sheets API error: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error appending to Google Sheets: {e}")
            return False


class ZendeskIntegration(BaseIntegration):
    """Zendesk support ticket integration"""
    
    def __init__(self, credentials: Dict):
        """
        Initialize Zendesk integration
        
        Args:
            credentials: {"subdomain": "...", "email": "...", "api_token": "..."}
        """
        super().__init__(credentials)
        self.provider = IntegrationProvider.ZENDESK
        self.subdomain = credentials.get("subdomain")
        self.email = credentials.get("email")
        self.api_token = credentials.get("api_token")
        self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"
    
    def test_connection(self) -> bool:
        """Test Zendesk connection"""
        try:
            from requests.auth import HTTPBasicAuth
            
            url = f"{self.base_url}/users/me"
            auth = HTTPBasicAuth(f"{self.email}/token", self.api_token)
            
            response = requests.get(url, auth=auth, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Zendesk connection test failed: {e}")
            return False
    
    def send_message(self, message: Dict) -> bool:
        """Not used for Zendesk"""
        return False
    
    def create_ticket(self, ticket_data: Dict) -> Optional[str]:
        """
        Create support ticket in Zendesk
        
        Args:
            ticket_data: {
                "subject": "...",
                "description": "...",
                "priority": "urgent/high/normal/low",
                "tags": [...]
            }
            
        Returns:
            Ticket ID or None
        """
        try:
            from requests.auth import HTTPBasicAuth
            
            url = f"{self.base_url}/tickets"
            
            priority_map = {
                "critical": "urgent",
                "high": "high",
                "medium": "normal",
                "low": "low"
            }
            
            payload = {
                "ticket": {
                    "subject": ticket_data.get("subject"),
                    "description": ticket_data.get("description"),
                    "priority": priority_map.get(ticket_data.get("priority"), "normal"),
                    "tags": ticket_data.get("tags", [])
                }
            }
            
            auth = HTTPBasicAuth(f"{self.email}/token", self.api_token)
            
            response = requests.post(url, json=payload, auth=auth, timeout=10)
            
            if response.status_code == 201:
                ticket_id = response.json()["ticket"]["id"]
                logger.info(f"Created Zendesk ticket: {ticket_id}")
                return str(ticket_id)
            else:
                logger.error(f"Zendesk API error: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error creating Zendesk ticket: {e}")
            return None


class IntegrationManager:
    """Manage all integrations"""
    
    def __init__(self):
        """Initialize integration manager"""
        self.integrations: Dict[str, BaseIntegration] = {}
    
    def register_integration(self, name: str, credentials: Dict, provider: IntegrationProvider) -> bool:
        """
        Register integration
        
        Args:
            name: Integration name/identifier
            credentials: Authentication credentials
            provider: Integration provider type
            
        Returns:
            True if successful
        """
        try:
            if provider == IntegrationProvider.SLACK:
                integration = SlackIntegration(credentials)
            elif provider == IntegrationProvider.TEAMS:
                integration = TeamsIntegration(credentials)
            elif provider == IntegrationProvider.GOOGLE_SHEETS:
                integration = GoogleSheetsIntegration(credentials)
            elif provider == IntegrationProvider.ZENDESK:
                integration = ZendeskIntegration(credentials)
            else:
                logger.error(f"Unknown provider: {provider}")
                return False
            
            # Test connection
            if not integration.test_connection():
                logger.error(f"Integration test failed: {name}")
                return False
            
            self.integrations[name] = integration
            logger.info(f"Registered integration: {name} ({provider.value})")
            return True
        
        except Exception as e:
            logger.error(f"Error registering integration {name}: {e}")
            return False
    
    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """Get integration by name"""
        return self.integrations.get(name)
    
    def send_alert_to_all(self, alert_data: Dict) -> Dict[str, bool]:
        """
        Send alert to all registered integrations
        
        Args:
            alert_data: Alert information
            
        Returns:
            Dictionary of integration result (name -> success)
        """
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                if integration.provider == IntegrationProvider.SLACK:
                    success = integration.send_alert(alert_data)
                else:
                    success = integration.send_message({
                        "title": f"Alert: {alert_data.get('alert_type')}",
                        "text": alert_data.get("description", ""),
                        "severity": alert_data.get("severity", "high"),
                        "metadata": alert_data
                    })
                
                results[name] = success
            
            except Exception as e:
                logger.error(f"Error sending to {name}: {e}")
                results[name] = False
        
        return results
    
    def get_integration_status(self) -> Dict:
        """Get status of all integrations"""
        status = {}
        
        for name, integration in self.integrations.items():
            status[name] = {
                "provider": integration.provider.value if integration.provider else "unknown",
                "connected": integration.test_connection()
            }
        
        return status
