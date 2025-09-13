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

    def test_geocode_postcode_uppercase(self):
        """Test geocoding endpoint with uppercase postcode E14 4QA"""
        params = {"q": "E14 4QA"}
        success, response = self.run_test("Geocode Uppercase E14 4QA", "GET", "/geocode", 200, params)
        if success and 'data' in response:
            data = response['data']
            print(f"   Latitude: {data.get('latitude', 'N/A')}")
            print(f"   Longitude: {data.get('longitude', 'N/A')}")
            print(f"   Display Name: {data.get('display_name', 'N/A')}")
            # Store coordinates for parking search test
            self.e14_coords = {"lat": data.get('latitude'), "lon": data.get('longitude')}
        return success

    def test_geocode_postcode_lowercase(self):
        """Test geocoding endpoint with lowercase postcode e14 4qa"""
        params = {"q": "e14 4qa"}
        success, response = self.run_test("Geocode Lowercase e14 4qa", "GET", "/geocode", 200, params)
        if success and 'data' in response:
            data = response['data']
            print(f"   Latitude: {data.get('latitude', 'N/A')}")
            print(f"   Longitude: {data.get('longitude', 'N/A')}")
        return success

    def test_geocode_postcode_mixed_case(self):
        """Test geocoding endpoint with mixed case postcode E14 4qa"""
        params = {"q": "E14 4qa"}
        success, response = self.run_test("Geocode Mixed Case E14 4qa", "GET", "/geocode", 200, params)
        if success and 'data' in response:
            data = response['data']
            print(f"   Latitude: {data.get('latitude', 'N/A')}")
            print(f"   Longitude: {data.get('longitude', 'N/A')}")
        return success

    def test_geocode_invalid_postcode(self):
        """Test geocoding endpoint with invalid postcode"""
        params = {"q": "INVALID123"}
        success, response = self.run_test("Geocode Invalid Postcode", "GET", "/geocode", 404, params)
        return success

    def test_geocode_missing_parameter(self):
        """Test geocoding endpoint without required parameter"""
        success, response = self.run_test("Geocode Missing Parameter", "GET", "/geocode", 422, {})
        return success

    def test_parking_search_with_e14_coordinates(self):
        """Test parking search with coordinates from E14 4QA geocoding"""
        if not hasattr(self, 'e14_coords') or not self.e14_coords.get('lat'):
            print("❌ Skipping E14 parking search - no coordinates from geocoding")
            return False
            
        search_params = {
            "latitude": self.e14_coords['lat'],
            "longitude": self.e14_coords['lon'],
            "radius_miles": 1.2
        }
        
        success, response = self.run_test("Parking Search E14 4QA Coordinates", "GET", "/parking/search", 200, search_params)
        if success and 'data' in response:
            spots = response['data']
            print(f"   Found {len(spots)} parking spots near E14 4QA")
            if spots:
                print(f"   Closest spot: {spots[0].get('name', 'N/A')}")
                print(f"   Distance: {spots[0].get('distance_km', 'N/A')} km")
                print(f"   Provider: {spots[0].get('provider', 'N/A')}")
        return success

    def test_complete_postcode_search_flow(self):
        """Test complete flow: geocode E14 4QA then search parking"""
        print("\n🔄 Testing Complete Postcode Search Flow...")
        
        # Step 1: Geocode E14 4QA
        params = {"q": "E14 4QA"}
        success1, response1 = self.run_test("Flow Step 1: Geocode E14 4QA", "GET", "/geocode", 200, params)
        
        if not success1 or 'data' not in response1:
            print("❌ Flow failed at geocoding step")
            return False
            
        coords = response1['data']
        lat = coords.get('latitude')
        lon = coords.get('longitude')
        
        if not lat or not lon:
            print("❌ Flow failed - no coordinates returned")
            return False
            
        # Step 2: Search parking with those coordinates
        search_params = {
            "latitude": lat,
            "longitude": lon,
            "radius_miles": 1.2
        }
        
        success2, response2 = self.run_test("Flow Step 2: Search Parking", "GET", "/parking/search", 200, search_params)
        
        if success2 and 'data' in response2:
            spots = response2['data']
            print(f"✅ Complete flow successful - Found {len(spots)} spots for E14 4QA")
            return True
        else:
            print("❌ Flow failed at parking search step")
            return False

    def test_parking_search_parameter_validation(self):
        """Test parking search parameter validation for 422 errors"""
        test_cases = [
            ("Invalid Latitude High", {"latitude": 91, "longitude": -0.1278}, 422),
            ("Invalid Latitude Low", {"latitude": -91, "longitude": -0.1278}, 422),
            ("Invalid Longitude High", {"latitude": 51.5074, "longitude": 181}, 422),
            ("Invalid Longitude Low", {"latitude": 51.5074, "longitude": -181}, 422),
            ("Missing Latitude", {"longitude": -0.1278}, 422),
            ("Missing Longitude", {"latitude": 51.5074}, 422),
            ("Invalid Radius", {"latitude": 51.5074, "longitude": -0.1278, "radius_miles": 15}, 422),
        ]
        
        all_passed = True
        for test_name, params, expected_status in test_cases:
            success, _ = self.run_test(f"Validation: {test_name}", "GET", "/parking/search", expected_status, params)
            if not success:
                all_passed = False
                
        return all_passed

    def test_cors_headers(self):
        """Test CORS headers are present"""
        url = f"{self.api_url}/health"
        print(f"\n🔍 Testing CORS Headers...")
        print(f"   URL: {url}")
        
        try:
            response = requests.options(url, timeout=10)
            headers = response.headers
            
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            missing_headers = []
            for header in cors_headers:
                if header not in headers:
                    missing_headers.append(header)
                else:
                    print(f"   ✅ {header}: {headers[header]}")
            
            if missing_headers:
                print(f"   ❌ Missing CORS headers: {missing_headers}")
                return False
            else:
                print("   ✅ All CORS headers present")
                return True
                
        except Exception as e:
            print(f"   ❌ CORS test failed: {str(e)}")
            return False

    def test_without_auth_headers(self):
        """Test endpoints without authentication headers"""
        print("\n🔍 Testing endpoints without authentication...")
        
        # Test geocoding without auth
        params = {"q": "E14 4QA"}
        success1, _ = self.run_test("Geocode without Auth", "GET", "/geocode", 200, params, headers={'Authorization': None})
        
        # Test parking search without auth
        search_params = {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "radius_miles": 1.2
        }
        success2, _ = self.run_test("Parking Search without Auth", "GET", "/parking/search", 200, search_params, headers={'Authorization': None})
        
        return success1 and success2

    def test_tfl_api_integration(self):
        """Test TfL API integration by checking if real-time data is available"""
        search_params = {
            "latitude": 51.5074,  # Central London
            "longitude": -0.1278,
            "radius_miles": 2.0
        }
        
        success, response = self.run_test("TfL Integration Test", "GET", "/parking/search", 200, search_params)
        
        if success and 'data' in response:
            spots = response['data']
            tfl_spots = [spot for spot in spots if spot.get('provider') == 'tfl']
            
            if tfl_spots:
                print(f"   ✅ Found {len(tfl_spots)} TfL parking spots")
                for spot in tfl_spots[:2]:  # Show first 2
                    print(f"   - {spot.get('name', 'N/A')} (Real-time: {spot.get('is_real_time', False)})")
                return True
            else:
                print("   ❌ No TfL spots found - integration may be failing")
                return False
        
        return False

