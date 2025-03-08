from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import os
import base64
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
import pickle
import json
import time
import datetime
from firebase_config import (
    create_user, sign_in_with_email_password, get_user_by_email,
    upload_file_to_storage, save_face_encoding, get_all_face_encodings,
    save_attendance_record, get_attendance_records, FIREBASE_AVAILABLE
)

app = Flask(__name__)
app.secret_key = 'minimal_app_secret_key'  # Change this to a random secret key

# Create directories for face data if they don't exist
os.makedirs('static/face_data', exist_ok=True)
os.makedirs('static/face_encodings', exist_ok=True)

# Mock user data
users = {
    'admin@example.com': {'password': 'admin123', 'role': 'admin', 'name': 'Admin User'},
    'student@example.com': {'password': 'student123', 'role': 'student', 'name': 'Student User'}
}

# Mock course data
courses = [
    {'id': '1', 'name': 'Computer Science'},
    {'id': '2', 'name': 'Mathematics'},
    {'id': '3', 'name': 'Physics'}
]

# Mock student data
students = [
    {'id': '1', 'name': 'John Doe', 'email': 'john@example.com', 'has_face_data': True},
    {'id': '2', 'name': 'Jane Smith', 'email': 'jane@example.com', 'has_face_data': False},
    {'id': '3', 'name': 'Bob Johnson', 'email': 'bob@example.com', 'has_face_data': True}
]

# Mock attendance data
attendance_records = [
    {'id': '1', 'course': 'Computer Science', 'date': '2023-09-01 09:00', 'method': 'face_recognition', 'student_name': 'John Doe'},
    {'id': '2', 'course': 'Mathematics', 'date': '2023-09-02 10:30', 'method': 'qr_code', 'student_name': 'Jane Smith'},
    {'id': '3', 'course': 'Physics', 'date': '2023-09-03 14:15', 'method': 'face_recognition', 'student_name': 'Bob Johnson'},
    {'id': '4', 'course': 'Computer Science', 'date': '2023-09-04 09:00', 'method': 'qr_code', 'student_name': 'John Doe'},
    {'id': '5', 'course': 'Mathematics', 'date': '2023-09-05 10:30', 'method': 'face_recognition', 'student_name': 'Jane Smith'}
]

# Face encodings dictionary - will be loaded from Firebase
face_encodings = {}

# Helper functions
def is_logged_in():
    return 'user_email' in session

def get_current_user():
    if is_logged_in():
        email = session['user_email']
        if email in users:
            user = users[email].copy()
            user['email'] = email
            return user
    return None

