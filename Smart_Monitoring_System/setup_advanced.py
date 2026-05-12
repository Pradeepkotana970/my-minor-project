#!/usr/bin/env python3
"""
Smart Monitoring System v4.0 - Quick Setup & Testing Script
Automated setup and testing for the advanced system
"""

import os
import subprocess
import sys
import json
import requests
import time
from pathlib import Path

class SystemSetup:
    """Setup and test the advanced monitoring system"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000/api/v1"
        self.token = None
        self.org_id = None
    
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "="*60)
        print(f"  {text}")
        print("="*60 + "\n")
    
    def step(self, number, text):
        """Print step information"""
        print(f"[Step {number}] {text}")
    
    def success(self, text):
        """Print success message"""
        print(f"✓ {text}")
    
    def error(self, text):
        """Print error message"""
        print(f"✗ {text}")
    
    def install_dependencies(self):
        """Install required packages"""
        self.print_header("Step 1: Installing Dependencies")
        
        self.step(1, "Installing Python packages...")
        
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                check=True
            )
            self.success("All dependencies installed")
            return True
        except subprocess.CalledProcessError:
            self.error("Failed to install dependencies")
            return False
    
    def setup_environment(self):
        """Setup environment variables"""
        self.print_header("Step 2: Setting Up Environment")
        
        self.step(2, "Checking environment variables...")
        
        env_file = ".env"
        
        if not os.path.exists(env_file):
            self.step(2, "Creating .env file...")
            
            env_content = """# Smart Monitoring System v4.0 Configuration

# Basic
ENV=development
PORT=5000
SECRET_KEY=dev-secret-key-change-in-production

# Database
DATABASE_URL=sqlite:///attendance.db
TENANTS_DB=sqlite:///tenants.db

# Redis (Optional but recommended)
REDIS_URL=redis://localhost:6379/0
USE_REDIS=false

# ML Models
ANOMALY_CONTAMINATION=0.1
ML_MODELS_PATH=./models/

# Streaming
MAX_STREAMING_CLIENTS=100
EVENT_BUFFER_SIZE=100
METRICS_FLUSH_INTERVAL=5

