import requests
import sys
import json
from datetime import datetime, timedelta

class ParkOnAPITester:
    def __init__(self, base_url="https://london-parking-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, params=data, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and 'message' in response_data:
                        print(f"   Message: {response_data['message']}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test("Health Check", "GET", "/health", 200)

    def test_guest_session(self):
        """Test guest session creation"""
        success, response = self.run_test("Guest Session", "POST", "/auth/guest", 200)
        if success and 'data' in response:
            print(f"   Guest ID: {response['data'].get('guest_id', 'N/A')}")
        return success

    def test_user_registration(self):
        """Test user registration"""
        test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@example.com"
        user_data = {
            "email": test_email,
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        success, response = self.run_test("User Registration", "POST", "/auth/register", 200, user_data)
        if success and 'data' in response:
            self.token = response['data'].get('access_token')
            self.user_data = response['data'].get('user')
            print(f"   User ID: {self.user_data.get('id', 'N/A')}")
            print(f"   User Role: {self.user_data.get('role', 'N/A')}")
        return success

    def test_user_login(self):
        """Test user login with existing user"""
        if not self.user_data:
            print("❌ Skipping login test - no user data available")
            return False
            
        login_data = {
            "email": self.user_data['email'],
            "password": "TestPass123!"
        }
        
        success, response = self.run_test("User Login", "POST", "/auth/login", 200, login_data)
        if success and 'data' in response:
            self.token = response['data'].get('access_token')
            print(f"   Login successful for: {self.user_data['email']}")
        return success

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.token:
            print("❌ Skipping current user test - no token available")
            return False
            
        return self.run_test("Get Current User", "GET", "/auth/me", 200)

    def test_parking_search(self):
        """Test parking search endpoint"""
        search_params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "radius_km": 2.0
        }
        
        success, response = self.run_test("Parking Search", "GET", "/parking/search", 200, search_params)
        if success and 'data' in response:
            spots = response['data']
            print(f"   Found {len(spots)} parking spots")
            if spots:
                print(f"   First spot: {spots[0].get('name', 'N/A')}")
                print(f"   Provider: {spots[0].get('provider', 'N/A')}")
        return success

    def test_parking_search_with_filters(self):
        """Test parking search with premium filters"""
        search_params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "radius_km": 2.0,
            "spot_type": "standard",
            "max_price": 10.0
        }
        
        success, response = self.run_test("Parking Search with Filters", "GET", "/parking/search", 200, search_params)
        if success and 'data' in response:
            spots = response['data']
            print(f"   Found {len(spots)} filtered parking spots")
        return success

    def test_parking_spot_details(self):
        """Test getting parking spot details"""
        spot_id = "tfl_cp_001"  # Using mock TfL spot ID
        return self.run_test("Parking Spot Details", "GET", f"/parking/spots/{spot_id}", 200)

    def test_subscription_plans(self):
        """Test getting subscription plans"""
        success, response = self.run_test("Subscription Plans", "GET", "/subscription/plans", 200)
        if success and 'data' in response:
            plans = response['data']
            print(f"   Available plans: {len(plans)}")
            for plan in plans:
                print(f"   - {plan.get('name', 'N/A')}: £{plan.get('price', 'N/A')}")
        return success

    def test_premium_upgrade(self):
        """Test premium upgrade"""
        if not self.token:
            print("❌ Skipping premium upgrade test - no token available")
            return False
            
        upgrade_data = {"plan_name": "Premium Monthly"}
        success, response = self.run_test("Premium Upgrade", "POST", "/subscription/upgrade", 200, upgrade_data)
        if success:
            print("   Successfully upgraded to Premium")
        return success

    def test_booking_creation(self):
        """Test booking creation (Premium feature)"""
        if not self.token:
            print("❌ Skipping booking test - no token available")
            return False
            
        booking_data = {
            "spot_id": "tfl_cp_001",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "vehicle_registration": "TEST123"
        }
        
        success, response = self.run_test("Create Booking", "POST", "/bookings", 200, booking_data)
        if success and 'data' in response:
            booking = response['data']
            print(f"   Booking Reference: {booking.get('booking_reference', 'N/A')}")
            print(f"   Total Cost: £{booking.get('total_cost', 'N/A')}")
        return success

    def test_get_user_bookings(self):
        """Test getting user bookings"""
        if not self.token:
            print("❌ Skipping bookings list test - no token available")
            return False
            
        success, response = self.run_test("Get User Bookings", "GET", "/bookings", 200)
        if success and 'data' in response:
            bookings = response['data']
            print(f"   User has {len(bookings)} bookings")
        return success

    def test_analytics_popular_spots(self):
        """Test analytics endpoint"""
        return self.run_test("Popular Spots Analytics", "GET", "/analytics/popular-spots", 200)

def main():
    print("🚗 Park On London - API Testing Suite")
    print("=" * 50)
    
    tester = ParkOnAPITester()
    
    # Test sequence
    test_results = []
    
    # Basic endpoints
    test_results.append(("Health Check", tester.test_health_check()))
    test_results.append(("Guest Session", tester.test_guest_session()))
    
    # Authentication flow
    test_results.append(("User Registration", tester.test_user_registration()))
    test_results.append(("User Login", tester.test_user_login()))
    test_results.append(("Get Current User", tester.test_get_current_user()))
    
    # Parking search
    test_results.append(("Parking Search", tester.test_parking_search()))
    test_results.append(("Parking Search with Filters", tester.test_parking_search_with_filters()))
    test_results.append(("Parking Spot Details", tester.test_parking_spot_details()))
    
    # Subscription features
    test_results.append(("Subscription Plans", tester.test_subscription_plans()))
    test_results.append(("Premium Upgrade", tester.test_premium_upgrade()))
    
    # Premium features (after upgrade)
    test_results.append(("Create Booking", tester.test_booking_creation()))
    test_results.append(("Get User Bookings", tester.test_get_user_bookings()))
    
    # Analytics
    test_results.append(("Popular Spots Analytics", tester.test_analytics_popular_spots()))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    failed_tests = []
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success:
            failed_tests.append(test_name)
    
    print(f"\nTests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())