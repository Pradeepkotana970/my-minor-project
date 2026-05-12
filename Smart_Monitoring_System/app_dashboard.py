"""
Flask Web Application - Enhanced Dashboard
Real-time monitoring with live video, statistics, and alerts
"""

from flask import Flask, render_template, Response, jsonify, request
import cv2
import threading
import logging
import json
from datetime import datetime
from pathlib import Path
import os

from app_enhanced_v2 import SmartMonitoringSystem
from database_enhanced import EnhancedDatabaseManager
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = config.SECRET_KEY

# Global instances
monitoring_system = None
db_manager = None
is_monitoring = False
monitoring_thread = None


def init_system():
    """Initialize monitoring system and database"""
    global monitoring_system, db_manager
    
    try:
        monitoring_system = SmartMonitoringSystem()
        db_manager = EnhancedDatabaseManager()
        logger.info("System initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        return False


def start_monitoring():
    """Start monitoring in background thread"""
    global is_monitoring, monitoring_thread
    
    if is_monitoring:
        return False
    
    is_monitoring = True
    monitoring_thread = threading.Thread(target=monitoring_system.run_video_loop, daemon=True)
    monitoring_thread.start()
    logger.info("Monitoring started")
    return True


def stop_monitoring():
    """Stop monitoring"""
    global is_monitoring
    is_monitoring = False
    if monitoring_system:
        monitoring_system.release_camera()
    logger.info("Monitoring stopped")


def video_generator():
    """Generate video frames for streaming"""
    while is_monitoring and monitoring_system:
        try:
            frame = monitoring_system.process_frame()
            if frame is not None:
                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
                       + frame_bytes + b'\r\n')
            else:
                logger.warning("Failed to get frame")
        except Exception as e:
            logger.error(f"Error in video generator: {e}")


# ========== WEB ROUTES ==========

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html', system_name="Smart Monitoring System v2.0")


