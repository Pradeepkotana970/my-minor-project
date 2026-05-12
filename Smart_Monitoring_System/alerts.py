"""
Advanced Alert System Module
Handles sound alerts, voice notifications, SMS, and email notifications
"""

import logging
import threading
import os
import json
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import queue

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages all types of alerts with rate limiting and deduplication"""
    
    # Alert types
    ALERT_SLEEP = "sleep"
    ALERT_IDLE = "idle"
    ALERT_UNKNOWN = "unknown"
    ALERT_SUSPICIOUS = "suspicious"
    
    def __init__(
        self,
        alert_cooldown_seconds: int = 5,
        enable_sound: bool = True,
        enable_voice: bool = False,
        enable_sms: bool = False,
        enable_email: bool = False
    ):
        """
        Initialize alert manager
        
        Args:
            alert_cooldown_seconds: Minimum seconds between alerts for same person/type
            enable_sound: Enable sound alerts
            enable_voice: Enable voice alerts
            enable_sms: Enable SMS alerts
            enable_email: Enable email alerts
        """
        self.alert_cooldown = alert_cooldown_seconds
        self.last_alert_times = defaultdict(lambda: defaultdict(lambda: 0))  # {person: {type: time}}
        
        # Alert enablement
        self.enable_sound = enable_sound
        self.enable_voice = enable_voice
        self.enable_sms = enable_sms
        self.enable_email = enable_email
        
        # Alert queue for async processing
        self.alert_queue = queue.Queue()
        self.alert_thread = None
        self.alert_thread_running = False
        
        # Sound alert file
        self.sound_file = "alert.wav"
        
        # Alert callbacks
        self.sound_callback = None
        self.voice_callback = None
        self.sms_callback = None
        self.email_callback = None
        
        # Start alert processing thread
        self._start_alert_thread()
        
        logger.info(f"AlertManager initialized (sound: {enable_sound}, voice: {enable_voice}, sms: {enable_sms}, email: {enable_email})")
    
    def _start_alert_thread(self):
        """Start background alert processing thread"""
        self.alert_thread_running = True
        self.alert_thread = threading.Thread(target=self._process_alert_queue, daemon=True)
        self.alert_thread.start()
        logger.info("Alert processing thread started")
    
    def _process_alert_queue(self):
        """Process alerts from queue in background"""
        while self.alert_thread_running:
            try:
                alert = self.alert_queue.get(timeout=1)
                self._execute_alert(alert)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing alert: {e}")
    
    def can_send_alert(self, person_name: str, alert_type: str) -> bool:
        """
        Check if alert should be sent (cooldown check)
        
        Args:
            person_name: Person's name
            alert_type: Alert type
            
        Returns:
            True if alert should be sent
        """
        last_time = self.last_alert_times[person_name][alert_type]
        current_time = datetime.now().timestamp()
        
        if current_time - last_time >= self.alert_cooldown:
            self.last_alert_times[person_name][alert_type] = current_time
            return True
        
        return False
    
    def trigger_alert(
        self,
        person_name: str,
        alert_type: str,
        track_id: int = None,
        behavior_data: Dict = None,
        frame: Optional[object] = None
    ) -> bool:
        """
        Trigger alert for a person
        Uses cooldown to prevent spam
        
        Args:
            person_name: Person's name
            alert_type: Type of alert
            track_id: Track ID for person
            behavior_data: Additional behavior data
            frame: Frame (for image saving)
            
        Returns:
            True if alert was triggered
        """
        if not self.can_send_alert(person_name, alert_type):
            return False
        
        alert_data = {
            "timestamp": datetime.now(),
            "person_name": person_name,
            "track_id": track_id,
            "alert_type": alert_type,
            "behavior_data": behavior_data or {},
            "frame": frame
        }
        
        # Queue alert for async processing
        self.alert_queue.put(alert_data)
        
        logger.info(f"Alert triggered for {person_name}: {alert_type}")
        return True
    
    def _execute_alert(self, alert_data: Dict):
        """Execute alert (called from background thread)"""
        person_name = alert_data["person_name"]
        alert_type = alert_data["alert_type"]
        
        logger.debug(f"Executing alert: {person_name} - {alert_type}")
        
        # Sound alert
        if self.enable_sound and self.sound_callback:
            try:
                self.sound_callback(alert_type)
            except Exception as e:
                logger.error(f"Error triggering sound alert: {e}")
        
        # Voice alert
        if self.enable_voice and self.voice_callback:
            try:
                self.voice_callback(person_name, alert_type)
            except Exception as e:
                logger.error(f"Error triggering voice alert: {e}")
        
        # SMS alert
        if self.enable_sms and self.sms_callback:
            try:
                self.sms_callback(person_name, alert_type)
            except Exception as e:
                logger.error(f"Error sending SMS alert: {e}")
        
        # Email alert
        if self.enable_email and self.email_callback:
            try:
                self.email_callback(person_name, alert_type, alert_data)
            except Exception as e:
                logger.error(f"Error sending email alert: {e}")
    
    def set_sound_callback(self, callback: Callable):
        """Set sound alert callback"""
        self.sound_callback = callback
    
    def set_voice_callback(self, callback: Callable):
        """Set voice alert callback"""
        self.voice_callback = callback
    
    def set_sms_callback(self, callback: Callable):
        """Set SMS alert callback"""
        self.sms_callback = callback
    
    def set_email_callback(self, callback: Callable):
        """Set email alert callback"""
        self.email_callback = callback
    
    def shutdown(self):
        """Shutdown alert manager"""
        self.alert_thread_running = False
        if self.alert_thread:
            self.alert_thread.join(timeout=5)
        logger.info("AlertManager shutdown")


class SoundAlertPlayer:
    """Plays non-blocking sound alerts"""
    
    def __init__(self, sound_file: str = "alert.wav"):
        """
        Initialize sound player
        
        Args:
            sound_file: Path to alert sound file
        """
        self.sound_file = sound_file
        self.playing_thread = None
        
        logger.info(f"SoundAlertPlayer initialized with {sound_file}")
    
    def play_alert(self, alert_type: str = "default"):
        """
        Play alert sound in background thread
        
        Args:
            alert_type: Type of alert (affects sound selection)
        """
        if not os.path.exists(self.sound_file):
            logger.warning(f"Alert sound file not found: {self.sound_file}")
            return
        
        # Play in separate thread to avoid blocking
        thread = threading.Thread(
            target=self._play_sound,
            args=(alert_type,),
            daemon=True
        )
        thread.start()
    
    def _play_sound(self, alert_type: str):
        """Play sound (runs in background thread)"""
        try:
            from playsound import playsound
            playsound(self.sound_file)
            logger.info(f"Alert sound played for {alert_type}")
        except ImportError:
            logger.warning("playsound not available, cannot play alert")
        except Exception as e:
            logger.error(f"Error playing alert sound: {e}")


class VoiceAlertGenerator:
    """Generates text-to-speech voice alerts"""
    
    def __init__(self):
        """Initialize voice alert generator"""
        self.tts_available = False
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.tts_available = True
            logger.info("Text-to-speech engine initialized")
        except ImportError:
            logger.warning("pyttsx3 not available for voice alerts")
    
    def speak_alert(self, person_name: str, alert_type: str):
        """
        Generate and play voice alert
        
        Args:
            person_name: Person's name
            alert_type: Type of alert
        """
        if not self.tts_available:
            return
        
        # Generate message based on alert type
        if alert_type == "sleep":
            message = f"{person_name}, please wake up"
        elif alert_type == "idle":
            message = f"{person_name}, please stay engaged"
        else:
            message = f"Alert: {person_name}"
        
        # Speak in background thread
        thread = threading.Thread(
            target=self._speak,
            args=(message,),
            daemon=True
        )
        thread.start()
    
    def _speak(self, message: str):
        """Speak message (runs in background thread)"""
        try:
            self.engine.say(message)
            self.engine.runAndWait()
            logger.info(f"Voice alert: {message}")
        except Exception as e:
            logger.error(f"Error generating voice alert: {e}")


class SMSAlertHandler:
    """Handles SMS notifications via Twilio"""
    
    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        from_number: str = None,
        to_numbers: List[str] = None
    ):
        """
        Initialize SMS handler
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number
            to_numbers: List of recipient phone numbers
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_numbers = to_numbers or []
        self.twilio_available = False
        
        try:
            from twilio.rest import Client
            if account_sid and auth_token:
                self.client = Client(account_sid, auth_token)
                self.twilio_available = True
                logger.info("Twilio SMS handler initialized")
        except ImportError:
            logger.warning("Twilio SDK not available for SMS alerts")
    
    def send_alert(self, person_name: str, alert_type: str, extra_info: str = ""):
        """
        Send SMS alert
        
        Args:
            person_name: Person's name
            alert_type: Type of alert
            extra_info: Additional information
        """
        if not self.twilio_available or len(self.to_numbers) == 0:
            return
        
        # Generate message
        if alert_type == "sleep":
            message = f"Alert: {person_name} is sleeping. Please check immediately."
        elif alert_type == "idle":
            message = f"Alert: {person_name} has been inactive for an extended period."
        else:
            message = f"Alert: {person_name} - {alert_type}"
        
        if extra_info:
            message += f"\nDetails: {extra_info}"
        
        # Send SMS in background thread
        thread = threading.Thread(
            target=self._send_sms,
            args=(message,),
            daemon=True
        )
        thread.start()
    
    def _send_sms(self, message: str):
        """Send SMS (runs in background thread)"""
        if not self.twilio_available:
            return
        
        try:
            for to_number in self.to_numbers:
                self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number
                )
            logger.info(f"SMS alert sent to {len(self.to_numbers)} recipients")
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")


