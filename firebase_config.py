"""
Firebase configuration for the Smart Attendance System.
This file contains the configuration for both Firebase Admin SDK and Pyrebase.
It includes fallback mock implementations when Firebase credentials aren't available.
"""

import os
import json
import datetime
import numpy as np

# Mock data for when Firebase is not available
mock_users = {
    'admin@example.com': {
        'uid': 'admin123',
        'email': 'admin@example.com',
        'password': 'admin123',
        'display_name': 'Admin User',
        'role': 'admin'
    },
    'student@example.com': {
        'uid': 'student123',
        'email': 'student@example.com',
        'password': 'student123',
        'display_name': 'Student User',
        'role': 'student'
    }
}

mock_face_encodings = {}
mock_attendance_records = []

# Firebase web configuration
firebase_web_config = {
    "apiKey": "AIzaSyB3OSZfLvwAO3oiQJyS9g_vD8J13lwj3Ak",
    "authDomain": "attendence-8d529.firebaseapp.com",
    "projectId": "attendence-8d529",
    "storageBucket": "attendence-8d529.appspot.com",
    "messagingSenderId": "644503888286",
    "appId": "1:644503888286:web:13241aeb5e12f23a15368f",
    "measurementId": "G-4H55WBXW1R",
    "databaseURL": "https://attendence-8d529-default-rtdb.firebaseio.com"
}

# Check if firebase-key.json exists
firebase_key_path = 'firebase-key.json'
FIREBASE_AVAILABLE = False

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth, storage
    import pyrebase
    
    if os.path.exists(firebase_key_path):
        try:
            # Firebase Admin SDK Configuration
            cred = credentials.Certificate(firebase_key_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': firebase_web_config['storageBucket']
            })
            
            # Initialize Firestore
            db = firestore.client()
            
            # Initialize Pyrebase
            firebase = pyrebase.initialize_app(firebase_web_config)
            firebase_auth = firebase.auth()
            firebase_storage = firebase.storage()
            firebase_db = firebase.database()
            
            # Set flag for Firebase availability
            FIREBASE_AVAILABLE = True
            print("Firebase initialized successfully")
            
        except Exception as e:
            print(f"Error initializing Firebase: {str(e)}")
            print("Please ensure you have placed a valid firebase-key.json file in the project directory")
            FIREBASE_AVAILABLE = False
    else:
        print(f"Firebase key file not found at {firebase_key_path}")
        print("Please download the service account key from Firebase Console and save it as firebase-key.json")
        FIREBASE_AVAILABLE = False
except ImportError as e:
    print(f"Firebase libraries not installed: {str(e)}")
    print("Please install required packages: pip install firebase-admin pyrebase4")
    FIREBASE_AVAILABLE = False

def create_user(email, password, display_name=None):
    """Create a new user in Firebase Authentication or mock database."""
    if FIREBASE_AVAILABLE:
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            return user.uid
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return None
    else:
        # Mock implementation
        if email in mock_users:
            print(f"User with email {email} already exists")
            return None
        
        uid = f"user_{len(mock_users) + 1}"
        mock_users[email] = {
            'uid': uid,
            'email': email,
            'password': password,
            'display_name': display_name or email.split('@')[0],
            'role': 'student'  # Default role
        }
        print(f"Mock user created: {email}")
        return uid

def sign_in_with_email_password(email, password):
    """Sign in a user with email and password."""
    if FIREBASE_AVAILABLE:
        try:
            user = firebase_auth.sign_in_with_email_and_password(email, password)
            return user
        except Exception as e:
            print(f"Error signing in: {str(e)}")
            return None
    else:
        # Mock implementation
        if email in mock_users and mock_users[email]['password'] == password:
            user = mock_users[email]
            return {
                'localId': user['uid'],
                'email': user['email'],
                'displayName': user['display_name']
            }
        return None

