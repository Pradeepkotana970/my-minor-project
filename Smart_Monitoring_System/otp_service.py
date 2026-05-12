"""
OTP SMS Service
Handles sending verification codes via SMS
"""

import os
import json
from datetime import datetime
from typing import Tuple, Optional

def send_otp_sms(phone: str, otp: str) -> Tuple[bool, str]:
    """
    Send OTP via SMS
    
    For production, replace with Twilio or similar service:
    from twilio.rest import Client
    
    For testing, uses mock SMS file
    """
    try:
        # Mock SMS - saves to file for testing
        sms_file = 'mock_sms_messages.txt'
        
        message = f"""
═══════════════════════════════════
📱 OTP VERIFICATION MESSAGE
═══════════════════════════════════
Phone: {phone}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Message: Your verification code is: {otp}
Valid for: 10 minutes
═══════════════════════════════════
"""
        
        with open(sms_file, 'a') as f:
            f.write(message + "\n")
        
        print(f"✅ OTP SMS sent to {phone}: {otp}")
        return True, f"OTP sent to {phone}"
    
    except Exception as e:
        print(f"❌ SMS sending error: {e}")
        return False, f"Failed to send SMS: {str(e)}"

def get_test_otp_from_file(phone: str) -> Optional[str]:
    """Get OTP from mock SMS file (for testing)"""
    try:
        sms_file = 'mock_sms_messages.txt'
        if not os.path.exists(sms_file):
            return None
        
        with open(sms_file, 'r') as f:
            lines = f.readlines()
        
        # Find the last OTP for this phone
        for i in range(len(lines) - 1, -1, -1):
            if f"Phone: {phone}" in lines[i]:
                # Next line should have "Message:"
                if i + 1 < len(lines) and "Message: Your verification code is:" in lines[i + 1]:
                    # Extract OTP
                    msg_line = lines[i + 1]
                    otp = msg_line.split("code is: ")[-1].strip()
                    return otp
        
        return None
    except:
        return None

# Optional: Real Twilio Integration (uncomment for production)
"""
from twilio.rest import Client

def send_otp_sms_twilio(phone: str, otp: str) -> Tuple[bool, str]:
    try:
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, twilio_phone]):
            return False, "Twilio credentials not configured"
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=f"Your verification code is: {otp}. Valid for 10 minutes.",
            from_=twilio_phone,
            to=phone
        )
        
        print(f"✅ SMS sent via Twilio to {phone}: {message.sid}")
        return True, f"OTP sent to {phone}"
    
    except Exception as e:
        print(f"❌ Twilio error: {e}")
        return False, f"Failed to send SMS: {str(e)}"
"""