class EmailAlertHandler:
    """Handles email notifications"""
    
    def __init__(
        self,
        sender_email: str = None,
        sender_password: str = None,
        recipient_emails: List[str] = None
    ):
        """
        Initialize email handler
        
        Args:
            sender_email: Sender's email address
            sender_password: Sender's email password or app password
            recipient_emails: List of recipient emails
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails or []
        
        logger.info("EmailAlertHandler initialized")
    
    def send_alert(
        self,
        person_name: str,
        alert_type: str,
        alert_data: Dict = None
    ):
        """
        Send email alert
        
        Args:
            person_name: Person's name
            alert_type: Type of alert
            alert_data: Additional alert data
        """
        if len(self.recipient_emails) == 0:
            return
        
        # Generate email content
        subject = f"Alert: {person_name} - {alert_type}"
        
        body = f"""
        Smart Monitoring System Alert
        
        Person: {person_name}
        Alert Type: {alert_type}
        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Details:
        {json.dumps(alert_data or {}, indent=2)}
        
        Please take appropriate action.
        """
        
        # Send email in background thread
        thread = threading.Thread(
            target=self._send_email,
            args=(subject, body),
            daemon=True
        )
        thread.start()
    
    def _send_email(self, subject: str, body: str):
        """Send email (runs in background thread)"""
        if not self.sender_email or not self.sender_password:
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {len(self.recipient_emails)} recipients")
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")


class NotificationLogger:
    """Logs all alerts for history and analysis"""
    
    def __init__(self, log_file: str = "logs/alerts.log"):
        """
        Initialize notification logger
        
        Args:
            log_file: Path to alert log file
        """
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
    
    def log_alert(
        self,
        person_name: str,
        alert_type: str,
        track_id: int = None,
        behavior_data: Dict = None
    ):
        """
        Log alert to file
        
        Args:
            person_name: Person's name
            alert_type: Alert type
            track_id: Track ID
            behavior_data: Behavior data
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = {
                "timestamp": timestamp,
                "person_name": person_name,
                "alert_type": alert_type,
                "track_id": track_id,
                "behavior_data": behavior_data or {}
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.debug(f"Alert logged: {person_name} - {alert_type}")
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