# Integrations (Optional)
# SLACK_WEBHOOK_URL=https://hooks.slack.com/...
# TEAMS_WEBHOOK_URL=https://outlook.webhook.office.com/...
# GOOGLE_SHEETS_SPREADSHEET_ID=
# ZENDESK_SUBDOMAIN=
"""
            
            with open(env_file, "w") as f:
                f.write(env_content)
            
            self.success(f"Created {env_file}")
        
        self.success("Environment configured")
        return True
    
    def register_user(self):
        """Register a test user"""
        self.print_header("Step 3: User Authentication")
        
        self.step(3, "Registering test user...")
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "TestPass123!",
                    "full_name": "Test User"
                },
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                self.success(f"User registered (ID: {data['data']['user_id']})")
                self.org_id = data['data']['org_id']
                return True
            elif response.status_code == 400 and "already exists" in response.text.lower():
                self.success("User already exists, proceeding...")
                return True
            else:
                self.error(f"Registration failed: {response.text}")
                return False
        
        except requests.ConnectionError:
            self.error("Cannot connect to server. Is it running?")
            return False
        except Exception as e:
            self.error(f"Error: {e}")
            return False
    
    def login_user(self):
        """Login and get authentication token"""
        self.step(3, "Logging in...")
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={
                    "username": "testuser",
                    "password": "TestPass123!"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data['data']['access_token']
                self.success(f"Login successful")
                return True
            else:
                self.error(f"Login failed: {response.text}")
                return False
        
        except Exception as e:
            self.error(f"Error: {e}")
            return False
    
    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        self.print_header("Step 4: Testing Basic Endpoints")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Health check
        self.step(4, "Testing health check...")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.success("Health check passed")
            else:
                self.error("Health check failed")
        except Exception as e:
            self.error(f"Health check error: {e}")
        
        # Get status
        self.step(4, "Testing status endpoint...")
        try:
            response = requests.get(f"{self.base_url}/status", headers=headers)
            if response.status_code == 200:
                self.success("Status endpoint working")
            else:
                self.error("Status endpoint failed")
        except Exception as e:
            self.error(f"Status error: {e}")
    
    def test_ml_endpoints(self):
        """Test advanced ML endpoints"""
        self.print_header("Step 5: Testing Advanced ML Endpoints")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test predictions endpoint
        self.step(5, "Testing behavior prediction...")
        try:
            response = requests.get(
                f"{self.base_url}/advanced/predictions/next-behavior",
                params={"org_id": self.org_id, "person_id": "test_person"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.success(f"Prediction API working (response: {data.get('status')})")
            else:
                self.error(f"Prediction failed: {response.status_code}")
        
        except requests.ConnectionError:
            self.error("Connection error - is server running?")
        except Exception as e:
            self.error(f"Error: {e}")
        
        # Test risk score endpoint
        self.step(5, "Testing risk score calculation...")
        try:
            response = requests.get(
                f"{self.base_url}/advanced/predictions/risk-score",
                params={"org_id": self.org_id, "person_id": "test_person"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.success("Risk score API working")
            else:
                self.error(f"Risk score failed: {response.status_code}")
        
        except Exception as e:
            self.error(f"Error: {e}")
    
    def test_streaming_endpoints(self):
        """Test real-time streaming endpoints"""
        self.print_header("Step 6: Testing Streaming Endpoints")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test streaming stats
        self.step(6, "Testing streaming server stats...")
        try:
            response = requests.get(
                f"{self.base_url}/advanced/streaming/stats",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('data', {})
                self.success(
                    f"Streaming stats: {stats.get('total_clients', 0)} clients, "
                    f"{stats.get('usage_percent', 0):.1f}% capacity"
                )
            else:
                self.error(f"Streaming stats failed: {response.status_code}")
        
        except Exception as e:
            self.error(f"Error: {e}")
    
    def test_caching(self):
        """Test caching endpoints"""
        self.print_header("Step 7: Testing Caching Endpoints")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test cache stats
        self.step(7, "Testing cache statistics...")
        try:
            response = requests.get(
                f"{self.base_url}/advanced/cache/stats",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                cache_stats = data.get('data', {})
                self.success(
                    f"Cache: {cache_stats.get('memory_cache_size', 0)} entries, "
                    f"Redis: {cache_stats.get('using_redis', False)}"
                )
            else:
                self.error(f"Cache stats failed: {response.status_code}")
        
        except Exception as e:
            self.error(f"Error: {e}")
    
    def test_integrations(self):
        """Test integration endpoints"""
        self.print_header("Step 8: Testing Integrations")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test integration status
        self.step(8, "Testing integration status...")
        try:
            response = requests.get(
                f"{self.base_url}/advanced/integrations/status",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                integrations = data.get('data', {})
                if integrations:
                    self.success(f"Found {len(integrations)} registered integrations")
                    for name, status in integrations.items():
                        connected = "✓" if status.get('connected') else "✗"
                        print(f"  {connected} {name} ({status.get('provider')})")
                else:
                    self.success("No integrations configured (optional)")
            else:
                self.error(f"Integration status failed: {response.status_code}")
        
        except Exception as e:
            self.error(f"Error: {e}")
    
    def test_performance(self):
        """Test performance monitoring"""
        self.print_header("Step 9: Testing Performance Monitoring")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Test performance summary
        self.step(9, "Testing performance summary...")
        try:
            response = requests.get(
                f"{self.base_url}/advanced/performance/summary",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                metrics = data.get('data', {})
                if metrics:
                    self.success(f"Performance metrics available for {len(metrics)} operations")
                else:
                    self.success("Performance monitoring active (no metrics yet)")
            else:
                self.error(f"Performance summary failed: {response.status_code}")
        
        except Exception as e:
            self.error(f"Error: {e}")
    
    def run_full_setup(self):
        """Run complete setup and testing"""
        self.print_header("Smart Monitoring System v4.0 - Setup & Testing")
        
        print("This script will help you set up and test the advanced system.\n")
        
        # Check if server is already running
        print("Checking if server is already running...")
        try:
            requests.get(f"{self.base_url}/health", timeout=2)
            print("✓ Server is already running!\n")
            server_running = True
        except:
            print("⚠ Server is not running. Please start it separately:")
            print("   python app_advanced_v4.py\n")
            server_running = False
        
        # Installation steps
        print("Running setup steps:\n")
        
        if not self.install_dependencies():
            return False
        
        if not self.setup_environment():
            return False
        
        if not server_running:
            print("\n⚠ Please start the server first:")
            print("   python app_advanced_v4.py")
            print("\nThen run this script again.")
            return False
        
        time.sleep(1)  # Wait for server to be ready
        
        if not self.register_user():
            return False
        
        if not self.login_user():
            return False
        
        self.test_basic_endpoints()
        self.test_ml_endpoints()
        self.test_streaming_endpoints()
        self.test_caching()
        self.test_integrations()
        self.test_performance()
        
        self.print_header("Setup Complete! 🎉")
        
        print("Next steps:")
        print("1. Access the advanced API at: http://localhost:5000/api/v1")
        print("2. Check the dashboard at: http://localhost:5000")
        print("3. Use your token for API authentication:")
        print(f"   Authorization: Bearer {self.token[:20]}...")
        print("4. Read the documentation: ADVANCED_FEATURES.md")
        print("\nExample requests:")
        print(f"curl http://localhost:5000/api/v1/advanced/cache/stats \\")
        print(f'  -H "Authorization: Bearer {self.token[:20]}..."')
        
        return True


if __name__ == "__main__":
    setup = SystemSetup()
    
    try:
        success = setup.run_full_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
