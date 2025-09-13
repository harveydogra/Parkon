#!/usr/bin/env python3
"""
Debug TfL backend processing
"""
import asyncio
import httpx
import json
from datetime import datetime

async def debug_tfl_processing():
    """Debug what happens when we process TfL data"""
    api_key = "79bb56428ea54847885426e03ed7c9ee"
    base_url = "https://api.tfl.gov.uk"
    
    print("🔍 Debugging TfL data processing...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/Place/Type/CarPark",
                params={"app_key": api_key},
                timeout=15.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Got {len(data)} car parks from TfL")
                
                # Process first few car parks
                processed_spots = []
                for i, carpark in enumerate(data[:5]):
                    print(f"\n--- Car Park {i+1} ---")
                    print(f"ID: {carpark.get('id', 'N/A')}")
                    print(f"Name: {carpark.get('commonName', 'N/A')}")
                    print(f"Lat: {carpark.get('lat', 'N/A')}")
                    print(f"Lon: {carpark.get('lon', 'N/A')}")
                    
                    if carpark.get('lat') and carpark.get('lon'):
                        # This is what our backend should create
                        additional_props = carpark.get('additionalProperties', [])
                        capacity = 50  # Default capacity
                        
                        # Try to find capacity in additional properties
                        for prop in additional_props:
                            if prop.get('key') == 'Capacity':
                                try:
                                    capacity = int(prop.get('value', 50))
                                    print(f"Found capacity: {capacity}")
                                except:
                                    capacity = 50
                        
                        spot = {
                            "id": f"tfl_{carpark.get('id', i)}",
                            "name": f"TfL Car Park - {carpark.get('commonName', 'Unknown')}",
                            "bayCount": capacity,
                            "spacesAvailable": max(1, capacity // 3),
                            "lat": float(carpark['lat']),
                            "lon": float(carpark['lon']),
                            "lastUpdated": datetime.utcnow().isoformat(),
                            "carParkType": "TfL Official"
                        }
                        processed_spots.append(spot)
                        print(f"✅ Processed: {spot['name']}")
                    else:
                        print("❌ No coordinates - skipping")
                
                print(f"\n📊 Summary: Processed {len(processed_spots)} valid TfL car parks")
                
                # Test distance calculation for central London
                central_lat, central_lon = 51.5074, -0.1278
                print(f"\n🎯 Distance from Central London ({central_lat}, {central_lon}):")
                
                for spot in processed_spots:
                    # Simple distance calculation
                    import math
                    R = 6371  # Earth's radius in km
                    
                    lat1_rad = math.radians(central_lat)
                    lat2_rad = math.radians(spot['lat'])
                    delta_lat = math.radians(spot['lat'] - central_lat)
                    delta_lon = math.radians(spot['lon'] - central_lon)
                    
                    a = (math.sin(delta_lat/2)**2 + 
                         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    
                    distance = R * c
                    print(f"   {spot['name']}: {distance:.2f} km")
                
            else:
                print(f"❌ TfL API failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_tfl_processing())