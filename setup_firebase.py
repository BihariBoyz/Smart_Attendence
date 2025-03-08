"""
Firebase Setup Script for Smart Attendance System

This script helps you set up your Firebase service account key.
It will guide you through the process of creating a proper firebase-key.json file.
"""

import os
import json
import sys

def print_header():
    print("\n" + "="*80)
    print(" "*25 + "FIREBASE SETUP ASSISTANT")
    print("="*80)

def print_step(step_num, title):
    print(f"\n[Step {step_num}] {title}")
    print("-" * 50)

def check_firebase_key():
    key_path = 'firebase-key.json'
    if os.path.exists(key_path):
        try:
            with open(key_path, 'r') as f:
                key_data = json.load(f)
            
            # Check if it's a placeholder
            if key_data.get('private_key_id') == 'placeholder-key-id':
                print(f"Found placeholder {key_path} file.")
                return False
            else:
                print(f"Found existing {key_path} file.")
                return True
        except json.JSONDecodeError:
            print(f"Error: {key_path} exists but is not valid JSON.")
            return False
    else:
        print(f"{key_path} not found.")
        return False

def create_service_account_key():
    key_path = 'firebase-key.json'
    
    print_step(1, "Create a Firebase Project")
    print("If you haven't already, create a Firebase project at:")
    print("https://console.firebase.google.com/")
    print("\nPress Enter when you're done...")
    input()
    
    print_step(2, "Generate a Service Account Key")
    print("1. Go to your Firebase project console")
    print("2. Click the gear icon (⚙️) next to 'Project Overview'")
    print("3. Select 'Project settings'")
    print("4. Go to the 'Service accounts' tab")
    print("5. Click 'Generate new private key' button")
    print("6. Save the JSON file")
    print("\nPress Enter when you've downloaded the key file...")
    input()
    
    print_step(3, "Copy Service Account Key Content")
    print("Open the downloaded JSON file in a text editor and copy its entire content.")
    print("Then paste it below (right-click to paste in the terminal).")
    print("Press Enter twice when done:")
    
    lines = []
    while True:
        line = input()
        if not line and lines and not lines[-1]:  # Two consecutive empty lines
            break
        lines.append(line)
    
    key_content = "\n".join(lines[:-1])  # Remove the last empty line
    
    try:
        key_data = json.loads(key_content)
        
        # Validate key data
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in key_data]
        
        if missing_fields:
            print(f"Error: Missing required fields in service account key: {', '.join(missing_fields)}")
            return False
        
        # Save the key
        with open(key_path, 'w') as f:
            json.dump(key_data, f, indent=2)
        
        print(f"\nSuccessfully saved service account key to {key_path}")
        return True
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format. {str(e)}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def setup_firebase_auth():
    print_step(4, "Set Up Firebase Authentication")
    print("1. In the Firebase console, go to 'Authentication' in the left sidebar")
    print("2. Click 'Get started'")
    print("3. Enable 'Email/Password' authentication method")
    print("4. Save the changes")
    print("\nPress Enter when you're done...")
    input()

def setup_firestore():
    print_step(5, "Set Up Firestore Database")
    print("1. In the Firebase console, go to 'Firestore Database' in the left sidebar")
    print("2. Click 'Create database'")
    print("3. Choose either production or test mode (test mode is easier for development)")
    print("4. Select a location for your database")
    print("5. Click 'Enable'")
    print("\nPress Enter when you're done...")
    input()

def setup_storage():
    print_step(6, "Set Up Firebase Storage")
    print("1. In the Firebase console, go to 'Storage' in the left sidebar")
    print("2. Click 'Get started'")
    print("3. Follow the setup steps")
    print("4. Set up security rules (you can start with test mode for development)")
    print("\nPress Enter when you're done...")
    input()

def main():
    print_header()
    
    print("This script will help you set up your Firebase service account key.")
    print("You'll need to have a Firebase project and the ability to create a service account key.")
    
    if check_firebase_key():
        print("\nYou already have a valid firebase-key.json file.")
        replace = input("Do you want to replace it? (y/n): ").lower()
        if replace != 'y':
            print("Setup canceled. Your existing firebase-key.json file will be used.")
            return
    
    if create_service_account_key():
        setup_firebase_auth()
        setup_firestore()
        setup_storage()
        
        print_step(7, "Restart Your Application")
        print("Now you can restart your application with:")
        print("python minimal_app.py")
        print("\nYou should see 'Firebase initialized successfully' in the console output.")
        
        print("\n" + "="*80)
        print(" "*20 + "FIREBASE SETUP COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
    else:
        print("\nSetup failed. Please try again.")

if __name__ == "__main__":
    main() 