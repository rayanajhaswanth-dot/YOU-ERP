"""
Backend API Tests for YOU - Governance ERP
Tests: WhatsApp Bot Status, AI Priority Analysis, Grievance CRUD, 10-Step Workflow
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWhatsAppBotStatus:
    """WhatsApp bot status endpoint tests"""
    
    def test_whatsapp_status_endpoint(self):
        """Test /api/whatsapp/status returns active with multi-lingual features"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200, f"WhatsApp status failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "active"
        assert data["twilio_configured"] == True
        assert "whatsapp_number" in data
        
        # Verify multi-lingual features are listed
        features = data.get("features", [])
        assert len(features) > 0, "No features listed"
        
        # Check for multi-lingual support
        features_text = " ".join(features).lower()
        assert "multi-lingual" in features_text or "telugu" in features_text or "hindi" in features_text, \
            f"Multi-lingual support not mentioned in features: {features}"
        
        print(f"✓ WhatsApp status: {data['status']}")
        print(f"✓ Features: {features}")


class TestAIPriorityAnalysis:
    """AI priority analysis endpoint tests"""
    
    def test_analyze_priority_returns_priority_level(self):
        """Test /api/ai/analyze_priority returns priority_level (not priority)"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "road damaged with potholes", "category": "Infrastructure"}
        )
        assert response.status_code == 200, f"AI priority analysis failed: {response.text}"
        
        data = response.json()
        # CRITICAL: Must return priority_level, not priority
        assert "priority_level" in data, f"Response missing 'priority_level': {data}"
        assert "category" in data
        assert "deadline_hours" in data
        
        # Verify priority_level is valid
        valid_priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        assert data["priority_level"] in valid_priorities, f"Invalid priority_level: {data['priority_level']}"
        
        print(f"✓ AI Priority Analysis: {data}")
    
    def test_analyze_priority_critical_health(self):
        """Test health issues get CRITICAL priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "hospital has no doctors, dengue outbreak", "category": "Health & Sanitation"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["priority_level"] == "CRITICAL"
        assert data["category"] == "Health & Sanitation"
        assert data["deadline_hours"] == 4
        print(f"✓ Health issue correctly marked CRITICAL: {data}")
    
    def test_analyze_priority_high_water(self):
        """Test water issues get HIGH priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "no water supply in village for 3 days", "category": "Water & Irrigation"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["priority_level"] == "HIGH"
        assert data["deadline_hours"] == 24
        print(f"✓ Water issue correctly marked HIGH: {data}")
    
    def test_analyze_priority_emergency_override(self):
        """Test emergency keywords override category priority"""
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze_priority",
            json={"text": "fire in the building, people trapped", "category": "Miscellaneous"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["priority_level"] == "CRITICAL"
        assert data["deadline_hours"] == 2  # Emergency gets 2 hours
        print(f"✓ Emergency correctly overrides to CRITICAL: {data}")


class TestGrievanceCRUD:
    """Grievance CRUD endpoint tests"""
    
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
            pytest.skip("Authentication failed - skipping grievance tests")
    
    def test_get_grievances_list(self):
        """Test GET /api/grievances/ returns list"""
        response = requests.get(f"{BASE_URL}/api/grievances/", headers=self.headers)
        assert response.status_code == 200, f"Get grievances failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} grievances")
        
        if len(data) > 0:
            grievance = data[0]
            assert "id" in grievance
            assert "status" in grievance
            print(f"✓ First grievance: ID={grievance['id'][:8]}, Status={grievance['status']}")
    
    def test_create_grievance(self):
        """Test POST /api/grievances/ creates new grievance"""
        grievance_data = {
            "citizen_name": "TEST_Workflow_User",
            "citizen_phone": "+919876543210",
            "location": "TEST_Village_Workflow",
            "category": "Infrastructure & Roads",
            "description": "TEST: Road has multiple potholes causing accidents",
            "priority_level": "HIGH"
        }
        
        response = requests.post(f"{BASE_URL}/api/grievances/", json=grievance_data, headers=self.headers)
        assert response.status_code == 200, f"Create grievance failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "message" in data
        print(f"✓ Created grievance: {data['id']}")
        
        # Store for workflow tests
        self.__class__.created_grievance_id = data["id"]
        return data["id"]
    
    def test_get_single_grievance(self):
        """Test GET /api/grievances/{id} returns single grievance"""
        # First create a grievance
        grievance_data = {
            "citizen_name": "TEST_Single_User",
            "location": "TEST_Village_Single",
            "category": "Water & Irrigation",
            "description": "TEST: No water supply for 2 days",
            "priority_level": "HIGH"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/grievances/", json=grievance_data, headers=self.headers)
        assert create_response.status_code == 200
        grievance_id = create_response.json()["id"]
        
        # Now get the single grievance
        response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert response.status_code == 200, f"Get single grievance failed: {response.text}"
        
        data = response.json()
        assert data["id"] == grievance_id
        assert "description" in data
        assert "status" in data
        print(f"✓ Retrieved single grievance: {data['id'][:8]}")
    
    def test_grievance_metrics(self):
        """Test GET /api/grievances/metrics returns comprehensive metrics"""
        response = requests.get(f"{BASE_URL}/api/grievances/metrics", headers=self.headers)
        assert response.status_code == 200, f"Metrics failed: {response.text}"
        
        data = response.json()
        required_fields = ["total", "resolved", "unresolved", "pending", "in_progress", "long_pending", "resolution_rate"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Metrics: Total={data['total']}, Resolved={data['resolved']}, Pending={data['pending']}")


class TestGrievanceWorkflow:
    """10-Step Grievance Workflow tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and create test grievance"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ramkumar@example.com",
            "password": "test123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed - skipping workflow tests")
    
    def _create_test_grievance(self):
        """Helper to create a test grievance"""
        grievance_data = {
            "citizen_name": f"TEST_Workflow_{uuid.uuid4().hex[:6]}",
            "citizen_phone": "+919876543210",
            "location": "TEST_Village_Workflow",
            "category": "Infrastructure & Roads",
            "description": "TEST: Workflow test grievance",
            "priority_level": "MEDIUM"
        }
        
        response = requests.post(f"{BASE_URL}/api/grievances/", json=grievance_data, headers=self.headers)
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_start_work_endpoint(self):
        """Test PUT /api/grievances/{id}/start-work changes status to IN_PROGRESS"""
        # Create a new grievance
        grievance_id = self._create_test_grievance()
        
        # Verify initial status is PENDING
        get_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "PENDING"
        
        # Start work
        response = requests.put(f"{BASE_URL}/api/grievances/{grievance_id}/start-work", headers=self.headers)
        assert response.status_code == 200, f"Start work failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert "message" in data
        
        # Verify status changed in database
        verify_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "IN_PROGRESS"
        
        print(f"✓ Start Work: Status changed to IN_PROGRESS")
        return grievance_id
    
    def test_upload_resolution_photo_endpoint(self):
        """Test PUT /api/grievances/{id}/upload-resolution-photo stores resolution_image_url"""
        # Create and start work on grievance
        grievance_id = self._create_test_grievance()
        requests.put(f"{BASE_URL}/api/grievances/{grievance_id}/start-work", headers=self.headers)
        
        # Upload resolution photo
        photo_url = "https://example.com/resolution-photo-test.jpg"
        response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/upload-resolution-photo",
            json={"resolution_image_url": photo_url},
            headers=self.headers
        )
        assert response.status_code == 200, f"Upload photo failed: {response.text}"
        
        data = response.json()
        assert data["can_resolve"] == True
        assert "message" in data
        
        # Verify photo URL stored in database
        verify_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["resolution_image_url"] == photo_url
        
        print(f"✓ Upload Resolution Photo: URL stored successfully")
        return grievance_id
    
    def test_resolve_requires_photo_verification(self):
        """Test PUT /api/grievances/{id}/resolve requires photo verification first"""
        # Create and start work on grievance (but don't upload photo)
        grievance_id = self._create_test_grievance()
        requests.put(f"{BASE_URL}/api/grievances/{grievance_id}/start-work", headers=self.headers)
        
        # Try to resolve without photo - should fail
        response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/resolve",
            json={"send_notification": False},
            headers=self.headers
        )
        assert response.status_code == 400, f"Resolve should fail without photo: {response.text}"
        
        data = response.json()
        assert "photo" in data["detail"].lower() or "verification" in data["detail"].lower()
        
        print(f"✓ Resolve correctly requires photo verification")
    
    def test_resolve_with_photo_verification(self):
        """Test PUT /api/grievances/{id}/resolve works after photo upload"""
        # Create, start work, and upload photo
        grievance_id = self._create_test_grievance()
        requests.put(f"{BASE_URL}/api/grievances/{grievance_id}/start-work", headers=self.headers)
        
        photo_url = "https://example.com/resolution-photo-complete.jpg"
        requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/upload-resolution-photo",
            json={"resolution_image_url": photo_url},
            headers=self.headers
        )
        
        # Now resolve should work
        response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/resolve",
            json={"send_notification": False},
            headers=self.headers
        )
        assert response.status_code == 200, f"Resolve failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "RESOLVED"
        
        # Verify status in database
        verify_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "RESOLVED"
        
        print(f"✓ Resolve with photo verification: Status changed to RESOLVED")
    
    def test_full_workflow_sequence(self):
        """Test complete 10-step workflow: PENDING -> IN_PROGRESS -> (photo) -> RESOLVED"""
        # Step 1: Create grievance (PENDING)
        grievance_id = self._create_test_grievance()
        
        get_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert get_response.json()["status"] == "PENDING"
        print(f"  Step 1: Created grievance - Status: PENDING")
        
        # Step 2: Start work (IN_PROGRESS)
        start_response = requests.put(f"{BASE_URL}/api/grievances/{grievance_id}/start-work", headers=self.headers)
        assert start_response.status_code == 200
        
        get_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert get_response.json()["status"] == "IN_PROGRESS"
        print(f"  Step 2: Started work - Status: IN_PROGRESS")
        
        # Step 3: Upload resolution photo
        photo_url = "https://example.com/full-workflow-photo.jpg"
        photo_response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/upload-resolution-photo",
            json={"resolution_image_url": photo_url},
            headers=self.headers
        )
        assert photo_response.status_code == 200
        
        get_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert get_response.json()["resolution_image_url"] == photo_url
        print(f"  Step 3: Uploaded photo - Photo URL stored")
        
        # Step 4: Resolve grievance
        resolve_response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/resolve",
            json={"send_notification": False},
            headers=self.headers
        )
        assert resolve_response.status_code == 200
        
        get_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert get_response.json()["status"] == "RESOLVED"
        print(f"  Step 4: Resolved - Status: RESOLVED")
        
        print(f"✓ Full workflow completed successfully!")


