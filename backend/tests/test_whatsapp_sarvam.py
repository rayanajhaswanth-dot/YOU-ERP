"""
Backend API Tests for WhatsApp with Sarvam AI and Gemini
Tests: WhatsApp webhook with Sarvam voice transcription, Gemini image OCR, welcome/help messages
"""
import pytest
import requests
import os

# Get the backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip().rstrip('/')
    except:
        pass
    return 'https://politech-hub-4.preview.emergentagent.com'

BASE_URL = get_backend_url()


class TestWhatsAppWebhookWelcome:
    """Test WhatsApp webhook welcome message"""
    
    def test_welcome_message_includes_voice_support(self):
        """Test that welcome message mentions voice message support"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={
                "From": "whatsapp:+919876543210",
                "To": "whatsapp:+14155238886",
                "Body": "hi",
                "ProfileName": "TestUser",
                "MessageSid": "SM123456789",
                "NumMedia": "0"
            }
        )
        assert response.status_code == 200
        assert "voice message" in response.text.lower()
        assert "🎤" in response.text
    
    def test_welcome_message_includes_photo_support(self):
        """Test that welcome message mentions photo support"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={
                "From": "whatsapp:+919876543210",
                "To": "whatsapp:+14155238886",
                "Body": "hello",
                "ProfileName": "TestUser",
                "MessageSid": "SM123456790",
                "NumMedia": "0"
            }
        )
        assert response.status_code == 200
        assert "photo" in response.text.lower()


class TestWhatsAppWebhookHelp:
    """Test WhatsApp webhook help command"""
    
    def test_help_mentions_voice_support(self):
        """Test that help command mentions voice message with Indian languages"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={
                "From": "whatsapp:+919876543210",
                "To": "whatsapp:+14155238886",
                "Body": "help",
                "ProfileName": "TestUser",
                "MessageSid": "SM123456791",
                "NumMedia": "0"
            }
        )
        assert response.status_code == 200
        assert "voice" in response.text.lower()


class TestWhatsAppStatus:
    """Test WhatsApp status endpoint"""
    
    def test_whatsapp_status_active(self):
        """Test that WhatsApp status returns active"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["twilio_configured"] == True


class TestWhatsAppWebhookTextGrievance:
    """Test WhatsApp webhook text grievance creation"""
    
    def test_text_grievance_creation(self):
        """Test that a text grievance is properly registered"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={
                "From": "whatsapp:+919876543210",
                "To": "whatsapp:+14155238886",
                "Body": "Water supply issue in my area for 3 days",
                "ProfileName": "TestUser",
                "MessageSid": "SM123456792",
                "NumMedia": "0"
            }
        )
        assert response.status_code == 200
        assert "Grievance Registered" in response.text or "registered" in response.text.lower()
        assert "Priority" in response.text or "priority" in response.text.lower()


class TestWhatsAppCodeReviewSarvamGemini:
    """Test that code uses Sarvam AI and Gemini correctly"""
    
    def test_sarvam_api_key_configured(self):
        """Test that SARVAM_API_KEY is in the code"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "SARVAM_API_KEY" in content, "Should have SARVAM_API_KEY configuration"
    
    def test_sarvam_api_endpoint(self):
        """Test that code uses correct Sarvam API endpoint"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "api.sarvam.ai" in content, "Should use Sarvam AI API endpoint"
    
    def test_sarvam_model_usage(self):
        """Test that code uses saaras:v1 model for Sarvam"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "saaras:v1" in content, "Should use saaras:v1 model for Indian dialects"
    
    def test_gemini_api_for_images(self):
        """Test that code uses Gemini API for image processing"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "gemini-2.0-flash" in content, "Should use Gemini 2.0 Flash for vision"
    
    def test_multipart_form_data(self):
        """Test that code uses multipart form data for Sarvam upload"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "files=" in content or "multipart" in content.lower(), "Should use multipart form data for Sarvam"
    
    def test_extended_timeouts(self):
        """Test that code has extended timeouts for media processing"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "timeout=" in content, "Should have explicit timeout settings"
    
    def test_twilio_auth_download(self):
        """Test that code authenticates with Twilio for media download"""
        with open('/app/backend/routes/whatsapp_routes.py', 'r') as f:
            content = f.read()
        assert "auth=" in content, "Should authenticate with Twilio for media download"


class TestBackendAPIEndpoints:
    """Test that all required backend API endpoints exist"""
    
    def test_auth_login_endpoint(self):
        """Test login endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "test"}
        )
        # Should return 401 or 400 for invalid credentials, not 404
        assert response.status_code != 404
    
    def test_grievances_endpoint(self):
        """Test grievances endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/grievances/")
        # Should return 401/403 unauthorized without token, not 404
        assert response.status_code in [200, 401, 403, 422]
    
    def test_analytics_dashboard_endpoint(self):
        """Test analytics dashboard endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard")
        assert response.status_code in [200, 401, 403, 422]
