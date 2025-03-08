import os
import cv2
import numpy as np
import subprocess
import json
import tempfile
from pathlib import Path

# Make face_recognition optional
FACE_RECOGNITION_AVAILABLE = False
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("Using built-in face_recognition module")
except ImportError:
    print("face_recognition module not available in this environment. Using system Python.")

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
from firebase_config import (
    FIREBASE_AVAILABLE,
    create_user, sign_in_with_email_password, get_user_by_email,
    upload_file_to_storage, save_face_encoding, get_all_face_encodings,
    save_attendance_record
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['UPLOAD_FOLDER'] = 'static/img/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Print Firebase status
print(f"Firebase available: {FIREBASE_AVAILABLE}")
if not FIREBASE_AVAILABLE:
    print("Using mock implementations for Firebase functionality")

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
    # Simplified user loading
    return User(user_id, f"user{user_id}@example.com", "admin" if user_id == "1" else "student")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper function for face recognition
def recognize_face(image_path):
    # If face_recognition is available in this environment, use it directly
    if FACE_RECOGNITION_AVAILABLE:
        # Load the image
        image = face_recognition.load_image_file(image_path)
        # Find all face locations in the image
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return None, "No face detected in the image."
        
        # Get face encodings for the faces in the image
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if not face_encodings:
            return None, "Could not encode the face."
        
        # Get all known face encodings from the database
        known_face_encodings = get_all_face_encodings()
        
        # If no known faces, return None
        if not known_face_encodings:
            return None, "No registered faces in the database."
        
        # Loop through each face found in the image
        for face_encoding in face_encodings:
            # Compare with all known faces
            for student_id, known_encoding in known_face_encodings.items():
                # Convert the known_encoding from string/list to numpy array if needed
                if isinstance(known_encoding, str):
                    try:
                        known_encoding = np.array(json.loads(known_encoding))
                    except:
                        continue
                elif isinstance(known_encoding, list):
                    known_encoding = np.array(known_encoding)
                
                # Compare faces
                matches = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=0.6)
                
                if matches[0]:
                    return student_id, "Face recognized successfully."
        
        return None, "Face not recognized."
    else:
        # Use system Python with face_recognition
        system_python = r"C:\Users\Dell\AppData\Local\Programs\Python\Python39\python.exe"
        
        # Create a temporary script to run face recognition
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            script_path = f.name
            f.write("""
import os
import json
import numpy as np
import face_recognition
import sys

def recognize_face(image_path):
    # Load the image
    image = face_recognition.load_image_file(image_path)
    # Find all face locations in the image
    face_locations = face_recognition.face_locations(image)
    
    if not face_locations:
        return None, "No face detected in the image."
    
    # Get face encodings for the faces in the image
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    if not face_encodings:
        return None, "Could not encode the face."
    
    # Get all known face encodings from the database
    # This is a simplified version - in your app you'd load from Firebase
    # For this script, we'll pass the encodings as a parameter
    known_face_encodings = {}
    
    # If no known faces, return None
    if not known_face_encodings:
        return None, "No registered faces in the database."
    
    # Loop through each face found in the image
    for face_encoding in face_encodings:
        # Compare with all known faces
        for student_id, known_encoding in known_face_encodings.items():
            # Convert the known_encoding from string/list to numpy array if needed
            if isinstance(known_encoding, str):
                try:
                    known_encoding = np.array(json.loads(known_encoding))
                except:
                    continue
            elif isinstance(known_encoding, list):
                known_encoding = np.array(known_encoding)
            
            # Compare faces
            matches = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=0.6)
            
            if matches[0]:
                return student_id, "Face recognized successfully."
    
    return None, "Face not recognized."

if __name__ == "__main__":
    image_path = sys.argv[1]
    result = recognize_face(image_path)
    print(json.dumps(result))
""")
        
        try:
            # Run the script with the system Python
            result = subprocess.run(
                [system_python, script_path, image_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the result
            output = result.stdout.strip()
            if output:
                try:
                    student_id, message = json.loads(output)
                    return student_id, message
                except json.JSONDecodeError:
                    return None, "Error parsing face recognition result."
            
            return None, "Face recognition failed."
        except subprocess.CalledProcessError as e:
            return None, f"Face recognition error: {e.stderr}"
        finally:
            # Clean up the temporary script
            try:
                os.unlink(script_path)
            except:
                pass

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Simplified login (no actual authentication)
        user_id = "1" if email == "admin@example.com" else "2"
        role = "admin" if email == "admin@example.com" else "student"
        
        user_obj = User(user_id, email, role)
        login_user(user_obj)
        
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('student_dashboard'))
    
    return render_template('admin_dashboard.html', firebase_available=FIREBASE_AVAILABLE)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied: Student privileges required')
        return redirect(url_for('admin_dashboard'))
    
    # Simplified attendance records
    attendance_records = [
        {'id': '1', 'course_name': 'Computer Science', 'timestamp': '2023-09-01 09:00', 'method': 'face_recognition'},
        {'id': '2', 'course_name': 'Mathematics', 'timestamp': '2023-09-02 10:30', 'method': 'qr_code'}
    ]
    
    return render_template('student_dashboard.html', attendance_records=attendance_records, firebase_available=FIREBASE_AVAILABLE)

@app.route('/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        
        # Get course details
        try:
            course_doc = db.collection('courses').document(course_id).get()
            if not course_doc.exists:
                flash('Course not found')
                return redirect(url_for('mark_attendance'))
            
            course_data = course_doc.to_dict()
            course_name = course_data.get('name', 'Unknown Course')
            
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
                
                # Recognize face
                student_id, message = recognize_face(filepath)
                
                if student_id:
                    # Mark attendance
                    db.collection('attendance').add({
                        'student_id': student_id,
                        'course_id': course_id,
                        'course_name': course_name,
                        'timestamp': firestore.SERVER_TIMESTAMP,
                        'method': 'face_recognition'
                    })
                    
                    flash(f'Attendance marked successfully. {message}')
                else:
                    flash(f'Face not recognized or not registered. {message}')
                
                # Delete the uploaded file
                os.remove(filepath)
        except Exception as e:
            flash(f'Error marking attendance: {str(e)}')
    
    # Get available courses
    courses = []
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

@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    students = []
    try:
        student_docs = db.collection('students').stream()
        for doc in student_docs:
            student_data = doc.to_dict()
            students.append({
                'id': doc.id,
                'name': student_data.get('name', 'Unknown'),
                'email': student_data.get('email', 'Unknown'),
                'has_face_data': 'face_encoding' in student_data
            })
    except Exception as e:
        print(f"Error fetching students: {e}")
    
    return render_template('admin_students.html', students=students)

@app.route('/admin/courses', methods=['GET', 'POST'])
@login_required
def admin_courses():
    if current_user.role != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        course_name = request.form.get('course_name')
        course_code = request.form.get('course_code')
        
        try:
            db.collection('courses').add({
                'name': course_name,
                'code': course_code,
                'created_at': firestore.SERVER_TIMESTAMP,
                'created_by': current_user.id
            })
            flash('Course added successfully')
        except Exception as e:
            flash(f'Error adding course: {str(e)}')
    
    courses = []
    try:
        course_docs = db.collection('courses').stream()
        for doc in course_docs:
            course_data = doc.to_dict()
            courses.append({
                'id': doc.id,
                'name': course_data.get('name', 'Unknown'),
                'code': course_data.get('code', 'Unknown')
            })
    except Exception as e:
        print(f"Error fetching courses: {e}")
    
    return render_template('admin_courses.html', courses=courses)

@app.route('/admin/attendance')
@login_required
def admin_attendance():
    if current_user.role != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    course_id = request.args.get('course_id')
    date = request.args.get('date')
    
    attendance_records = []
    try:
        query = db.collection('attendance')
        
        if course_id:
            query = query.where('course_id', '==', course_id)
        
        if date:
            # Convert date string to datetime objects for range query
            start_date = datetime.strptime(date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=1)
            query = query.where('timestamp', '>=', start_date).where('timestamp', '<', end_date)
        
        records = query.order_by('timestamp', direction='DESCENDING').stream()
        
        for record in records:
            record_data = record.to_dict()
            student_id = record_data.get('student_id')
            student_name = 'Unknown'
            
            # Get student name
            if student_id:
                student_doc = db.collection('students').document(student_id).get()
                if student_doc.exists:
                    student_data = student_doc.to_dict()
                    student_name = student_data.get('name', 'Unknown')
            
            attendance_records.append({
                'id': record.id,
                'student_name': student_name,
                'course': record_data.get('course_name', 'Unknown'),
                'date': record_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M'),
                'method': record_data.get('method', 'Unknown')
            })
    except Exception as e:
        print(f"Error fetching attendance records: {e}")
    
    # Get courses for filter
    courses = []
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
    
    return render_template('admin_attendance.html', attendance_records=attendance_records, courses=courses)

@app.route('/admin/register-face', methods=['GET', 'POST'])
@login_required
def admin_register_face():
    if current_user.role != 'admin':
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        
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
            
            try:
                # Load the image
                image = face_recognition.load_image_file(filepath)
                
                # Find all face locations and encodings
                face_locations = face_recognition.face_locations(image)
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                if not face_encodings:
                    flash('No face detected in the image')
                    os.remove(filepath)
                    return redirect(request.url)
                
                # Use the first face found
                face_encoding = face_encodings[0].tolist()
                
                # Store face encoding in Firestore
                db.collection('students').document(student_id).update({
                    'face_encoding': json.dumps(face_encoding),
                    'face_updated_at': firestore.SERVER_TIMESTAMP
                })
                
                flash('Face registered successfully')
                
                # Delete the uploaded file
                os.remove(filepath)
            except Exception as e:
                flash(f'Error registering face: {str(e)}')
                if os.path.exists(filepath):
                    os.remove(filepath)
    
    # Get students without face data
    students = []
    try:
        student_docs = db.collection('students').stream()
        for doc in student_docs:
            student_data = doc.to_dict()
            if 'face_encoding' not in student_data:
                students.append({
                    'id': doc.id,
                    'name': student_data.get('name', 'Unknown'),
                    'email': student_data.get('email', 'Unknown')
                })
    except Exception as e:
        print(f"Error fetching students: {e}")
    
    return render_template('admin_register_face.html', students=students)

@app.route('/qr-attendance/<course_id>')
@login_required
def qr_attendance(course_id):
    if current_user.role != 'student':
        flash('Access denied: Student privileges required')
        return redirect(url_for('index'))
    
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

@app.route('/test-firebase')
def test_firebase():
    """Test Firebase connection."""
    try:
        # Try to list all students
        if FIREBASE_AVAILABLE:
            students = []
            student_docs = db.collection('students').stream()
            for doc in student_docs:
                student_data = doc.to_dict()
                students.append({
                    'id': doc.id,
                    'name': student_data.get('name', 'Unknown'),
                    'email': student_data.get('email', 'Unknown')
                })
            return jsonify({
                'status': 'success',
                'firebase_available': True,
                'message': 'Firebase connection successful',
                'students': students
            })
        else:
            return jsonify({
                'status': 'warning',
                'firebase_available': False,
                'message': 'Firebase not available, using mock data',
                'students': []
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'firebase_available': False,
            'message': f'Error testing Firebase: {str(e)}',
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True)