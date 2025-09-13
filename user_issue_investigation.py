import requests
import json

def investigate_user_issue():
    """
    Investigate the user's specific complaint:
    "All 11 parking spots showing for every postcode search instead of location-specific results"
    """
    
    base_url = 'https://london-parking-1.preview.emergentagent.com/api'
    
    # Test locations from the user's report
    test_locations = [
        ('E14 4QA', 'Canary Wharf'),
        ('SW11 1AJ', 'Battersea'), 
        ('IG1 1TR', 'Ilford')
    ]
    
    print("🔍 INVESTIGATING USER'S DISTANCE FILTERING BUG REPORT")
    print("=" * 70)
    print("User complaint: 'All 11 parking spots showing for every postcode search'")
    print("Expected: Different locations should return different parking spots")
    print("=" * 70)
    
    # Test with different radius values that user might be using
    radius_tests = [
        ("Default (1.2 miles)", 1.2),
        ("Small (0.5 miles)", 0.5),
        ("Medium (2.0 miles)", 2.0),
        ("Large (5.0 miles)", 5.0),
        ("Very Large (10.0 miles)", 10.0)
    ]
    
    for radius_name, radius_miles in radius_tests:
        print(f"\n🎯 TESTING WITH {radius_name.upper()}")
        print("-" * 50)
        
        location_results = {}
        all_spot_counts = []
        all_spot_ids = []
        
        for postcode, area_name in test_locations:
            # Step 1: Geocode the postcode
            geocode_response = requests.get(f'{base_url}/geocode', params={'q': postcode})
            
            if geocode_response.status_code != 200:
                print(f"❌ {postcode}: Geocoding failed")
                continue
                
            geocode_data = geocode_response.json()
            if not geocode_data.get('success'):
                print(f"❌ {postcode}: Geocoding error")
                continue
            
            coords = geocode_data['data']
            lat, lon = coords['latitude'], coords['longitude']
            
            # Step 2: Search parking with the radius
            search_response = requests.get(f'{base_url}/parking/search', params={
                'latitude': lat,
                'longitude': lon,
                'radius_miles': radius_miles
            })
            
            if search_response.status_code != 200:
                print(f"❌ {postcode}: Search failed")
                continue
                
            search_data = search_response.json()
            if not search_data.get('success'):
                print(f"❌ {postcode}: Search error")
                continue
            
            spots = search_data['data']
            spot_count = len(spots)
            spot_ids = set(spot['id'] for spot in spots)
            
            location_results[postcode] = {
                'area': area_name,
                'count': spot_count,
                'spot_ids': spot_ids,
                'spots': spots
            }
            
            all_spot_counts.append(spot_count)
            all_spot_ids.append(spot_ids)
            
            print(f"📍 {postcode} ({area_name}): {spot_count} spots found")
            
            # Show first few spot names for verification
            if spots:
                for i, spot in enumerate(spots[:3]):
                    distance_miles = spot.get('distance_km', 0) * 0.621371
                    print(f"   {i+1}. {spot.get('name', 'Unknown')} ({distance_miles:.1f} miles)")
                if len(spots) > 3:
                    print(f"   ... and {len(spots) - 3} more spots")
        
        # Analysis
        print(f"\n📊 ANALYSIS FOR {radius_name.upper()}:")
        
        if len(all_spot_counts) >= 2:
            # Check if all locations return the same number of spots
            if len(set(all_spot_counts)) == 1:
                print(f"⚠️  All locations return EXACTLY {all_spot_counts[0]} spots")
                if all_spot_counts[0] == 11:
                    print("🚨 THIS MATCHES THE USER'S COMPLAINT! (11 spots for every search)")
            else:
                print(f"✅ Different locations return different spot counts: {all_spot_counts}")
            
            # Check if all locations return identical spot sets
            first_spot_set = all_spot_ids[0]
            identical_spots = all(spot_set == first_spot_set for spot_set in all_spot_ids[1:])
            
            if identical_spots:
                print("🚨 CRITICAL BUG: All locations return IDENTICAL spot sets!")
                print("🚨 This confirms the user's distance filtering bug report!")
            else:
                print("✅ Different locations return different spot sets (distance filtering working)")
                
                # Show overlap analysis
                for i, (postcode1, _) in enumerate(test_locations):
                    for j, (postcode2, _) in enumerate(test_locations[i+1:], i+1):
                        overlap = len(all_spot_ids[i] & all_spot_ids[j])
                        total_unique = len(all_spot_ids[i] | all_spot_ids[j])
                        print(f"   {postcode1} ∩ {postcode2}: {overlap} shared spots, {total_unique} total unique")
        
        print()
    
    print("=" * 70)
    print("🎯 CONCLUSION:")
    print("=" * 70)
    
    # Final test: Check if there's a scenario where user sees 11 spots everywhere
    print("Testing specific scenario that might cause user's issue...")
    
    # Test with a radius that might return ~11 spots for all locations
    test_radius = 3.0  # 3 miles
    spot_counts_3miles = []
    
    for postcode, area_name in test_locations:
        geocode_response = requests.get(f'{base_url}/geocode', params={'q': postcode})
        if geocode_response.status_code == 200:
            coords = geocode_response.json()['data']
            search_response = requests.get(f'{base_url}/parking/search', params={
                'latitude': coords['latitude'],
                'longitude': coords['longitude'],
                'radius_miles': test_radius
            })
            if search_response.status_code == 200:
                spots = search_response.json()['data']
                spot_counts_3miles.append(len(spots))
    
    if spot_counts_3miles and all(count == 11 for count in spot_counts_3miles):
        print(f"🚨 FOUND THE ISSUE! With {test_radius} mile radius, all locations return exactly 11 spots!")
        print("🚨 User might be using a large radius setting that shows all available spots!")
    elif spot_counts_3miles:
        print(f"With {test_radius} mile radius: {spot_counts_3miles} spots per location")
        print("✅ Distance filtering appears to be working correctly")
        print("💡 User's issue might be:")
        print("   1. Using a very large search radius")
        print("   2. Frontend caching issue")
        print("   3. Browser cache showing old results")
        print("   4. User testing in an area with limited parking data")
    
    print("\n🔧 RECOMMENDATIONS:")
    print("1. Check if user is using a large search radius (5+ miles)")
    print("2. Verify frontend is not caching search results incorrectly")
    print("3. Test with smaller radius values (0.5-1.2 miles)")
    print("4. Clear browser cache and test again")

if __name__ == "__main__":
    investigate_user_issue()