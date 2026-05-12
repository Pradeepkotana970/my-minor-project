"""
Advanced Smart Monitoring System v4.0
Integrating ML, Real-time Streaming, Caching, and Enterprise Integrations
"""

import logging
import os
import sqlite3
from flask import Flask, request, g, jsonify, render_template, Response, session
import cv2, os, csv, time, json, io, base64, threading
from datetime import datetime
from dotenv import load_dotenv
import json

from startup_features import startup_manager

# Import enterprise modules from previous phases
from app_enterprise import app as base_app
from api_gateway import ResponseFormatter

# Import advanced modules
from advanced_ml import (
    AnomalyDetector, PredictiveAnalytics, BehaviorClustering,
    TimeSeriesForecast, ModelEvaluation
)
from streaming import (
    StreamingServer, EventType, LiveDashboardManager,
    EventBuffer, MetricsCollector, StreamingAnalytics, NotificationQueue
)
from caching import (
    CacheManager, QueryOptimizer, ConnectionPool,
    BatchProcessor, PerformanceMonitor
)
from integrations import (
    IntegrationManager, IntegrationProvider
)
from behavior_capture import (
    BehaviorCaptureAnalyzer, BehaviorReportGenerator
)
from config import DATABASE_PATH

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app (inherits from enterprise app)
app = base_app

# ============= Initialize Advanced Components =============

# ML Models
anomaly_detector = AnomalyDetector(contamination=float(os.getenv('ANOMALY_CONTAMINATION', 0.1)))
predictor = PredictiveAnalytics()
clustering = BehaviorClustering(n_clusters=4)
evaluator = ModelEvaluation()

# Streaming
streaming_server = StreamingServer(max_clients=int(os.getenv('MAX_STREAMING_CLIENTS', 100)))
live_dashboard = LiveDashboardManager(streaming_server)
event_buffer = EventBuffer(
    batch_size=int(os.getenv('EVENT_BUFFER_SIZE', 100)),
    flush_interval=int(os.getenv('METRICS_FLUSH_INTERVAL', 5))
)
metrics_collector = MetricsCollector()
streaming_analytics = StreamingAnalytics(streaming_server)
notification_queue = NotificationQueue()

# Caching & Performance
cache_manager = CacheManager(
    redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    use_redis=os.getenv('USE_REDIS', 'true').lower() == 'true'
)
query_optimizer = QueryOptimizer(cache_manager)
performance_monitor = PerformanceMonitor()
batch_processor = BatchProcessor(batch_size=100, flush_interval=5)

# Integrations
integration_manager = IntegrationManager()

# Behavior Capture
behavior_analyzer = BehaviorCaptureAnalyzer()

# Initialize integrations if configured
def init_integrations():
    """Initialize configured integrations"""
    try:
        # Slack
        if os.getenv('SLACK_WEBHOOK_URL'):
            integration_manager.register_integration(
                "slack",
                {"webhook_url": os.getenv('SLACK_WEBHOOK_URL')},
                IntegrationProvider.SLACK
            )
        
        # Microsoft Teams
        if os.getenv('TEAMS_WEBHOOK_URL'):
            integration_manager.register_integration(
                "teams",
                {"webhook_url": os.getenv('TEAMS_WEBHOOK_URL')},
                IntegrationProvider.TEAMS
            )
        
        # Google Sheets
        if os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID'):
            integration_manager.register_integration(
                "sheets",
                {
                    "spreadsheet_id": os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID'),
                    "sheet_name": os.getenv('GOOGLE_SHEETS_SHEET_NAME', 'Attendance'),
                    "api_key": os.getenv('GOOGLE_SHEETS_API_KEY')
                },
                IntegrationProvider.GOOGLE_SHEETS
            )
        
        # Zendesk
        if os.getenv('ZENDESK_SUBDOMAIN'):
            integration_manager.register_integration(
                "zendesk",
                {
                    "subdomain": os.getenv('ZENDESK_SUBDOMAIN'),
                    "email": os.getenv('ZENDESK_EMAIL'),
                    "api_token": os.getenv('ZENDESK_API_TOKEN')
                },
                IntegrationProvider.ZENDESK
            )
        
        logger.info(f"Initialized {len(integration_manager.integrations)} integrations")
    
    except Exception as e:
        logger.error(f"Error initializing integrations: {e}")

