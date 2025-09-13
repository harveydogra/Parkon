#!/usr/bin/env python3
"""
Test TfL integration after the fix
"""
import requests

def test_tfl_integration():
    """Test if TfL spots are now appearing"""
    base_url = "https://london-parking-1.preview.emergentagent.com/api"
    
    # Test with central London coordinates where TfL car parks should exist
    test_locations = [
        {"name": "Central London", "lat": 51.5074, "lon": -0.1278},
        {"name": "King's Cross", "lat": 51.5308, "lon": -0.1238},
        {"name": "Westminster", "lat": 51.4994, "lon": -0.1244},
    ]
    
    for location in test_locations:
        print(f"\n🔍 Testing TfL integration at {location['name']}...")
        
        try:
            response = requests.get(
                f"{base_url}/parking/search",
                params={
                    "latitude": location['lat'],
                    "longitude": location['lon'],
                    "radius_miles": 3.0  # Larger radius to catch more spots
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                tfl_spots = [spot for spot in data if spot.get('provider') == 'tfl']
                justpark_spots = [spot for spot in data if spot.get('provider') == 'justpark']
                
                print(f"   Total spots: {len(data)}")
                print(f"   TfL spots: {len(tfl_spots)}")
                print(f"   JustPark spots: {len(justpark_spots)}")
                
                if tfl_spots:
                    print("   ✅ TfL spots found:")
                    for spot in tfl_spots[:3]:
                        print(f"     - {spot.get('name', 'N/A')} ({spot.get('distance_km', 'N/A')} km)")
                else:
                    print("   ❌ No TfL spots found")
                    
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_tfl_integration()