def get_user_by_email(email):
    """Get a user by email."""
    if FIREBASE_AVAILABLE:
        try:
            user = auth.get_user_by_email(email)
            return user
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None
    else:
        # Mock implementation
        if email in mock_users:
            user_data = mock_users[email]
            class MockUser:
                def __init__(self, data):
                    self.uid = data['uid']
                    self.email = data['email']
                    self.display_name = data['display_name']
            return MockUser(user_data)
        return None

def upload_file_to_storage(file_path, destination_path):
    """Upload a file to Firebase Storage or mock storage."""
    if FIREBASE_AVAILABLE:
        try:
            firebase_storage.child(destination_path).put(file_path)
            return firebase_storage.child(destination_path).get_url(None)
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None
    else:
        # Mock implementation
        print(f"Mock file upload: {file_path} -> {destination_path}")
        return f"https://mock-storage.example.com/{destination_path}"

def save_face_encoding(user_id, student_name, encoding):
    """Save a face encoding to Firestore or mock database."""
    if FIREBASE_AVAILABLE:
        try:
            doc_ref = db.collection('face_encodings').document(user_id)
            doc_ref.set({
                'name': student_name,
                'encoding': encoding.tolist() if isinstance(encoding, np.ndarray) else encoding,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"Error saving face encoding: {str(e)}")
            return False
    else:
        # Mock implementation
        mock_face_encodings[user_id] = {
            'name': student_name,
            'encoding': encoding.tolist() if isinstance(encoding, np.ndarray) else encoding,
            'timestamp': datetime.datetime.now()
        }
        print(f"Mock face encoding saved for {student_name}")
        return True

def get_all_face_encodings():
    """Get all face encodings from Firestore or mock database."""
    if FIREBASE_AVAILABLE:
        try:
            encodings = {}
            docs = db.collection('face_encodings').stream()
            for doc in docs:
                data = doc.to_dict()
                encodings[doc.id] = {
                    'name': data.get('name'),
                    'encoding': np.array(data.get('encoding')) if data.get('encoding') else None
                }
            return encodings
        except Exception as e:
            print(f"Error getting face encodings: {str(e)}")
            return {}
    else:
        # Mock implementation
        return {
            user_id: {
                'name': data['name'],
                'encoding': np.array(data['encoding']) if data.get('encoding') else None
            }
            for user_id, data in mock_face_encodings.items()
        }

def save_attendance_record(student_id, student_name, course_id, course_name, method):
    """Save an attendance record to Firestore or mock database."""
    if FIREBASE_AVAILABLE:
        try:
            doc_ref = db.collection('attendance').document()
            record = {
                'student_id': student_id,
                'student_name': student_name,
                'course_id': course_id,
                'course_name': course_name,
                'method': method,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            doc_ref.set(record)
            return True
        except Exception as e:
            print(f"Error saving attendance record: {str(e)}")
            return False
    else:
        # Mock implementation
        mock_attendance_records.append({
            'id': len(mock_attendance_records) + 1,
            'student_id': student_id,
            'student_name': student_name,
            'course_id': course_id,
            'course_name': course_name,
            'method': method,
            'timestamp': datetime.datetime.now()
        })
        print(f"Mock attendance record saved for {student_name}")
        return True

def get_attendance_records(student_id=None):
    """Get attendance records from Firestore or mock database."""
    if FIREBASE_AVAILABLE:
        try:
            if student_id:
                docs = db.collection('attendance').where('student_id', '==', student_id).stream()
            else:
                docs = db.collection('attendance').stream()
            
            records = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                records.append(data)
            
            return sorted(records, key=lambda x: x.get('timestamp', datetime.datetime.min), reverse=True)
        except Exception as e:
            print(f"Error getting attendance records: {str(e)}")
            return []
    else:
        # Mock implementation
        if student_id:
            records = [r for r in mock_attendance_records if r['student_id'] == student_id]
        else:
            records = mock_attendance_records.copy()
        return sorted(records, key=lambda x: x['timestamp'], reverse=True) 