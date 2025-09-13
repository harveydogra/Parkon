# 🚇 TfL API Key Setup Guide

## Step 1: Register for TfL API (FREE)
1. Go to: https://api.tfl.gov.uk/
2. Click "Register" in the top right corner
3. Fill out the registration form:
   - Email: your-email@example.com
   - Password: Create a strong password
   - Developer Type: Select "Individual Developer"
   - Accept terms and conditions

## Step 2: Create Application
1. After registration, log in to your TfL account
2. Go to "My Apps" section
3. Click "Add new app"
4. Fill out the application form:
   - **App name**: "Park On"
   - **Description**: "Smart parking finder app with real-time availability"
   - **Website**: "https://parkon.app" (or your domain)
   - **Contact email**: your-email@example.com

## Step 3: Get Your API Key
1. After creating the app, you'll see your API key
2. Copy the API key (it looks like: `12345abcdef67890ghijk`)
3. Keep it secure - don't share publicly

## Step 4: Add API Key to App
Replace `placeholder-tfl-key-add-real-key-here` in `/app/backend/.env` with your real key:

```
TFL_API_KEY=your-real-tfl-api-key-here
```

## Step 5: Test Integration
After adding the key, restart the backend:
```bash
sudo supervisorctl restart backend
```

## Benefits of Real TfL API Key:
- ✅ Real-time car park occupancy data
- ✅ Live parking availability updates
- ✅ Accurate bay counts and space information
- ✅ No rate limits for reasonable usage
- ✅ Completely FREE forever

## API Endpoints Used:
- Car Park Occupancy: `https://api.tfl.gov.uk/Occupancy/CarPark`
- Street Works: `https://api.tfl.gov.uk/StopPoint`
- Road Disruptions: `https://api.tfl.gov.uk/Road/Disruption`

## Troubleshooting:
- If you get 401 errors, check your API key is correct
- If you get 429 errors, you're hitting rate limits (very unlikely)
- Contact TfL support at: api@tfl.gov.uk

---
💡 **Note**: TfL API is completely free with no usage charges!