class TestFeedbackRating:
    """Feedback rating endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ramkumar@example.com",
            "password": "test123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
    
    def test_record_feedback(self):
        """Test PUT /api/grievances/{id}/feedback records rating"""
        # Create and resolve a grievance first
        grievance_data = {
            "citizen_name": "TEST_Feedback_User",
            "location": "TEST_Village_Feedback",
            "category": "Miscellaneous",
            "description": "TEST: Feedback test grievance",
            "priority_level": "LOW"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/grievances/", json=grievance_data, headers=self.headers)
        grievance_id = create_response.json()["id"]
        
        # Start work, upload photo, resolve
        requests.put(f"{BASE_URL}/api/grievances/{grievance_id}/start-work", headers=self.headers)
        requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/upload-resolution-photo",
            json={"resolution_image_url": "https://example.com/feedback-test.jpg"},
            headers=self.headers
        )
        requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/resolve",
            json={"send_notification": False},
            headers=self.headers
        )
        
        # Record feedback
        response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/feedback",
            json={"rating": 5},
            headers=self.headers
        )
        assert response.status_code == 200, f"Feedback failed: {response.text}"
        
        data = response.json()
        assert data["rating"] == 5
        
        # Verify in database
        verify_response = requests.get(f"{BASE_URL}/api/grievances/{grievance_id}", headers=self.headers)
        assert verify_response.json()["feedback_rating"] == 5
        
        print(f"✓ Feedback rating recorded: 5/5")
    
    def test_feedback_validation(self):
        """Test feedback rating validation (1-5)"""
        # Create a grievance
        grievance_data = {
            "citizen_name": "TEST_Feedback_Validation",
            "location": "TEST_Village",
            "category": "Miscellaneous",
            "description": "TEST: Validation test",
            "priority_level": "LOW"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/grievances/", json=grievance_data, headers=self.headers)
        grievance_id = create_response.json()["id"]
        
        # Try invalid rating
        response = requests.put(
            f"{BASE_URL}/api/grievances/{grievance_id}/feedback",
            json={"rating": 10},
            headers=self.headers
        )
        assert response.status_code == 400
        print(f"✓ Invalid rating (10) correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
