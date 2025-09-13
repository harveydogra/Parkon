import requests
import sys
import json
import math
from datetime import datetime

class DistanceFilteringTester:
    def __init__(self, base_url="https://london-parking-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test locations with exact coordinates from the review request
        self.test_locations = {
            "E14 4QA": {"lat": 51.5047998, "lon": -0.0236412, "name": "Canary Wharf"},
            "SW11 1AJ": {"lat": 51.461379, "lon": -0.1716723, "name": "Battersea"},
            "IG1 1TR": {"lat": 51.56166, "lon": 0.08565, "name": "Ilford"}
        }
        
        # Test radius values in miles
        self.test_radii = [0.5, 1.2, 2.0, 5.0]

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers (same as backend)"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def run_test(self, name, test_func):
        """Run a single test and track results"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            success = test_func()
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED: {name}")
                self.test_results.append((name, True, ""))
            else:
                print(f"❌ FAILED: {name}")
                self.test_results.append((name, False, "Test function returned False"))
            return success
        except Exception as e:
            print(f"❌ FAILED: {name} - Error: {str(e)}")
            self.test_results.append((name, False, str(e)))
            return False

    def search_parking(self, lat, lon, radius_miles, description=""):
        """Make parking search API call"""
        url = f"{self.api_url}/parking/search"
        params = {
            "latitude": lat,
            "longitude": lon,
            "radius_miles": radius_miles
        }
        
        print(f"   Searching at {lat}, {lon} with radius {radius_miles} miles {description}")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    return data['data']
                else:
                    print(f"   API returned success=False: {data.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"   API returned status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"   API call failed: {str(e)}")
            return None

    def test_geocoding_accuracy(self):
        """Test that geocoding returns expected coordinates"""
        print("   Testing geocoding accuracy for test locations...")
        
        for postcode, expected in self.test_locations.items():
            url = f"{self.api_url}/geocode"
            params = {"q": postcode}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and 'data' in data:
                        actual_lat = data['data']['latitude']
                        actual_lon = data['data']['longitude']
                        
                        # Check if coordinates are close (within 0.01 degrees ~ 1km)
                        lat_diff = abs(actual_lat - expected['lat'])
                        lon_diff = abs(actual_lon - expected['lon'])
                        
                        if lat_diff < 0.01 and lon_diff < 0.01:
                            print(f"   ✅ {postcode}: Geocoded correctly ({actual_lat}, {actual_lon})")
                        else:
                            print(f"   ⚠️  {postcode}: Geocoded to ({actual_lat}, {actual_lon}), expected ({expected['lat']}, {expected['lon']})")
                            print(f"      Difference: lat={lat_diff:.4f}, lon={lon_diff:.4f}")
                    else:
                        print(f"   ❌ {postcode}: Geocoding failed - {data.get('message', 'Unknown error')}")
                        return False
                else:
                    print(f"   ❌ {postcode}: Geocoding API returned {response.status_code}")
                    return False
            except Exception as e:
                print(f"   ❌ {postcode}: Geocoding error - {str(e)}")
                return False
        
        return True

    def test_distance_calculation_accuracy(self):
        """Test that distance calculations match expected values"""
        print("   Testing distance calculation accuracy...")
        
        # Test known distances between our test locations
        test_cases = [
            ("E14 4QA", "SW11 1AJ", 15.5),  # Canary Wharf to Battersea ~ 15.5km
            ("E14 4QA", "IG1 1TR", 18.2),   # Canary Wharf to Ilford ~ 18.2km
            ("SW11 1AJ", "IG1 1TR", 32.8),  # Battersea to Ilford ~ 32.8km
        ]
        
        for loc1, loc2, expected_km in test_cases:
            coords1 = self.test_locations[loc1]
            coords2 = self.test_locations[loc2]
            
            calculated_km = self.calculate_distance(
                coords1['lat'], coords1['lon'],
                coords2['lat'], coords2['lon']
            )
            
            # Allow 10% tolerance
            tolerance = expected_km * 0.1
            if abs(calculated_km - expected_km) <= tolerance:
                print(f"   ✅ {loc1} to {loc2}: {calculated_km:.1f}km (expected ~{expected_km}km)")
            else:
                print(f"   ❌ {loc1} to {loc2}: {calculated_km:.1f}km (expected ~{expected_km}km) - Outside tolerance")
                return False
        
        return True

    def test_radius_conversion(self):
        """Test that miles to km conversion is correct"""
        print("   Testing radius conversion (miles to km)...")
        
        test_cases = [
            (0.5, 0.80467),   # 0.5 miles = 0.80467 km
            (1.2, 1.93121),   # 1.2 miles = 1.93121 km
            (2.0, 3.21869),   # 2.0 miles = 3.21869 km
            (5.0, 8.04672),   # 5.0 miles = 8.04672 km
        ]
        
        for miles, expected_km in test_cases:
            calculated_km = miles * 1.60934  # Same conversion as backend
            
            if abs(calculated_km - expected_km) < 0.001:
                print(f"   ✅ {miles} miles = {calculated_km:.5f} km (expected {expected_km:.5f} km)")
            else:
                print(f"   ❌ {miles} miles = {calculated_km:.5f} km (expected {expected_km:.5f} km)")
                return False
        
        return True

    def test_different_locations_return_different_results(self):
        """CRITICAL: Test that different locations return different parking spots"""
        print("   Testing that different locations return different results...")
        
        radius_miles = 1.2  # Use consistent radius
        location_results = {}
        
        # Get results for each location
        for postcode, coords in self.test_locations.items():
            spots = self.search_parking(coords['lat'], coords['lon'], radius_miles, f"({coords['name']})")
            if spots is None:
                print(f"   ❌ Failed to get results for {postcode}")
                return False
            
            location_results[postcode] = spots
            print(f"   {postcode} ({coords['name']}): {len(spots)} spots found")
        
        # Check if all locations return the same spots (BUG INDICATOR)
        all_spot_ids = []
        for postcode, spots in location_results.items():
            spot_ids = set(spot['id'] for spot in spots)
            all_spot_ids.append((postcode, spot_ids))
            print(f"   {postcode}: Spot IDs = {sorted(list(spot_ids))}")
        
        # Compare results between locations
        if len(all_spot_ids) >= 2:
            first_postcode, first_ids = all_spot_ids[0]
            
            identical_results = True
            for postcode, spot_ids in all_spot_ids[1:]:
                if spot_ids != first_ids:
                    identical_results = False
                    print(f"   ✅ {first_postcode} and {postcode} return different spots (GOOD)")
                else:
                    print(f"   🚨 {first_postcode} and {postcode} return IDENTICAL spots (BUG!)")
            
            if identical_results:
                print(f"   🚨 CRITICAL BUG DETECTED: All locations return identical spot sets!")
                print(f"   🚨 This confirms the reported issue - distance filtering is not working!")
                return False
            else:
                print(f"   ✅ Different locations return different spots (distance filtering working)")
                return True
        
        return False

    def test_radius_filtering_accuracy(self):
        """Test that spots are actually within the specified radius"""
        print("   Testing radius filtering accuracy...")
        
        # Test with Canary Wharf location and different radii
        test_location = self.test_locations["E14 4QA"]
        
        for radius_miles in self.test_radii:
            radius_km = radius_miles * 1.60934
            spots = self.search_parking(test_location['lat'], test_location['lon'], radius_miles, 
                                      f"(radius {radius_miles} miles = {radius_km:.2f} km)")
            
            if spots is None:
                print(f"   ❌ Failed to get results for radius {radius_miles} miles")
                return False
            
            print(f"   Radius {radius_miles} miles: {len(spots)} spots found")
            
            # Check each spot is within the radius
            spots_outside_radius = 0
            for spot in spots:
                if 'location' in spot:
                    spot_lat = spot['location']['latitude']
                    spot_lon = spot['location']['longitude']
                    
                    distance_km = self.calculate_distance(
                        test_location['lat'], test_location['lon'],
                        spot_lat, spot_lon
                    )
                    
                    if distance_km > radius_km + 0.1:  # Allow small tolerance for rounding
                        spots_outside_radius += 1
                        print(f"   ⚠️  Spot '{spot.get('name', 'Unknown')}' is {distance_km:.2f}km away (outside {radius_km:.2f}km radius)")
            
            if spots_outside_radius > 0:
                print(f"   ❌ {spots_outside_radius} spots found outside the {radius_miles} mile radius")
                return False
            else:
                print(f"   ✅ All spots are within {radius_miles} mile radius")
        
        return True

    def test_smaller_radius_returns_fewer_spots(self):
        """Test that smaller radius returns fewer or equal spots"""
        print("   Testing that smaller radius returns fewer spots...")
        
        test_location = self.test_locations["E14 4QA"]
        previous_count = None
        
        for radius_miles in sorted(self.test_radii):
            spots = self.search_parking(test_location['lat'], test_location['lon'], radius_miles)
            
            if spots is None:
                print(f"   ❌ Failed to get results for radius {radius_miles} miles")
                return False
            
            current_count = len(spots)
            print(f"   Radius {radius_miles} miles: {current_count} spots")
            
            if previous_count is not None:
                if current_count < previous_count:
                    print(f"   ❌ Smaller radius ({radius_miles}) returned more spots ({current_count}) than larger radius ({previous_count})")
                    return False
                elif current_count == previous_count:
                    print(f"   ✅ Same number of spots (expected for overlapping radii)")
                else:
                    print(f"   ✅ Larger radius returned more spots ({current_count} vs {previous_count})")
            
            previous_count = current_count
        
        return True

    def test_complete_search_flow_all_locations(self):
        """Test complete geocode -> search flow for all test locations"""
        print("   Testing complete search flow for all locations...")
        
        for postcode, expected_coords in self.test_locations.items():
            print(f"   Testing flow for {postcode} ({expected_coords['name']})...")
            
            # Step 1: Geocode
            geocode_url = f"{self.api_url}/geocode"
            geocode_params = {"q": postcode}
            
            try:
                response = requests.get(geocode_url, params=geocode_params, timeout=10)
                if response.status_code != 200:
                    print(f"   ❌ Geocoding failed for {postcode}: {response.status_code}")
                    return False
                
                geocode_data = response.json()
                if not geocode_data.get('success') or 'data' not in geocode_data:
                    print(f"   ❌ Geocoding returned error for {postcode}: {geocode_data.get('message')}")
                    return False
                
                coords = geocode_data['data']
                lat = coords['latitude']
                lon = coords['longitude']
                
                # Step 2: Search parking
                spots = self.search_parking(lat, lon, 1.2, f"from geocoded {postcode}")
                
                if spots is None:
                    print(f"   ❌ Parking search failed for {postcode}")
                    return False
                
                print(f"   ✅ {postcode}: Geocoded to ({lat:.6f}, {lon:.6f}) -> {len(spots)} spots found")
                
            except Exception as e:
                print(f"   ❌ Flow failed for {postcode}: {str(e)}")
                return False
        
        return True

    def test_spot_distance_metadata(self):
        """Test that returned spots include correct distance metadata"""
        print("   Testing spot distance metadata...")
        
        test_location = self.test_locations["E14 4QA"]
        spots = self.search_parking(test_location['lat'], test_location['lon'], 2.0)
        
        if spots is None:
            print("   ❌ Failed to get spots for distance metadata test")
            return False
        
        if not spots:
            print("   ❌ No spots returned for distance metadata test")
            return False
        
        for i, spot in enumerate(spots[:5]):  # Check first 5 spots
            if 'distance_km' not in spot:
                print(f"   ❌ Spot {i+1} missing distance_km field")
                return False
            
            if 'location' not in spot:
                print(f"   ❌ Spot {i+1} missing location field")
                return False
            
            # Verify distance calculation
            reported_distance = spot['distance_km']
            spot_lat = spot['location']['latitude']
            spot_lon = spot['location']['longitude']
            
            calculated_distance = self.calculate_distance(
                test_location['lat'], test_location['lon'],
                spot_lat, spot_lon
            )
            
            # Allow small tolerance for rounding differences
            if abs(reported_distance - calculated_distance) > 0.1:
                print(f"   ❌ Spot {i+1} distance mismatch: reported {reported_distance}km, calculated {calculated_distance:.2f}km")
                return False
            
            print(f"   ✅ Spot {i+1}: {spot.get('name', 'Unknown')} - {reported_distance}km (verified)")
        
        return True

    def run_all_tests(self):
        """Run all distance filtering tests"""
        print("🚗 Park On London - Distance Filtering Bug Investigation")
        print("🎯 Testing distance filtering functionality")
        print("=" * 80)
        
        # Run all tests
        tests = [
            ("Geocoding Accuracy", self.test_geocoding_accuracy),
            ("Distance Calculation Accuracy", self.test_distance_calculation_accuracy),
            ("Radius Conversion (Miles to KM)", self.test_radius_conversion),
            ("Different Locations Return Different Results", self.test_different_locations_return_different_results),
            ("Radius Filtering Accuracy", self.test_radius_filtering_accuracy),
            ("Smaller Radius Returns Fewer Spots", self.test_smaller_radius_returns_fewer_spots),
            ("Complete Search Flow All Locations", self.test_complete_search_flow_all_locations),
            ("Spot Distance Metadata", self.test_spot_distance_metadata),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print detailed summary
        print("\n" + "=" * 80)
        print("📊 DISTANCE FILTERING TEST RESULTS")
        print("=" * 80)
        
        critical_failures = []
        for test_name, success, error in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if not success:
                if error:
                    print(f"    Error: {error}")
                # Mark critical tests
                if test_name in ["Different Locations Return Different Results", "Radius Filtering Accuracy"]:
                    critical_failures.append(test_name)
        
        print(f"\nTests passed: {self.tests_passed}/{self.tests_run}")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL FAILURES DETECTED:")
            for test in critical_failures:
                print(f"   - {test}")
            print(f"\n🚨 These failures confirm the reported distance filtering bug!")
        
        return len(critical_failures) == 0

def main():
    tester = DistanceFilteringTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())