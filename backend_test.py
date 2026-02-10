#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for YOU - Governance ERP Platform
Tests all endpoints including auth, grievances, WhatsApp, verification, and AI
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

class GovERPTester:
    def __init__(self, base_url="https://you-legislate.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_grievance_id = None

    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple:
        """Run a single API test and return success status and response"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing {name}... ({method} {endpoint})")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}", "PASS")
                try:
                    return True, response.json()
                except:
                    return True, {"status": "success", "raw_response": response.text}
            else:
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}", "FAIL")
                self.log(f"   Response: {response.text[:200]}...", "FAIL")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:500]
                })
                try:
                    return False, response.json()
                except:
                    return False, {"error": response.text}

        except requests.exceptions.Timeout:
            self.log(f"❌ FAILED - Request timeout", "FAIL")
            self.failed_tests.append({"test": name, "error": "timeout"})
            return False, {"error": "timeout"}
        except Exception as e:
            self.log(f"❌ FAILED - Error: {str(e)}", "FAIL")
            self.failed_tests.append({"test": name, "error": str(e)})
            return False, {"error": str(e)}

    def test_api_root(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "api/",
            200
        )
        return success

    def test_login(self):
        """Test login with provided credentials"""
        self.log("=== AUTHENTICATION TESTS ===")
        
        success, response = self.run_test(
            "Login with ramkumar@example.com",
            "POST",
            "api/auth/login",
            200,
            data={
                "email": "ramkumar@example.com",
                "password": "password123"
            }
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            self.log(f"✅ Login successful - User: {self.user_data.get('full_name', 'Unknown')}")
            self.log(f"   Role: {self.user_data.get('role', 'Unknown')}")
            self.log(f"   Politician ID: {self.user_data.get('politician_id', 'None')}")
            return True
        else:
            self.log("❌ Login failed - Cannot proceed with authenticated tests")
            return False

    def test_auth_me(self):
        """Test /auth/me endpoint"""
        if not self.token:
            return False
            
        success, response = self.run_test(
            "Get Current User Info",
            "GET",
            "api/auth/me",
            200
        )
        return success

    def test_grievance_endpoints(self):
        """Test all grievance-related endpoints"""
        if not self.token:
            return False
            
        self.log("=== GRIEVANCE MANAGEMENT TESTS ===")
        
        # Test get grievances
        success1, grievances = self.run_test(
            "Get All Grievances",
            "GET",
            "api/grievances/",
            200
        )
        
        if success1:
            self.log(f"   Found {len(grievances)} grievances")
            
        # Test grievance metrics
        success2, metrics = self.run_test(
            "Get Grievance Metrics",
            "GET",
            "api/grievances/metrics",
            200
        )
        
        if success2:
            self.log(f"   Metrics - Total: {metrics.get('total', 0)}, Resolved: {metrics.get('resolved', 0)}")
            
        # Test grievance stats
        success3, stats = self.run_test(
            "Get Grievance Stats Overview",
            "GET",
            "api/grievances/stats/overview",
            200
        )
        
        # Test create grievance
        success4, create_response = self.run_test(
            "Create Test Grievance",
            "POST",
            "api/grievances/",
            200,
            data={
                "village": "Test Village",
                "description": "Test grievance for API testing - road repair needed",
                "issue_type": "Infrastructure",
                "ai_priority": 7
            }
        )
        
        if success4 and 'id' in create_response:
            self.test_grievance_id = create_response['id']
            self.log(f"   Created test grievance: {self.test_grievance_id}")
            
            # Test get specific grievance
            success5, grievance_detail = self.run_test(
                "Get Specific Grievance",
                "GET",
                f"api/grievances/{self.test_grievance_id}",
                200
            )
            
            # Test update grievance status
            success6, update_response = self.run_test(
                "Update Grievance Status to IN_PROGRESS",
                "PATCH",
                f"api/grievances/{self.test_grievance_id}",
                200,
                data={"status": "IN_PROGRESS"}
            )
            
            return all([success1, success2, success3, success4, success5, success6])
        
        return all([success1, success2, success3])

    def test_whatsapp_endpoints(self):
        """Test WhatsApp integration endpoints"""
        if not self.token:
            return False
            
        self.log("=== WHATSAPP INTEGRATION TESTS ===")
        
        # Test WhatsApp status
        success1, status = self.run_test(
            "WhatsApp Bot Status",
            "GET",
            "api/whatsapp/status",
            200
        )
        
        if success1:
            self.log(f"   Twilio configured: {status.get('twilio_configured', False)}")
            self.log(f"   WhatsApp number: {status.get('whatsapp_number', 'Not set')}")
        
        # Test webhook endpoint (should accept POST)
        success2, webhook_response = self.run_test(
            "WhatsApp Webhook Endpoint",
            "POST",
            "api/whatsapp/webhook",
            200,
            data={
                "From": "whatsapp:+1234567890",
                "To": "whatsapp:+14155238886",
                "Body": "Test message for API testing",
                "MessageSid": "test_sid_123",
                "ProfileName": "Test User"
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        return all([success1, success2])

    def test_verification_endpoints(self):
        """Test photo verification endpoints"""
        if not self.token or not self.test_grievance_id:
            return False
            
        self.log("=== PHOTO VERIFICATION TESTS ===")
        
        # Test verification status
        success1, verification_status = self.run_test(
            "Get Verification Status",
            "GET",
            f"api/verification/verification-status/{self.test_grievance_id}",
            200
        )
        
        if success1:
            self.log(f"   Verification status: {verification_status.get('verification_status', 'None')}")
            self.log(f"   Has before photo: {verification_status.get('has_before_photo', False)}")
        
        # Test verify resolution (with dummy base64 image)
        dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        success2, verification_result = self.run_test(
            "Verify Resolution with Photo",
            "POST",
            "api/verification/verify-resolution",
            200,
            data={
                "grievance_id": self.test_grievance_id,
                "image_base64": dummy_image_b64,
                "notes": "Test verification - road has been repaired"
            }
        )
        
        if success2:
            self.log(f"   Verification result: {verification_result.get('verification', {}).get('is_verified', False)}")
            self.log(f"   Confidence: {verification_result.get('verification', {}).get('confidence_score', 0)}")
        
        return all([success1, success2])

    def test_ai_endpoints(self):
        """Test AI integration endpoints"""
        if not self.token:
            return False
            
        self.log("=== AI INTEGRATION TESTS ===")
        
        # Test AI grievance analysis
        success1, ai_analysis = self.run_test(
            "AI Grievance Analysis",
            "POST",
            "api/ai/analyze-grievance",
            200,
            data={
                "text": "The road in our village has many potholes and needs urgent repair",
                "analysis_type": "triage"
            }
        )
        
        if success1:
            self.log(f"   AI Analysis completed")
        
        # Test constituency summary generation
        success2, summary = self.run_test(
            "Generate Constituency Summary",
            "POST",
            "api/ai/generate-constituency-summary",
            200,
            data={}
        )
        
        if success2:
            self.log(f"   Summary generated: {len(summary.get('summary', ''))} characters")
        
        return all([success1, success2])

    def test_analytics_endpoints(self):
        """Test analytics and dashboard endpoints"""
        if not self.token:
            return False
            
        self.log("=== ANALYTICS & DASHBOARD TESTS ===")
        
        # Test dashboard data
        success1, dashboard = self.run_test(
            "Dashboard Analytics",
            "GET",
            "api/analytics/dashboard",
            200
        )
        
        if success1:
            self.log(f"   Dashboard data - Grievances: {dashboard.get('total_grievances', 0)}")
            self.log(f"   Resolved: {dashboard.get('resolved_grievances', 0)}")
            self.log(f"   Posts: {dashboard.get('total_posts', 0)}")
        
        return success1

    def run_all_tests(self):
        """Run comprehensive test suite"""
        self.log("🚀 Starting YOU - Governance ERP API Testing")
        self.log(f"Testing against: {self.base_url}")
        
        start_time = time.time()
        
        # Test sequence
        tests = [
            ("API Root", self.test_api_root),
            ("Authentication", self.test_login),
            ("User Profile", self.test_auth_me),
            ("Grievance Management", self.test_grievance_endpoints),
            ("WhatsApp Integration", self.test_whatsapp_endpoints),
            ("Photo Verification", self.test_verification_endpoints),
            ("AI Integration", self.test_ai_endpoints),
            ("Analytics Dashboard", self.test_analytics_endpoints),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.log(f"❌ {test_name} failed with exception: {e}", "ERROR")
                results[test_name] = False
        
        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        
        self.log("=" * 60)
        self.log("🏁 TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed}")
        self.log(f"Failed: {len(self.failed_tests)}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        self.log(f"Duration: {duration:.2f} seconds")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                self.log(f"  - {failure.get('test', 'Unknown')}: {failure.get('error', 'Status mismatch')}")
        
        # Expected stats validation
        self.log("\n📊 EXPECTED DATA VALIDATION:")
        if hasattr(self, 'dashboard_data'):
            expected_grievances = 8
            expected_resolved = 1
            expected_posts = 0
            
            actual_grievances = self.dashboard_data.get('total_grievances', 0)
            actual_resolved = self.dashboard_data.get('resolved_grievances', 0)
            actual_posts = self.dashboard_data.get('total_posts', 0)
            
            self.log(f"Grievances - Expected: {expected_grievances}, Actual: {actual_grievances}")
            self.log(f"Resolved - Expected: {expected_resolved}, Actual: {actual_resolved}")
            self.log(f"Posts - Expected: {expected_posts}, Actual: {actual_posts}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = GovERPTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())