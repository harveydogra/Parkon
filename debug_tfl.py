#!/usr/bin/env python3
"""
Debug script to test TfL API integration directly
"""
import requests
import json

def test_tfl_api_direct():
    """Test TfL API directly to see what data we get"""
    print("🔍 Testing TfL API directly...")
    
    api_key = "79bb56428ea54847885426e03ed7c9ee"
    base_url = "https://api.tfl.gov.uk"
    
    endpoints_to_test = [
        "/Road",
        "/StopPoint/Type/NaptanPublicBusCoachTram",
        "/Place/Type/CarPark",
        "/Occupancy/CarPark"
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n📍 Testing endpoint: {endpoint}")
        try:
            response = requests.get(
                f"{base_url}{endpoint}",
                params={"app_key": api_key},
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Data type: {type(data)}")
                print(f"   Data length: {len(data) if isinstance(data, list) else 'N/A'}")
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"   First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")
                    print(f"   Sample item: {json.dumps(data[0], indent=2)[:500]}...")
                elif isinstance(data, dict):
                    print(f"   Dict keys: {list(data.keys())}")
                    
            else:
                print(f"   Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"   Exception: {e}")

def test_backend_parking_search():
    """Test our backend parking search to see what data is returned"""
    print("\n🔍 Testing backend parking search...")
    
    url = "https://london-parking-1.preview.emergentagent.com/api/parking/search"
    params = {
        "latitude": 51.5074,
        "longitude": -0.1278,
        "radius_miles": 2.0
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            spots = data.get('data', [])
            print(f"   Found {len(spots)} spots")
            
            for spot in spots:
                print(f"   - {spot.get('name', 'N/A')} (Provider: {spot.get('provider', 'N/A')})")
                
        else:
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_tfl_api_direct()
    test_backend_parking_search()