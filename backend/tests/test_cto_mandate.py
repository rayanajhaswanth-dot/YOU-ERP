"""
Test Suite for CTO Mandate Implementation
Tests: Language Detection, Translation, AI Priority Analysis, Analytics, WhatsApp Bot Status
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://legismate.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "ramkumar@example.com"
TEST_PASSWORD = "test123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


class TestWhatsAppBotStatus:
    """WhatsApp Bot Status Endpoint Tests"""
    
    def test_whatsapp_status_returns_version_2(self):
        """WhatsApp bot status should return version 2.0 with CTO Mandate features"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "active"
        assert "2.0" in data["version"]
        assert "CTO Mandate" in data["version"]
    
    def test_whatsapp_status_has_9_features(self):
        """WhatsApp bot should list 9 key features"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        
        data = response.json()
        features = data.get("features", [])
        assert len(features) >= 9, f"Expected 9+ features, got {len(features)}"
        
        # Check for key features
        feature_text = " ".join(features).lower()
        assert "language" in feature_text, "Missing language detection feature"
        assert "pdf" in feature_text, "Missing PDF extraction feature"
        assert "image" in feature_text or "ocr" in feature_text, "Missing image OCR feature"
        assert "voice" in feature_text or "whisper" in feature_text, "Missing voice transcription feature"
    
    def test_whatsapp_status_has_12_categories(self):
        """WhatsApp bot should list 12 official English categories"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        
        data = response.json()
        categories = data.get("categories", [])
        assert len(categories) == 12, f"Expected 12 categories, got {len(categories)}"
        
        # Verify all categories are in English
        expected_categories = [
            "Water & Irrigation", "Agriculture", "Forests & Environment",
            "Health & Sanitation", "Education", "Infrastructure & Roads",
            "Law & Order", "Welfare Schemes", "Finance & Taxation",
            "Urban & Rural Development", "Electricity", "Miscellaneous"
        ]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"


