import os
import cv2
import numpy as np
import face_recognition
import json
from datetime import datetime

class FaceRecognitionModel:
    def __init__(self, tolerance=0.6, model="hog"):
        """
        Initialize the face recognition model.
        
        Args:
            tolerance (float): The tolerance for face comparison (lower is more strict)
            model (str): The face detection model to use ('hog' for CPU, 'cnn' for GPU)
        """
        self.tolerance = tolerance
        self.model = model
        self.known_face_encodings = []
        self.known_face_ids = []
    
    def load_known_faces(self, face_data):
        """
        Load known faces from a list of dictionaries.
        
        Args:
            face_data (list): List of dictionaries with 'id' and 'face_encoding' keys
        """
        self.known_face_encodings = []
        self.known_face_ids = []
        
        for face in face_data:
            if 'id' in face and 'face_encoding' in face:
                face_encoding = np.array(json.loads(face['face_encoding']))
                self.known_face_encodings.append(face_encoding)
                self.known_face_ids.append(face['id'])
    
    def recognize_face(self, image_path):
        """
        Recognize a face in an image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str or None: The ID of the recognized face, or None if no face is recognized
        """
        # Load the image
        image = face_recognition.load_image_file(image_path)
        
        # Find all face locations and encodings
        face_locations = face_recognition.face_locations(image, model=self.model)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        # If no faces found, return None
        if not face_encodings:
            return None
        
        # Compare with known faces
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=self.tolerance)
            
            # If a match is found, return the ID
            if True in matches:
                match_index = matches.index(True)
                return self.known_face_ids[match_index]
        
        # No match found
        return None
    
    def encode_face(self, image_path):
        """
        Encode a face from an image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            list or None: The face encoding as a list, or None if no face is found
        """
        # Load the image
        image = face_recognition.load_image_file(image_path)
        
        # Find all face locations and encodings
        face_locations = face_recognition.face_locations(image, model=self.model)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        # If no faces found, return None
        if not face_encodings:
            return None
        
        # Return the first face encoding
        return face_encodings[0].tolist()
    
    def save_face_image(self, image_path, output_dir, student_id):
        """
        Save a cropped face image.
        
        Args:
            image_path (str): Path to the image file
            output_dir (str): Directory to save the cropped face
            student_id (str): Student ID to use in the filename
            
        Returns:
            str or None: Path to the saved face image, or None if no face is found
        """
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        # Convert to RGB (face_recognition uses RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Find all face locations
        face_locations = face_recognition.face_locations(rgb_image, model=self.model)
        
        # If no faces found, return None
        if not face_locations:
            return None
        
        # Get the first face location
        top, right, bottom, left = face_locations[0]
        
        # Add some margin
        margin = 30
        top = max(0, top - margin)
        left = max(0, left - margin)
        bottom = min(image.shape[0], bottom + margin)
        right = min(image.shape[1], right + margin)
        
        # Crop the face
        face_image = image[top:bottom, left:right]
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{student_id}_{timestamp}.jpg"
        output_path = os.path.join(output_dir, filename)
        
        # Save the face image
        cv2.imwrite(output_path, face_image)
        
        return output_path 