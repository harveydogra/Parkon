import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom parking markers
const createParkingIcon = (available = true) => {
  const color = available ? '#10b981' : '#ef4444';
  return L.divIcon({
    html: `
      <div style="
        background: ${color};
        width: 30px;
        height: 30px;
        border-radius: 50%;
        border: 3px solid white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">P</div>
    `,
    className: 'custom-parking-icon',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });
};

// Components
const Sidebar = ({ isOpen, onClose, user, onLogout, onUpgrade }) => (
  <div className={`sidebar-overlay ${isOpen ? 'active' : ''}`} onClick={onClose}>
    <div className={`sidebar ${isOpen ? 'active' : ''}`} onClick={(e) => e.stopPropagation()}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon">🅿️</span>
          <span className="logo-text">Park On</span>
        </div>
        <button className="sidebar-close" onClick={onClose}>×</button>
      </div>
      
      <div className="sidebar-content">
        {user && (
          <>
            <div className="user-profile">
              <div className="user-avatar">
                {user.full_name 
                  ? user.full_name.charAt(0).toUpperCase() 
                  : user.email 
                    ? user.email.charAt(0).toUpperCase()
                    : 'G'
                }
              </div>
              <div className="user-info">
                <h3>{user.full_name || user.email || 'Guest User'}</h3>
                <p>{user.email || 'Guest Session'}</p>
                <span className={`user-badge ${user.role}`}>
                  {user.role === 'premium' ? '⭐ Premium' : user.role === 'free' ? '🆓 Free' : '👤 Guest'}
                </span>
              </div>
            </div>
            
            <div className="sidebar-menu">
              <div className="menu-section">
                <h4>Account</h4>
                <ul>
                  <li><a href="#profile">My Profile</a></li>
                  {user.role === 'premium' && (
                    <li><a href="#history">Parking History</a></li>
                  )}
                  {user.role === 'premium' && (
                    <li><a href="#bookings">My Bookings</a></li>
                  )}
                </ul>
              </div>
              
              {user.role !== 'premium' && (
                <div className="menu-section">
                  <h4>Upgrade</h4>
                  <ul>
                    <li>
                      <button className="upgrade-menu-btn" onClick={onUpgrade}>
                        ⭐ Upgrade to Premium
                      </button>
                    </li>
                  </ul>
                </div>
              )}
              
              <div className="menu-section">
                <h4>App</h4>
                <ul>
                  <li><a href="#settings">Settings</a></li>
                  <li><a href="#help">Help & Support</a></li>
                  <li><a href="#about">About</a></li>
                </ul>
              </div>
            </div>
            
            <div className="sidebar-footer">
              <button className="btn btn-secondary logout-btn" onClick={onLogout}>
                🚪 Logout
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  </div>
);

const Header = ({ user, onLogin, onLogout, onUpgrade, onToggleSidebar }) => (
  <header className="header">
    <div className="header-content">
      <div className="header-left">
        {user ? (
          <button className="hamburger-menu" onClick={onToggleSidebar}>
            <span></span>
            <span></span>
            <span></span>
          </button>
        ) : null}
        
        <div className="logo">
          <span className="logo-icon">🅿️</span>
          <span className="logo-text">Park On</span>
        </div>
      </div>
      
      <nav className="nav">
        {!user && (
          <div className="auth-buttons">
            <button className="btn btn-primary" onClick={() => onLogin(false)}>
              Login / Sign Up
            </button>
            <button className="btn btn-secondary" onClick={() => onLogin(true)}>
              Continue as Guest
            </button>
          </div>
        )}
      </nav>
    </div>
  </header>
);

const SearchForm = ({ onSearch, isLoading, userRole }) => {
  const [searchData, setSearchData] = useState({
    latitude: 51.5074,
    longitude: -0.1278,
    radius_miles: 1.2,
    spot_type: '',
    max_price: ''
  });
  
  const [locationInput, setLocationInput] = useState('');
  const [geocoding, setGeocoding] = useState(false);

  const geocodeLocation = async (address) => {
    if (!address.trim()) return false;
    
    setGeocoding(true);
    try {
      const response = await axios.get(`${API}/geocode`, { 
        params: { q: address }
      });
      
      if (response.data.success) {
        const { latitude, longitude } = response.data.data;
        setSearchData({
          ...searchData,
          latitude,
          longitude
        });
        return true;
      }
    } catch (error) {
      console.error('Geocoding failed:', error);
      alert('Could not find location. Please check the address or postcode.');
      return false;
    } finally {
      setGeocoding(false);
    }
    return false;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // If user entered a location, geocode it first
    if (locationInput.trim()) {
      const geocoded = await geocodeLocation(locationInput);
      if (!geocoded) return; // Don't search if geocoding failed
    }
    
    onSearch(searchData);
  };

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setSearchData({
            ...searchData,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
        },
        (error) => {
          console.error('Geolocation error:', error);
          alert('Could not get your location. Using London center.');
        }
      );
    }
  };

  return (
    <div className="search-section">
      <h2>Find Premium Parking</h2>
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-row">
          <div className="input-group">
            <label>Location</label>
            <div className="location-input">
              <input
                type="text"
                placeholder="Enter address or use current location"
                className="input"
              />
              <button 
                type="button" 
                className="btn btn-location"
                onClick={getCurrentLocation}
                title="Use current location"
              >
                📍
              </button>
            </div>
          </div>
          
          <div className="input-group">
            <label>Search Radius</label>
            <select 
              value={searchData.radius_miles}
              onChange={(e) => setSearchData({...searchData, radius_miles: parseFloat(e.target.value)})}
              className="input"
            >
              <option value={0.3}>0.3 miles</option>
              <option value={0.6}>0.6 miles</option>
              <option value={1.2}>1.2 miles</option>
              <option value={2.5}>2.5 miles</option>
              <option value={5.0}>5 miles</option>
            </select>
          </div>
        </div>

        {userRole === 'premium' && (
          <div className="premium-filters">
            <div className="premium-badge">⭐ Premium Filters</div>
            <div className="search-row">
              <div className="input-group">
                <label>Parking Type</label>
                <select 
                  value={searchData.spot_type}
                  onChange={(e) => setSearchData({...searchData, spot_type: e.target.value})}
                  className="input"
                >
                  <option value="">Any Type</option>
                  <option value="standard">Standard</option>
                  <option value="disabled">Disabled Access</option>
                  <option value="electric">Electric Charging</option>
                  <option value="motorcycle">Motorcycle</option>
                </select>
              </div>
              
              <div className="input-group">
                <label>Max Price (£/hour)</label>
                <input
                  type="number"
                  placeholder="10.00"
                  value={searchData.max_price}
                  onChange={(e) => setSearchData({...searchData, max_price: e.target.value})}
                  className="input"
                  step="0.50"
                  min="0"
                />
              </div>
            </div>
          </div>
        )}
        
        <button type="submit" className="btn btn-primary btn-search" disabled={isLoading}>
          {isLoading ? 'Searching...' : 'Find Parking'}
        </button>
      </form>
    </div>
  );
};

