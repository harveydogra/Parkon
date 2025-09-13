from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Path, BackgroundTasks, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path as FilePath
import os
import logging
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import asyncio
import httpx
import json
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
ROOT_DIR = FilePath(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'park_on_db')]

# Create the main app without a prefix
app = FastAPI(title="Park On - Parking API", description="Find and book parking spaces", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# TfL and API configuration
TFL_API_KEY = os.environ.get('TFL_API_KEY', 'placeholder-tfl-key')
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'placeholder-google-key')

# Email configuration for verification
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums
class ParkingSpotStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"

class ParkingSpotType(str, Enum):
    STANDARD = "standard"
    DISABLED = "disabled"
    ELECTRIC = "electric"
    MOTORCYCLE = "motorcycle"

class UserRole(str, Enum):
    GUEST = "guest"
    FREE = "free"
    PREMIUM = "premium"

class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

# Models
class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str
    postcode: str
    city: str = "London"

class ParkingPricing(BaseModel):
    hourly_rate: float
    daily_rate: Optional[float] = None
    currency: str = "GBP"

class ParkingSpot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    location: Location
    name: str
    status: ParkingSpotStatus
    spot_type: ParkingSpotType
    pricing: ParkingPricing
    capacity: int = 1
    amenities: List[str] = Field(default_factory=list)
    provider: str
    is_real_time: bool = False
    distance_km: Optional[float] = None
    walk_time_mins: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.FREE
    is_active: bool = True
    is_verified: bool = False
    verification_token: Optional[str] = None
    subscription_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ParkingHistoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    spot_id: str
    spot_name: str
    start_time: datetime
    end_time: datetime
    duration_hours: float
    total_cost: float
    booking_reference: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BookingRequest(BaseModel):
    spot_id: str
    start_time: datetime
    end_time: datetime
    vehicle_registration: str
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v