class TestLanguageDetection:
    """Language Detection Endpoint Tests"""
    
    def test_detect_telugu(self):
        """Should correctly detect Telugu text"""
        response = requests.post(
            f"{BASE_URL}/api/ai/detect_language",
            json={"text": "నా గ్రామంలో నీటి సమస్య ఉంది"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "te", f"Expected 'te', got {data['language']}"
    
    def test_detect_hindi(self):
        """Should correctly detect Hindi text"""
        response = requests.post(
            f"{BASE_URL}/api/ai/detect_language",
            json={"text": "मेरे गांव में पानी की समस्या है"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "hi", f"Expected 'hi', got {data['language']}"
    
    def test_detect_tamil(self):
        """Should correctly detect Tamil text"""
        response = requests.post(
            f"{BASE_URL}/api/ai/detect_language",
            json={"text": "எங்கள் கிராமத்தில் தண்ணீர் பிரச்சனை உள்ளது"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "ta", f"Expected 'ta', got {data['language']}"
    
    def test_detect_english(self):
        """Should correctly detect English text"""
        response = requests.post(
            f"{BASE_URL}/api/ai/detect_language",
            json={"text": "There is a water problem in my village"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en", f"Expected 'en', got {data['language']}"
    
    def test_detect_kannada(self):
        """Should correctly detect Kannada text"""
        response = requests.post(
            f"{BASE_URL}/api/ai/detect_language",
            json={"text": "ನಮ್ಮ ಹಳ್ಳಿಯಲ್ಲಿ ನೀರಿನ ಸಮಸ್ಯೆ ಇದೆ"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "kn", f"Expected 'kn', got {data['language']}"


class TestAIPriorityAnalysis:
    """AI Priority Analysis Endpoint Tests"""
    
    def test_priority_returns_english_category(self):
        """AI priority analysis should return English category"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "Water supply problem in my village"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Category must be in English
        assert "category" in data
        assert data["category"] in [
            "Water & Irrigation", "Agriculture", "Forests & Environment",
            "Health & Sanitation", "Education", "Infrastructure & Roads",
            "Law & Order", "Welfare Schemes", "Finance & Taxation",
            "Urban & Rural Development", "Electricity", "Miscellaneous"
        ], f"Category not in official list: {data['category']}"
    
    def test_water_issue_high_priority(self):
        """Water issues should be HIGH priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "No drinking water in our village for 3 days"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["category"] == "Water & Irrigation"
        assert data["priority_level"] == "HIGH"
        assert data["deadline_hours"] == 24
    
    def test_health_issue_critical_priority(self):
        """Health emergencies should be CRITICAL priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "Hospital has no medicines, patients suffering"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["category"] == "Health & Sanitation"
        assert data["priority_level"] == "CRITICAL"
        assert data["deadline_hours"] == 4
    
    def test_electricity_issue_critical_priority(self):
        """Electricity issues should be CRITICAL priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "Open electric wire on the road, very dangerous"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["priority_level"] == "CRITICAL"
        assert data["deadline_hours"] == 4
    
    def test_road_issue_high_priority(self):
        """Road/Infrastructure issues should be HIGH priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "Big pothole on main road causing accidents"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["category"] == "Infrastructure & Roads"
        assert data["priority_level"] == "HIGH"


class TestGrievanceAnalytics:
    """Grievance Analytics Endpoint Tests"""
    
    def test_analytics_returns_normalized_categories(self, auth_token):
        """Analytics should return normalized English categories"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/grievance-stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "total" in data
        assert "by_category" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert "categories" in data
        
        # Verify categories are in English
        official_categories = [
            "Water & Irrigation", "Agriculture", "Forests & Environment",
            "Health & Sanitation", "Education", "Infrastructure & Roads",
            "Law & Order", "Welfare Schemes", "Finance & Taxation",
            "Urban & Rural Development", "Electricity", "Miscellaneous"
        ]
        
        for cat_data in data["by_category"]:
            assert cat_data["name"] in official_categories, f"Non-English category found: {cat_data['name']}"
    
    def test_analytics_total_count(self, auth_token):
        """Analytics should return correct total count"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/grievance-stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Total should be >= 109 (as mentioned in request)
        assert data["total"] >= 100, f"Expected 100+ grievances, got {data['total']}"
    
    def test_analytics_has_12_official_categories(self, auth_token):
        """Analytics should list all 12 official categories"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/grievance-stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        categories = data.get("categories", [])
        assert len(categories) == 12, f"Expected 12 categories, got {len(categories)}"


class TestTranslation:
    """Translation Endpoint Tests"""
    
    def test_translate_to_telugu(self, auth_token):
        """Should translate English to Telugu"""
        response = requests.post(
            f"{BASE_URL}/api/ai/translate",
            json={"text": "Your grievance has been registered", "target_lang": "te"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "translated" in data
        assert data["target_lang"] == "te"
        # Telugu text should contain Telugu characters
        translated = data["translated"]
        has_telugu = any(0x0C00 <= ord(c) <= 0x0C7F for c in translated)
        assert has_telugu, f"Translation doesn't contain Telugu characters: {translated}"
    
    def test_translate_to_hindi(self, auth_token):
        """Should translate English to Hindi"""
        response = requests.post(
            f"{BASE_URL}/api/ai/translate",
            json={"text": "Your grievance has been registered", "target_lang": "hi"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "translated" in data
        assert data["target_lang"] == "hi"
        # Hindi text should contain Devanagari characters
        translated = data["translated"]
        has_hindi = any(0x0900 <= ord(c) <= 0x097F for c in translated)
        assert has_hindi, f"Translation doesn't contain Hindi characters: {translated}"
    
    def test_no_translation_for_english(self, auth_token):
        """Should return same text when target is English"""
        original_text = "Your grievance has been registered"
        response = requests.post(
            f"{BASE_URL}/api/ai/translate",
            json={"text": original_text, "target_lang": "en"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["translated"] == original_text


class TestGrievanceWorkflow:
    """Grievance CRUD and Workflow Tests"""
    
    def test_get_grievances_list(self, auth_token):
        """Should return list of grievances"""
        response = requests.get(
            f"{BASE_URL}/api/grievances/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 100, f"Expected 100+ grievances, got {len(data)}"
    
    def test_create_grievance_with_english_category(self, auth_token):
        """Should create grievance with English category"""
        payload = {
            "citizen_name": "TEST_CTO_Mandate_User",
            "citizen_phone": "9876543210",
            "location": "Test Village",
            "village": "Test Village",
            "category": "Water & Irrigation",
            "description": "Test grievance for CTO Mandate testing",
            "priority_level": "HIGH",
            "status": "PENDING"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/grievances/",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code in [200, 201], f"Create failed: {response.text}"
        
        data = response.json()
        assert data["category"] == "Water & Irrigation"
        assert data["citizen_name"] == "TEST_CTO_Mandate_User"
        
        # Cleanup - delete the test grievance
        grievance_id = data.get("id")
        if grievance_id:
            requests.delete(
                f"{BASE_URL}/api/grievances/{grievance_id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
    
    def test_grievance_metrics(self, auth_token):
        """Should return grievance metrics"""
        response = requests.get(
            f"{BASE_URL}/api/grievances/metrics",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data or "total_grievances" in data


class TestAuthentication:
    """Authentication Tests"""
    
    def test_login_success(self):
        """Should login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["email"] == TEST_EMAIL
        assert data["role"] == "politician"
    
    def test_login_invalid_credentials(self):
        """Should reject invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@example.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 400, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
