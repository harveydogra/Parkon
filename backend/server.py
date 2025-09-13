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

# Load environment variables
ROOT_DIR = FilePath(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'park_on_db')]

# Create the main app without a prefix
app = FastAPI(title="Park On - London Parking API", description="Find and book parking in London", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# TfL and API configuration
TFL_API_KEY = os.environ.get('TFL_API_KEY', 'placeholder-tfl-key')
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'placeholder-google-key')

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
    subscription_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

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

# TfL API Client
class TfLClient:
    def __init__(self):
        self.base_url = "https://api.tfl.gov.uk"
        self.api_key = TFL_API_KEY
        
    async def get_car_park_occupancy(self) -> List[Dict[str, Any]]:
        """Get car park occupancy data from TfL"""
        try:
            async with httpx.AsyncClient() as client:
                params = {}
                if self.api_key != 'placeholder-tfl-key':
                    params = {"app_key": self.api_key}
                
                response = await client.get(
                    f"{self.base_url}/Occupancy/CarPark",
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"TfL API returned status {response.status_code}")
                    return self._get_mock_tfl_data()
        except Exception as e:
            logger.error(f"TfL API error: {e}")
            return self._get_mock_tfl_data()
    
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
    """Mock JustPark parking spots for demonstration"""
    return [
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
    """Register a new user"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        role=UserRole.FREE
    )
    
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return APIResponse(
        success=True,
        data={"user": user, "access_token": access_token, "token_type": "bearer"},
        message="User registered successfully"
    )

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

@api_router.get("/parking/search", response_model=APIResponse)
async def search_parking_spots(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(2.0, ge=0.1, le=10.0),
    spot_type: Optional[ParkingSpotType] = Query(None),
    max_price: Optional[float] = Query(None, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Search for parking spots near location"""
    try:
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
        if spot_type:
            all_spots = [spot for spot in all_spots if spot.spot_type == spot_type]
        
        if max_price:
            all_spots = [spot for spot in all_spots if spot.pricing.hourly_rate <= max_price]
        
        # Sort by distance
        all_spots.sort(key=lambda x: x.distance_km or 0)
        
        # Cache results for offline access
        cache_data = {
            "spots": [spot.dict() for spot in all_spots],
            "search_params": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km
            },
            "cached_at": datetime.utcnow()
        }
        await db.parking_cache.insert_one(cache_data)
        
        return APIResponse(
            success=True,
            data=all_spots[:20],  # Limit to 20 results
            message=f"Found {len(all_spots)} parking spots"
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@api_router.get("/parking/spots/{spot_id}", response_model=APIResponse)
async def get_parking_spot_details(
    spot_id: str = Path(...),
    current_user: Optional[User] = Depends(get_current_user) if security else None
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

class UpgradeRequest(BaseModel):
    plan_name: str

@api_router.post("/subscription/upgrade", response_model=APIResponse)
async def upgrade_to_premium(
    upgrade_request: UpgradeRequest,
    current_user: User = Depends(get_current_user)
):
    """Upgrade user to premium subscription"""
    # Mock payment processing
    duration_days = 30 if "Monthly" in upgrade_request.plan_name else 365
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
    
    logger.info("Park On API ready!")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()