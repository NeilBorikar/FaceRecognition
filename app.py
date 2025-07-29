from flask import Flask, render_template, Response, jsonify, g, request,redirect,url_for,flash
import cv2
import numpy as np
from attendance_system import load_known_faces, mark_attendance
from database import FaceDatabase
import threading
import face_recognition
import logging
from datetime import datetime, timedelta
from functools import lru_cache
import time
from logging.handlers import RotatingFileHandler
import sqlite3


# Initialize Flask app
app = Flask(__name__)
app.config.update({
    'VIDEO_SOURCE': 0,
    'FACE_RECOGNITION_THRESHOLD': 0.6,
    'CACHE_TIMEOUT_MINUTES': 5,
    'FRAME_SKIP_RATE': 2 , # Process every 2nd frame
    'SECRET_KEY': 'your_secret_key_here'
})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Global variables with thread safety
current_frame = None
processing_lock = threading.Lock()
last_cache_clear = datetime.now()

# Database connection management
def get_db():
    if 'db' not in g:
        g.db = FaceDatabase()
        try:
            g.db._create_tables()
        except Exception as e:
            app.logger.error(f"Table creation failed: {str(e)}")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Face caching with automatic refresh
@lru_cache(maxsize=1)
def get_cached_known_faces():
    logging.info("Loading known faces from database")
    return load_known_faces()

def clear_face_cache():
    global last_cache_clear
    now = datetime.now()
    if now - last_cache_clear > timedelta(minutes=app.config['CACHE_TIMEOUT_MINUTES']):
        get_cached_known_faces.cache_clear()
        last_cache_clear = now
        logging.info("Cleared face recognition cache")

# Video feed generator
def generate_frames():
    # Initialize camera with error handling
    global current_frame
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Could not open camera")
    except Exception as e:
        logging.error(f"Camera initialization failed: {str(e)}")
        return
    
    frame_counter = 0
    
    try:
        while True:
            success, frame = cap.read()
            frame_counter += 1
            
            if not success:
                logging.warning("Frame capture failed")
                break
                
            # Skip frames for performance
            if frame_counter % app.config['FRAME_SKIP_RATE'] != 0:
                continue
                
            # Process frame
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Face detection
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            with processing_lock:
                current_frame = frame.copy()
                known_encodings, known_names, user_ids = get_cached_known_faces()
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # Face recognition
                    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    confidence = 1 - face_distances[best_match_index]
                    
                    if confidence > app.config['FACE_RECOGNITION_THRESHOLD']:
                        name = known_names[best_match_index]
                        user_id = user_ids[best_match_index]
                        
                        # Scale coordinates back to original size
                        top *= 4; right *= 4; bottom *= 4; left *= 4
                        
                        # Draw bounding box and label
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(
                            frame, 
                            f"{name} ({confidence:.2f})", 
                            (left + 6, bottom - 6), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.5, 
                            (255, 255, 255), 
                            1
                        )
            
            # Yield frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    finally:
        cap.release()
        logging.info("Camera resource released")

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    clear_face_cache()  # Periodic cache maintenance
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
@app.route('/mark_attendance')
def mark_attendance_endpoint():
    try:
        clear_face_cache()
        
        with processing_lock:
            # Check camera frame
            if current_frame is None:
                app.logger.error("No frame available for attendance marking")
                return jsonify({
                    "status": "error", 
                    "message": "Camera feed not available"
                }), 400
                
            # Process frame
            small_frame = cv2.resize(current_frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_small_frame)
            
            if not face_encodings:
                app.logger.warning("No faces detected in frame")
                return jsonify({
                    "status": "error", 
                    "message": "No face detected - please face the camera"
                }), 400
                
            # Get known faces with validation
            known_encodings, known_names, user_ids = get_cached_known_faces()
            if not known_encodings:
                app.logger.error("No registered faces in database")
                return jsonify({
                    "status": "error",
                    "message": "System has no registered users"
                }), 400
                
            # Calculate face distances
            face_distances = face_recognition.face_distance(known_encodings, face_encodings[0])
            if len(face_distances) == 0:
                app.logger.error("Face distance calculation failed")
                return jsonify({
                    "status": "error",
                    "message": "Recognition system error"
                }), 500
                
            best_match_index = np.argmin(face_distances)
            confidence = 1 - face_distances[best_match_index]
            
            if confidence > app.config['FACE_RECOGNITION_THRESHOLD']:
                name = known_names[best_match_index]
                user_id = user_ids[best_match_index]
                
                try:
                    db = get_db()
                    success = mark_attendance(user_id, name)
                    current_time = datetime.now().strftime("%H:%M:%S")
                    
                    if success:
                        app.logger.info(f"Attendance marked for {name}")
                        return jsonify({
                            "status": "success",
                            "name": name,
                            "time": current_time,
                            "confidence": round(confidence, 2)
                        })
                    else:
                        app.logger.info(f"Duplicate attendance for {name}")
                        return jsonify({
                            "status": "info",
                            "message": f"{name} already marked today",
                            "time": current_time
                        })
                        
                except Exception as e:
                    app.logger.error(f"Database error: {str(e)}")
                    return jsonify({
                        "status": "error",
                        "message": "Database operation failed"
                    }), 500
                    
            return jsonify({
                "status": "error", 
                "message": "Recognition confidence too low"
            }), 400
            
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/users')
def view_users():
    try:
        db = get_db()
        users = db.conn.execute('SELECT * FROM users').fetchall()
        return render_template('users.html', users=users)
    except Exception as e:
        logging.error(f"Failed to fetch users: {str(e)}")
        return "Error loading user list", 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            email = request.form.get('email')
            
            # Get uploaded image
            if 'image' not in request.files:
                return "No image uploaded", 400
                
            image = request.files['image']
            if image.filename == '':
                return "No selected image", 400
                
            # Process image
            img = face_recognition.load_image_file(image)
            encodings = face_recognition.face_encodings(img)
            
            if not encodings:
                return "No face found in image", 400
                
            # Save to database
            db = get_db()
            user_id = db.add_user(name, email)
            db.add_face_encoding(user_id, encodings[0])
            
            return redirect(url_for('index'))
            
        except Exception as e:
            return f"Registration failed: {str(e)}", 500
            
    return render_template('register.html')

@app.route('/attendance')
def view_attendance():
    try:
        db = get_db()
        
        # Get filter parameters with defaults
        filter_type = request.args.get('filter_type', 'single')
        date = request.args.get('date')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Base query
        query = '''
            SELECT u.name, a.timestamp 
            FROM attendance_records a
            JOIN users u ON a.user_id = u.user_id
        '''
        params = []
        
        # Apply filters
        if filter_type == 'single' and date:
            query += ' WHERE DATE(a.timestamp) = ?'
            params.append(date)
        elif filter_type == 'range' and start_date and end_date:
            query += ' WHERE DATE(a.timestamp) BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        
        query += ' ORDER BY a.timestamp DESC'
        
        # Execute query
        cursor = db.conn.cursor()
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # Format results
        formatted_records = []
        for name, timestamp in records:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') if isinstance(timestamp, str) else timestamp
            formatted_records.append({
                'name': name,
                'timestamp': dt,
                'formatted_time': dt.strftime('%Y-%m-%d %H:%M')
            })
        
        return render_template(
            'attendance.html',
            records=formatted_records,
            filter_type=filter_type,
            date=date,
            start_date=start_date,
            end_date=end_date
        )
        
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {str(e)}")
        flash('Database error occurred', 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        flash('An unexpected error occurred', 'danger')
        return redirect(url_for('index'))

# Entry point
if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True, 
        threaded=True,
        use_reloader=False
    )