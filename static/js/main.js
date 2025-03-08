// Main JavaScript for Smart Attendance System

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Firebase Configuration
function initFirebase() {
    // Firebase configuration
    const firebaseConfig = {
        apiKey: "AIzaSyB3OSZfLvwAO3oiQJyS9g_vD8J13lwj3Ak",
        authDomain: "attendence-8d529.firebaseapp.com",
        projectId: "attendence-8d529",
        storageBucket: "attendence-8d529.firebasestorage.app",
        messagingSenderId: "644503888286",
        appId: "1:644503888286:web:13241aeb5e12f23a15368f",
        measurementId: "G-4H55WBXW1R"
    };
    
    // Initialize Firebase if not already initialized
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }
    
    return firebase;
}

// Camera Utilities
const cameraUtils = {
    // Start camera stream
    startCamera: async function(videoElement) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            videoElement.srcObject = stream;
            return stream;
        } catch (err) {
            console.error('Error accessing camera:', err);
            throw err;
        }
    },
    
    // Capture photo from video stream
    capturePhoto: function(videoElement, canvasElement) {
        const context = canvasElement.getContext('2d');
        context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
        return canvasElement.toDataURL('image/jpeg');
    },
    
    // Stop camera stream
    stopCamera: function(stream) {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    }
};

// QR Code Utilities
const qrUtils = {
    // Generate QR code
    generateQR: function(elementId, text, width = 200, height = 200) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Clear previous QR code
        element.innerHTML = '';
        
        // Generate new QR code
        new QRCode(element, {
            text: text,
            width: width,
            height: height,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.H
        });
    },
    
    // Download QR code as image
    downloadQR: function(elementId, filename = 'qrcode.png') {
        const canvas = document.querySelector(`#${elementId} canvas`);
        if (!canvas) return;
        
        const link = document.createElement('a');
        link.download = filename;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }
};

// Form Validation Utilities
const formUtils = {
    // Validate email format
    isValidEmail: function(email) {
        const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(String(email).toLowerCase());
    },
    
    // Validate password strength
    isStrongPassword: function(password) {
        // At least 8 characters, 1 uppercase, 1 lowercase, 1 number
        const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/;
        return re.test(password);
    },
    
    // Show validation error
    showError: function(inputElement, message) {
        const formGroup = inputElement.closest('.form-group') || inputElement.closest('.mb-3');
        const errorElement = formGroup.querySelector('.invalid-feedback') || document.createElement('div');
        
        errorElement.className = 'invalid-feedback';
        errorElement.textContent = message;
        
        if (!formGroup.querySelector('.invalid-feedback')) {
            formGroup.appendChild(errorElement);
        }
        
        inputElement.classList.add('is-invalid');
    },
    
    // Clear validation error
    clearError: function(inputElement) {
        inputElement.classList.remove('is-invalid');
    }
};

// API Utilities
const apiUtils = {
    // Generic fetch with error handling
    fetchAPI: async function(url, options = {}) {
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // POST request
    postData: async function(url, data) {
        return this.fetchAPI(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
    },
    
    // GET request
    getData: async function(url) {
        return this.fetchAPI(url);
    },
    
    // PUT request
    updateData: async function(url, data) {
        return this.fetchAPI(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
    },
    
    // DELETE request
    deleteData: async function(url) {
        return this.fetchAPI(url, {
            method: 'DELETE'
        });
    }
};

// Export utilities
window.cameraUtils = cameraUtils;
window.qrUtils = qrUtils;
window.formUtils = formUtils;
window.apiUtils = apiUtils;
window.initFirebase = initFirebase; 