init_integrations()

# ============= Camera & Attendance Logic (Restored) =============
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

cam = None
camera_lock = threading.Lock()
frame_lock = threading.Lock()
current_frame = None
last_behavior_result = {"behavior": "Active", "confidence": 100}
behavior_lock = threading.Lock()

def get_camera():
    global cam
    if cam is not None:
        return cam
    
    # Try multiple indices
    for index in [0, 1, 2, -1]:
        try:
            logger.info(f"Attempting to initialize camera with index {index}...")
            temp_cam = cv2.VideoCapture(index)
            if temp_cam.isOpened():
                ret, frame = temp_cam.read()
                if ret:
                    logger.info(f"Successfully initialized camera with index {index}")
                    cam = temp_cam
                    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    return cam
                else:
                    logger.warning(f"Camera index {index} opened but failed to read frame.")
                    temp_cam.release()
            else:
                logger.warning(f"Could not open camera index {index}")
        except Exception as e:
            logger.error(f"Error initializing camera index {index}: {e}")
            
    logger.error("All camera indices failed.")
    return None

def release_camera():
    global cam
    if cam is not None:
        try:
            cam.release()
            logger.info("Camera released successfully")
        except Exception as e:
            logger.error(f"Error releasing camera: {e}")
        cam = None

def generate_frames():
    global current_frame
    logger.info("Starting frame generation...")
    camera = get_camera()
    if not camera:
        logger.error("No camera available for streaming")
        return
    
    try:
        while camera.isOpened():
            with camera_lock:
                ret, frame = camera.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                break
            
            # Apply some processing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, "Face Detected", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Behavior Analysis (every 5 frames to save CPU)
            if int(time.time() * 10) % 5 == 0:
                global last_behavior_result
                res = behavior_analyzer.analyze_behavior_state(frame)
                with behavior_lock:
                    last_behavior_result = res
            
            with behavior_lock:
                status = last_behavior_result.get('behavior', 'Active')
                conf = last_behavior_result.get('confidence', 0)
                # Color coding: Green for Active, Yellow for Dull, Orange for Drowsy, Red for Sleepy
                color = (0, 255, 0) if status == "Active" else \
                        (0, 255, 255) if status == "Dull" else \
                        (0, 165, 255) if status == "Drowsy" else \
                        (0, 0, 255)
                cv2.putText(frame, f"State: {status} ({conf:.0f}%)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            with frame_lock:
                current_frame = frame.copy()
            
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Add a small sleep to prevent CPU hogging
            time.sleep(0.03) 
    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        release_camera()
        logger.info("Frame generation stream closed and camera released")

# ============= Startup & Frontend Routes =============

@app.route('/')
def index():
    """Serve the premium monitoring dashboard."""
    return render_template('index_premium.html')

@app.route('/register', methods=['GET'])
def register_page():
    """Serve the advanced registration page."""
    return render_template('register_advanced.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stop_video_feed', methods=['POST'])
def stop_video_feed():
    """Release the server-side camera so browser can use it for registration."""
    release_camera()
    return jsonify({"success": True, "message": "Camera released"})

@app.route('/api/stats')
def get_stats():
    """Get system statistics for dashboard."""
    total_students = 0
    if os.path.exists('students.csv'):
        with open('students.csv', 'r') as f:
            total_students = sum(1 for line in f) - 1 # Subtract header
    
    present = 0
    if os.path.exists('attendance.csv'):
        with open('attendance.csv', 'r') as f:
            present = sum(1 for line in f) - 1
            
    return jsonify({
        "total_students": max(0, total_students),
        "present_today": max(0, present),
        "absent_today": max(0, total_students - present)
    })

@app.route('/api/chart_data')
def chart_data():
    """Get data for the doughnut chart."""
    total_students = 0
    if os.path.exists('students.csv'):
        with open('students.csv', 'r') as f:
            total_students = sum(1 for line in f) - 1
    
    present = 0
    if os.path.exists('attendance.csv'):
        with open('attendance.csv', 'r') as f:
            present = sum(1 for line in f) - 1
            
    return jsonify({
        "present": max(0, present),
        "absent": max(0, total_students - present)
    })

@app.route('/api/unknown_alert')
def unknown_alert():
    """Check if an unknown person was recently detected."""
    # This is a mock for now, ideally tracked in generate_frames
    return jsonify({"unknown_detected": False})

@app.route('/api/reset_attendance', methods=['POST'])
def reset_attendance():
    """Reset today's attendance records."""
    try:
        if os.path.exists('attendance.csv'):
            os.remove('attendance.csv')
        return jsonify({"success": True, "message": "Attendance records cleared."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/behavior_status')
def behavior_status():
    """Get the latest behavior analysis result."""
    with behavior_lock:
        return jsonify(last_behavior_result)

@app.route('/api/camera_check')
def camera_check():
    """Check camera availability status without holding the camera."""
    try:
        temp = cv2.VideoCapture(0)
        if temp.isOpened():
            ret, _ = temp.read()
            temp.release()
            return jsonify({"status": "connected" if ret else "error",
                            "message": "Camera is active" if ret else "Camera failed to read"})
    except Exception as e:
        pass
    return jsonify({"status": "disconnected", "message": "Camera not found or in use"})

@app.route('/api/export_attendance')
def export_attendance():
    """Download attendance CSV."""
    from flask import send_file
    if os.path.exists('attendance.csv'):
        return send_file(os.path.abspath('attendance.csv'),
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='attendance.csv')
    # Return empty CSV if no records
    import io
    output = io.StringIO()
    output.write("Timestamp,Name,Roll,Status\n")
    output.seek(0)
    from flask import make_response
    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=attendance.csv'
    return resp

@app.route('/history')
def history():
    """Attendance history page."""
    records = []
    if os.path.exists('attendance.csv'):
        with open('attendance.csv', 'r') as f:
            reader = csv.DictReader(f)
            records = list(reader)
    return render_template('history_premium.html', records=records)

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register user via API (Multipart/FormData)"""
    try:
        name = request.form.get('name', '').strip()
        roll = request.form.get('roll', '000').strip()
        method = request.form.get('method', 'camera')
        
        # Save dataset
        dataset_dir = 'dataset'
        os.makedirs(dataset_dir, exist_ok=True)
        
        saved_count = 0
        user_id = abs(hash(name)) % 10000
        
        # Handle uploaded files
        files = request.files
        for key in files:
            if key.startswith('image_'):
                file = files[key]
                filename = os.path.join(dataset_dir, f"{name}_{user_id}_{saved_count}.jpg")
                file.save(filename)
                saved_count += 1
                
        if saved_count == 0:
            return jsonify({"success": False, "message": "No images received."})

        # Update students.csv
        file_exists = os.path.exists('students.csv')
        with open('students.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Name", "Roll"])
            writer.writerow([name, roll])

        return jsonify({
            "success": True, 
            "message": f"Successfully registered {name}. neural paths established.",
            "saved_count": saved_count
        })
    except Exception as e:
        logger.error(f"API Registration Error: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/dashboard')
def dashboard():
    """Serve the dashboard"""
    return render_template('dashboard.html')

@app.route('/behavior-detection')
def behavior_detection():
    """Serve the behavior detection interface"""
    return render_template('behavior_detection.html')

@app.route('/register', methods=['POST'])
def face_register():
    """Advanced Registration Endpoint handling face scans"""
    import base64
    import os
    from io import BytesIO
    from PIL import Image

    try:
        data = request.json or {}
        name = data.get('name', 'Unknown').strip()
        roll = data.get('roll', '000').strip()
        faces = data.get('faces', [])

        if not name or not faces:
            return jsonify({"success": False, "message": "Missing name or face data."})

        # Save the dataset
        dataset_dir = 'dataset'
        os.makedirs(dataset_dir, exist_ok=True)
        
        saved_count = 0
        user_id = abs(hash(name)) % 10000

        for idx, base64_img in enumerate(faces):
            if ',' in base64_img:
                base64_img = base64_img.split(',')[1]
            try:
                img_bytes = base64.b64decode(base64_img)
                img = Image.open(BytesIO(img_bytes))
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                filename = os.path.join(dataset_dir, f"{name}_{user_id}_{idx}.jpg")
                img.save(filename, 'JPEG', quality=95)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving face: {e}")

        logger.info(f"Registered user {name} with {saved_count} face snapshots.")
        
        return jsonify({
            "success": True,
            "message": f"Successfully registered {name}. Neural paths established.",
            "auto_marked": True
        })
    except Exception as e:
        logger.error(f"Registration Error: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/v1/apikeys/generate', methods=['POST'])
def generate_api_key():
    """Startup API key generation endpoint"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'test_user')
        tier = data.get('tier', 'free')
        
        result = startup_manager.generate_api_key(user_id, tier)
        return ResponseFormatter.success(data=result, message="API Key Generated")
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        return ResponseFormatter.error(str(e), "API_ERROR", 500)

@app.route('/api/v1/context/weather', methods=['GET'])
def get_weather_context():
    """Fetch external Open-Meteo context"""
    try:
        # Default coords to NYC for demo
        lat = float(request.args.get('lat', 40.7128))
        lon = float(request.args.get('lon', -74.0060))
        
        result = startup_manager.fetch_weather_context(lat, lon)
        if result.get("status") == "success":
            return ResponseFormatter.success(data=result)
        else:
            return ResponseFormatter.error("Weather API failed", "EXTERNAL_API_ERROR", 500)
    except Exception as e:
        logger.error(f"Error fetching weather context: {e}")
        return ResponseFormatter.error(str(e), "CONTEXT_ERROR", 500)


# ============= User Management & Analytics Routes =============

@app.route('/api/v1/advanced/users', methods=['GET'])
def get_registered_users():
    """Fetch list of registered users with their details"""
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT name, roll_number as roll, registration_date as reg_date FROM users ORDER BY registration_date DESC")
        users = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"success": True, "users": users})
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/v1/advanced/analytics/progress', methods=['GET'])
def get_progress_analytics():
    """Fetch attendance trends and behavior distribution for the progress section"""
    try:
        conn = sqlite3.connect(str(DATABASE_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Last 7 days attendance trend
        c.execute("""
            SELECT date(check_in) as date, COUNT(DISTINCT user_id) as count 
            FROM attendance 
            WHERE check_in >= date('now', '-7 days') 
            GROUP BY date(check_in) 
            ORDER BY date ASC
        """)
        trend = [dict(row) for row in c.fetchall()]
        
        # Behavior distribution
        c.execute("""
            SELECT behavior_status as behavior, COUNT(*) as count 
            FROM attendance 
            GROUP BY behavior_status
        """)
        behavior_dist = [dict(row) for row in c.fetchall()]
        
        # Engagement over time (mocked for now based on behavior)
        # In a real scenario, this would use a more complex engagement score
        engagement_trend = []
        for day in trend:
            engagement_trend.append({
                "date": day['date'],
                "score": 85 + (hash(day['date']) % 15) # Simulated score
            })
        
        conn.close()
        return jsonify({
            "success": True, 
            "attendance_trend": trend,
            "behavior_distribution": behavior_dist,
            "engagement_trend": engagement_trend
        })
    except Exception as e:
        logger.error(f"Error calculating progress analytics: {e}")
        return jsonify({"success": False, "message": str(e)})


# ============= Advanced ML Routes =============

@app.route('/api/v1/advanced/predictions/next-behavior', methods=['GET'])
def get_next_behavior_prediction():
    """Predict next behavior for student"""
    try:
        org_id = request.args.get('org_id')
        person_id = request.args.get('person_id')
        
        if not org_id or not person_id:
            return ResponseFormatter.error("Missing org_id or person_id", "MISSING_PARAMS", 400)
        
        # Check cache
        cache_key = f"prediction:behavior:{person_id}"
        cached = cache_manager.get(cache_key)
        if cached:
            logger.debug(f"Cache hit: {cache_key}")
            return ResponseFormatter.success(data=cached)
        
        # Get prediction
        start_time = datetime.now()
        prediction = predictor.predict_next_behavior(org_id, person_id)
        prediction_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Cache result
        cache_manager.set(cache_key, prediction, ttl=300)
        
        # Record metric
        metrics_collector.record_metric(org_id, "prediction_latency_ms", prediction_time)
        performance_monitor.record_operation("predict_behavior", prediction_time)
        
        return ResponseFormatter.success(data=prediction)
    
    except Exception as e:
        logger.error(f"Error predicting behavior: {e}")
        return ResponseFormatter.error(str(e), "PREDICTION_ERROR", 500)


@app.route('/api/v1/advanced/predictions/risk-score', methods=['GET'])
def get_risk_score():
    """Calculate risk score for student"""
    try:
        org_id = request.args.get('org_id')
        person_id = request.args.get('person_id')
        
        if not org_id or not person_id:
            return ResponseFormatter.error("Missing org_id or person_id", "MISSING_PARAMS", 400)
        
        # Get risk score
        risk = predictor.calculate_risk_score(org_id, person_id)
        
        # Publish event if high risk
        if risk.get('risk_score', 0) >= 70:
            streaming_server.publish_event(
                EventType.PREDICTION_UPDATE,
                risk,
                org_id
            )
            streaming_analytics.track_event(EventType.PREDICTION_UPDATE, org_id)
        
        return ResponseFormatter.success(data=risk)
    
    except Exception as e:
        logger.error(f"Error calculating risk score: {e}")
        return ResponseFormatter.error(str(e), "RISK_ERROR", 500)


@app.route('/api/v1/advanced/predictions/attendance-forecast', methods=['GET'])
def get_attendance_forecast():
    """Forecast attendance for next N days"""
    try:
        org_id = request.args.get('org_id')
        person_id = request.args.get('person_id')
        days = request.args.get('days', default=7, type=int)
        
        if not org_id or not person_id:
            return ResponseFormatter.error("Missing org_id or person_id", "MISSING_PARAMS", 400)
        
        forecast = TimeSeriesForecast.forecast_attendance(org_id, person_id, days)
        
        return ResponseFormatter.success(data=forecast)
    
    except Exception as e:
        logger.error(f"Error forecasting attendance: {e}")
        return ResponseFormatter.error(str(e), "FORECAST_ERROR", 500)


# ============= Anomaly Detection Routes =============

@app.route('/api/v1/advanced/anomalies/detect', methods=['POST'])
def detect_anomaly():
    """Detect anomalous behavior"""
    try:
        data = request.get_json()
        org_id = data.get('org_id')
        features = data.get('features', {})
        
        if not org_id:
            return ResponseFormatter.error("Missing org_id", "MISSING_ORG", 400)
        
        # Detect anomaly
        is_anomaly, confidence = anomaly_detector.detect(features)
        
        if is_anomaly:
            # Publish anomaly event
            streaming_server.publish_event(
                EventType.ANOMALY_DETECTED,
                {
                    "is_anomaly": True,
                    "confidence": confidence,
                    "features": features
                },
                org_id
            )
            streaming_analytics.track_event(EventType.ANOMALY_DETECTED, org_id)
            
            # Notify dashboard
            live_dashboard.broadcast_anomaly(org_id, {
                "severity": "high" if confidence > 0.8 else "medium",
                "confidence": confidence
            })
        
        return ResponseFormatter.success(
            data={
                "is_anomaly": is_anomaly,
                "confidence": float(confidence)
            }
        )
    
    except Exception as e:
        logger.error(f"Error detecting anomaly: {e}")
        return ResponseFormatter.error(str(e), "ANOMALY_ERROR", 500)


# ============= Clustering Routes =============

@app.route('/api/v1/advanced/clusters/assignments', methods=['GET'])
def get_cluster_assignments():
    """Get behavioral cluster assignments"""
    try:
        org_id = request.args.get('org_id')
        
        if not org_id:
            return ResponseFormatter.error("Missing org_id", "MISSING_ORG", 400)
        
        # Check cache
        cache_key = f"clusters:assignments:{org_id}"
        cached = cache_manager.get(cache_key)
        if cached:
            return ResponseFormatter.success(data=cached)
        
        # Get clusters
        db_path = f"attendance_{org_id}.db"
        clusters = clustering.train_clusters(org_id, db_path)
        
        # Format as list
        cluster_list = [
            {
                "person_id": person_id,
                **cluster_data
            }
            for person_id, cluster_data in clusters.items()
        ]
        
        # Cache result
        cache_manager.set(cache_key, cluster_list, ttl=3600)
        
        return ResponseFormatter.success(data=cluster_list)
    
    except Exception as e:
        logger.error(f"Error getting clusters: {e}")
        return ResponseFormatter.error(str(e), "CLUSTER_ERROR", 500)


@app.route('/api/v1/advanced/clusters/summary', methods=['GET'])
def get_cluster_summary():
    """Get cluster summary statistics"""
    try:
        org_id = request.args.get('org_id')
        
        if not org_id:
            return ResponseFormatter.error("Missing org_id", "MISSING_ORG", 400)
        
        # Get clusters
        db_path = f"attendance_{org_id}.db"
        clusters = clustering.train_clusters(org_id, db_path)
        
        # Aggregate by cluster
        cluster_stats = {}
        for person_id, cluster_data in clusters.items():
            cluster_id = cluster_data['cluster']
            
            if cluster_id not in cluster_stats:
                cluster_stats[cluster_id] = {
                    "id": cluster_id,
                    "name": cluster_data['cluster_name'],
                    "size": 0,
                    "total_engagement": 0
                }
            
            cluster_stats[cluster_id]["size"] += 1
            cluster_stats[cluster_id]["total_engagement"] += cluster_data['statistics']['engagement']
        
        # Calculate averages
        for cluster_data in cluster_stats.values():
            cluster_data["avg_engagement"] = cluster_data["total_engagement"] / cluster_data["size"]
        
        return ResponseFormatter.success(data=list(cluster_stats.values()))
    
    except Exception as e:
        logger.error(f"Error getting cluster summary: {e}")
        return ResponseFormatter.error(str(e), "CLUSTER_ERROR", 500)


# ============= Real-time Streaming Routes =============

@app.route('/api/v1/advanced/streaming/stats', methods=['GET'])
def get_streaming_stats():
    """Get streaming server statistics"""
    try:
        stats = streaming_server.get_client_stats()
        
        return ResponseFormatter.success(data=stats)
    
    except Exception as e:
        logger.error(f"Error getting streaming stats: {e}")
        return ResponseFormatter.error(str(e), "STREAMING_ERROR", 500)


@app.route('/api/v1/advanced/streaming/event-summary', methods=['GET'])
def get_event_summary():
    """Get event summary for organization"""
    try:
        org_id = request.args.get('org_id')
        
        if not org_id:
            return ResponseFormatter.error("Missing org_id", "MISSING_ORG", 400)
        
        summary = streaming_analytics.get_event_summary(org_id)
        
        return ResponseFormatter.success(data=summary)
    
    except Exception as e:
        logger.error(f"Error getting event summary: {e}")
        return ResponseFormatter.error(str(e), "STREAMING_ERROR", 500)


# ============= Caching & Performance Routes =============

@app.route('/api/v1/advanced/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = cache_manager.get_stats()
        
        return ResponseFormatter.success(data=stats)
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return ResponseFormatter.error(str(e), "CACHE_ERROR", 500)


@app.route('/api/v1/advanced/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache pattern"""
    try:
        data = request.get_json()
        pattern = data.get('pattern', '*')
        
        cache_manager.clear(pattern)
        
        return ResponseFormatter.success(message=f"Cleared cache pattern: {pattern}")
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return ResponseFormatter.error(str(e), "CACHE_ERROR", 500)


@app.route('/api/v1/advanced/performance/summary', methods=['GET'])
def get_performance_summary():
    """Get performance summary"""
    try:
        summary = performance_monitor.get_performance_summary()
        
        return ResponseFormatter.success(data=summary)
    
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return ResponseFormatter.error(str(e), "PERFORMANCE_ERROR", 500)


@app.route('/api/v1/advanced/performance/bottlenecks', methods=['GET'])
def get_bottlenecks():
    """Identify performance bottlenecks"""
    try:
        bottlenecks = performance_monitor.get_bottlenecks()
        
        return ResponseFormatter.success(data=[
            {"operation": op, "avg_ms": time} for op, time in bottlenecks
        ])
    
    except Exception as e:
        logger.error(f"Error getting bottlenecks: {e}")
        return ResponseFormatter.error(str(e), "PERFORMANCE_ERROR", 500)


# ============= Integration Routes =============

@app.route('/api/v1/advanced/integrations/status', methods=['GET'])
def get_integration_status():
    """Get integration status"""
    try:
        status = integration_manager.get_integration_status()
        
        return ResponseFormatter.success(data=status)
    
    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        return ResponseFormatter.error(str(e), "INTEGRATION_ERROR", 500)


@app.route('/api/v1/advanced/integrations/test', methods=['POST'])
def test_integration():
    """Test integration connection"""
    try:
        data = request.get_json()
        integration_name = data.get('integration_name')
        
        if not integration_name:
            return ResponseFormatter.error("Missing integration_name", "MISSING_PARAM", 400)
        
        integration = integration_manager.get_integration(integration_name)
        if not integration:
            return ResponseFormatter.error(f"Integration not found: {integration_name}", "NOT_FOUND", 404)
        
        is_connected = integration.test_connection()
        
        return ResponseFormatter.success(
            data={
                "integration": integration_name,
                "status": "connected" if is_connected else "disconnected",
                "last_test": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"Error testing integration: {e}")
        return ResponseFormatter.error(str(e), "INTEGRATION_ERROR", 500)


@app.route('/api/v1/advanced/integrations/send-alert', methods=['POST'])
def send_alert_to_integrations():
    """Send alert to registered integrations"""
    try:
        data = request.get_json()
        alert_data = data.get('alert_data', {})
        integrations = data.get('integrations', [])
        
        if not alert_data:
            return ResponseFormatter.error("Missing alert_data", "MISSING_DATA", 400)
        
        # Send to specific integrations if listed
        if integrations:
            results = {}
            for integration_name in integrations:
                integration = integration_manager.get_integration(integration_name)
                if integration:
                    try:
                        if hasattr(integration, 'send_alert'):
                            results[integration_name] = integration.send_alert(alert_data)
                        else:
                            results[integration_name] = integration.send_message({
                                "title": f"Alert: {alert_data.get('alert_type')}",
                                "text": alert_data.get("description", ""),
                                "metadata": alert_data
                            })
                    except Exception as e:
                        logger.error(f"Error sending to {integration_name}: {e}")
                        results[integration_name] = False
        else:
            # Send to all
            results = integration_manager.send_alert_to_all(alert_data)
        
        return ResponseFormatter.success(data=results)
    
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        return ResponseFormatter.error(str(e), "INTEGRATION_ERROR", 500)


# ============= Behavior Capture Routes =============

@app.route('/api/v1/behavior/start-capture', methods=['POST'])
def start_behavior_capture():
    """Start capturing behavior from webcam"""
    try:
        data = request.get_json() or {}
        camera_id = data.get('camera_id', 0)
        
        # Initialize camera
        success = behavior_analyzer.initialize_camera(camera_id)
        
        if not success:
            return ResponseFormatter.error("Failed to initialize camera", "CAMERA_ERROR", 500)
        
        return ResponseFormatter.success(
            data={"status": "capturing", "camera_id": camera_id},
            message="Behavior capture started"
        )
    except Exception as e:
        logger.error(f"Error starting behavior capture: {e}")
        return ResponseFormatter.error(str(e), "CAPTURE_ERROR", 500)


@app.route('/api/v1/behavior/analyze-frame', methods=['GET'])
def analyze_behavior_frame():
    """Capture and analyze single frame for behavior"""
    try:
        # Capture frame
        frame = behavior_analyzer.capture_frame()
        if frame is None:
            return ResponseFormatter.error("Failed to capture frame", "CAPTURE_ERROR", 500)
        
        # Analyze behavior
        analysis = behavior_analyzer.analyze_behavior_state(frame)
        
        # Get frame as base64
        frame_b64 = behavior_analyzer.get_frame_base64()
        
        result = {
            **analysis,
            "frame": frame_b64
        }
        
        return ResponseFormatter.success(data=result)
    
    except Exception as e:
        logger.error(f"Error analyzing behavior frame: {e}")
        return ResponseFormatter.error(str(e), "ANALYSIS_ERROR", 500)


@app.route('/api/v1/behavior/stream', methods=['GET'])
def stream_behavior():
    """Stream behavior analysis results"""
    try:
        def generate():
            import time
            while True:
                try:
                    # Capture and analyze frame
                    frame = behavior_analyzer.capture_frame()
                    if frame is None:
                        continue
                    
                    analysis = behavior_analyzer.analyze_behavior_state(frame)
                    frame_b64 = behavior_analyzer.get_frame_base64()
                    
                    data = {
                        **analysis,
                        "frame": frame_b64
                    }
                    
                    # Yield as SSE
                    yield f"data: {json.dumps(data)}\n\n"
                    time.sleep(0.033)  # ~30 FPS
                
                except Exception as e:
                    logger.error(f"Error in stream: {e}")
                    time.sleep(0.1)
        
        return app.response_class(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        logger.error(f"Error streaming behavior: {e}")
        return ResponseFormatter.error(str(e), "STREAM_ERROR", 500)


@app.route('/api/v1/behavior/summary', methods=['GET'])
def get_behavior_summary():
    """Get behavior summary from recent captures"""
    try:
        summary = behavior_analyzer.get_behavior_summary()
        return ResponseFormatter.success(data=summary)
    
    except Exception as e:
        logger.error(f"Error getting behavior summary: {e}")
        return ResponseFormatter.error(str(e), "SUMMARY_ERROR", 500)


@app.route('/api/v1/behavior/report', methods=['POST'])
def generate_behavior_report():
    """Generate comprehensive behavior report"""
    try:
        data = request.get_json() or {}
        behavior_data = data.get('behavior_data', [])
        
        if not behavior_data:
            return ResponseFormatter.error("No behavior data provided", "MISSING_DATA", 400)
        
        report = BehaviorReportGenerator.generate_report(behavior_data)
        return ResponseFormatter.success(data=report)
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return ResponseFormatter.error(str(e), "REPORT_ERROR", 500)


@app.route('/api/v1/behavior/stop-capture', methods=['POST'])
def stop_behavior_capture():
    """Stop capturing behavior and release camera"""
    try:
        behavior_analyzer.release_camera()
        return ResponseFormatter.success(
            data={"status": "stopped"},
            message="Behavior capture stopped"
        )
    except Exception as e:
        logger.error(f"Error stopping behavior capture: {e}")
        return ResponseFormatter.error(str(e), "STOP_ERROR", 500)


# ============= System Status Routes =============

@app.route('/api/v1/advanced/system/status', methods=['GET'])
def get_system_status():
    """Get advanced system status"""
    try:
        status = {
            "version": "4.0",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "ml_models": {
                    "anomaly_detector": "active",
                    "predictor": "active",
                    "clustering": "active"
                },
                "streaming": {
                    "connected_clients": streaming_server.get_client_stats()['total_clients'],
                    "event_queue_size": streaming_server.get_client_stats()['event_queue_size']
                },
                "caching": cache_manager.get_stats(),
                "integrations": len(integration_manager.integrations),
                "performance": {
                    "operations_tracked": len(performance_monitor.metrics)
                }
            }
        }
        
        return ResponseFormatter.success(data=status)
    
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return ResponseFormatter.error(str(e), "STATUS_ERROR", 500)


# ============= Error Handlers =============

@app.errorhandler(400)
def bad_request(error):
    return ResponseFormatter.error("Bad Request", "BAD_REQUEST", 400)


@app.errorhandler(404)
def not_found(error):
    return ResponseFormatter.error("Not Found", "NOT_FOUND", 404)


@app.errorhandler(500)
def internal_error(error):
    return ResponseFormatter.error("Internal Server Error", "INTERNAL_ERROR", 500)


if __name__ == '__main__':
    logger.info("Starting Advanced Smart Monitoring System v4.0")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"Redis enabled: {os.getenv('USE_REDIS', 'true')}")
    logger.info(f"Integrations: {len(integration_manager.integrations)}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('ENV', 'development') == 'development',
        threaded=True
    )
