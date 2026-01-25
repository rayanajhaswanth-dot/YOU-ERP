"""
Backend API Tests for WhatsApp with OpenAI Whisper and GPT-4o Vision
Tests: WhatsApp webhook with OpenAI Whisper voice transcription, GPT-4o image analysis, welcome/help messages
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
    return 'https://legislator-hub.preview.emergentagent.com'

BASE_URL = get_backend_url()


class TestWhatsAppStatus:
    """WhatsApp status endpoint tests"""
    
    def test_whatsapp_status_endpoint(self):
        """Test /api/whatsapp/status returns active status"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200, f"Status endpoint failed: {response.text}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "active"
        assert "twilio_configured" in data
        assert "whatsapp_number" in data
        print(f"✓ WhatsApp status: {data}")


class TestWhatsAppWebhookWelcomeMessage:
    """Test WhatsApp webhook welcome message mentions voice support"""
    
    def test_welcome_message_hi(self):
        """Test 'hi' command returns welcome message with voice support"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': 'hi',
            'MessageSid': 'TEST_MSG_001',
            'ProfileName': 'Test User',
            'NumMedia': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data
        )
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        # Response should be XML (TwiML)
        assert 'application/xml' in response.headers.get('content-type', '')
        
        # Check response contains voice message mention
        response_text = response.text
        assert 'voice message' in response_text.lower() or '🎤' in response_text, \
            f"Welcome message should mention voice support. Got: {response_text}"
        
        print(f"✓ Welcome message mentions voice support")
    
    def test_welcome_message_hello(self):
        """Test 'hello' command returns welcome message with voice support"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': 'hello',
            'MessageSid': 'TEST_MSG_002',
            'ProfileName': 'Test User',
            'NumMedia': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data
        )
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        response_text = response.text
        assert 'voice message' in response_text.lower() or '🎤' in response_text, \
            f"Welcome message should mention voice support. Got: {response_text}"
        
        print(f"✓ Hello command returns welcome with voice support")
    
    def test_welcome_message_namaste(self):
        """Test 'namaste' command returns welcome message with voice support"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': 'namaste',
            'MessageSid': 'TEST_MSG_003',
            'ProfileName': 'Test User',
            'NumMedia': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data
        )
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        response_text = response.text
        assert 'voice message' in response_text.lower() or '🎤' in response_text, \
            f"Welcome message should mention voice support. Got: {response_text}"
        
        print(f"✓ Namaste command returns welcome with voice support")


class TestWhatsAppWebhookHelpCommand:
    """Test WhatsApp webhook help command mentions voice transcription"""
    
    def test_help_command_mentions_voice(self):
        """Test 'help' command mentions voice message transcription"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': 'help',
            'MessageSid': 'TEST_MSG_004',
            'ProfileName': 'Test User',
            'NumMedia': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data
        )
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        response_text = response.text
        
        # Check for voice message mention
        assert 'voice message' in response_text.lower() or '🎤' in response_text, \
            f"Help should mention voice messages. Got: {response_text}"
        
        # Check for Indian language support mention
        indian_languages = ['hindi', 'tamil', 'telugu', 'kannada', 'malayalam', 'bengali', 'marathi', 'gujarati', 'punjabi']
        has_language_mention = any(lang in response_text.lower() for lang in indian_languages)
        assert has_language_mention or 'indian language' in response_text.lower() or 'transcribed' in response_text.lower(), \
            f"Help should mention Indian language support. Got: {response_text}"
        
        print(f"✓ Help command mentions voice transcription and Indian languages")


class TestWhatsAppWebhookAudioHandling:
    """Test WhatsApp webhook handles audio/voice media types"""
    
    def test_webhook_accepts_audio_ogg(self):
        """Test webhook accepts audio/ogg media type (WhatsApp voice format)"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': '',
            'MessageSid': 'TEST_MSG_005',
            'ProfileName': 'Test User',
            'NumMedia': '1',
            'MediaUrl0': 'https://api.twilio.com/test-audio.ogg',
            'MediaContentType0': 'audio/ogg'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data,
            timeout=60  # Voice processing may take time
        )
        
        # Should return 200 (even if audio processing fails, it should handle gracefully)
        assert response.status_code == 200, f"Webhook failed for audio: {response.text}"
        
        # Response should be XML
        assert 'application/xml' in response.headers.get('content-type', '')
        
        # Should contain some response (either success or graceful error)
        response_text = response.text
        assert '<Message>' in response_text, f"Should return TwiML message. Got: {response_text}"
        
        print(f"✓ Webhook accepts audio/ogg media type")
    
    def test_webhook_accepts_audio_mp3(self):
        """Test webhook accepts audio/mp3 media type"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': '',
            'MessageSid': 'TEST_MSG_006',
            'ProfileName': 'Test User',
            'NumMedia': '1',
            'MediaUrl0': 'https://api.twilio.com/test-audio.mp3',
            'MediaContentType0': 'audio/mp3'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data,
            timeout=60
        )
        
        assert response.status_code == 200, f"Webhook failed for audio: {response.text}"
        assert 'application/xml' in response.headers.get('content-type', '')
        
        print(f"✓ Webhook accepts audio/mp3 media type")


