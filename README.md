# Smart Attendance System

A facial recognition-based attendance system with QR code backup for educational institutions.

## Features

- **Face Recognition**: Automated attendance marking using facial recognition
- **Admin Dashboard**: For managing students, courses, and viewing attendance reports
- **Student Portal**: For students to view their attendance records
- **QR Code Backup**: Alternative attendance marking method
- **Authentication**: Secure login with Firebase Auth (Google Sign-In)
- **Database**: Real-time data storage with Firebase Firestore

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python (Flask)
- **Face Recognition**: OpenCV
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth

## Installation

1. Clone the repository
```
git clone https://github.com/yourusername/smart-attendance-system.git
cd smart-attendance-system
```

2. Install dependencies
```
pip install -r requirements.txt
```

3. Set up Firebase
   - Create a Firebase project
   - Enable Authentication (Google Sign-In)
   - Set up Firestore Database
   - Download service account key and save as `firebase-key.json` in the project root

4. Configure environment variables
   - Create a `.env` file in the project root
   - Add the following variables:
     ```
     FLASK_APP=app.py
     FLASK_ENV=development
     SECRET_KEY=your_secret_key
     ```

5. Run the application
```
flask run
```

## Usage

1. **Admin**:
   - Register and login with admin credentials
   - Add/manage students and courses
   - View attendance reports
   - Export attendance data

2. **Students**:
   - Register and login with student credentials
   - View personal attendance records
   - Mark attendance via face recognition or QR code

## License

This project is licensed under the MIT License - see the LICENSE file for details. 