class Booking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    spot_id: str
    start_time: datetime
    end_time: datetime
    vehicle_registration: str
    status: BookingStatus = BookingStatus.CONFIRMED
    total_cost: float
    booking_reference: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SubscriptionPlan(BaseModel):
    name: str
    price: float
    duration_days: int
    features: List[str]

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Email verification function
async def send_verification_email(email: str, verification_token: str):
    """Send email verification"""
    try:
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured, skipping email verification")
            return True
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        msg['Subject'] = "Park On - Email Verification"
        
        # Send verification email
        verification_link = f"https://parkon.app/verify?token={verification_token}"
        
        body = f"""
        <html>
        <body style="background-color: #000000; color: #ffffff; font-family: Inter, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                <div style="text-align: center; margin-bottom: 40px;">
                    <h1 style="color: #d4af37; font-size: 2rem; margin: 0;">🅿️ Park On</h1>
                    <p style="color: #888888; margin: 5px 0 0 0;">London</p>
                </div>
                
                <div style="background: #111111; border: 1px solid #333333; border-radius: 16px; padding: 30px;">
                    <h2 style="color: #ffffff; margin-bottom: 20px;">Welcome to Park On!</h2>
                    <p style="color: #cccccc; margin-bottom: 30px;">Please verify your email address to complete your registration.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" 
                           style="background: linear-gradient(135deg, #d4af37 0%, #f4d03f 100%); 
                                  color: #000000; 
                                  padding: 15px 30px; 
                                  text-decoration: none; 
                                  border-radius: 8px; 
                                  font-weight: 700;">
                            Verify Email Address
                        </a>
                    </div>
                    
                    <p style="color: #888888; font-size: 0.875rem; margin-top: 30px;">
                        If you didn't create an account with Park On, please ignore this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, email, text)
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False

# TfL API Client
class TfLClient:
    def __init__(self):
        self.base_url = "https://api.tfl.gov.uk"
        self.api_key = TFL_API_KEY
        
    async def get_car_park_occupancy(self) -> List[Dict[str, Any]]:
        """Get car park data from TfL"""
        try:
            async with httpx.AsyncClient() as client:
                params = {"app_key": self.api_key}
                
                # Use the correct TfL car park endpoint
                try:
                    response = await client.get(
                        f"{self.base_url}/Place/Type/CarPark",
                        params=params,
                        timeout=15.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Convert TfL car park data to our format
                        return self._convert_tfl_carpark_data(data[:10])  # Limit to 10 results
                    else:
                        logger.warning(f"TfL CarPark endpoint failed with status {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"TfL CarPark endpoint failed: {e}")
                
                # Fallback to Road endpoint if CarPark fails
                try:
                    response = await client.get(
                        f"{self.base_url}/Road",
                        params=params,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return self._convert_tfl_data_to_parking(data[:5])  # Limit to 5 results
                        
                except Exception as e:
                    logger.warning(f"TfL Road endpoint failed: {e}")
                
                # If all endpoints fail, use mock data
                logger.warning("All TfL endpoints failed, using mock data")
                return self._get_mock_tfl_data()
                        
        except Exception as e:
            logger.error(f"TfL API error: {e}")
            return self._get_mock_tfl_data()
    
    def _convert_tfl_carpark_data(self, carpark_data: List[Dict]) -> List[Dict[str, Any]]:
        """Convert TfL car park data to parking spot format"""
        parking_spots = []
        
        for i, carpark in enumerate(carpark_data):
            if carpark.get('lat') and carpark.get('lon'):
                # Extract additional properties for better data
                additional_props = carpark.get('additionalProperties', [])
                capacity = 50  # Default capacity
                
                # Try to find capacity in additional properties
                for prop in additional_props:
                    if prop.get('key') == 'Capacity':
                        try:
                            capacity = int(prop.get('value', 50))
                        except:
                            capacity = 50
                
                parking_spots.append({
                    "id": f"tfl_{carpark.get('id', i)}",
                    "name": f"TfL Car Park - {carpark.get('commonName', 'Unknown')}",
                    "bayCount": capacity,
                    "spacesAvailable": max(1, capacity // 3),  # Mock availability as 1/3 of capacity
                    "lat": float(carpark['lat']),
                    "lon": float(carpark['lon']),
                    "lastUpdated": datetime.utcnow().isoformat(),
                    "carParkType": "TfL Official"
                })
        
        return parking_spots
    
    def _convert_tfl_data_to_parking(self, road_data: List[Dict]) -> List[Dict[str, Any]]:
        """Convert TfL road data to parking spot format"""
        parking_spots = []
        
        for i, road in enumerate(road_data):
            if road.get('bounds'):
                # Extract coordinates from bounds
                bounds = road['bounds']
                if len(bounds) >= 2 and len(bounds[0]) >= 2:
                    lat = (bounds[0][1] + bounds[1][1]) / 2  # Average latitude
                    lon = (bounds[0][0] + bounds[1][0]) / 2  # Average longitude
                    
                    # Create parking spot near this road
                    parking_spots.append({
                        "id": f"tfl_road_{road.get('id', i)}",
                        "name": f"Street Parking - {road.get('displayName', 'Unknown Road')}",
                        "bayCount": 50 + (i * 10),  # Mock bay count
                        "spacesAvailable": 15 + (i * 5),  # Mock availability
                        "lat": lat,
                        "lon": lon,
                        "lastUpdated": datetime.utcnow().isoformat(),
                        "roadStatus": road.get('statusSeverityDescription', 'Good')
                    })
        
        return parking_spots
    
    def _get_mock_tfl_data(self) -> List[Dict[str, Any]]:
        """Mock TfL car park data for demonstration"""
        return [
            {
                "id": "tfl_cp_001",
                "name": "Westminster Station Car Park",
                "bayCount": 100,
                "spacesAvailable": 25,
                "lat": 51.4994,
                "lon": -0.1244,
                "lastUpdated": datetime.utcnow().isoformat()
            },
            {
                "id": "tfl_cp_002", 
                "name": "King's Cross Station Car Park",
                "bayCount": 150,
                "spacesAvailable": 80,
                "lat": 51.5308,
                "lon": -0.1238,
                "lastUpdated": datetime.utcnow().isoformat()
            },
            {
                "id": "tfl_cp_003",
                "name": "London Bridge Station Car Park", 
                "bayCount": 75,
                "spacesAvailable": 12,
                "lat": 51.5049,
                "lon": -0.0863,
                "lastUpdated": datetime.utcnow().isoformat()
            }
        ]

# Mock JustPark data
def get_mock_justpark_data() -> List[Dict[str, Any]]:
    """Mock JustPark parking spots for comprehensive London coverage"""
    return [
        # East London
        {
            "id": "jp_001",
            "name": "Private Driveway - Shoreditch",
            "location": {"lat": 51.5254, "lng": -0.0863},
            "address": "123 Brick Lane",
            "postcode": "E1 6QL",
            "hourly_rate": 3.50,
            "daily_rate": 25.00,
            "type": "standard",
            "amenities": ["covered", "secure"],
            "capacity": 1
        },
        {
            "id": "jp_002", 
            "name": "Office Car Park - Canary Wharf",
            "location": {"lat": 51.5054, "lng": -0.0235},
            "address": "45 Bank Street",
            "postcode": "E14 5NY",
            "hourly_rate": 6.00,
            "daily_rate": 45.00,
            "type": "standard",
            "amenities": ["covered", "electric_charging"],
            "capacity": 2
        },
        {
            "id": "jp_003",
            "name": "Hotel Parking - Covent Garden", 
            "location": {"lat": 51.5118, "lng": -0.1246},
            "address": "78 Long Acre",
            "postcode": "WC2E 9NG",
            "hourly_rate": 8.50,
            "daily_rate": 65.00,
            "type": "standard",
            "amenities": ["valet", "covered"],
            "capacity": 1
        },
        
        # Southwest London (SW postcodes)
        {
            "id": "jp_004",
            "name": "Battersea Residential Parking",
            "location": {"lat": 51.4614, "lng": -0.1717},
            "address": "12 Lavender Hill",
            "postcode": "SW11 1AJ",
            "hourly_rate": 4.00,
            "daily_rate": 28.00,
            "type": "standard",
            "amenities": ["secure"],
            "capacity": 1
        },
        {
            "id": "jp_005",
            "name": "Chelsea Private Car Park",
            "location": {"lat": 51.4875, "lng": -0.1687},
            "address": "Kings Road",
            "postcode": "SW3 4LY",
            "hourly_rate": 12.00,
            "daily_rate": 85.00,
            "type": "standard",
            "amenities": ["valet", "covered", "secure"],
            "capacity": 3
        },
        {
            "id": "jp_006",
            "name": "Clapham Junction Station Parking",
            "location": {"lat": 51.4643, "lng": -0.1705},
            "address": "Station Approach",
            "postcode": "SW11 2QP",
            "hourly_rate": 3.20,
            "daily_rate": 22.00,
            "type": "standard",
            "amenities": ["monitored"],
            "capacity": 2
        },
        
        # North London (N postcodes)
        {
            "id": "jp_007",
            "name": "Camden Market Parking",
            "location": {"lat": 51.5412, "lng": -0.1434},
            "address": "Camden Lock Place",
            "postcode": "NW1 8AF",
            "hourly_rate": 5.50,
            "daily_rate": 38.00,
            "type": "standard",
            "amenities": ["covered"],
            "capacity": 1
        },
        {
            "id": "jp_008",
            "name": "Islington Residential Parking",
            "location": {"lat": 51.5362, "lng": -0.1031},
            "address": "Upper Street",
            "postcode": "N1 2TX",
            "hourly_rate": 4.80,
            "daily_rate": 32.00,
            "type": "standard",
            "amenities": ["secure"],
            "capacity": 1
        },
        
        # Southeast London (SE postcodes)  
        {
            "id": "jp_009",
            "name": "Greenwich Observatory Parking",
            "location": {"lat": 51.4769, "lng": 0.0005},
            "address": "Romney Road",
            "postcode": "SE10 9NF",
            "hourly_rate": 3.80,
            "daily_rate": 26.00,
            "type": "standard",
            "amenities": ["tourist_friendly"],
            "capacity": 2
        },
        {
            "id": "jp_010",
            "name": "Bermondsey Street Parking",
            "location": {"lat": 51.4977, "lng": -0.0782},
            "address": "Bermondsey Street",
            "postcode": "SE1 3UW",
            "hourly_rate": 4.20,
            "daily_rate": 29.00,
            "type": "standard",
            "amenities": ["covered"],
            "capacity": 1
        },
        
        # Northwest London (NW postcodes)
        {
            "id": "jp_011", 
            "name": "Hampstead Heath Parking",
            "location": {"lat": 51.5606, "lng": -0.1665},
            "address": "Hampstead Lane",
            "postcode": "NW3 7JR",
            "hourly_rate": 2.50,
            "daily_rate": 18.00,
            "type": "standard",
            "amenities": ["scenic"],
            "capacity": 1
        },
        {
            "id": "jp_012",
            "name": "Baker Street Underground Parking",
            "location": {"lat": 51.5226, "lng": -0.1571},
            "address": "Baker Street",
            "postcode": "NW1 6XE",
            "hourly_rate": 7.20,
            "daily_rate": 50.00,
            "type": "standard",
            "amenities": ["underground", "secure"],
            "capacity": 2
        },
        
        # Outer London Areas
        {
            "id": "jp_013",
            "name": "Ilford Town Centre Parking",
            "location": {"lat": 51.5617, "lng": 0.0857},
            "address": "High Road",
            "postcode": "IG1 1TR",
            "hourly_rate": 2.80,
            "daily_rate": 19.00,
            "type": "standard",
            "amenities": ["shopping_centre"],
            "capacity": 2
        },
        {
            "id": "jp_014",
            "name": "Richmond Park Parking",
            "location": {"lat": 51.4613, "lng": -0.2839},
            "address": "Petersham Road",
            "postcode": "TW10 5HS",
            "hourly_rate": 2.00,
            "daily_rate": 15.00,
            "type": "standard",
            "amenities": ["park_access"],
            "capacity": 3
        },
        {
            "id": "jp_015",
            "name": "Croydon Shopping Centre",
            "location": {"lat": 51.3727, "lng": -0.0963},
            "address": "North End",
            "postcode": "CR0 1TY",
            "hourly_rate": 3.00,
            "daily_rate": 20.00,
            "type": "standard",
            "amenities": ["shopping_centre", "covered"],
            "capacity": 4
        }
    ]

# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user_doc = await db.users.find_one({"email": email})
    if user_doc is None:
        raise credentials_exception
    
    return User(**user_doc)

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            return None
    except jwt.PyJWTError:
        return None
    
    user_doc = await db.users.find_one({"email": email})
    if user_doc is None:
        return None
    
    return User(**user_doc)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    import math
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

# Authentication endpoints
@api_router.post("/auth/register", response_model=APIResponse)
async def register_user(user_data: UserCreate):
    """Register a new user with email verification"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate verification token
    verification_token = str(uuid.uuid4())
    
    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=UserRole.FREE,
        is_verified=False,
        verification_token=verification_token
    )
    
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    
    await db.users.insert_one(user_dict)
    
    # Send verification email
    await send_verification_email(user.email, verification_token)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return APIResponse(
        success=True,
        data={"user": user, "access_token": access_token, "token_type": "bearer"},
        message="User registered successfully. Please check your email for verification."
    )