class TestWhatsAppWebhookStatusCommand:
    """Test WhatsApp webhook status command"""
    
    def test_status_command(self):
        """Test 'status' command returns grievance status"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': 'status',
            'MessageSid': 'TEST_MSG_008',
            'ProfileName': 'Test User',
            'NumMedia': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data
        )
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        response_text = response.text
        # Should contain either grievances or "no grievances" message
        assert 'grievance' in response_text.lower() or 'Grievance' in response_text, \
            f"Status should mention grievances. Got: {response_text}"
        
        print(f"✓ Status command works correctly")


class TestWhatsAppWebhookTextGrievance:
    """Test WhatsApp webhook creates grievance from text"""
    
    def test_text_grievance_creation(self):
        """Test that text message creates a grievance"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': 'TEST_WHATSAPP: The road in my village is completely damaged and needs urgent repair',
            'MessageSid': 'TEST_MSG_009',
            'ProfileName': 'Test User',
            'NumMedia': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data,
            timeout=60  # AI analysis may take time
        )
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        response_text = response.text
        
        # Should contain success indicators
        success_indicators = ['registered', 'success', 'reference', 'priority', 'category']
        has_success = any(indicator in response_text.lower() for indicator in success_indicators)
        assert has_success, f"Should indicate grievance was registered. Got: {response_text}"
        
        print(f"✓ Text grievance created successfully")


class TestWhatsAppCodeReviewOpenAI:
    """Code review tests for WhatsApp OpenAI Whisper and GPT-4o implementation"""
    
    def test_openai_whisper_import(self):
        """Verify OpenAISpeechToText import exists in whatsapp_routes.py"""
        whatsapp_routes_path = '/app/backend/routes/whatsapp_routes.py'
        assert os.path.exists(whatsapp_routes_path), "whatsapp_routes.py not found"
        
        with open(whatsapp_routes_path, 'r') as f:
            content = f.read()
        
        # Check for OpenAI Whisper import
        assert "OpenAISpeechToText" in content, "Should import OpenAISpeechToText for Whisper"
        assert "from emergentintegrations.llm.openai import OpenAISpeechToText" in content, \
            "Should import OpenAISpeechToText from emergentintegrations.llm.openai"
        
        print(f"✓ OpenAISpeechToText import verified")
    
    def test_whisper_model_usage(self):
        """Verify whisper-1 model is used for transcription"""
        whatsapp_routes_path = '/app/backend/routes/whatsapp_routes.py'
        
        with open(whatsapp_routes_path, 'r') as f:
            content = f.read()
        
        # Check for whisper-1 model usage
        assert "whisper-1" in content, "Should use whisper-1 model for transcription"
        assert "stt.transcribe" in content or "transcribe(" in content, \
            "Should call transcribe method"
        
        print(f"✓ Whisper-1 model usage verified")
    
    def test_gpt4o_vision_usage(self):
        """Verify GPT-4o is used for image analysis"""
        whatsapp_routes_path = '/app/backend/routes/whatsapp_routes.py'
        
        with open(whatsapp_routes_path, 'r') as f:
            content = f.read()
        
        # Check for GPT-4o vision usage
        assert "gpt-4o" in content, "Should use GPT-4o for image analysis"
        assert "ImageContent" in content, "Should use ImageContent for image processing"
        
        print(f"✓ GPT-4o Vision usage verified")
    
    def test_image_content_import(self):
        """Verify ImageContent import exists"""
        whatsapp_routes_path = '/app/backend/routes/whatsapp_routes.py'
        
        with open(whatsapp_routes_path, 'r') as f:
            content = f.read()
        
        # Check for ImageContent import
        assert "ImageContent" in content, "Should import ImageContent"
        assert "from emergentintegrations.llm.chat import" in content and "ImageContent" in content, \
            "Should import ImageContent from emergentintegrations.llm.chat"
        
        print(f"✓ ImageContent import verified")
    
    def test_voice_processing_code_structure(self):
        """Verify voice processing code exists with OpenAI Whisper"""
        whatsapp_routes_path = '/app/backend/routes/whatsapp_routes.py'
        
        with open(whatsapp_routes_path, 'r') as f:
            content = f.read()
        
        # Check for audio handling code
        assert "audio/" in content, "Should check for audio content type"
        assert "OpenAISpeechToText" in content, "Should use OpenAISpeechToText for audio"
        
        # Check for voice transcription in welcome/help messages
        assert "voice message" in content.lower() or "🎤" in content, "Should mention voice in messages"
        
        print(f"✓ Voice processing code structure verified with OpenAI Whisper")


class TestWhatsAppWebhookImageHandling:
    """Test WhatsApp webhook handles image media types"""
    
    def test_webhook_accepts_image_jpeg(self):
        """Test webhook accepts image/jpeg media type"""
        form_data = {
            'From': 'whatsapp:+919876543210',
            'To': 'whatsapp:+14155238886',
            'Body': '',
            'MessageSid': 'TEST_MSG_010',
            'ProfileName': 'Test User',
            'NumMedia': '1',
            'MediaUrl0': 'https://api.twilio.com/test-image.jpg',
            'MediaContentType0': 'image/jpeg'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data=form_data,
            timeout=60  # Image processing may take time
        )
        
        # Should return 200 (even if image processing fails, it should handle gracefully)
        assert response.status_code == 200, f"Webhook failed for image: {response.text}"
        
        # Response should be XML
        assert 'application/xml' in response.headers.get('content-type', '')
        
        # Should contain some response (either success or graceful error)
        response_text = response.text
        assert '<Message>' in response_text, f"Should return TwiML message. Got: {response_text}"
        
        print(f"✓ Webhook accepts image/jpeg media type")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
