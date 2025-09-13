import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'placeholder-google-key';

// Components
const Header = ({ user, onLogin, onLogout, onUpgrade }) => (
  <header className="header">
    <div className="header-content">
      <div className="logo">
        <span className="logo-icon">🅿️</span>
        <span className="logo-text">Park On</span>
        <span className="logo-subtitle">London</span>
      </div>
      
      <nav className="nav">
        {user ? (
          <div className="user-section">
            <span className="user-welcome">
              Hello, {user.full_name || user.email}
            </span>
            <span className={`user-badge ${user.role}`}>
              {user.role === 'premium' ? '⭐ Premium' : '🆓 Free'}
            </span>
            {user.role !== 'premium' && (
              <button className="btn btn-upgrade" onClick={onUpgrade}>
                Upgrade to Premium
              </button>
            )}
            <button className="btn btn-secondary" onClick={onLogout}>
              Logout
            </button>
          </div>
        ) : (
          <div className="auth-buttons">
            <button className="btn btn-primary" onClick={onLogin}>
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

  const handleSubmit = (e) => {
    e.preventDefault();
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
      <h2>Find Parking in London</h2>
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
              value={searchData.radius_km}
              onChange={(e) => setSearchData({...searchData, radius_km: parseFloat(e.target.value)})}
              className="input"
            >
              <option value={0.5}>0.5 km</option>
              <option value={1.0}>1 km</option>
              <option value={2.0}>2 km</option>
              <option value={5.0}>5 km</option>
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
          {isLoading ? 'Searching...' : 'Find Parking Spots'}
        </button>
      </form>
    </div>
  );
};

const ParkingSpotCard = ({ spot, userRole, onBook, onViewDetails }) => (
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
      </div>
    </div>
    
    <div className="card-body">
      <div className="location-info">
        <p className="address">📍 {spot.location.address}</p>
        <div className="distance-info">
          <span>🚶 {spot.walk_time_mins} min walk</span>
          <span>📏 {spot.distance_km} km away</span>
        </div>
      </div>
      
      <div className="pricing-info">
        <div className="price-main">
          <span className="price">£{spot.pricing.hourly_rate}</span>
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

const MapView = ({ spots, center }) => {
  useEffect(() => {
    if (window.google && window.google.maps) {
      initMap();
    } else {
      loadGoogleMaps();
    }
  }, [spots, center]);

  const loadGoogleMaps = () => {
    if (GOOGLE_MAPS_API_KEY === 'placeholder-google-key') {
      return;
    }
    
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&callback=initMap`;
    script.async = true;
    script.defer = true;
    window.initMap = initMap;
    document.head.appendChild(script);
  };

  const initMap = () => {
    if (!window.google || !window.google.maps) return;

    const map = new window.google.maps.Map(document.getElementById('map'), {
      zoom: 13,
      center: { lat: center.latitude, lng: center.longitude },
      styles: [
        {
          featureType: 'poi',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }]
        }
      ]
    });

    // Add markers for parking spots
    spots.forEach(spot => {
      const marker = new window.google.maps.Marker({
        position: { 
          lat: spot.location.latitude, 
          lng: spot.location.longitude 
        },
        map: map,
        title: spot.name,
        icon: {
          url: spot.status === 'available' ? 
            'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
                <circle cx="16" cy="16" r="14" fill="#10b981" stroke="#fff" stroke-width="2"/>
                <text x="16" y="20" text-anchor="middle" fill="white" font-size="16">P</text>
              </svg>
            `) :
            'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
                <circle cx="16" cy="16" r="14" fill="#ef4444" stroke="#fff" stroke-width="2"/>
                <text x="16" y="20" text-anchor="middle" fill="white" font-size="16">P</text>
              </svg>
            `),
          scaledSize: new window.google.maps.Size(32, 32)
        }
      });

      const infoWindow = new window.google.maps.InfoWindow({
        content: `
          <div style="padding: 10px;">
            <h3 style="margin: 0 0 10px 0;">${spot.name}</h3>
            <p style="margin: 5px 0;"><strong>Price:</strong> £${spot.pricing.hourly_rate}/hour</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> ${spot.status}</p>
            <p style="margin: 5px 0;"><strong>Distance:</strong> ${spot.distance_km} km</p>
          </div>
        `
      });

      marker.addListener('click', () => {
        infoWindow.open(map, marker);
      });
    });
  };

  return (
    <div className="map-container">
      <div id="map" className="map"></div>
      {GOOGLE_MAPS_API_KEY === 'placeholder-google-key' && (
        <div className="map-placeholder">
          <div className="map-placeholder-content">
            <h3>Map View</h3>
            <p>Google Maps integration requires API key</p>
            <p>Found {spots.length} parking spots in the area</p>
          </div>
        </div>
      )}
    </div>
  );
};

const AdBanner = ({ userRole }) => {
  if (userRole === 'premium') return null;

  return (
    <div className="ad-banner">
      <div className="ad-content">
        <h3>🚗 Premium Parking App</h3>
        <p>Upgrade to Premium for ad-free experience and exclusive features!</p>
        <button className="btn btn-upgrade">Upgrade Now</button>
      </div>
    </div>
  );
};

const LoginModal = ({ isOpen, onClose, isGuest = false }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isGuest) {
        const response = await axios.post(`${API}/auth/guest`);
        localStorage.setItem('user', JSON.stringify({ 
          role: 'guest', 
          guest_id: response.data.data.guest_id 
        }));
        window.location.reload();
        return;
      }

      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      if (response.data.success) {
        localStorage.setItem('token', response.data.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.data.user));
        window.location.reload();
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
        `${API}/subscription/upgrade`,
        { plan_name: plans[selectedPlan].name },
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
            className="btn btn-primary btn-upgrade-action"
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

  useEffect(() => {
    // Check for stored user session
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }

    // Perform initial search for London center
    performSearch({ latitude: 51.5074, longitude: -0.1278, radius_km: 2.0 });
  }, []);

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
    window.location.reload();
  };

  const handleUpgrade = () => {
    if (!user || user.role === 'guest') {
      alert('Please create an account to upgrade to Premium');
      setShowLoginModal(true);
      return;
    }
    setShowUpgradeModal(true);
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
      <Header 
        user={user}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onUpgrade={handleUpgrade}
      />
      
      <main className="main-content">
        <AdBanner userRole={user?.role} />
        
        <SearchForm 
          onSearch={performSearch}
          isLoading={loading}
          userRole={user?.role}
        />
        
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
      />
      
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
      />
    </div>
  );
}

export default App;