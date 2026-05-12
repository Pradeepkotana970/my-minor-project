from flask import Flask, render_template, Response, jsonify, request, session
import cv2, os, csv, time, json, io, base64
from datetime import datetime
import numpy as np
from PIL import Image
import threading
from playsound import playsound
from functools import wraps

# Import authentication modules
from auth_manager import UserDatabase
from otp_service import send_otp_sms

app = Flask(__name__)
app.secret_key = 'smart_monitor_secret_key_2024'

# -------- AUTHENTICATION MIDDLEWARE --------
def require_login(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.cookies.get('session_token')
        if not token:
            token = session.get('session_token')
        
        if not token:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        user_session = UserDatabase.verify_session(token)
        if not user_session:
            return jsonify({'success': False, 'message': 'Session expired'}), 401
        
        request.user = user_session
        return f(*args, **kwargs)
    return decorated_function

# -------- LOAD MODEL --------
# Try multiple methods to get LBPH recognizer
recognizer = None
try:
    if hasattr(cv2.face, 'LBPHFaceRecognizer_create'):
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    elif hasattr(cv2, 'face') and hasattr(cv2.face, 'createLBPHFaceRecognizer'):
        recognizer = cv2.face.createLBPHFaceRecognizer()
    else:
        # Fallback: create a simple sklearn-based recognizer
        from sklearn.svm import SVC
        recognizer = SVC(kernel='rbf', C=100, gamma='scale')
        recognizer.train = lambda X, y: recognizer.fit(np.array(X).reshape(len(X), -1), y)
        recognizer.predict = lambda roi: (0, 100)  # Dummy prediction
        print("⚠️ Using fallback recognizer (sklearn)")
except Exception as e:
    print(f"⚠️ Error loading recognizer: {e}")
    recognizer = None

recognizer_path = 'trainer/trainer.yml'
if recognizer and os.path.exists(recognizer_path):
    try:
        recognizer.read(recognizer_path)
    except:
        print("⚠️ Could not load trainer.yml")

face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

eye_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)

# -------- LABELS & STUDENTS --------
names = {}
students = {}