@api_router.get("/verify")
async def verify_email(token: str):
    """Verify user email address"""
    user_doc = await db.users.find_one({"verification_token": token})
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    await db.users.update_one(
        {"verification_token": token},
        {"$set": {"is_verified": True}, "$unset": {"verification_token": ""}}
    )
    
    return {"message": "Email verified successfully"}

@api_router.post("/auth/login", response_model=APIResponse)
async def login_user(login_data: UserLogin):
    """Authenticate user and return access token"""
    user_doc = await db.users.find_one({"email": login_data.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(login_data.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = User(**user_doc)
    access_token = create_access_token(data={"sub": user.email})
    
    return APIResponse(
        success=True,
        data={"user": user, "access_token": access_token, "token_type": "bearer"},
        message="Login successful"
    )

@api_router.get("/auth/me", response_model=APIResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return APIResponse(
        success=True,
        data=current_user,
        message="User information retrieved"
    )

# Guest user endpoint (no auth required)
@api_router.post("/auth/guest", response_model=APIResponse)
async def create_guest_session():
    """Create a guest session"""
    guest_id = str(uuid.uuid4())
    return APIResponse(
        success=True,
        data={"guest_id": guest_id, "role": "guest"},
        message="Guest session created"
    )

# Parking search endpoints
# Geocoding helper function
async def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """Convert address/postcode to coordinates using Nominatim"""
    try:
        async with httpx.AsyncClient() as client:
            # Use Nominatim API for geocoding
            params = {
                'q': f"{address}, London, UK",
                'format': 'json',
                'addressdetails': '1',
                'limit': '1'
            }
            
            response = await client.get(
                'https://nominatim.openstreetmap.org/search',
                params=params,
                headers={'User-Agent': 'ParkOn/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return {
                        'latitude': float(result['lat']),
                        'longitude': float(result['lon']),
                        'display_name': result.get('display_name', address)
                    }
            
            return None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None

@api_router.get("/geocode", response_model=APIResponse)
async def geocode_location(
    q: str = Query(..., description="Address or postcode to geocode")
):
    """Convert address or postcode to coordinates"""
    try:
        result = await geocode_address(q)
        
        if result:
            return APIResponse(
                success=True,
                data=result,
                message=f"Successfully geocoded: {q}"
            )
        else:
            raise HTTPException(status_code=404, detail="Location not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geocoding endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Geocoding failed")

@api_router.get("/parking/search", response_model=APIResponse)
async def search_parking_spots(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_miles: float = Query(1.2, ge=0.1, le=10.0, description="Search radius in miles"),
    spot_type: Optional[str] = Query(None),
    max_price: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search for parking spots near location"""
    try:
        # Handle empty string parameters from mobile apps
        if spot_type == "":
            spot_type = None
        if max_price == "":
            max_price = None
            
        # Validate spot_type if provided
        parsed_spot_type = None
        if spot_type:
            try:
                parsed_spot_type = ParkingSpotType(spot_type)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid spot_type: {spot_type}")
        
        # Validate max_price if provided
        parsed_max_price = None
        if max_price:
            try:
                parsed_max_price = float(max_price)
                if parsed_max_price < 0:
                    raise HTTPException(status_code=422, detail="max_price must be non-negative")
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid max_price: {max_price}")
        
        # Convert miles to kilometers for internal calculations
        radius_km = radius_miles * 1.60934
        
        all_spots = []
        
        # Get TfL car park data (always available)
        tfl_client = TfLClient()
        tfl_data = await tfl_client.get_car_park_occupancy()
        
        for car_park in tfl_data:
            if car_park.get('lat') and car_park.get('lon'):
                distance = calculate_distance(
                    latitude, longitude,
                    float(car_park['lat']), float(car_park['lon'])
                )
                
                if distance <= radius_km:
                    # For premium users, show real-time availability
                    is_premium = current_user and current_user.role == UserRole.PREMIUM
                    spaces_available = car_park.get('spacesAvailable', 0) if is_premium else None
                    
                    spot = ParkingSpot(
                        id=f"tfl_{car_park['id']}",
                        location=Location(
                            latitude=float(car_park['lat']),
                            longitude=float(car_park['lon']),
                            address=car_park.get('name', 'TfL Car Park'),
                            postcode="",
                            city="London"
                        ),
                        name=car_park.get('name', 'TfL Car Park'),
                        status=ParkingSpotStatus.AVAILABLE if spaces_available and spaces_available > 0 else ParkingSpotStatus.OCCUPIED,
                        spot_type=ParkingSpotType.STANDARD,
                        pricing=ParkingPricing(hourly_rate=4.00, daily_rate=30.00),
                        capacity=car_park.get('bayCount', 1),
                        amenities=["secure", "monitored"],
                        provider="tfl",
                        is_real_time=bool(is_premium),
                        distance_km=round(distance, 2),
                        walk_time_mins=int(distance * 12)  # Approximate walking time
                    )
                    all_spots.append(spot)
        
        # Get JustPark mock data
        justpark_data = get_mock_justpark_data()
        
        for jp_spot in justpark_data:
            location = jp_spot['location']
            distance = calculate_distance(
                latitude, longitude,
                location['lat'], location['lng']
            )
            
            if distance <= radius_km:
                spot = ParkingSpot(
                    id=jp_spot['id'],
                    location=Location(
                        latitude=location['lat'],
                        longitude=location['lng'],
                        address=jp_spot['address'],
                        postcode=jp_spot['postcode'],
                        city="London"
                    ),
                    name=jp_spot['name'],
                    status=ParkingSpotStatus.AVAILABLE,
                    spot_type=ParkingSpotType(jp_spot['type']),
                    pricing=ParkingPricing(
                        hourly_rate=jp_spot['hourly_rate'],
                        daily_rate=jp_spot.get('daily_rate')
                    ),
                    capacity=jp_spot['capacity'],
                    amenities=jp_spot.get('amenities', []),
                    provider="justpark",
                    is_real_time=False,
                    distance_km=round(distance, 2),
                    walk_time_mins=int(distance * 12)
                )
                all_spots.append(spot)
        
        # Apply filters
        if parsed_spot_type:
            all_spots = [spot for spot in all_spots if spot.spot_type == parsed_spot_type]
        
        if parsed_max_price:
            all_spots = [spot for spot in all_spots if spot.pricing.hourly_rate <= parsed_max_price]
        
        # Sort by distance
        all_spots.sort(key=lambda x: x.distance_km or 0)
        
        # Cache results for offline access
        cache_data = {
            "spots": [spot.dict() for spot in all_spots],
            "search_params": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_miles": radius_miles
            },
            "cached_at": datetime.utcnow()
        }
        await db.parking_cache.insert_one(cache_data)
        
        return APIResponse(
            success=True,
            data=all_spots[:20],  # Limit to 20 results
            message=f"Found {len(all_spots)} parking spots"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@api_router.get("/parking/spots/{spot_id}", response_model=APIResponse)
async def get_parking_spot_details(
    spot_id: str = Path(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get detailed information about a parking spot"""
    # Mock detailed spot information
    spot_details = {
        "id": spot_id,
        "detailed_amenities": ["24/7 access", "CCTV monitoring", "Mobile payment"],
        "opening_hours": "24/7",
        "restrictions": "Maximum stay 24 hours",
        "reviews": [
            {"rating": 4, "comment": "Great location, easy access"},
            {"rating": 5, "comment": "Very secure and convenient"}
        ],
        "average_rating": 4.5,
        "photos": [
            "https://via.placeholder.com/400x300?text=Parking+Spot+1",
            "https://via.placeholder.com/400x300?text=Parking+Spot+2"
        ]
    }
    
    return APIResponse(
        success=True,
        data=spot_details,
        message="Spot details retrieved"
    )

# Parking History endpoints
@api_router.get("/parking/history", response_model=APIResponse)
async def get_parking_history(current_user: User = Depends(get_current_user)):
    """Get parking history for premium users"""
    if current_user.role != UserRole.PREMIUM:
        raise HTTPException(
            status_code=403, 
            detail="Parking history feature requires Premium subscription"
        )
    
    # Get user's parking history
    history_cursor = db.parking_history.find({"user_id": current_user.id})
    history = await history_cursor.to_list(length=None)
    
    # If no history exists, create some mock data
    if not history:
        mock_history = [
            {
                "user_id": current_user.id,
                "spot_id": "tfl_tfl_cp_001",
                "spot_name": "Westminster Station Car Park",
                "start_time": datetime.utcnow() - timedelta(days=3),
                "end_time": datetime.utcnow() - timedelta(days=3, hours=-3),
                "duration_hours": 3.0,
                "total_cost": 12.00,
                "booking_reference": "PO" + str(uuid.uuid4())[:8].upper()
            },
            {
                "user_id": current_user.id,
                "spot_id": "jp_003",
                "spot_name": "Hotel Parking - Covent Garden",
                "start_time": datetime.utcnow() - timedelta(days=7),
                "end_time": datetime.utcnow() - timedelta(days=7, hours=-5),
                "duration_hours": 5.0,
                "total_cost": 42.50,
                "booking_reference": "PO" + str(uuid.uuid4())[:8].upper()
            }
        ]
        
        for item in mock_history:
            history_item = ParkingHistoryItem(**item)
            await db.parking_history.insert_one(history_item.dict())
        
        history = mock_history
    
    return APIResponse(
        success=True,
        data=[ParkingHistoryItem(**item) for item in history],
        message="Parking history retrieved"
    )

# Booking endpoints
@api_router.post("/bookings", response_model=APIResponse)
async def create_booking(
    booking_request: BookingRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a parking booking (Premium feature)"""
    if current_user.role != UserRole.PREMIUM:
        raise HTTPException(
            status_code=403, 
            detail="Booking feature requires Premium subscription"
        )
    
    # Calculate duration and cost
    duration_hours = (booking_request.end_time - booking_request.start_time).total_seconds() / 3600
    hourly_rate = 5.00  # Mock rate
    total_cost = duration_hours * hourly_rate
    
    booking = Booking(
        user_id=current_user.id,
        spot_id=booking_request.spot_id,
        start_time=booking_request.start_time,
        end_time=booking_request.end_time,
        vehicle_registration=booking_request.vehicle_registration,
        total_cost=total_cost,
        booking_reference=f"PO{str(uuid.uuid4())[:8].upper()}"
    )
    
    await db.bookings.insert_one(booking.dict())
    
    # Add to parking history
    history_item = ParkingHistoryItem(
        user_id=current_user.id,
        spot_id=booking_request.spot_id,
        spot_name="Mock Parking Spot",  # Would fetch real name in production
        start_time=booking_request.start_time,
        end_time=booking_request.end_time,
        duration_hours=duration_hours,
        total_cost=total_cost,
        booking_reference=booking.booking_reference
    )
    
    await db.parking_history.insert_one(history_item.dict())
    
    return APIResponse(
        success=True,
        data=booking,
        message="Booking created successfully"
    )

@api_router.get("/bookings", response_model=APIResponse)
async def get_user_bookings(current_user: User = Depends(get_current_user)):
    """Get user's bookings"""
    bookings_cursor = db.bookings.find({"user_id": current_user.id})
    bookings = await bookings_cursor.to_list(length=None)
    
    return APIResponse(
        success=True,
        data=[Booking(**booking) for booking in bookings],
        message="Bookings retrieved"
    )

# Premium subscription endpoints
@api_router.get("/subscription/plans", response_model=APIResponse)
async def get_subscription_plans():
    """Get available subscription plans"""
    plans = [
        SubscriptionPlan(
            name="Premium Monthly",
            price=9.99,
            duration_days=30,
            features=[
                "Real-time parking availability",
                "No advertisements", 
                "Advanced search filters",
                "Best fare comparison",
                "Parking reservations",
                "Parking history tracking",
                "Priority customer support"
            ]
        ),
        SubscriptionPlan(
            name="Premium Annual",
            price=99.99,
            duration_days=365,
            features=[
                "Real-time parking availability",
                "No advertisements",
                "Advanced search filters", 
                "Best fare comparison",
                "Parking reservations",
                "Parking history tracking",
                "Priority customer support",
                "20% savings vs monthly"
            ]
        )
    ]
    
    return APIResponse(
        success=True,
        data=plans,
        message="Subscription plans retrieved"
    )

@api_router.post("/subscription/upgrade", response_model=APIResponse)
async def upgrade_to_premium(
    plan_name: str = Query(..., description="Name of the subscription plan"),
    current_user: User = Depends(get_current_user)
):
    """Upgrade user to premium subscription"""
    # Mock payment processing
    duration_days = 30 if "Monthly" in plan_name else 365
    expires_at = datetime.utcnow() + timedelta(days=duration_days)
    
    await db.users.update_one(
        {"email": current_user.email},
        {"$set": {
            "role": UserRole.PREMIUM,
            "subscription_expires": expires_at
        }}
    )
    
    return APIResponse(
        success=True,
        data={"subscription_expires": expires_at},
        message="Successfully upgraded to Premium"
    )

# Analytics and admin endpoints
@api_router.get("/analytics/popular-spots", response_model=APIResponse)
async def get_popular_spots():
    """Get popular parking spots (for ads/sponsored content)"""
    popular_spots = [
        {"name": "Westminster Station", "bookings": 150, "revenue": 750.00},
        {"name": "Canary Wharf Office", "bookings": 120, "revenue": 720.00},
        {"name": "Covent Garden Hotel", "bookings": 90, "revenue": 765.00}
    ]
    
    return APIResponse(
        success=True,
        data=popular_spots,
        message="Popular spots retrieved"
    )

# Health check
@api_router.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    return APIResponse(
        success=True,
        data={"status": "healthy", "timestamp": datetime.utcnow()},
        message="Park On API is healthy"
    )

# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database collections"""
    logger.info("Park On API starting up...")
    
    # Create indexes for better performance
    await db.users.create_index("email", unique=True)
    await db.bookings.create_index("user_id")
    await db.parking_cache.create_index("cached_at")
    await db.parking_history.create_index("user_id")
    
    logger.info("Park On API ready!")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()