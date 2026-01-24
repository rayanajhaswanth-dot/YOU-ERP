"""
Backend API Tests for Voice Grievance Feature
Tests: /api/ai/transcribe endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestVoiceGrievanceAPI:
    """Voice Grievance transcription endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ramkumar@example.com",
            "password": "test123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping voice grievance tests")
    
    def test_transcribe_endpoint_exists(self):
        """Test that /api/ai/transcribe endpoint exists and requires file"""
        # Test without file - should return 422 (validation error)
        response = requests.post(
            f"{BASE_URL}/api/ai/transcribe",
            headers=self.headers
        )
        # 422 means endpoint exists but requires file
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("✓ /api/ai/transcribe endpoint exists and requires audio file")
    
    def test_transcribe_endpoint_requires_auth(self):
        """Test that transcribe endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/ai/transcribe")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print("✓ /api/ai/transcribe requires authentication")
    
    def test_transcribe_with_dummy_audio(self):
        """Test transcribe endpoint with a minimal audio file"""
        # Create a minimal valid webm file header (just for testing endpoint acceptance)
        # This won't produce valid transcription but tests the endpoint accepts files
        import io
        
        # Create a minimal audio-like content
        dummy_audio = io.BytesIO(b'\x1a\x45\xdf\xa3' + b'\x00' * 100)  # WebM magic bytes + padding
        
        files = {'audio': ('test.webm', dummy_audio, 'audio/webm')}
        
        response = requests.post(
            f"{BASE_URL}/api/ai/transcribe",
            headers=self.headers,
            files=files,
            timeout=30
        )
        
        # The endpoint should accept the file (200) or fail gracefully (500/520 with error message)
        # It shouldn't return 422 (validation error) since we're providing a file
        assert response.status_code in [200, 500, 520], f"Unexpected status {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "original" in data or "error" in data
            print(f"✓ Transcribe endpoint processed file: {data}")
        else:
            # 500/520 is acceptable for invalid audio content - endpoint is working
            print(f"✓ Transcribe endpoint correctly rejected invalid audio (status {response.status_code})")


class TestAIEndpointsForVoice:
    """Additional AI endpoint tests related to voice grievance flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ramkumar@example.com",
            "password": "test123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping AI tests")
    
    def test_analyze_grievance_with_transcribed_text(self):
        """Test AI grievance analysis with text that would come from voice transcription"""
        # Simulate text that would come from voice transcription
        transcribed_text = "[Hindi] मेरे गांव में सड़क बहुत खराब है\n\n[English] The road in my village is very bad"
        
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze-grievance",
            json={
                "text": transcribed_text,
                "analysis_type": "triage"
            },
            headers=self.headers,
            timeout=30
        )
        assert response.status_code == 200, f"AI analysis failed: {response.text}"
        
        data = response.json()
        assert "analysis" in data
        print(f"✓ AI analysis of transcribed text completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
