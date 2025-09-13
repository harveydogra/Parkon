#!/usr/bin/env python3
"""
Focused test for postcode search functionality
"""
import requests
import json

def test_postcode_search_critical():
    """Test the critical postcode search functionality"""
    base_url = "https://london-parking-1.preview.emergentagent.com/api"
    
    print("🎯 FOCUSED POSTCODE SEARCH TESTING")
    print("=" * 50)
    
    # Test 1: Geocode E14 4QA
    print("\n1. Testing Geocode E14 4QA...")
    try:
        response = requests.get(f"{base_url}/geocode", params={"q": "E14 4QA"}, timeout=10)
        if response.status_code == 200:
            data = response.json()['data']
            lat, lon = data['latitude'], data['longitude']
            print(f"   ✅ Geocoded: {lat}, {lon}")
            
            # Test 2: Search parking with those coordinates
            print("\n2. Testing Parking Search with E14 4QA coordinates...")
            search_response = requests.get(
                f"{base_url}/parking/search",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "radius_miles": 1.2
                },
                timeout=10
            )
            
            if search_response.status_code == 200:
                search_data = search_response.json()['data']
                print(f"   ✅ Found {len(search_data)} parking spots")
                
                # Check for TfL spots
                tfl_spots = [spot for spot in search_data if spot.get('provider') == 'tfl']
                justpark_spots = [spot for spot in search_data if spot.get('provider') == 'justpark']
                
                print(f"   - TfL spots: {len(tfl_spots)}")
                print(f"   - JustPark spots: {len(justpark_spots)}")
                
                if tfl_spots:
                    print("   ✅ TfL integration working")
                    for spot in tfl_spots[:2]:
                        print(f"     - {spot.get('name', 'N/A')} ({spot.get('distance_km', 'N/A')} km)")
                else:
                    print("   ❌ No TfL spots found")
                
                if justpark_spots:
                    print("   ✅ JustPark data available")
                    for spot in justpark_spots[:2]:
                        print(f"     - {spot.get('name', 'N/A')} ({spot.get('distance_km', 'N/A')} km)")
                
                return len(search_data) > 0
            else:
                print(f"   ❌ Parking search failed: {search_response.status_code}")
                return False
        else:
            print(f"   ❌ Geocoding failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_mobile_specific_issues():
    """Test for mobile-specific issues that might cause 'search failed'"""
    base_url = "https://london-parking-1.preview.emergentagent.com/api"
    
    print("\n🔍 MOBILE-SPECIFIC ISSUE TESTING")
    print("=" * 50)
    
    # Test with various parameter formats that mobile might send
    test_cases = [
        {"q": "E14 4QA"},  # Standard
        {"q": "e14 4qa"},  # Lowercase
        {"q": "E14  4QA"}, # Extra space
        {"q": " E14 4QA "}, # Leading/trailing spaces
    ]
    
    for i, params in enumerate(test_cases, 1):
        print(f"\n{i}. Testing geocode with: '{params['q']}'")
        try:
            response = requests.get(f"{base_url}/geocode", params=params, timeout=10)
            if response.status_code == 200:
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test parking search with edge case parameters
    print("\n5. Testing parking search with edge case parameters...")
    edge_cases = [
        {"latitude": 51.5047998, "longitude": -0.0236412, "radius_miles": 1.2},  # Standard
        {"latitude": 51.5047998, "longitude": -0.0236412, "radius_miles": 1.2, "spot_type": "", "max_price": ""},  # Empty filters
        {"latitude": 51.5047998, "longitude": -0.0236412},  # No radius (should use default)
    ]
    
    for i, params in enumerate(edge_cases, 1):
        print(f"   Case {i}: {params}")
        try:
            response = requests.get(f"{base_url}/parking/search", params=params, timeout=10)
            print(f"     Status: {response.status_code}")
            if response.status_code != 200:
                print(f"     Error: {response.text}")
        except Exception as e:
            print(f"     Exception: {e}")

if __name__ == "__main__":
    success = test_postcode_search_critical()
    test_mobile_specific_issues()
    
    if success:
        print("\n🎉 CRITICAL POSTCODE SEARCH FUNCTIONALITY WORKING")
    else:
        print("\n❌ CRITICAL POSTCODE SEARCH FUNCTIONALITY FAILED")