def load_data():
    global names, students
    names = {}
    students = {}
    
    if os.path.exists('trainer/labels.txt'):
        with open('trainer/labels.txt') as f:
            for line in f:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    id_, name = parts
                    names[int(id_)] = name
    
    if os.path.exists('students.csv'):
        with open('students.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                students[row['Name']] = row['Roll']

load_data()

attendance_marked = set()  # Today's marked attendance
attendance_status = {}  # Track status: "first_time" or "already_marked"
last_unknown_record_time = 0  # Timestamp of last unknown person recording
attendance_timestamps = {}  # Track when each person was marked (for 24-hour prevention)
cam = None  # Lazy initialization - will be created when needed
eyes_closed_start = None
current_frame = None
frame_lock = threading.Lock()
camera_lock = threading.Lock()  # Prevent concurrent camera access

# -------- SOUND ALERT TRACKING --------
alert_cooldown = {}  # Track last alert time per behavior type
ALERT_COOLDOWN_SECONDS = 3  # Only alert every 3 seconds for same behavior
sleeping_start_time = {}  # Track when each face started sleeping
SLEEP_ALERT_THRESHOLD = 10  # Alert after 10 seconds of sleeping

# -------- ATTENDANCE TRACKING --------
attendance_records = []

# -------- CAMERA MANAGEMENT --------
def get_camera():
    """Get or initialize camera with error handling"""
    global cam
    
    # Even if cam exists, validate it's still working
    if cam is not None:
        try:
            with camera_lock:
                ret, test_frame = cam.read()
            if ret and test_frame is not None:
                print("✅ Camera already initialized and working")
                return cam
            else:
                print("⚠️ Camera exists but not responding, reinitializing...")
                cam.release()
                cam = None
        except:
            print("⚠️ Camera exists but failed validation, reinitializing...")
            if cam is not None:
                try:
                    cam.release()
                except:
                    pass
            cam = None
    
    try:
        # Try to initialize camera with retry logic
        for attempt in range(3):
            try:
                cam = cv2.VideoCapture(0)
                # Set camera properties for better reliability
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cam.set(cv2.CAP_PROP_FPS, 30)
                
                # Give camera time to initialize
                time.sleep(0.5)
                
                # Test if camera is working
                ret, test_frame = cam.read()
                if ret and test_frame is not None:
                    print(f"✅ Camera initialized successfully (attempt {attempt + 1})")
                    return cam
                else:
                    if cam is not None:
                        cam.release()
                    cam = None
                    time.sleep(0.5)  # Wait before retry
                    if attempt < 2:
                        print(f"⚠️ Camera test failed, retrying... (attempt {attempt + 1}/3)")
            except Exception as inner_e:
                print(f"❌ Camera init attempt {attempt + 1} failed: {inner_e}")
                if cam is not None:
                    cam.release()
                cam = None
                time.sleep(1)
        
        raise Exception("Camera initialization failed after 3 attempts")
    except Exception as e:
        print(f"❌ Failed to initialize camera: {e}")
        cam = None
        raise Exception(f"Camera initialization failed: {e}")

def release_camera():
    """Safely release camera resources"""
    global cam
    if cam is not None:
        try:
            cam.release()
            print("✅ Camera released")
        except:
            pass
        finally:
            cam = None

def mark_attendance(name, confidence=0, behavior="Active"):
    """Mark attendance with behavior tracking and 24-hour prevention"""
    global attendance_records, attendance_timestamps, attendance_status
    
    if name == "Unknown":
        return
    
    # Only mark if person is registered
    if name not in students:
        print(f"⚠️ {name} not registered. Skipping attendance.")
        return
    
    if name in attendance_marked:
        # Already marked today
        attendance_status[name] = "already_marked"
        return
    
    # Check if person was marked in last 24 hours
    current_time = datetime.now()
    if name in attendance_timestamps:
        last_marked_time = attendance_timestamps[name]
        time_diff = (current_time - last_marked_time).total_seconds()
        if time_diff < 86400:  # 86400 seconds = 24 hours
            print(f"⏱️ {name} already marked today. Cannot mark again for {int(86400 - time_diff)} seconds.")
            attendance_status[name] = "already_marked"
            return

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    roll = students.get(name, "N/A")
    status = "Present"

    record = {
        "timestamp": now,
        "name": name,
        "roll": roll,
        "status": status,
        "behavior": behavior,
        "confidence": round(confidence, 2)
    }
    
    attendance_records.append(record)
    
    file_exists = os.path.exists('attendance.csv')
    with open('attendance.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Name", "Roll", "Status", "Behavior", "Confidence"])
        writer.writerow([now, name, roll, status, behavior, confidence])

    attendance_marked.add(name)
    attendance_status[name] = "first_time"  # Mark as first time marking
    attendance_timestamps[name] = current_time  # Record timestamp for 24-hour check
    print(f"✅ Attendance marked: {name} (Confidence: {confidence:.2f}%)")

def record_unknown_person(confidence=0, behavior="Unknown", frame=None):
    """Log unknown persons with proper alerts and image saving"""
    global last_unknown_record_time
    
    current_time = time.time()
    
    # Only log every 3 seconds (not every frame)
    if current_time - last_unknown_record_time < 3:
        return
    
    last_unknown_record_time = current_time
    
    # Create unknown persons directory
    unknown_dir = 'alerts/unknown_persons'
    os.makedirs(unknown_dir, exist_ok=True)
    
    # Save unknown face image for review
    if frame is not None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{unknown_dir}/unknown_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"🚨 UNKNOWN PERSON DETECTED!")
            print(f"   ⚠️  Confidence: {confidence:.2f}%")
            print(f"   📸 Image saved: {filename}")
            print(f"   ℹ️  This person needs to be registered first")
            print(f"   📋 Go to: http://localhost:5000/register")
        except Exception as e:
            print(f"❌ Error saving unknown image: {e}")
    else:
        print(f"🚨 UNKNOWN PERSON DETECTED (Confidence: {confidence:.2f}%)")
        print(f"   ℹ️  Person not in registered database")
        print(f"   📋 Registration required at: http://localhost:5000/register")

# -------- BEHAVIOR ANALYSIS --------
def analyze_behavior(face_roi, eyes):
    """Analyze person's behavior based on eyes and motion - IMPROVED"""
    if len(eyes) == 0:
        return "Sleeping"
    elif len(eyes) >= 2:
        return "Active"
    elif len(eyes) == 1:
        return "Idle"
    else:
        return "Active"  # Default to active

# -------- SOUND ALERT --------
def play_alert(behavior_type, face_id=None):
    """Play alert sound in a separate thread without blocking video processing - DISABLED"""
    # ALERT SOUNDS ARE DISABLED
    return

# -------- FACE REGISTRATION --------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        # Get list of registered students for display
        registered = list(students.keys())
        return render_template('register_advanced.html', registered=registered)
    
    data = request.json
    name = data.get('name', '').strip()
    roll = data.get('roll', '').strip()
    faces = data.get('faces', [])

    if not name or not roll or len(faces) < 1:
        return jsonify({
            "success": False,
            "message": "Invalid data. Need name, roll, and at least 1 face image."
        })
    
    # Check if user already registered
    if name in students:
        return jsonify({
            "success": False,
            "message": f"User {name} is already registered. Delete first if you want to re-register."
        })

    # Create dataset directory if not exists
    dataset_dir = 'dataset'
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)

    # Save face images
    face_id = len(names)
    saved_count = 0
    
    for idx, face_data in enumerate(faces):
        try:
            # Handle base64 decoding with better error handling
            if not face_data:
                print(f"Empty face data at index {idx}")
                continue
            
            # Split on comma to get actual base64 data
            if ',' in face_data:
                img_str = face_data.split(',')[1]
            else:
                img_str = face_data
            
            # Decode base64
            try:
                img_bytes = base64.b64decode(img_str)
            except Exception as decode_err:
                print(f"Base64 decode error for face {idx}: {decode_err}")
                continue
            
            # Open and save image
            try:
                img = Image.open(io.BytesIO(img_bytes))
                
                # Convert to RGB if necessary (in case it's RGBA)
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                filename = f"{dataset_dir}/{name}_{face_id}_{idx}.jpg"
                img.save(filename, 'JPEG', quality=95)
                saved_count += 1
                print(f"✅ Saved face {idx+1} for {name}")
            except Exception as img_err:
                print(f"Image processing error for face {idx}: {img_err}")
                continue
                
        except Exception as e:
            print(f"Error saving face {idx}: {e}")

    if saved_count < 1:
        print(f"Failed to save any faces for {name}. Faces: {len(faces)}")
        return jsonify({
            "success": False,
            "message": f"Failed to save faces. Saved: {saved_count}/{len(faces)}. Check server logs for details."
        })

    # Update labels
    names[face_id] = name
    with open('trainer/labels.txt', 'a') as f:
        f.write(f"{face_id},{name}\n")

    # Update students - ensure roll number is valid
    roll_str = str(roll).strip()
    if not roll_str:
        return jsonify({
            "success": False,
            "message": "Invalid roll number"
        })
    
    if name not in students:
        students[name] = roll_str
        file_exists = os.path.exists('students.csv')
        with open('students.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Name", "Roll"])
            writer.writerow([name, roll_str])
        print(f"✅ Added {name} to students.csv")

    # Auto-train the model
    try:
        train_success = train_model_internal()
        if train_success:
            print(f"✅ Model trained successfully for {name}")
            load_data()  # Reload model and labels
        else:
            print(f"⚠️ Model training returned false")
    except Exception as e:
        print(f"Auto-training error: {e}")
        return jsonify({
            "success": False,
            "message": f"Faces saved but model training failed: {e}"
        })
    
    # Auto-mark attendance after successful registration
    try:
        mark_attendance(name, confidence=95, behavior="Active")
        attendance_marked_msg = " and marked attendance"
    except Exception as e:
        print(f"Warning: Could not mark attendance for {name}: {e}")
        attendance_marked_msg = ""

    return jsonify({
        "success": True,
        "message": f"✅ {name} registered successfully! Saved {saved_count} sample(s), trained model{attendance_marked_msg}.",
        "face_id": face_id,
        "name": name,
        "auto_marked": True,
        "faces_saved": saved_count
    })

# -------- TRAIN MODEL --------
def train_model_internal():
    """Internal function to train the model"""
    dataset_path = 'dataset'
    trainer_path = 'trainer'

    if not os.path.exists(trainer_path):
        os.makedirs(trainer_path)

    face_samples = []
    ids = []
    current_id = 0

    image_files = [f for f in os.listdir(dataset_path) if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    if not image_files:
        return False

    for filename in image_files:
        try:
            filepath = os.path.join(dataset_path, filename)
            img = Image.open(filepath).convert('L')
            img_np = np.array(img, 'uint8')

            name = filename.split('_')[0]

            # Get ID from current names or assign new one
            id_ = None
            for existing_id, existing_name in names.items():
                if existing_name == name:
                    id_ = existing_id
                    break
            
            if id_ is None:
                id_ = len(names)
                names[id_] = name

            faces = face_detector.detectMultiScale(img_np)

            for (x, y, w, h) in faces:
                        # Normalize face size so training arrays are homogeneous
                        face_img = img_np[y:y+h, x:x+w]
                        try:
                            face_resized = cv2.resize(face_img, (200, 200))
                        except Exception:
                            # Skip faces that cannot be resized
                            continue
                        face_samples.append(face_resized)
                ids.append(id_)
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    if face_samples:
        recognizer.train(face_samples, np.array(ids))
        recognizer.write(f"{trainer_path}/trainer.yml")
        return True
    
    return False

# -------- API REGISTER (for FormData from camera/upload) --------
@app.route('/api/register', methods=['POST'])
def api_register():
    """Register user with camera or uploaded images"""
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        method = request.form.get('method', 'unknown')
        
        # For API, use name as roll number (can be email or phone)
        roll = email if email else (phone if phone else name)
        
        if not name or not roll:
            return jsonify({
                "success": False,
                "message": "Name and at least email or phone required"
            }), 400

        # Check if user already registered
        if name in students:
            return jsonify({
                "success": False,
                "message": f"User {name} is already registered. Delete first if you want to re-register."
            }), 400

        # Create dataset directory if not exists
        dataset_dir = 'dataset'
        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir)

        # Get uploaded files
        files = request.files
        images = []
        for key in files:
            if key.startswith('image_'):
                images.append(files[key])

        if len(images) < 1:
            return jsonify({
                "success": False,
                "message": "No images provided"
            }), 400

        # Save images
        face_id = len(names)
        saved_count = 0
        
        for idx, file in enumerate(images):
            try:
                img = Image.open(file.stream)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                filename = f"{dataset_dir}/{name}_{face_id}_{idx}.jpg"
                img.save(filename, 'JPEG', quality=95)
                saved_count += 1
                print(f"✅ Saved face {idx+1} for {name}")
            except Exception as img_err:
                print(f"Image processing error for face {idx}: {img_err}")
                continue

        if saved_count < 1:
            return jsonify({
                "success": False,
                "message": f"Failed to save any faces. Saved: {saved_count}/{len(images)}"
            }), 400

        # Update labels
        names[face_id] = name
        if not os.path.exists('trainer'):
            os.makedirs('trainer')
        
        with open('trainer/labels.txt', 'a') as f:
            f.write(f"{face_id},{name}\n")

        # Update students
        if name not in students:
            students[name] = roll
            file_exists = os.path.exists('students.csv')
            with open('students.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Name", "Roll"])
                writer.writerow([name, roll])
            print(f"✅ Added {name} to students.csv")

        # Auto-train the model
        try:
            train_success = train_model_internal()
            if train_success:
                print(f"✅ Model trained successfully for {name}")
                load_data()
            else:
                print(f"⚠️ Model training returned false")
        except Exception as e:
            print(f"Auto-training error: {e}")
            return jsonify({
                "success": False,
                "message": f"Faces saved but model training failed: {e}"
            }), 500

        # Auto-mark attendance
        try:
            mark_attendance(name, confidence=95, behavior="Active")
            attendance_marked_msg = " and marked attendance"
        except Exception as e:
            print(f"Warning: Could not mark attendance for {name}: {e}")
            attendance_marked_msg = ""

        return jsonify({
            "success": True,
            "message": f"✅ {name} registered successfully! Saved {saved_count} sample(s), trained model{attendance_marked_msg}.",
            "face_id": face_id,
            "name": name,
            "auto_marked": True,
            "faces_saved": saved_count
        })

    except Exception as e:
        print(f"❌ API Register error: {e}")
        return jsonify({
            "success": False,
            "message": f"Registration error: {str(e)}"
        }), 500

@app.route('/train', methods=['POST'])
def train():
    """Train or retrain the face recognition model"""
    try:
        if train_model_internal():
            load_data()
            print("✅ Model trained and reloaded")
            return jsonify({"success": True, "message": "✅ Model trained successfully"})
        else:
            return jsonify({"success": False, "message": "No training images found"})
    except Exception as e:
        print(f"❌ Training error: {e}")
        return jsonify({"success": False, "message": str(e)})

# -------- VIDEO STREAM --------
def generate_frames():
    global eyes_closed_start, current_frame
    last_train_time = time.time()
    frame_count = 0
    camera = None
    
    try:
        camera = get_camera()
    except Exception as e:
        print(f"❌ Cannot access camera: {e}")
        # Send error frame
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camera Error", (150, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        cv2.putText(error_frame, "Already in use by another app", (50, 270),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(error_frame, "Close other apps or restart", (60, 320),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        _, buffer = cv2.imencode('.jpg', error_frame)
        for _ in range(300):  # Send error frame for longer duration
            try:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except:
                break
        return

    try:
        while True:
            try:
                with camera_lock:
                    ret, frame = camera.read()
                if not ret:
                    print("⚠️ Camera read failed, attempting recovery...")
                    release_camera()
                    try:
                        camera = get_camera()
                        continue
                    except:
                        break

                frame = cv2.resize(frame, (640, 480))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Improved face detection parameters for better reliability
                faces = face_detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(30, 30), maxSize=(500, 500))

                current_detected = set()

                for (x, y, w, h) in faces:
                    roi = gray[y:y+h, x:x+w]
                    
                    try:
                        id_, conf = recognizer.predict(roi)
                        confidence = 100 - conf
                        
                        # IMPROVED RECOGNITION: conf < 50 (>50% confidence) AND id_ must exist
                        # Relaxed threshold for better detection of registered faces
                        if conf < 50 and id_ in names:
                            name = names[id_]
                            color = (0, 255, 0)  # Green for known
                            mark_attendance(name, confidence, "Active")
                            status = f"✅ RECOGNIZED ({confidence:.0f}%)"
                        else:
                            # UNKNOWN PERSON - conf >= 50 OR id not in names
                            name = "❌ UNKNOWN PERSON"
                            color = (0, 0, 255)  # Red for unknown
                            record_unknown_person(confidence if conf >= 50 else 0, "Unknown", frame)
                            status = f"🚨 NOT REGISTERED (Conf: {confidence:.0f}%)"
                    except Exception as e:
                        name = "❌ UNKNOWN PERSON"
                        color = (0, 0, 255)
                        record_unknown_person(0, "Unknown", frame)
                        status = "🚨 DETECTION ERROR"

                    # Detect eyes for behavior
                    eyes = eye_detector.detectMultiScale(roi)
                    behavior = analyze_behavior(roi, eyes)
                    
                    # RESET SLEEP TIMER if not sleeping
                    if behavior != "Sleeping" and id_ in sleeping_start_time:
                        del sleeping_start_time[id_]
                    
                    # Display behavior status (no alert triggered)
                    behavior_color = (0, 255, 0) if behavior == "Active" else (0, 165, 255) if behavior == "Idle" else (0, 0, 255)
                    
                    # DRAW BOUNDING BOX - Thicker for unknown
                    box_thickness = 4 if "UNKNOWN" in name else 2
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, box_thickness)
                    
                    # Draw background for text (better visibility)
                    label_text = name
                    text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                    cv2.rectangle(frame, (x, y-40), (x + text_size[0] + 10, y), color, -1)
                    
                    # Draw labels
                    cv2.putText(frame, label_text, (x+5, y-15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame, status, (x, y+h+25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    # Draw behavior status
                    cv2.putText(frame, f"Status: {behavior}", (x, y+h+50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, behavior_color, 2)
                    
                    # Draw "REGISTER FIRST" message for unknown
                    if "UNKNOWN" in name:
                        cv2.putText(frame, "👉 REGISTER FIRST", (x, y+h+75),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    current_detected.add(name)

                # Add stats on frame
                cv2.putText(frame, f"Present: {len(attendance_marked)}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Total Registered: {len(students)}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Check for unknown persons and show alert
                unknown_found = any("UNKNOWN" in str(person) for person in current_detected)
                if unknown_found:
                    # Draw alert banner
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 80), (0, 0, 255), -1)
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 80), (0, 255, 255), 3)
                    
                    # Draw alert text
                    cv2.putText(frame, "🚨 UNKNOWN PERSON DETECTED!", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                    cv2.putText(frame, "Please register the person first at: http://localhost:5000/register", (20, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                with frame_lock:
                    current_frame = frame.copy()

                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

                frame_count += 1
            except Exception as e:
                print(f"Frame processing error: {e}")
                break
    finally:
        # CRITICAL: Always release camera when stream ends
        print("🔚 Video stream ended, releasing camera...")
        release_camera()

# -------- ROUTES --------
@app.route('/')
def index():
    return render_template('index_premium.html')

@app.route('/history')
def history():
    return render_template('history_premium.html')

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stats')
def stats():
    """Get attendance statistics"""
    total = len(students)
    present = len(attendance_marked)  # Only registered students marked
    
    # Get unique registered persons who attended
    registered_attended = set()
    for record in attendance_records:
        if record.get('status') == 'Present':
            registered_attended.add(record.get('name'))
    
    return jsonify({
        "total": total,
        "present": len(registered_attended),  # Count of registered persons who attended
        "absent": total - len(registered_attended),
        "records": len(attendance_records)  # Only registered person records
    })

@app.route('/api/attendance')
def get_attendance():
    """Get attendance records with status indicators"""
    # Add status color to each record based on attendance_status
    records_with_status = []
    for record in attendance_records:
        record_copy = record.copy()
        name = record.get('name', '')
        
        if name in attendance_status:
            status = attendance_status[name]
            if status == "first_time":
                record_copy['status_color'] = 'green'  # Just marked
            elif status == "already_marked":
                record_copy['status_color'] = 'blue'   # Already marked today
        elif name == 'Unknown':
            record_copy['status_color'] = 'red'        # Unregistered
        
        records_with_status.append(record_copy)
    
    return jsonify({"attendance": records_with_status})

@app.route('/api/reset', methods=['POST'])
def reset_attendance():
    """Reset attendance for new school day"""
    global attendance_marked, attendance_records, last_unknown_record_time, attendance_timestamps, attendance_status
    
    try:
        attendance_marked.clear()
        attendance_records.clear()
        attendance_timestamps.clear()  # Clear 24-hour tracking
        attendance_status.clear()  # Clear status tracking
        last_unknown_record_time = 0  # Reset unknown person recording timer
        
        print("✅ Attendance reset for new day")
        return jsonify({"success": True, "message": "✅ Attendance reset successfully for new day"})
    except Exception as e:
        print(f"❌ Reset error: {e}")
        return jsonify({"success": False, "message": f"Reset failed: {e}"})

@app.route('/api/delete-user/<name>', methods=['POST'])
def delete_user(name):
    """Delete a registered user and their data"""
    global students, names, attendance_records
    
    try:
        # Remove from students
        if name in students:
            del students[name]
        
        # Remove from labels
        if os.path.exists('trainer/labels.txt'):
            with open('trainer/labels.txt', 'r') as f:
                lines = f.readlines()
            
            with open('trainer/labels.txt', 'w') as f:
                for line in lines:
                    if not line.startswith(f"*,{name}" ) and f",{name}" not in line:
                        f.write(line)
        
        # Remove from attendance records
        attendance_records = [r for r in attendance_records if r.get('name') != name]
        
        # Delete dataset files
        dataset_dir = 'dataset'
        if os.path.exists(dataset_dir):
            for filename in os.listdir(dataset_dir):
                if filename.startswith(f"{name}_"):
                    try:
                        os.remove(os.path.join(dataset_dir, filename))
                    except:
                        pass
        
        # Retrain model
        try:
            train_model_internal()
            load_data()
        except:
            pass
        
        print(f"✅ User {name} deleted successfully")
        return jsonify({"success": True, "message": f"User {name} and all data deleted successfully"})
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return jsonify({"success": False, "message": f"Delete failed: {e}"})

# -------- BEHAVIORAL ALERTS --------
behavioral_alerts = []
system_settings = {
    "alertSound": False,
    "drowsiness": True,
    "sleep": True,
    "vibration": False,
    "unknownAlert": True,
    "reportTime": "16:00",
    "emailRecipients": [],
    "phoneRecipients": [],
    "drowsinessThreshold": 70,
    "sleepThreshold": 85,
    "alertDuration": 3,
    "vibrationDuration": 3
}

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Get or update system settings"""
    global system_settings
    
    if request.method == 'GET':
        return jsonify(system_settings)
    
    try:
        data = request.json
        # Update settings from request
        for key, value in data.items():
            if key in system_settings:
                system_settings[key] = value
        
        # Save settings to file
        try:
            with open('settings.json', 'w') as f:
                json.dump(system_settings, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save settings to file: {e}")
        
        print(f"✅ Settings updated")
        return jsonify({"success": True, "message": "Settings updated successfully", "settings": system_settings})
    except Exception as e:
        print(f"❌ Settings error: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/behavioral_alerts', methods=['GET', 'POST'])
def manage_behavioral_alerts():
    """Get or add behavioral alerts"""
    global behavioral_alerts
    
    if request.method == 'GET':
        # Filter by query parameters
        person = request.args.get('person', None)
        alert_type = request.args.get('type', None)
        date_filter = request.args.get('date', None)
        
        filtered_alerts = behavioral_alerts.copy()
        
        if person:
            filtered_alerts = [a for a in filtered_alerts if person.lower() in a.get('person', '').lower()]
        
        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.get('type') == alert_type]
        
        if date_filter:
            filtered_alerts = [a for a in filtered_alerts if date_filter in a.get('timestamp', '')]
        
        # Return paginated results (recent first)
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated = filtered_alerts[::-1][start:end]
        
        return jsonify({
            "total": len(filtered_alerts),
            "page": page,
            "per_page": per_page,
            "alerts": paginated
        })
    
    try:
        data = request.json
        
        # Create new behavioral alert
        alert = {
            "id": len(behavioral_alerts) + 1,
            "person": data.get('person', 'Unknown'),
            "type": data.get('type', 'Unknown'),  # drowsiness, sleep, yawn, headpose, emotion
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "duration": data.get('duration', 0),
            "soundSent": data.get('soundSent', False),
            "details": data.get('details', {}),
            "confidence": data.get('confidence', 0)
        }
        
        behavioral_alerts.append(alert)
        
        # Limit stored alerts to last 1000 to prevent memory bloat
        if len(behavioral_alerts) > 1000:
            behavioral_alerts = behavioral_alerts[-1000:]
        
        print(f"📊 Behavioral alert recorded: {alert['person']} - {alert['type']}")
        return jsonify({"success": True, "message": "Alert recorded", "alert": alert})
    except Exception as e:
        print(f"❌ Alert recording error: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/behavioral_stats', methods=['GET'])
def get_behavioral_stats():
    """Get behavioral alert statistics"""
    try:
        total_alerts = len(behavioral_alerts)
        alert_types = {}
        people_counts = {}
        
        for alert in behavioral_alerts:
            alert_type = alert.get('type', 'Unknown')
            person = alert.get('person', 'Unknown')
            
            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            people_counts[person] = people_counts.get(person, 0) + 1
        
        return jsonify({
            "total": total_alerts,
            "by_type": alert_types,
            "by_person": people_counts,
            "drowsy_alerts": alert_types.get('drowsiness', 0),
            "sleeping_alerts": alert_types.get('sleep', 0),
            "yawn_alerts": alert_types.get('yawn', 0)
        })
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/video_feed')
def video_feed():
    """Video feed endpoint alias"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def load_settings():
    """Load settings from file if it exists"""
    global system_settings
    try:
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                saved_settings = json.load(f)
                system_settings.update(saved_settings)
            print("✅ Settings loaded from file")
    except Exception as e:
        print(f"⚠️ Could not load settings from file: {e}")

# Load settings on startup
load_settings()

def shutdown_handler():
    """Handle graceful shutdown"""
    print("\n🛑 Shutting down...")
    release_camera()
    print("✅ Cleanup complete")

if __name__ == "__main__":
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        shutdown_handler()
    finally:
        shutdown_handler()