def login_required(view):
    def wrapped_view(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__
    return wrapped_view

# Global variables for video streaming
camera = None
output_frame = None
lock = None
face_cascade = None

def initialize_video():
    global camera, lock, face_cascade
    import threading
    camera = cv2.VideoCapture(0)
    lock = threading.Lock()
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def detect_faces_in_frame(frame):
    global face_cascade, face_encodings
    
    # Load face encodings from Firebase if not already loaded
    if not face_encodings:
        face_encodings = get_all_face_encodings()
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    # Process each face
    for (x, y, w, h) in faces:
        # Extract face region
        face_img = frame[y:y+h, x:x+w]
        
        # Skip if face is too small
        if w < 50 or h < 50:
            continue
            
        try:
            # Resize for consistent encoding
            face_img_resized = cv2.resize(face_img, (128, 128))
            
            # Create encoding
            current_encoding = face_img_resized.flatten()
            
            # Compare with stored encodings
            best_match = None
            best_score = float('inf')
            
            for student_id, data in face_encodings.items():
                stored_encoding = np.array(data['encoding'])
                
                # Calculate Euclidean distance (lower is better)
                score = np.linalg.norm(current_encoding - stored_encoding)
                
                # Set a threshold for matching
                if score < best_score and score < 20000:  # Threshold may need adjustment
                    best_score = score
                    best_match = data['name']
            
            # Draw rectangle and name
            if best_match:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, best_match, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "Unknown", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        
        except Exception as e:
            print(f"Error processing face: {str(e)}")
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
    
    return frame

def generate_frames():
    global camera, output_frame, lock
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Process the frame
            with lock:
                output_frame = detect_faces_in_frame(frame.copy())
                
                # Encode the frame
                ret, buffer = cv2.imencode('.jpg', output_frame)
                frame = buffer.tobytes()
            
            # Yield the frame in the response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Add a small delay
        time.sleep(0.03)

@app.route('/')
def index():
    return render_template('index.html', firebase_available=FIREBASE_AVAILABLE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email in users and users[email]['password'] == password:
            session['user_email'] = email
            session['user_role'] = users[email]['role']
            
            if users[email]['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html', firebase_available=FIREBASE_AVAILABLE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role', 'student')
        
        if email in users:
            flash('Email already registered')
        else:
            users[email] = {'password': password, 'role': role, 'name': name}
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
    
    return render_template('register.html', firebase_available=FIREBASE_AVAILABLE)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    return render_template('admin_dashboard.html', firebase_available=FIREBASE_AVAILABLE)

@app.route('/admin/students')
@login_required
def admin_students():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    return render_template('admin_students.html', students=students, firebase_available=FIREBASE_AVAILABLE)

@app.route('/admin/add-student', methods=['GET', 'POST'])
@login_required
def admin_add_student():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        for student in students:
            if student['email'] == email:
                flash('A student with this email already exists')
                return render_template('admin_add_student.html', courses=courses, firebase_available=FIREBASE_AVAILABLE)
        
        # Add new student
        new_id = str(len(students) + 1)
        students.append({
            'id': new_id,
            'name': name,
            'email': email,
            'has_face_data': False
        })
        
        # Add user account
        users[email] = {'password': password, 'role': 'student', 'name': name}
        
        flash('Student added successfully')
        return redirect(url_for('admin_students'))
    
    return render_template('admin_add_student.html', courses=courses, firebase_available=FIREBASE_AVAILABLE)

@app.route('/admin/register-face')
@login_required
def admin_register_face():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    # Get student ID from query parameter
    student_id = request.args.get('student_id')
    
    # Filter students without face data
    students_without_face = [s for s in students if not s['has_face_data']]
    
    return render_template('admin_register_face.html', students=students_without_face, firebase_available=FIREBASE_AVAILABLE)

@app.route('/admin/simulate-face-register', methods=['POST'])
@login_required
def simulate_face_register():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    student_id = request.form.get('student_id')
    
    # Update the student's face data status
    for student in students:
        if student['id'] == student_id:
            student['has_face_data'] = True
            flash(f'Face data for {student["name"]} registered successfully!')
            break
    
    return redirect(url_for('admin_students'))

@app.route('/admin/courses')
@login_required
def admin_courses():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    return render_template('admin_courses.html', courses=courses, firebase_available=FIREBASE_AVAILABLE)

@app.route('/admin/add-course', methods=['POST'])
@login_required
def admin_add_course():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    course_name = request.form.get('course_name')
    
    # Check if course already exists
    for course in courses:
        if course['name'].lower() == course_name.lower():
            flash('A course with this name already exists')
            return redirect(url_for('admin_courses'))
    
    # Add new course
    new_id = str(len(courses) + 1)
    courses.append({
        'id': new_id,
        'name': course_name
    })
    
    flash('Course added successfully')
    return redirect(url_for('admin_courses'))

@app.route('/admin/edit-course', methods=['POST'])
@login_required
def admin_edit_course():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    course_id = request.form.get('course_id')
    course_name = request.form.get('course_name')
    
    # Update course
    for course in courses:
        if course['id'] == course_id:
            course['name'] = course_name
            flash('Course updated successfully')
            break
    
    return redirect(url_for('admin_courses'))

@app.route('/admin/delete-course', methods=['POST'])
@login_required
def admin_delete_course():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    course_id = request.form.get('course_id')
    
    # Delete course
    for i, course in enumerate(courses):
        if course['id'] == course_id:
            courses.pop(i)
            flash('Course deleted successfully')
            break
    
    return redirect(url_for('admin_courses'))

@app.route('/admin/attendance')
@login_required
def admin_attendance():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    return render_template('admin_attendance.html', attendance_records=attendance_records, courses=courses, firebase_available=FIREBASE_AVAILABLE)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    user = get_current_user()
    if not user or user['role'] != 'student':
        return redirect(url_for('admin_dashboard'))
    
    return render_template('student_dashboard.html', attendance_records=attendance_records, firebase_available=FIREBASE_AVAILABLE)

@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    user = get_current_user()
    if not user or user['role'] != 'student':
        flash('Access denied: Student privileges required')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        
        # Find course name
        course_name = "Unknown Course"
        for course in courses:
            if course['id'] == course_id:
                course_name = course['name']
                break
        
        flash(f'Attendance marked successfully for {course_name}')
        return redirect(url_for('student_dashboard'))
    
    return render_template('mark_attendance.html', courses=courses, firebase_available=FIREBASE_AVAILABLE)

@app.route('/qr-attendance/<course_id>')
@login_required
def qr_attendance(course_id):
    user = get_current_user()
    if not user or user['role'] != 'student':
        flash('Access denied: Student privileges required')
        return redirect(url_for('index'))
    
    # Find course name
    course_name = "Unknown Course"
    for course in courses:
        if course['id'] == course_id:
            course_name = course['name']
            break
    
    flash(f'Attendance marked successfully via QR code for {course_name}')
    return redirect(url_for('student_dashboard'))

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/realtime_recognition')
@login_required
def realtime_recognition():
    """Real-time face recognition page."""
    # Initialize video if not already done
    global camera
    if camera is None:
        initialize_video()
    
    # Load face encodings from Firebase
    global face_encodings
    face_encodings = get_all_face_encodings()
    
    return render_template('realtime_recognition.html', firebase_available=FIREBASE_AVAILABLE)

@app.route('/firebase-status')
def firebase_status():
    """Check Firebase availability."""
    return {
        'available': FIREBASE_AVAILABLE,
        'message': 'Firebase is available and configured correctly' if FIREBASE_AVAILABLE else 'Firebase is not available. Using mock implementations.'
    }

if __name__ == '__main__':
    print(f"Firebase available: {FIREBASE_AVAILABLE}")
    if not FIREBASE_AVAILABLE:
        print("Using mock implementations for Firebase functionality")
    app.run(debug=True) 