const ParkingSpotCard = ({ spot, userRole, onBook, onViewDetails }) => {
  // Add discount logic for some spots
  const hasDiscount = Math.random() > 0.6; // 40% chance of discount
  const discountPercent = hasDiscount ? Math.floor(Math.random() * 30) + 10 : 0; // 10-40% discount
  const originalPrice = spot.pricing.hourly_rate;
  const discountedPrice = hasDiscount ? originalPrice * (1 - discountPercent / 100) : originalPrice;

  return (
    <div className="parking-card">
      <div className="card-header">
        <h3 className="spot-name">{spot.name}</h3>
        <div className="spot-badges">
          <span className={`status-badge ${spot.status}`}>
            {spot.status === 'available' ? '✅ Available' : '❌ Occupied'}
          </span>
          <span className="provider-badge">{spot.provider}</span>
          {spot.is_real_time && (
            <span className="realtime-badge">🔄 Real-time</span>
          )}
          {hasDiscount && (
            <span className="discount-badge">🎉 {discountPercent}% OFF</span>
          )}
        </div>
      </div>
      
      <div className="card-body">
        <div className="location-info">
          <p className="address">📍 {spot.location.address}</p>
          <div className="distance-info">
            <span>🚶 {spot.walk_time_mins} min walk</span>
            <span>📏 {(spot.distance_km * 0.621371).toFixed(1)} miles away</span>
          </div>
        </div>
        
        <div className="pricing-info">
          <div className="price-main">
            {hasDiscount && (
              <span className="original-price">£{originalPrice.toFixed(2)}</span>
            )}
            <span className={`price ${hasDiscount ? 'discounted' : ''}`}>
              £{discountedPrice.toFixed(2)}
            </span>
            <span className="price-unit">/hour</span>
          </div>
          {spot.pricing.daily_rate && (
            <div className="price-daily">
              Daily: £{spot.pricing.daily_rate}
            </div>
          )}
        </div>
        
        {spot.amenities && spot.amenities.length > 0 && (
          <div className="amenities">
            {spot.amenities.map((amenity, index) => (
              <span key={index} className="amenity-tag">
                {amenity}
              </span>
            ))}
          </div>
        )}
      </div>
      
      <div className="card-actions">
        <button 
          className="btn btn-secondary"
          onClick={() => onViewDetails(spot)}
        >
          View Details
        </button>
        
        {userRole === 'premium' ? (
          <button 
            className="btn btn-primary"
            onClick={() => onBook(spot)}
            disabled={spot.status !== 'available'}
          >
            Book Now
          </button>
        ) : (
          <button 
            className="btn btn-upgrade"
            onClick={() => alert('Upgrade to Premium to book parking spots!')}
          >
            Upgrade to Book
          </button>
        )}
      </div>
    </div>
  );
};