@app.route('/video_feed')
def video_feed():
    """Video streaming endpoint"""
    if not is_monitoring:
        return "Monitoring not active", 503
    
    return Response(video_generator(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify({
        "monitoring_active": is_monitoring,
        "system_initialized": monitoring_system is not None,
        "timestamp": datetime.now().isoformat(),
        "frames_processed": monitoring_system.session_data["frames_processed"] if monitoring_system else 0,
        "total_faces_detected": monitoring_system.session_data["total_faces_detected"] if monitoring_system else 0
    })


@app.route('/api/start_monitoring', methods=['POST'])
def api_start_monitoring():
    """Start monitoring endpoint"""
    if not monitoring_system:
        return jsonify({"success": False, "error": "System not initialized"}), 500
    
    success = start_monitoring()
    return jsonify({"success": success, "message": "Monitoring started" if success else "Already monitoring"})


@app.route('/api/stop_monitoring', methods=['POST'])
def api_stop_monitoring():
    """Stop monitoring endpoint"""
    stop_monitoring()
    return jsonify({"success": True, "message": "Monitoring stopped"})


@app.route('/api/stats')
def get_stats():
    """Get monitoring statistics"""
    if not monitoring_system:
        return jsonify({"error": "System not initialized"}), 500
    
    session_data = monitoring_system.session_data
    active_tracks = len(monitoring_system.tracker.get_active_tracks())
    
    return jsonify({
        "frames_processed": session_data["frames_processed"],
        "total_faces_detected": session_data["total_faces_detected"],
        "unique_persons": len(session_data["unique_persons"]),
        "active_tracks": active_tracks,
        "fps": monitoring_system.fps,
        "session_duration": str(datetime.now() - session_data["start_time"])
    })


@app.route('/api/active_tracks')
def get_active_tracks():
    """Get currently active tracks"""
    if not monitoring_system:
        return jsonify({"error": "System not initialized"}), 500
    
    tracks = monitoring_system.tracker.get_active_tracks()
    
    track_list = []
    for track in tracks:
        track_list.append({
            "track_id": track.get("id"),
            "frames_alive": track.get("frames_alive"),
            "identity": track.get("identity", "Unknown"),
            "current_behavior": monitoring_system.behavior_analyzer.person_state.get(
                track["id"], {}
            ).get("current_behavior", "Unknown")
        })
    
    return jsonify({"tracks": track_list})


@app.route('/api/attendance/today')
def get_today_attendance():
    """Get today's attendance"""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500
    
    today = datetime.now().strftime("%Y-%m-%d")
    attendance = db_manager.get_attendance_by_date(today)
    
    return jsonify({
        "date": today,
        "total": len(attendance),
        "records": attendance
    })


@app.route('/api/alerts/unacknowledged', methods=['GET'])
def get_unacknowledged_alerts():
    """Get unacknowledged alerts"""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500
    
    limit = request.args.get('limit', 50, type=int)
    alerts = db_manager.get_unacknowledged_alerts(limit)
    
    return jsonify({
        "total": len(alerts),
        "alerts": alerts
    })


@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500
    
    notes = request.json.get('notes', '') if request.json else ''
    db_manager.acknowledge_alert(alert_id, notes)
    
    return jsonify({"success": True, "message": "Alert acknowledged"})


@app.route('/api/person/<name>/behavior', methods=['GET'])
def get_person_behavior(name):
    """Get person's behavior summary"""
    if not db_manager or not monitoring_system:
        return jsonify({"error": "System not initialized"}), 500
    
    days = request.args.get('days', 7, type=int)
    
    # Get from database
    db_summary = db_manager.get_person_behavior_summary(name, days)
    
    # Get real-time state if person is being tracked
    person_state = None
    for track in monitoring_system.tracker.get_active_tracks():
        if track.get("identity") == name:
            person_state = monitoring_system.behavior_analyzer.get_person_state(track["id"])
            break
    
    return jsonify({
        "name": name,
        "database_summary": db_summary,
        "current_state": person_state
    })


@app.route('/api/report/daily', methods=['GET'])
def get_daily_report():
    """Get daily report"""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500
    
    date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    report = db_manager.export_daily_report(date)
    
    return jsonify(report)


@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Get or update system settings"""
    if request.method == 'GET':
        settings = {
            "confidence_threshold": config.CONFIDENCE_THRESHOLD,
            "sleep_threshold": config.SLEEP_THRESHOLD,
            "idle_threshold": config.IDLE_THRESHOLD,
            "alert_cooldown": config.ALERT_COOLDOWN_SECONDS,
            "enable_alerts": config.ENABLE_ALERTS,
            "enable_sound_alerts": config.ENABLE_SOUND_ALERTS,
            "enable_voice_alerts": config.ENABLE_VOICE_ALERTS,
            "enable_email": config.EMAIL_ENABLED,
            "enable_sms": config.SMS_ENABLED
        }
        return jsonify(settings)
    
    else:  # POST
        data = request.json
        
        # Update live settings
        if "confidence_threshold" in data:
            monitoring_system.face_recognizer.set_confidence_threshold(data["confidence_threshold"])
        
        if "sleep_threshold" in data:
            monitoring_system.behavior_analyzer.sleep_threshold = data["sleep_threshold"]
        
        if "idle_threshold" in data:
            monitoring_system.behavior_analyzer.idle_threshold = data["idle_threshold"]
        
        return jsonify({"success": True, "message": "Settings updated"})


@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export attendance data as CSV"""
    if not db_manager:
        return jsonify({"error": "Database not initialized"}), 500
    
    date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    report = db_manager.export_daily_report(date)
    
    # Create CSV response
    import io
    csv_buffer = io.StringIO()
    
    if report.get("attendance_details"):
        headers = report["attendance_details"][0].keys()
        csv_buffer.write(','.join(headers) + '\n')
        
        for record in report["attendance_details"]:
            values = [str(record.get(h, '')) for h in headers]
            csv_buffer.write(','.join(values) + '\n')
    
    response = app.response_class(
        response=csv_buffer.getvalue(),
        status=200,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance_" + date + ".csv"}
    )
    
    return response


# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Server error"}), 500


# ========== STARTUP/SHUTDOWN ==========

@app.before_first_request
def startup():
    """Initialize on first request"""
    logger.info("Starting Smart Monitoring Dashboard")
    init_system()


def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down")
    stop_monitoring()
    if monitoring_system:
        monitoring_system.shutdown()


# Register shutdown
import atexit
atexit.register(shutdown)


# ========== MAIN ==========

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG_MODE,
        use_reloader=False  # Important for threading
    )
