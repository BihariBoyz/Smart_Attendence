import os
# import cv2  # Commented out
import numpy as np
# import face_recognition  # Commented out
import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['UPLOAD_FOLDER'] = 'static/img/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Initialize Firebase
try:
    cred = credentials.Certificate('firebase-key.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    # Create a mock database for testing
    db = None
    print("Using mock database for testing")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, email, role):
        self.id = user_id
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    # For testing without Firebase
    if db is None:
        return User(user_id, f"user{user_id}@example.com", "admin" if user_id == "1" else "student")
    
    try:
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return User(user_id, user_data.get('email'), user_data.get('role'))
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Mock function for face recognition (for testing)
def mock_recognize_face(image_path):
    # This is a mock function that always returns the first student ID
    # In a real application, this would use face_recognition
    print(f"Mock recognizing face from {image_path}")
    return "student1"

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if db is None:
            # Mock login for testing
            user_id = "1" if email == "admin@example.com" else "2"
            role = "admin" if email == "admin@example.com" else "student"
            user_obj = User(user_id, email, role)
            login_user(user_obj)
            
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            try:
                # Authenticate with Firebase
                user = auth.get_user_by_email(email)
                
                # Get user role from Firestore
                user_doc = db.collection('users').document(user.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_obj = User(user.uid, email, user_data.get('role', 'student'))
                    login_user(user_obj)
                    
                    if user_data.get('role') == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('student_dashboard'))
                else:
                    flash('User not found in database')
            except Exception as e:
                flash(f'Login failed: {str(e)}')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role', 'student')
        
        if db is None:
            # Mock registration for testing
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        else:
            try:
                # Create user in Firebase Auth
                user = auth.create_user(
                    email=email,
                    password=password,
                    display_name=name
                )
                
                # Store additional user data in Firestore
                db.collection('users').document(user.uid).set({
                    'email': email,
                    'name': name,
                    'role': role,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                
                if role == 'student':
                    # Create student record
                    db.collection('students').document(user.uid).set({
                        'name': name,
                        'email': email,
                        'created_at': firestore.SERVER_TIMESTAMP
                    })
                
                flash('Registration successful! Please login.')
                return redirect(url_for('login'))
            except Exception as e:
                flash(f'Registration failed: {str(e)}')
    
    return render_template('register.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    return render_template('admin_dashboard.html')

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    
    # Get student attendance records
    attendance_records = []
    
    if db is None:
        # Mock attendance records for testing
        attendance_records = [
            {
                'id': '1',
                'course': 'Computer Science',
                'date': '2023-09-01 09:00',
                'method': 'face_recognition'
            },
            {
                'id': '2',
                'course': 'Mathematics',
                'date': '2023-09-02 10:30',
                'method': 'qr_code'
            }
        ]
    else:
        try:
            records = db.collection('attendance').where('student_id', '==', current_user.id).order_by('timestamp', direction='DESCENDING').limit(10).stream()
            for record in records:
                record_data = record.to_dict()
                attendance_records.append({
                    'id': record.id,
                    'course': record_data.get('course_name', 'Unknown'),
                    'date': record_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M'),
                    'method': record_data.get('method', 'Unknown')
                })
        except Exception as e:
            print(f"Error fetching attendance records: {e}")
    
    return render_template('student_dashboard.html', attendance_records=attendance_records)

@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        
        # Get course details
        course_name = "Unknown Course"
        
        if db is None:
            # Mock course data for testing
            if course_id == "1":
                course_name = "Computer Science"
            elif course_id == "2":
                course_name = "Mathematics"
        else:
            try:
                course_doc = db.collection('courses').document(course_id).get()
                if not course_doc.exists:
                    flash('Course not found')
                    return redirect(url_for('mark_attendance'))
                
                course_data = course_doc.to_dict()
                course_name = course_data.get('name', 'Unknown Course')
            except Exception as e:
                flash(f'Error getting course: {str(e)}')
                return redirect(url_for('mark_attendance'))
        
        # Check if file was uploaded
        if 'image' not in request.files:
            flash('No image uploaded')
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            flash('No image selected')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Use mock face recognition instead of actual face recognition
            student_id = mock_recognize_face(filepath)
            
            if student_id:
                if db is not None:
                    # Mark attendance in Firebase
                    db.collection('attendance').add({
                        'student_id': student_id,
                        'course_id': course_id,
                        'course_name': course_name,
                        'timestamp': firestore.SERVER_TIMESTAMP,
                        'method': 'face_recognition'
                    })
                
                flash('Attendance marked successfully')
            else:
                flash('Face not recognized or not registered')
            
            # Delete the uploaded file
            os.remove(filepath)
    
    # Get available courses
    courses = []
    
    if db is None:
        # Mock courses for testing
        courses = [
            {'id': '1', 'name': 'Computer Science'},
            {'id': '2', 'name': 'Mathematics'},
            {'id': '3', 'name': 'Physics'}
        ]
    else:
        try:
            course_docs = db.collection('courses').stream()
            for doc in course_docs:
                course_data = doc.to_dict()
                courses.append({
                    'id': doc.id,
                    'name': course_data.get('name', 'Unknown')
                })
        except Exception as e:
            print(f"Error fetching courses: {e}")
    
    return render_template('mark_attendance.html', courses=courses)

@app.route('/qr-attendance/<course_id>')
@login_required
def qr_attendance(course_id):
    if current_user.role != 'student':
        flash('Access denied: Student privileges required')
        return redirect(url_for('index'))
    
    course_name = "Unknown Course"
    
    if db is None:
        # Mock course data for testing
        if course_id == "1":
            course_name = "Computer Science"
        elif course_id == "2":
            course_name = "Mathematics"
        
        flash('Attendance marked successfully via QR code')
    else:
        try:
            # Get course details
            course_doc = db.collection('courses').document(course_id).get()
            if not course_doc.exists:
                flash('Course not found')
                return redirect(url_for('student_dashboard'))
            
            course_data = course_doc.to_dict()
            course_name = course_data.get('name', 'Unknown Course')
            
            # Mark attendance
            db.collection('attendance').add({
                'student_id': current_user.id,
                'course_id': course_id,
                'course_name': course_name,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'method': 'qr_code'
            })
            
            flash('Attendance marked successfully via QR code')
        except Exception as e:
            flash(f'Error marking attendance: {str(e)}')
    
    return redirect(url_for('student_dashboard'))

if __name__ == '__main__':
    app.run(debug=True) 