const ParkingHistory = ({ userRole }) => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (userRole === 'premium') {
      // Mock parking history for premium users
      setHistory([
        {
          id: 1,
          spotName: "Westminster Station Car Park",
          date: "2025-09-12",
          duration: "3 hours",
          cost: "£12.00",
          status: "completed"
        },
        {
          id: 2,
          spotName: "Covent Garden Hotel",
          date: "2025-09-10",
          duration: "5 hours",
          cost: "£42.50",
          status: "completed"
        },
        {
          id: 3,
          spotName: "King's Cross Station",
          date: "2025-09-08",
          duration: "2 hours",
          cost: "£8.00",
          status: "completed"
        }
      ]);
    }
  }, [userRole]);

  if (userRole !== 'premium' || history.length === 0) {
    return null;
  }

  return (
    <div className="history-section">
      <h3>⭐ Your Parking History</h3>
      {history.map(item => (
        <div key={item.id} className="history-item">
          <h4>{item.spotName}</h4>
          <p>{item.date} • {item.duration} • {item.cost}</p>
        </div>
      ))}
    </div>
  );
};

const MapView = ({ spots, center }) => {
  const mapCenter = [center.latitude, center.longitude];

  return (
    <div className="map-container">
      <MapContainer 
        center={mapCenter} 
        zoom={13} 
        className="map"
        style={{ height: '500px', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {spots.map(spot => (
          <Marker
            key={spot.id}
            position={[spot.location.latitude, spot.location.longitude]}
            icon={createParkingIcon(spot.status === 'available')}
          >
            <Popup>
              <div className="map-popup">
                <h3 style={{ margin: '0 0 10px 0', color: 'var(--text-primary)' }}>
                  {spot.name}
                </h3>
                <p style={{ margin: '5px 0', color: 'var(--text-secondary)' }}>
                  <strong>Price:</strong> £{spot.pricing.hourly_rate}/hour
                </p>
                <p style={{ margin: '5px 0', color: 'var(--text-secondary)' }}>
                  <strong>Status:</strong> {spot.status}
                </p>
                <p style={{ margin: '5px 0', color: 'var(--text-secondary)' }}>
                  <strong>Distance:</strong> {(spot.distance_km * 0.621371).toFixed(1)} miles
                </p>
                {spot.amenities && spot.amenities.length > 0 && (
                  <p style={{ margin: '5px 0', color: 'var(--text-secondary)' }}>
                    <strong>Amenities:</strong> {spot.amenities.join(', ')}
                  </p>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

const AdBanner = ({ userRole, onUpgrade }) => {
  if (userRole === 'premium') return null;

  return (
    <div className="ad-banner">
      <div className="ad-content">
        <h3>Upgrade Now</h3>
        <p>Real-time availability and booking, ad-free experience, and best fare comparison.</p>
        <button className="btn btn-upgrade" onClick={onUpgrade}>Upgrade Now</button>
      </div>
    </div>
  );
};

const LoginModal = ({ isOpen, onClose, isGuest = false, onUserLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  });
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isGuest) {
        const response = await axios.post(`${API}/auth/guest`);
        const guestUser = {
          role: 'guest',
          guest_id: response.data.data.guest_id,
          email: 'guest@parkon.com',
          full_name: 'Guest User'
        };
        localStorage.setItem('user', JSON.stringify(guestUser));
        onUserLogin(guestUser);
        onClose();
        return;
      }

      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      if (response.data.success) {
        if (!isLogin) {
          // Show email verification message for registration
          setEmailSent(true);
          setTimeout(() => {
            localStorage.setItem('token', response.data.data.access_token);
            localStorage.setItem('user', JSON.stringify(response.data.data.user));
            onUserLogin(response.data.data.user);
            onClose();
          }, 2000);
        } else {
          localStorage.setItem('token', response.data.data.access_token);
          localStorage.setItem('user', JSON.stringify(response.data.data.user));
          onUserLogin(response.data.data.user);
          onClose();
        }
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2>{isGuest ? 'Continue as Guest' : (isLogin ? 'Login' : 'Sign Up')}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className="auth-form">
          {emailSent && !isLogin && (
            <div className="email-verification">
              <p>✉️ Verification email sent! Please check your inbox.</p>
            </div>
          )}
          
          {isGuest ? (
            <div className="guest-info">
              <p>As a guest, you can:</p>
              <ul>
                <li>Search for parking spots</li>
                <li>View basic location information</li>
                <li>See pricing details</li>
              </ul>
              <p><strong>Upgrade to Premium for:</strong></p>
              <ul>
                <li>Real-time availability</li>
                <li>Booking functionality</li>
                <li>Advanced filters</li>
                <li>Ad-free experience</li>
                <li>Parking history</li>
              </ul>
            </div>
          ) : (
            <>
              {!isLogin && (
                <input
                  type="text"
                  placeholder="Full Name"
                  value={formData.full_name}
                  onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  className="input"
                />
              )}
              
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="input"
                required
              />
              
              <input
                type="password"
                placeholder="Password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="input"
                required
              />
            </>
          )}
          
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Processing...' : (isGuest ? 'Continue as Guest' : (isLogin ? 'Login' : 'Sign Up'))}
          </button>
          
          {!isGuest && (
            <p className="auth-switch">
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button 
                type="button" 
                className="link-btn"
                onClick={() => setIsLogin(!isLogin)}
              >
                {isLogin ? 'Sign Up' : 'Login'}
              </button>
            </p>
          )}
        </form>
      </div>
    </div>
  );
};

const UpgradeModal = ({ isOpen, onClose }) => {
  const [selectedPlan, setSelectedPlan] = useState('monthly');
  const [loading, setLoading] = useState(false);

  const plans = {
    monthly: {
      name: 'Premium Monthly',
      price: 9.99,
      duration: 'month',
      savings: null
    },
    annual: {
      name: 'Premium Annual', 
      price: 99.99,
      duration: 'year',
      savings: '20%'
    }
  };

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API}/subscription/upgrade?plan_name=${encodeURIComponent(plans[selectedPlan].name)}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.success) {
        alert('Successfully upgraded to Premium!');
        window.location.reload();
      }
    } catch (error) {
      alert('Upgrade failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal upgrade-modal">
        <div className="modal-header">
          <h2>⭐ Upgrade to Premium</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="upgrade-content">
          <div className="premium-features">
            <h3>Premium Features Include:</h3>
            <ul>
              <li>🔄 Real-time parking availability</li>
              <li>🚫 No advertisements</li>
              <li>🔍 Advanced search filters</li>
              <li>💰 Best fare comparison</li>
              <li>📅 Parking spot reservations</li>
              <li>📊 Parking history tracking</li>
              <li>⭐ Priority customer support</li>
            </ul>
          </div>
          
          <div className="pricing-plans">
            <div 
              className={`plan-card ${selectedPlan === 'monthly' ? 'selected' : ''}`}
              onClick={() => setSelectedPlan('monthly')}
            >
              <h4>Monthly Plan</h4>
              <div className="price">£9.99<span>/month</span></div>
              <p>Perfect for occasional users</p>
            </div>
            
            <div 
              className={`plan-card ${selectedPlan === 'annual' ? 'selected' : ''}`}
              onClick={() => setSelectedPlan('annual')}
            >
              <div className="popular-badge">Most Popular</div>
              <h4>Annual Plan</h4>
              <div className="price">£99.99<span>/year</span></div>
              <div className="savings">Save 20%</div>
              <p>Best value for regular users</p>
            </div>
          </div>
          
          <button 
            className="btn btn-upgrade btn-upgrade-action"
            onClick={handleUpgrade}
            disabled={loading}
          >
            {loading ? 'Processing...' : `Upgrade to ${plans[selectedPlan].name}`}
          </button>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [user, setUser] = useState(null);
  const [parkingSpots, setParkingSpots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [isGuestLogin, setIsGuestLogin] = useState(false);
  const [searchCenter, setSearchCenter] = useState({ latitude: 51.5074, longitude: -0.1278 });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);

  useEffect(() => {
    // Check for stored user session
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }

    // Perform initial search for London center
    performSearch({ latitude: 51.5074, longitude: -0.1278, radius_miles: 1.2 });

    // PWA Install Prompt
    const handleBeforeInstallPrompt = (e) => {
      // Prevent the mini-infobar from appearing on mobile
      e.preventDefault();
      // Stash the event so it can be triggered later
      setDeferredPrompt(e);
      setShowInstallPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallApp = async () => {
    if (deferredPrompt) {
      // Show the install prompt
      deferredPrompt.prompt();
      // Wait for the user to respond to the prompt
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`User response to the install prompt: ${outcome}`);
      // Clear the deferredPrompt
      setDeferredPrompt(null);
      setShowInstallPrompt(false);
    }
  };

  const performSearch = async (searchParams) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      const response = await axios.get(`${API}/parking/search`, { 
        params: searchParams,
        headers 
      });
      
      if (response.data.success) {
        setParkingSpots(response.data.data);
        setSearchCenter({
          latitude: searchParams.latitude,
          longitude: searchParams.longitude
        });
      }
    } catch (error) {
      console.error('Search failed:', error);
      alert('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = (asGuest = false) => {
    setIsGuestLogin(asGuest);
    setShowLoginModal(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setSidebarOpen(false);
    window.location.reload();
  };

  const handleUpgrade = () => {
    if (!user || user.role === 'guest') {
      alert('Please create an account to upgrade to Premium');
      setIsGuestLogin(false); // Show regular login, not guest
      setShowLoginModal(true);
      setSidebarOpen(false);
      return;
    }
    setShowUpgradeModal(true);
    setSidebarOpen(false);
  };

  const handleToggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const handleCloseSidebar = () => {
    setSidebarOpen(false);
  };

  const handleBooking = (spot) => {
    // Mock booking flow
    alert(`Booking functionality would open here for ${spot.name}`);
  };

  const handleViewDetails = (spot) => {
    // Mock details view
    alert(`Detailed view would open here for ${spot.name}`);
  };

  return (
    <div className="App">
      {/* PWA Install Prompt */}
      {showInstallPrompt && (
        <div className="install-prompt">
          <div className="install-content">
            <span>📱 Install Park On app on your device for better experience!</span>
            <div className="install-actions">
              <button className="btn btn-primary" onClick={handleInstallApp}>
                Install App
              </button>
              <button className="btn btn-secondary" onClick={() => setShowInstallPrompt(false)}>
                Maybe Later
              </button>
            </div>
          </div>
        </div>
      )}

      <Sidebar
        isOpen={sidebarOpen}
        onClose={handleCloseSidebar}
        user={user}
        onLogout={handleLogout}
        onUpgrade={handleUpgrade}
      />
      
      <Header 
        user={user}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onUpgrade={handleUpgrade}
        onToggleSidebar={handleToggleSidebar}
      />
      
      <main className="main-content">
        <AdBanner userRole={user?.role} onUpgrade={handleUpgrade} />
        
        <SearchForm 
          onSearch={performSearch}
          isLoading={loading}
          userRole={user?.role}
        />
        
        <ParkingHistory userRole={user?.role} />
        
        <div className="content-grid">
          <div className="results-section">
            <div className="results-header">
              <h2>Available Parking ({parkingSpots.length})</h2>
              {user?.role !== 'premium' && (
                <div className="upgrade-hint">
                  <span>⭐ Upgrade to Premium for real-time availability and booking</span>
                </div>
              )}
            </div>
            
            <div className="parking-grid">
              {parkingSpots.map(spot => (
                <ParkingSpotCard
                  key={spot.id}
                  spot={spot}
                  userRole={user?.role}
                  onBook={handleBooking}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
            
            {parkingSpots.length === 0 && !loading && (
              <div className="no-results">
                <h3>No parking spots found</h3>
                <p>Try adjusting your search criteria or expanding the search radius.</p>
              </div>
            )}
          </div>
          
          <div className="map-section">
            <MapView spots={parkingSpots} center={searchCenter} />
          </div>
        </div>
      </main>
      
      <LoginModal 
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        isGuest={isGuestLogin}
        onUserLogin={setUser}
      />
      
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
      />
    </div>
  );
}

export default App;