def main():
    print("🚗 Park On London - API Testing Suite")
    print("🎯 Focus: Postcode Search Functionality Testing")
    print("=" * 60)
    
    tester = ParkOnAPITester()
    
    # Test sequence
    test_results = []
    
    # Basic endpoints
    test_results.append(("Health Check", tester.test_health_check()))
    test_results.append(("Guest Session", tester.test_guest_session()))
    
    # CORS and Headers Testing
    test_results.append(("CORS Headers", tester.test_cors_headers()))
    
    # Postcode Geocoding Tests (PRIORITY)
    print("\n" + "🎯" * 20 + " POSTCODE GEOCODING TESTS " + "🎯" * 20)
    test_results.append(("Geocode E14 4QA (Uppercase)", tester.test_geocode_postcode_uppercase()))
    test_results.append(("Geocode e14 4qa (Lowercase)", tester.test_geocode_postcode_lowercase()))
    test_results.append(("Geocode E14 4qa (Mixed Case)", tester.test_geocode_postcode_mixed_case()))
    test_results.append(("Geocode Invalid Postcode", tester.test_geocode_invalid_postcode()))
    test_results.append(("Geocode Missing Parameter", tester.test_geocode_missing_parameter()))
    
    # Parking Search Tests (PRIORITY)
    print("\n" + "🎯" * 20 + " PARKING SEARCH TESTS " + "🎯" * 20)
    test_results.append(("Parking Search E14 Coordinates", tester.test_parking_search_with_e14_coordinates()))
    test_results.append(("Complete Postcode Search Flow", tester.test_complete_postcode_search_flow()))
    test_results.append(("Parameter Validation (422 Errors)", tester.test_parking_search_parameter_validation()))
    
    # Authentication Tests
    test_results.append(("Without Auth Headers", tester.test_without_auth_headers()))
    
    # TfL Integration Test
    test_results.append(("TfL API Integration", tester.test_tfl_api_integration()))
    
    # Authentication flow
    test_results.append(("User Registration", tester.test_user_registration()))
    test_results.append(("User Login", tester.test_user_login()))
    test_results.append(("Get Current User", tester.test_get_current_user()))
    
    # Standard parking search tests
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
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    failed_tests = []
    critical_failed = []
    
    # Define critical tests for postcode functionality
    critical_tests = [
        "Geocode E14 4QA (Uppercase)",
        "Geocode e14 4qa (Lowercase)", 
        "Geocode E14 4qa (Mixed Case)",
        "Parking Search E14 Coordinates",
        "Complete Postcode Search Flow",
        "TfL API Integration"
    ]
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        priority = "🔥 CRITICAL" if test_name in critical_tests and not success else ""
        print(f"{status} {test_name} {priority}")
        if not success:
            failed_tests.append(test_name)
            if test_name in critical_tests:
                critical_failed.append(test_name)
    
    print(f"\nTests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if critical_failed:
        print(f"\n🔥 CRITICAL FAILURES (Postcode Search Issues):")
        for test in critical_failed:
            print(f"   - {test}")
    
    if failed_tests:
        print(f"\n❌ All failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())