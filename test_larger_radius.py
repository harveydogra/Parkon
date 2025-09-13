#!/usr/bin/env python3
"""
Test with larger radius to find TfL car parks
"""
import requests

def test_with_larger_radius():
    """Test parking search with larger radius to catch TfL car parks"""
    base_url = "https://london-parking-1.preview.emergentagent.com/api"
    
    # Test with different radii
    radii = [1.2, 5.0, 10.0]  # miles
    
    for radius in radii:
        print(f"\n🔍 Testing with {radius} mile radius...")
        
        try:
            response = requests.get(
                f"{base_url}/parking/search",
                params={
                    "latitude": 51.5074,  # Central London
                    "longitude": -0.1278,
                    "radius_miles": radius
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
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_with_larger_radius()