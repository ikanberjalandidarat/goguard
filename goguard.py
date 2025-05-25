"""
GoGuard - AI Guardian Angel for Safe Rides
Enhanced Hackathon Mockup with Voice Support and Gojek-like UI
"""

from flask import Flask, render_template, request, jsonify, session, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import json
import random
from datetime import datetime, timedelta
import threading
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import pandas as pd
import os
from typing import Tuple
import base64
import hashlib
import time
import requests
import io

# Import Qwen AI integration
try:
    from qwen_inference import QwenSafetyAI
    ai_assistant = QwenSafetyAI()
except Exception as e:
    print(f"Qwen AI module not found. Using fallback AI simulation: {e}")
    ai_assistant = None

# Import SerpAPI
try:
    from serpapi import GoogleSearch
    SERPAPI_KEY = "99bc69e7729d9076fb8b863ba4f99df50286f1816be181bd578f646905aa1cba"
except:
    print("SerpAPI not installed. Using requests fallback.")
    SERPAPI_KEY = "99bc69e7729d9076fb8b863ba4f99df50286f1816be181bd578f646905aa1cba"


app = Flask(__name__)
app.secret_key = 'goguard-secret-key-hackathon-2024'

# Mock Data Classes
@dataclass
class Driver:
    """Driver data class to match your existing structure"""
    id: str
    name: str
    photo: str
    rating: float
    total_rides: int
    acceptance_rate: float
    vehicle_number: str
    vehicle_model: str
    phone: str = ""
    join_date: str = ""
    status: str = "active"
    vehicle_type: str = ""
    vehicle_year: int = 2020
    last_location: Tuple[float, float] = (0.0, 0.0)
    total_earnings: int = 0
    avg_trip_duration: float = 0.0
    cancellation_rate: float = 0.0
    languages: str = ""
    vehicle_color: str = ""
    
    @property
    def safety_score(self) -> float:
        """Calculate safety score based on driver metrics"""
        # Base score from rating (normalized to 0-1)
        rating_score = (self.rating - 1) / 4  # Convert 1-5 rating to 0-1
        
        # Experience factor (more rides = higher safety)
        experience_factor = min(1.0, self.total_rides / 2000)
        
        # Acceptance rate factor
        acceptance_factor = self.acceptance_rate
        
        # Low cancellation rate is good
        cancellation_factor = 1 - self.cancellation_rate
        
        # Weighted average
        safety_score = (rating_score * 0.4 + 
                       experience_factor * 0.3 + 
                       acceptance_factor * 0.2 + 
                       cancellation_factor * 0.1)
        
        return min(1.0, max(0.0, safety_score))

@dataclass
class Ride:
    id: str
    driver: Driver
    pickup_location: str
    dropoff_location: str
    pickup_coords: tuple
    dropoff_coords: tuple
    estimated_duration: int
    route_type: str
    status: str
    is_safe_triggered: bool
    start_time: Optional[datetime] = None
    safety_events: List[Dict] = None
    transcripts: List[str] = None

# Mock Database
MOCK_DRIVERS = [
    Driver("D001", "Yadi Riyadi", "driver1.jpg", 5.0, 1523, 0.92, "D5323ACF", "Honda Vario"),
    Driver("D002", "Budi Santoso", "driver2.jpg", 4.5, 892, 0.85, "B5678DEF", "Yamaha NMAX"),
    Driver("D003", "Ahmad Prakoso", "driver3.jpg", 4.2, 234, 0.75, "B9012GHI", "Honda Beat"),
]

MOCK_LOCATIONS = {
    "home": {"name": "Jalan Jeruk Sitrun", "coords": (-6.2088, 106.8456), "safety_score": 0.9},
    "office": {"name": "GoTower - Pasaraya", "coords": (-6.2433, 106.7987), "safety_score": 0.95},
    "mall": {"name": "Grand Indonesia Mall", "coords": (-6.1951, 106.8218), "safety_score": 0.88},
    "friend": {"name": "Sarah's Place - Kemang", "coords": (-6.2633, 106.8133), "safety_score": 0.82},
    "restaurant": {"name": "Sate Khas Senayan", "coords": (-6.2275, 106.8007), "safety_score": 0.87},
}

# In-memory storage for active rides
active_rides: Dict[str, Ride] = {}
ride_reports = {}

def load_drivers_from_csv(file_path: str = 'drivers.csv') -> List[Driver]:
    """Load drivers from CSV file and return list of Driver objects"""
    try:
        df = pd.read_csv(file_path)
        drivers = []
        
        for _, row in df.iterrows():
            driver = Driver(
                id=row['driver_id'],
                name=row['name'],
                photo=row['photo'],
                rating=float(row['rating']),
                total_rides=int(row['total_trips']),
                acceptance_rate=float(row['acceptance_rate']),
                vehicle_number=row['license_plate'],
                vehicle_model=row['vehicle_model'],
                phone=row.get('phone', ''),
                join_date=row.get('join_date', ''),
                status=row.get('status', 'active'),
                vehicle_type=row.get('vehicle_type', ''),
                vehicle_year=int(row.get('vehicle_year', 2020)),
                last_location=(float(row.get('last_location_lat', 0)), 
                              float(row.get('last_location_lng', 0))),
                total_earnings=int(row.get('total_earnings', 0)),
                avg_trip_duration=float(row.get('avg_trip_duration', 0)),
                cancellation_rate=float(row.get('cancellation_rate', 0)),
                languages=row.get('languages', ''),
                vehicle_color=row.get('vehicle_color', '')
            )
            drivers.append(driver)
        
        print(f"✅ Successfully loaded {len(drivers)} drivers from CSV")
        return drivers
        
    except FileNotFoundError:
        print(f"❌ Error: {file_path} not found")
        return []
    except Exception as e:
        print(f"❌ Error loading drivers: {e}")
        return []

def load_locations_from_csv(file_path: str = 'locations.csv') -> Dict:
    """Load locations from CSV file and return dictionary compatible with your existing code"""
    try:
        df = pd.read_csv(file_path)
        locations = {}
        
        for _, row in df.iterrows():
            # Create a simple key from location_id (remove LOC prefix and convert to lowercase)
            key = row['location_id'].replace('LOC', '').zfill(3)  # e.g., LOC001 -> 001
            
            # You can also create more meaningful keys based on category or name
            # For compatibility with your existing code, let's also add some standard keys
            location_data = {
                "name": row['name'],
                "coords": (float(row['latitude']), float(row['longitude'])),
                "safety_score": float(row['safety_score']),
                "category": row.get('category', ''),
                "address": row.get('address', ''),
                "district": row.get('district', ''),
                "city": row.get('city', ''),
                "postal_code": row.get('postal_code', ''),
                "operating_hours": row.get('operating_hours', ''),
                "parking_available": row.get('parking_available', False),
                "accessibility": row.get('accessibility', ''),
                "popularity_score": float(row.get('popularity_score', 0)),
                "avg_wait_time": int(row.get('avg_wait_time', 0))
            }
            
            locations[key] = location_data
        
        # Map some locations to the original keys (For prototypes)
        if '001' in locations:  # Home location
            locations['home'] = locations['001']
        if '002' in locations:  # Office location
            locations['office'] = locations['002']
        if '003' in locations:  # Mall location
            locations['mall'] = locations['003']
        if '004' in locations:  # Friend location
            locations['friend'] = locations['004']
        if '005' in locations:  # Restaurant location
            locations['restaurant'] = locations['005']
        
        print(f"✅ Successfully loaded {len(locations)} locations from CSV")
        return locations
        
    except FileNotFoundError:
        print(f"❌ Error: {file_path} not found")
        return {}
    except Exception as e:
        print(f"❌ Error loading locations: {e}")
        return {}

def create_location_key_mapping(locations: Dict) -> Dict[str, str]:
    """Create a mapping of location names to keys for easier lookup"""
    mapping = {}
    for key, location in locations.items():
        # Create mappings based on name keywords
        name_lower = location['name'].lower()
        if 'home' in name_lower or 'apartment' in name_lower:
            mapping['home'] = key
        elif 'office' in name_lower or 'tower' in name_lower:
            mapping['office'] = key
        elif 'mall' in name_lower and 'grand indonesia' in name_lower:
            mapping['mall'] = key
        elif 'kemang' in name_lower:
            mapping['friend'] = key
        elif 'restaurant' in name_lower or 'sate' in name_lower:
            mapping['restaurant'] = key
    
    return mapping

# Main loading function
def load_all_data(drivers_file: str = 'drivers.csv', locations_file: str = 'locations.csv'):
    """Load both drivers and locations data"""
    print("🔄 Loading data from CSV files...")
    
    drivers = load_drivers_from_csv(drivers_file)
    locations = load_locations_from_csv(locations_file)
    location_mapping = create_location_key_mapping(locations)
    
    print(f"📊 Data loading complete:")
    print(f"   - Drivers: {len(drivers)}")
    print(f"   - Locations: {len(locations)}")
    print(f"   - Location mappings: {len(location_mapping)}")
    
    return drivers, locations, location_mapping

# Simple one-line loader for main method
def load_csv_data():
    """One-line method to load all CSV data and return as tuple"""
    return load_all_data()

news_cache = {}  # Cache news results to avoid excessive API calls

# News Analysis Functions
def search_safety_news(pickup_area: str, dropoff_area: str) -> List[Dict]:
    """Search for safety-related news using SerpAPI"""
    cache_key = f"{pickup_area}_{dropoff_area}_{datetime.now().strftime('%Y%m%d')}"
    
    # Check cache first (24-hour cache)
    if cache_key in news_cache:
        cached_data = news_cache[cache_key]
        if (datetime.now() - cached_data['timestamp']).seconds < 86400:  # 24 hours
            return cached_data['results']
    
    try:
        # Prepare search queries
        queries = [
            f"kecelakaan ojol {pickup_area} OR {dropoff_area} Jakarta",
            f"penculikan ojol {pickup_area} {dropoff_area} Jakarta",
            f"demo macet bahaya {pickup_area} OR {dropoff_area} malam",
            f"begal ojol {pickup_area} OR {dropoff_area} malam",
        ]
        
        all_results = []
        
        for query in queries:
            params = {
                "q": query,
                "location": "Jakarta, Indonesia",
                "hl": "id",
                "gl": "id",
                "google_domain": "google.co.id",
                "api_key": SERPAPI_KEY,
                "num": 5,  # Limit results per query
                "tbs": "qdr:w"  # Results from past week
            }
            
            try:
                # Try using serpapi library if available
                search = GoogleSearch(params)
                results = search.get_dict()
            except:
                # Fallback to requests
                response = requests.get('https://serpapi.com/search', params=params)
                results = response.json()
            
            if 'organic_results' in results:
                for result in results['organic_results'][:3]:  # Top 3 per query
                    news_item = {
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', ''),
                        'source': result.get('source', 'Unknown'),
                        'link': result.get('link', ''),
                        'date': result.get('date', 'Recent'),
                        'severity': analyze_news_severity(result)
                    }
                    all_results.append(news_item)
        
        # Cache results
        news_cache[cache_key] = {
            'timestamp': datetime.now(),
            'results': all_results
        }
        
        return all_results
        
    except Exception as e:
        print(f"News search error: {e}")
        return []

def analyze_news_severity(news_item: Dict) -> str:
    """Analyze news severity based on content"""
    title = news_item.get('title', '').lower()
    snippet = news_item.get('snippet', '').lower()
    combined_text = title + ' ' + snippet
    
    # High severity keywords
    high_severity = ['penculikan', 'pembunuhan', 'pemerkosaan', 'perampokan', 
                     'begal', 'tewas', 'meninggal', 'korban jiwa']
    
    # Medium severity keywords
    medium_severity = ['kecelakaan', 'tabrakan', 'luka', 'terluka', 'pencurian',
                       'copet', 'jambret', 'kriminal']
    
    # Check severity
    if any(keyword in combined_text for keyword in high_severity):
        return 'high'
    elif any(keyword in combined_text for keyword in medium_severity):
        return 'medium'
    else:
        return 'low'

def calculate_news_impact_on_safety(news_results: List[Dict], base_score: float) -> Dict:
    """Calculate how news impacts the safety score"""
    if not news_results:
        return {
            'adjusted_score': base_score,
            'news_factor': 1.0,
            'risk_increase': 0
        }
    
    # Count severity levels
    severity_counts = {'high': 0, 'medium': 0, 'low': 0}
    for news in news_results:
        severity_counts[news.get('severity', 'low')] += 1
    
    # Calculate impact
    news_factor = 1.0
    if severity_counts['high'] > 0:
        news_factor = 0.75  # 25% reduction for high severity news
    elif severity_counts['medium'] >= 2:
        news_factor = 0.85  # 15% reduction for multiple medium severity
    elif severity_counts['medium'] == 1:
        news_factor = 0.92  # 8% reduction for single medium severity
    
    adjusted_score = base_score * news_factor
    risk_increase = round((1 - news_factor) * 100)
    
    return {
        'adjusted_score': adjusted_score,
        'news_factor': news_factor,
        'risk_increase': risk_increase,
        'severity_summary': severity_counts
    }

# AI Safety Analysis Functions
def calculate_ride_risk_score(driver: Driver, pickup: str, dropoff: str, time_of_day: int) -> Dict:
    """Calculate risk score using Qwen AI or fallback"""
    if ai_assistant:
        ride_data = {
            "driver_name": driver.name,
            "driver_rating": driver.rating,
            "driver_rides": driver.total_rides,
            "time": f"{time_of_day}:00",
            "pickup": MOCK_LOCATIONS[pickup]['name'],
            "dropoff": MOCK_LOCATIONS[dropoff]['name']
        }
        return ai_assistant.analyze_ride_safety(ride_data)
    
    # Fallback calculation
    base_score = driver.safety_score
    time_factor = 1.0
    if time_of_day >= 22 or time_of_day <= 5:
        time_factor = 0.8
    elif time_of_day >= 19:
        time_factor = 0.9
    
    pickup_safety = MOCK_LOCATIONS.get(pickup, {}).get("safety_score", 0.8)
    dropoff_safety = MOCK_LOCATIONS.get(dropoff, {}).get("safety_score", 0.8)
    location_factor = (pickup_safety + dropoff_safety) / 2
    experience_factor = min(1.0, driver.total_rides / 1000)
    
    final_score = (base_score * 0.4 + location_factor * 0.3 + 
                   time_factor * 0.2 + experience_factor * 0.1)
    
    risk_level = "LOW"
    if final_score < 0.7:
        risk_level = "HIGH"
    elif final_score < 0.85:
        risk_level = "MEDIUM"
    
    return {
        "safety_score": round(final_score, 2),
        "risk_level": risk_level,
        "factors": {
            "driver": round(base_score, 2),
            "location": round(location_factor, 2),
            "time": round(time_factor, 2),
            "experience": round(experience_factor, 2)
        }
    }

total_text = []

def analyze_voice_sentiment(text: str, context: Dict = None) -> Dict:
    global total_text
    
    """Analyze voice sentiment using Qwen AI or fallback"""
    if ai_assistant:
        return ai_assistant.analyze_voice_distress(text, context or {})
    
    # Append
    total_text.append(text)
    
    # Fallback analysis
    distress_keywords = ["help", "stop", "wrong", "scared", "please", "no", "hurt"]
    concern_keywords = ["uncomfortable", "weird", "strange", "lost", "where"]
    
    text_lower = text.lower()
    distress_count = sum(1 for word in distress_keywords if word in text_lower)
    concern_count = sum(1 for word in concern_keywords if word in text_lower)
    
    if distress_count >= 2:
        return {
            "distress_level": "DISTRESS",
            "confidence": 0.9,
            "ai_response": "I've detected you might be in distress. Would you like me to contact emergency services?",
            "actions": ["contact_emergency", "share_location", "silent_alarm"]
        }
    elif distress_count >= 1 or concern_count >= 2:
        return {
            "distress_level": "CONCERN",
            "confidence": 0.7,
            "ai_response": "I noticed you might be uncomfortable. How can I help you feel safer?",
            "actions": ["share_location", "call_support"]
        }
    else:
        return {
            "distress_level": "NORMAL",
            "confidence": 0.8,
            "ai_response": "Your ride is progressing smoothly. I'm here if you need anything!",
            "actions": []
        }

# Routes
@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')

@app.route('/book-ride')
def book_ride():
    """Ride booking page"""
    return render_template('book_ride.html', 
                         locations=MOCK_LOCATIONS,
                         current_time=datetime.now().hour)

@app.route('/api/calculate-risk', methods=['POST'])
def calculate_risk():
    """API endpoint for risk calculation with news integration"""
    data = request.json
    driver = random.choice(MOCK_DRIVERS)
    
    # Get base risk analysis
    risk_analysis = calculate_ride_risk_score(
        driver,
        data['pickup'],
        data['dropoff'],
        datetime.now().hour
    )
    
    # Get location names for news search
    pickup_name = MOCK_LOCATIONS.get(data['pickup'], {}).get('name', '')
    dropoff_name = MOCK_LOCATIONS.get(data['dropoff'], {}).get('name', '')
    
    # Extract area names
    pickup_area = extract_area_name(pickup_name)
    dropoff_area = extract_area_name(dropoff_name)
    
    # Search for safety news
    news_results = search_safety_news(pickup_area, dropoff_area)
    
    # Calculate news impact on safety
    news_impact = calculate_news_impact_on_safety(
        news_results, 
        risk_analysis.get('safety_score', risk_analysis.get('score', 0.85))
    )
    
    # Update risk analysis with news impact
    risk_analysis['original_score'] = risk_analysis.get('safety_score', risk_analysis.get('score'))
    risk_analysis['safety_score'] = news_impact['adjusted_score']
    risk_analysis['score'] = news_impact['adjusted_score']
    
    # Adjust risk level based on new score
    if news_impact['adjusted_score'] < 0.7:
        risk_analysis['risk_level'] = 'HIGH'
        risk_analysis['level'] = 'HIGH'
    elif news_impact['adjusted_score'] < 0.85:
        risk_analysis['risk_level'] = 'MEDIUM'
        risk_analysis['level'] = 'MEDIUM'
    
    return jsonify({
        "driver": {
            "name": driver.name,
            "rating": driver.rating,
            "rides": driver.total_rides,
            "vehicle": driver.vehicle_number
        },
        "risk_analysis": risk_analysis,
        "safe_route_available": risk_analysis.get('risk_level', 'LOW') != 'LOW',
        "locations": {
            "pickup": pickup_name,
            "dropoff": dropoff_name,
            "pickup_area": pickup_area,
            "dropoff_area": dropoff_area
        },
        "news_analysis": {
            "news_found": len(news_results),
            "news_items": news_results[:5],  # Limit to 5 items for UI
            "impact": news_impact,
            "timestamp": datetime.now().isoformat()
        }
    })
    
def extract_area_name(location: str) -> str:
    """Extract area name from full location string"""
    # Common Jakarta area mappings
    area_mappings = {
        'Sudirman': ['Sudirman', 'Jalan Sudirman'],
        'Kemang': ['Kemang', 'Jalan Kemang'],
        'Senayan': ['Senayan', 'Jalan Senayan'],
        'Thamrin': ['Thamrin', 'Grand Indonesia'],
        'Blok M': ['Blok M', 'Pasaraya'],
        'Serpong': ['Serpong', 'BSD'],
        'PIK': ['PIK', 'Pantai Indah Kapuk'],
        'Kelapa Gading': ['Kelapa Gading', 'Gading'],
        'Pondok Indah': ['Pondok Indah', 'PI'],
        'Kuningan': ['Kuningan', 'Rasuna Said']
    }
    
    location_lower = location.lower()
    for area, keywords in area_mappings.items():
        for keyword in keywords:
            if keyword.lower() in location_lower:
                return area
    
    # If no specific area found, try to extract from location
    parts = location.split(' - ')
    if len(parts) > 1:
        return parts[1].split()[0]  # Get first word after dash
    
    return location.split()[0]  # Default to first word

@app.route('/api/search-news', methods=['POST'])
def api_search_news():
    """Direct API endpoint for news search"""
    data = request.json
    pickup_area = data.get('pickup_area', 'Jakarta')
    dropoff_area = data.get('dropoff_area', 'Jakarta')
    
    news_results = search_safety_news(pickup_area, dropoff_area)
    
    return jsonify({
        "status": "success",
        "news_count": len(news_results),
        "news_items": news_results,
        "areas_searched": [pickup_area, dropoff_area],
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/start-ride', methods=['POST'])
def start_ride():
    """Start a ride and initialize GoGuard monitoring"""
    data = request.json
    ride_id = f"RIDE_{int(time.time())}"
    
    driver = MOCK_DRIVERS[random.randrange(0, len(MOCK_DRIVERS))]  # Use Yadi Riyadi for demo
    ride = Ride(
        id=ride_id,
        driver=driver,
        pickup_location=MOCK_LOCATIONS[data['pickup']]['name'],
        dropoff_location=MOCK_LOCATIONS[data['dropoff']]['name'],
        pickup_coords=MOCK_LOCATIONS[data['pickup']]['coords'],
        dropoff_coords=MOCK_LOCATIONS[data['dropoff']]['coords'],
        estimated_duration=random.randint(1, 1), # For testing purposes
        route_type=data.get('route_type', 'standard'),
        status='ACTIVE',
        start_time=datetime.now(),
        safety_events=[],
        transcripts=[],
        is_safe_triggered=False,
    )
    
    active_rides[ride_id] = ride
    session['current_ride'] = ride_id
    
    # Start monitoring thread
    threading.Thread(target=monitor_ride, args=(ride_id,), daemon=True).start()
    
    return jsonify({
        "ride_id": ride_id,
        "status": "STARTED",
        "guardian_active": True
    })

@app.route('/ride-monitor/<ride_id>')
def ride_monitor(ride_id):
    """Real-time ride monitoring dashboard"""
    if ride_id not in active_rides:
        return "Ride not found", 404
    
    ride = active_rides[ride_id]
    return render_template('ride_monitor.html', ride=ride)

@app.route('/api/ride-status/<ride_id>')
def ride_status(ride_id):
    """Get current ride status and safety events"""
    if ride_id not in active_rides:
        return jsonify({"error": "Ride not found"}), 404
    
    ride = active_rides[ride_id]
    elapsed = (datetime.now() - ride.start_time).seconds / 60
    progress = min(100, (elapsed / ride.estimated_duration) * 100)
    
    return jsonify({
        "ride_id": ride_id,
        "status": ride.status,
        "progress": round(progress, 1),
        "elapsed_minutes": round(elapsed, 1),
        "safety_events": ride.safety_events,
        "current_location": simulate_current_location(ride, progress)
    })

@app.route('/api/voice-check', methods=['POST'])
def voice_check():
    """Analyze voice input for safety concerns"""
    data = request.json
    ride_id = data.get('ride_id')
    voice_text = data.get('text', '')
    
    if ride_id not in active_rides:
        return jsonify({"error": "Ride not found"}), 404
    
    ride = active_rides[ride_id]
    ride.transcripts.append(voice_text)
    elapsed = (datetime.now() - ride.start_time).seconds / 60
    
    context = {
        "location": "En route",
        "duration": round(elapsed)
    }
    
    sentiment = analyze_voice_sentiment(voice_text, context)
    ride.is_safe_triggered = ride.is_safe_triggered or sentiment["is_safe_triggered"]
    
    if sentiment['distress_level'] in ['DISTRESS', 'CONCERN']:
        active_rides[ride_id].safety_events.append({
            "timestamp": datetime.now().isoformat(),
            "type": "VOICE_ALERT",
            "level": sentiment['distress_level'],
            "details": f"Voice analysis detected {sentiment['distress_level']}"
        })
    
    return jsonify(sentiment)

@app.route('/api/emergency-action', methods=['POST'])
def emergency_action():
    """Handle emergency actions"""
    data = request.json
    ride_id = data.get('ride_id')
    action = data.get('action')
    
    if ride_id not in active_rides:
        return jsonify({"error": "Ride not found"}), 404
    
    ride = active_rides[ride_id]
    ride.safety_events.append({
        "timestamp": datetime.now().isoformat(),
        "type": "EMERGENCY_ACTION",
        "action": action,
        "status": "TRIGGERED"
    })
    
    response = {
        "action": action,
        "status": "SUCCESS",
        "message": ""
    }
    
    if action == "contact_emergency":
        response["message"] = "Emergency services have been notified. Help is on the way."
        response["emergency_id"] = f"EMG_{int(time.time())}"
    elif action == "share_location":
        response["message"] = "Your location has been shared with trusted contacts."
        response["shared_with"] = ["Mom", "Best Friend"]
    elif action == "silent_alarm":
        response["message"] = "Silent alarm activated. GoOps team is monitoring your ride."
        response["monitoring_id"] = f"MON_{int(time.time())}"
    
    return jsonify(response)

@app.route('/api/end-ride/<ride_id>', methods=['POST'])
def end_ride(ride_id):
    """End ride and generate safety report"""
    if ride_id not in active_rides:
        return jsonify({"error": "Ride not found"}), 404
    
    ride = active_rides[ride_id]
    ride.status = "COMPLETED"
    
    # Generate safety report
    ride_reports[ride_id] = generate_safety_report(ride)
    
    del active_rides[ride_id]
    session.pop('current_ride', None)
    
    return jsonify({
        "status": "COMPLETED",
        "safety_report": ride_reports[ride_id]
    })

@app.route('/safety-report/<ride_id>')
def safety_report(ride_id):
    """Display post-ride safety report"""
    
    print("===== DEBUGGING =========")
    print(ride_reports)

    mock_report = {
        "ride_id": ride_id,
        "overall_safety_score": 0.92,
        "duration": f"{ride_reports[ride_id]['duration']}",
        "route_compliance": "98%",
        "driver_behavior": "Excellent",
        "incidents": 0,
        "ai_interventions": 1,
        "recommendations": [
            "Consider using Safe Route mode for late-night rides",
            "Your trusted contacts were successfully notified"
        ],
        'transcript': " ".join(total_text),
        'qwen_response': ride_reports[ride_id]['qwen_response'],
    }
    
    
    print("======== DEBUGGING =======")
    print(ride_reports[ride_id]['qwen_response'])
    
    return render_template('safety_report.html', report={"ride_id": ride_id, **ride_reports[ride_id]})

@app.route('/download-report/<ride_id>')
def download_report(ride_id):
    print("DOWNLOAD REPORT", ride_id)
    
    data = ride_reports[ride_id]
    
    print("Data", data)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Ride Safety Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Overview
    overview_data = [
        ["ID", data.get("id", "RIDE_NULL")],
        ["Safety Score", data.get("safety_score", "")],
        ["Driver", f'{data["driver"]["name"]} ({data["driver"]["phone"]})'],
        ["Driver Rating", data["driver"]["rating"]],
        ["Driver Vehicle", f'{data["driver"]["vehicle_color"]} {data["driver"]["vehicle_model"]} {data["driver"]["vehicle_number"]}'],
        ["Pickup", f'{data.get("pickup_location", "Unknown")} {data.get("pickup_coords", "")}'],
        ["Dropoff", f'{data.get("dropoff_location", "Unknown")} {data.get("dropoff_coords", "")}'],
        ["Route Type", data.get("route_type", "")],
        ["Duration", data.get("duration", "")],
        # ["Incidents", data.get("incidents", "")],
        ["Transcripts", data.get("transcripts", [])],
        ["Recommendations", ', '.join(data.get("recommendations", []))],
        ["Summary", data.get("qwen_response", "")],
    ]
    for key, value in overview_data:
        elements.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Safety Events
    events = data.get("safety_events", [])
    if events:
        event_keys = list(events[0].keys())
        table_data = [event_keys]  # headers
        for event in events:
            table_data.append([str(event.get(k, "")) for k in event_keys])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(Paragraph("Safety Events", styles['Heading2']))
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='ride_report.pdf',
        mimetype='application/pdf'
    )

# Helper Functions
def monitor_ride(ride_id):
    """Background thread to monitor ride"""
    while ride_id in active_rides and active_rides[ride_id].status == 'ACTIVE':
        time.sleep(10)
        
        if random.random() < 0.05:
            active_rides[ride_id].safety_events.append({
                "timestamp": datetime.now().isoformat(),
                "type": "ROUTE_DEVIATION",
                "details": "Minor route adjustment detected"
            })

def simulate_current_location(ride, progress):
    """Simulate current location based on progress"""
    lat1, lon1 = ride.pickup_coords
    lat2, lon2 = ride.dropoff_coords
    
    current_lat = lat1 + (lat2 - lat1) * (progress / 100)
    current_lon = lon1 + (lon2 - lon1) * (progress / 100)
    
    return {
        "lat": round(current_lat, 6),
        "lon": round(current_lon, 6),
        "address": f"En route - {round(progress)}% completed"
    }

def generate_safety_report(ride: Ride):
    """Generate post-ride safety report"""

    print("===== DEBUGGING =========")
    print(ai_assistant)
    
    if ai_assistant:
        ride_data = {
            "duration": f"{(datetime.now() - ride.start_time).seconds // 60} minutes",
            "route_type": ride.route_type,
            "events": ride.safety_events,
            "is_safe_triggered": ride.is_safe_triggered,
        }
        test_output = ai_assistant.summarize_ride_safety(ride_data)
        
        print("===== DEBUGGING - AI ASSISTANT =========")
        print(test_output)
        
        ride_dict = asdict(ride)
        
        return {**ride_dict, **test_output}
    
    print("===== DEBUGGING - NO AI ASSISTANT =========")

    incident_count = len([e for e in ride.safety_events if e['type'] != 'VOICE_CHECK'])
    safety_score = max(0.5, 1.0 - (incident_count * 0.1))
    
    return {
        "overall_score": round(safety_score, 2),
        "incidents": incident_count,
        "duration": f"{(datetime.now() - ride.start_time).seconds // 60} minutes",
        "driver_rating": ride.driver.rating,
        "route_type": ride.route_type,
        "events": ride.safety_events
    }

# Create templates directory and HTML templates
if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Load the data
    MOCK_DRIVERS, MOCK_LOCATIONS, location_mapping = load_csv_data()
    
    # Create base template with enhanced stylin
    base_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoGuard - {% block title %}{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: #f5f5f5;
            color: #333;
        }
        .mobile-container {
            max-width: 430px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            position: relative;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        .gojek-header {
            background: #333;
            color: white;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .gojek-header h1 {
            font-size: 20px;
            font-weight: 600;
        }
        .container { padding: 20px; }
        .card { 
            background: white; 
            border-radius: 16px; 
            padding: 20px; 
            margin-bottom: 16px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .btn { 
            display: inline-block; 
            padding: 14px 24px; 
            background: #00AA13; 
            color: white; 
            text-decoration: none; 
            border-radius: 25px; 
            border: none; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 600;
            width: 100%;
            text-align: center;
            transition: all 0.3s;
        }
        .btn:hover { background: #008810; transform: translateY(-1px); }
        .btn-secondary { background: #666; }
        .btn-outline {
            background: white;
            border: 2px solid #00AA13;
            color: #00AA13;
        }
        .btn-danger { background: #ff4444; }
        .risk-score { 
            display: inline-block; 
            padding: 6px 16px; 
            border-radius: 20px; 
            font-weight: bold;
            font-size: 14px;
        }
        .risk-low { background: #E8F5E9; color: #2E7D32; }
        .risk-medium { background: #FFF3E0; color: #F57C00; }
        .risk-high { background: #FFEBEE; color: #C62828; }
        .safety-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-content {
            background: white;
            border-radius: 20px;
            padding: 24px;
            margin: 20px;
            max-width: 380px;
            width: 90%;
            text-align: center;
        }
        .shield-icon {
            font-size: 60px;
            color: #00AA13;
            margin-bottom: 16px;
        }
        .map-container {
            width: 100%;
            height: 300px;
            background: #e0e0e0;
            border-radius: 12px;
            position: relative;
            overflow: hidden;
            margin-bottom: 16px;
        }
        .driver-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .driver-photo {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: #00AA13;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
        }
        .driver-info h3 {
            margin: 0;
            font-size: 18px;
        }
        .driver-info p {
            margin: 4px 0;
            color: #666;
            font-size: 14px;
        }
        .action-buttons {
            display: flex;
            gap: 12px;
            margin-top: 16px;
        }
        .action-btn {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .action-btn:hover {
            background: #f5f5f5;
        }
        .voice-indicator {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: linear-gradient(135deg, #00AA13, #00DD17);
            margin: 20px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            cursor: pointer;
            transition: all 0.3s;
        }
        .voice-indicator.active {
            animation: pulse 1.5s infinite;
        }
        .voice-indicator:hover {
            transform: scale(1.05);
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(0, 170, 19, 0.4); }
            70% { box-shadow: 0 0 0 20px rgba(0, 170, 19, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 170, 19, 0); }
        }
        .status-pill {
            display: inline-block;
            padding: 4px 12px;
            background: #E8F5E9;
            color: #2E7D32;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .progress-container {
            margin: 20px 0;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #e0e0e0;
            border-radius: 3px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: #00AA13;
            transition: width 0.3s;
        }
        .emergency-fab {
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: #ff4444;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 12px rgba(255,68,68,0.3);
            cursor: pointer;
            z-index: 50;
        }
        .bottom-sheet {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            border-radius: 20px 20px 0 0;
            padding: 20px;
            transform: translateY(100%);
            transition: transform 0.3s;
            max-width: 430px;
            margin: 0 auto;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
        }
        .bottom-sheet.active {
            transform: translateY(0);
        }
        .safety-event {
            padding: 12px;
            margin: 8px 0;
            border-left: 4px solid #FF9800;
            background: #FFF3E0;
            border-radius: 8px;
        }
        .safety-event.distress {
            border-left-color: #f44336;
            background: #FFEBEE;
        }
        input[type="text"], select {
            width: 100%;
            padding: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus, select:focus {
            outline: none;
            border-color: #00AA13;
        }
        .location-item {
            display: flex;
            align-items: center;
            padding: 12px 0;
            gap: 12px;
        }
        .location-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: #E8F5E9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #00AA13;
        }
        @media (max-width: 430px) {
            .mobile-container {
                box-shadow: none;
            }
        }
    </style>
    {% block extra_style %}{% endblock %}
</head>
<body>
    <div class="mobile-container">
        <div class="gojek-header">
            <h1>GoRide</h1>
            <span style="font-size: 12px;">🛡️ GoGuard Active</span>
        </div>
        {% block content %}{% endblock %}
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    {% block extra_script %}{% endblock %}
</body>
</html>'''
    
    # Create index.html
    index_html = '''{% extends "base.html" %}
{% block title %}Home{% endblock %}
{% block content %}
<div class="container">
    <div class="card" style="background: linear-gradient(135deg, #00AA13, #00DD17); color: white;">
        <h2 style="font-size: 28px; margin-bottom: 12px;">Welcome to GoGuard 🛡️</h2>
        <p style="font-size: 16px; opacity: 0.95; line-height: 1.6;">
            Your AI-powered safety companion for every Gojek ride
        </p>
    </div>
    
    <div class="card">
        <h3 style="margin-bottom: 20px;">How GoGuard Protects You</h3>
        
        <div class="location-item">
            <div class="location-icon">🤖</div>
            <div>
                <strong>AI Voice Guardian</strong>
                <p style="color: #666; font-size: 14px;">Real-time monitoring detects distress</p>
            </div>
        </div>
        
        <div class="location-item">
            <div class="location-icon">🗺️</div>
            <div>
                <strong>Safe Route Mode</strong>
                <p style="color: #666; font-size: 14px;">Well-lit paths with surveillance</p>
            </div>
        </div>
        
        <div class="location-item">
            <div class="location-icon">🚨</div>
            <div>
                <strong>One-Touch Emergency</strong>
                <p style="color: #666; font-size: 14px;">Instant help when you need it</p>
            </div>
        </div>
        
        <div class="location-item">
            <div class="location-icon">📊</div>
            <div>
                <strong>Safety Analytics</strong>
                <p style="color: #666; font-size: 14px;">AI-powered risk assessment</p>
            </div>
        </div>
    </div>
    
    <div style="padding: 0 20px;">
        <a href="/book-ride" class="btn">
            Start Safe Ride Demo
        </a>
    </div>
</div>
{% endblock %}'''
    
    # Create book_ride.html
    book_ride_html = '''{% extends "base.html" %}
{% block title %}Book Safe Ride{% endblock %}
{% block content %}
<div class="container">
    <div class="card">
        <h3 style="margin-bottom: 20px;">Where are you going?</h3>
        
        <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 8px; color: #666; font-size: 14px;">
                <span style="color: #00AA13;">●</span> Pickup location
            </label>
            <select id="pickup">
                {% for key, loc in locations.items() %}
                <option value="{{ key }}">{{ loc.name }}</option>
                {% endfor %}
            </select>
        </div>
        
        <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 8px; color: #666; font-size: 14px;">
                <span style="color: #ff4444;">●</span> Drop-off location
            </label>
            <select id="dropoff">
                {% for key, loc in locations.items() %}
                <option value="{{ key }}" {% if key == 'office' %}selected{% endif %}>{{ loc.name }}</option>
                {% endfor %}
            </select>
        </div>
        
        <button onclick="calculateRisk()" class="btn">
            Check Safety & Continue
        </button>
    </div>
    
    <!-- News Alert Section -->
    <div id="newsAlert" style="display: none;">
        <div class="card news-alert">
            <h4 style="margin-bottom: 12px;">📰 AI Safety Intelligence - Recent Area Updates</h4>
            <div id="newsContent">
                <div style="text-align: center; padding: 20px;">
                    <div class="loading-spinner"></div>
                    <p style="margin-top: 12px; color: #666;">Analyzing safety data from multiple sources...</p>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Safety Modal -->
<div id="safetyModal" class="safety-modal" style="display: none;">
    <div class="modal-content">
        <div class="shield-icon">🛡️</div>
        <h2>Turn On "Safe Route Mode"?</h2>
        <p style="color: #666; margin: 16px 0; line-height: 1.5;">
            Our AI will continuously monitor your journey and promptly send assistance upon detecting any sounds indicating distress.
        </p>
        
        <div id="riskInfo" style="margin: 20px 0;"></div>
        
        <button onclick="startRide('safe')" class="btn" style="margin-bottom: 12px;">
            Turn On
        </button>
        <button onclick="startRide('standard')" class="btn btn-outline">
            Maybe later
        </button>
    </div>
</div>

<!-- Loading Spinner -->
<div id="loadingSpinner" style="display: none; text-align: center; padding: 20px;">
  <img src="https://i.imgur.com/Yk52CBY.gif" alt="Loading..."/>
</div>

<style>
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>

<script>
let currentRiskData = null;


function calculateRisk() {
    const pickup = document.getElementById('pickup').value;
    const dropoff = document.getElementById('dropoff').value;
    document.getElementById('loadingSpinner').style.display = 'block'; // Show spinner

    fetch('/api/calculate-risk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pickup, dropoff})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('loadingSpinner').style.display = 'none'; // Hide spinner

        currentRiskData = data;
        showSafetyModal(data);
    });
}

let newsData = [];

function calculateRisk() {
    const pickup = document.getElementById('pickup').value;
    const dropoff = document.getElementById('dropoff').value;
    
    document.getElementById('loadingSpinner').style.display = 'block'; // Show spinner
    document.getElementById('newsAlert').style.display = 'block'; // Show news section immediately

    fetch('/api/calculate-risk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ pickup, dropoff })
    })
    .then(res => res.json())
    .then(data => {
        currentRiskData = data;
        
        const newsContent = document.getElementById('newsContent');
        const newsItems = data.news_analysis?.news_items || [];
        const impact = data.news_analysis?.impact;

        if (!newsItems || newsItems.length === 0) {
            newsContent.innerHTML = `
                <div class="news-box safe">
                    <div class="icon">✅</div>
                    <div class="headline">No recent safety incidents reported</div>
                    <div class="summary">This area has been safe in the past week</div>
                </div>
            `;
        } else {
            let newsHtml = '';

            if (impact && impact.risk_increase > 0) {
                newsHtml += `
                    <div class="news-alert-box">
                        <div class="icon">⚠️ Safety Alert</div>
                        <div class="headline">
                            Recent incidents detected. Risk increased by ${impact.risk_increase}%
                        </div>
                        <div class="summary">
                            ${impact.severity_summary.high} high severity<br>
                            ${impact.severity_summary.medium} medium severity
                        </div>
                    </div>
                `;
            }

            newsItems.forEach(item => {
                const severityIcon = item.severity === 'high' ? '🚨' :
                                     item.severity === 'medium' ? '⚠️' : 'ℹ️';
                const severityLabel = item.severity?.toUpperCase() || 'LOW';

                newsHtml += `
                    <div class="news-item">
                        <div class="title">${item.title}</div>
                        <div class="snippet">${item.snippet}</div>
                        <div class="meta">
                            ${item.source} • ${item.date} • ${severityIcon} ${severityLabel}
                        </div>
                    </div>
                `;
            });

            newsHtml += `
                <div class="news-footer">
                    Areas analyzed: ${currentRiskData.locations.pickup_area} → ${currentRiskData.locations.dropoff_area}<br>
                    Data sources: News articles, police reports, community alerts<br>
                    Last updated: ${new Date().toLocaleTimeString()}
                </div>
            `;

            newsContent.innerHTML = newsHtml;
        }

        // Show safety modal after a short delay
        setTimeout(() => showSafetyModal(data), 1000);
    })
    .catch(error => {
        console.error('Risk calculation error:', error);
        document.getElementById('newsContent').innerHTML = `
            <div class="error-message">❌ Unable to fetch safety data. Please try again.</div>
        `;
    });
}



function showSafetyModal(data) {
    const riskLevel = data.risk_analysis.risk_level || data.risk_analysis.level;
    const riskScore = data.risk_analysis.safety_score || data.risk_analysis.score;
    
    let riskHtml = `
        <div style="text-align: center;">
            <p style="font-size: 14px; color: #666;">AI Safety Score</p>
            <h3 style="font-size: 32px; margin: 8px 0;">${Math.round(riskScore * 100)}%</h3>
            <span class="risk-score risk-${riskLevel.toLowerCase()}">${riskLevel} RISK</span>
        </div>
    `;
    
    if (riskLevel !== 'LOW') {
        riskHtml += `
            <div style="margin-top: 16px; padding: 12px; background: #FFF3E0; border-radius: 8px;">
                <p style="color: #F57C00; font-size: 14px;">
                    ⚠️ Late night ride detected. Safe Route adds 2-3 minutes but uses well-lit streets.
                </p>
            </div>
        `;
    }
    
    document.getElementById('riskInfo').innerHTML = riskHtml;
    document.getElementById('safetyModal').style.display = 'flex';
}

function startRide(routeType) {
    const pickup = document.getElementById('pickup').value;
    const dropoff = document.getElementById('dropoff').value;
    
    fetch('/api/start-ride', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pickup, dropoff, route_type: routeType})
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'STARTED') {
            window.location.href = `/ride-monitor/${data.ride_id}`;
        }
    });
}

// Close modal on outside click
document.getElementById('safetyModal').addEventListener('click', function(e) {
    if (e.target === this) {
        this.style.display = 'none';
    }
});
</script>
{% endblock %}'''
    
    # Create ride_monitor.html with enhanced UI
    ride_monitor_html = '''{% extends "base.html" %}
{% block title %}Ride in Progress{% endblock %}
{% block content %}
<!-- Map Container -->
<div style="position: relative; width: 100%; height: 300px; border-radius: 12px; overflow: hidden;">
    <div id="map" style="width: 100%; height: 100%;"></div>

    <div style="position: absolute; bottom: 20px; left: 10px; background: white; padding: 8px 12px; border-radius: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); z-index: 10;">
        <span class="status-pill">● On the way with you</span>
    </div>
</div>

<script>
  function initMap() {
    const dropoffCoords = { lat: {{ ride.dropoff_coords[0] }}, lng: {{ ride.dropoff_coords[1] }} };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((position) => {
        const pickupCoords = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };

        const map = new google.maps.Map(document.getElementById("map"), {
          center: pickupCoords,
          zoom: 13,
        });

        const directionsService = new google.maps.DirectionsService();
        const directionsRenderer = new google.maps.DirectionsRenderer();
        directionsRenderer.setMap(map);

        const request = {
          origin: pickupCoords,
          destination: dropoffCoords,
          travelMode: google.maps.TravelMode.DRIVING,
        };

        directionsService.route(request, function (result, status) {
          if (status === google.maps.DirectionsStatus.OK) {
            directionsRenderer.setDirections(result);
          } else {
            alert("Could not display route due to: " + status);
          }
        });
      }, () => {
        alert("Geolocation failed.");
      });
    } else {
      alert("Geolocation not supported by this browser.");
    }
  }
</script>

<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyACBCUnTPrc4-YTMDc4Xvk3CqBcHlMTILE&callback=initMap" async defer></script>

<div class="container">
    <!-- Driver Card -->
    <div class="driver-card" style="margin-top: -40px; position: relative; z-index: 10;">
        <div class="driver-photo">{{ ride.driver.name[0] }}</div>
        <div class="driver-info" style="flex: 1;">
            <h3>{{ ride.driver.name }}</h3>
            <p>{{ ride.driver.vehicle_number }} • <span style="color: #FFB300;">⭐ {{ ride.driver.rating }}</span></p>
            <p style="font-size: 12px;">{{ ride.driver.total_rides }} trips in the past 1 year</p>
        </div>
        <div style="background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
            ✓
        </div>
    </div>
    
    <!-- Action Buttons -->
    <div class="action-buttons">
        <div class="action-btn" onclick="alert('Calling driver...')">
            <div style="font-size: 20px;">📞</div>
            <div style="font-size: 14px; margin-top: 4px;">Call</div>
        </div>
        <div class="action-btn" onclick="alert('Opening chat...')">
            <div style="font-size: 20px;">💬</div>
            <div style="font-size: 14px; margin-top: 4px;">Chat</div>
        </div>
    </div>
    
    <!-- Trip Info -->
    <div class="card" style="margin-top: 16px;">
        <div class="location-item" style="padding: 8px 0;">
            <div style="color: #00AA13; font-size: 20px;">●</div>
            <div style="flex: 1;">
                <p style="font-size: 12px; color: #666;">PICKUP LOCATION</p>
                <p style="font-weight: 600;">{{ ride.pickup_location }}</p>
            </div>
        </div>
        
        <div style="border-left: 2px dashed #ddd; margin-left: 10px; height: 20px;"></div>
        
        <div class="location-item" style="padding: 8px 0;">
            <div style="color: #ff4444; font-size: 20px;">●</div>
            <div style="flex: 1;">
                <p style="font-size: 12px; color: #666;">DROP-OFF LOCATION</p>
                <p style="font-weight: 600;">{{ ride.dropoff_location }}</p>
            </div>
        </div>
        
        <div class="progress-container">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px; color: #666;">Trip progress</span>
                <span style="font-size: 14px; font-weight: 600;">
                    <span id="elapsedTime">0</span> / {{ ride.estimated_duration }} min
                </span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar" style="width: 0%;"></div>
            </div>
        </div>
    </div>
    
    <!-- Voice Guardian -->
    <div class="card" style="text-align: center;">
        <h3 style="margin-bottom: 16px;">🛡️ GoGuard is Active</h3>
        <p style="color: #666; margin-bottom: 20px;">Tap to speak or use voice command</p>
        
        <div class="voice-indicator" id="voiceIndicator" onclick="toggleVoice()">
            <span style="color: white; font-size: 40px;">🎤</span>
        </div>
        
        <p id="voiceStatus" style="margin-top: 16px; font-size: 14px; color: #666;">
            Click microphone to start
        </p>
        
        <!-- Hidden input for fallback -->
        <input type="text" id="voiceInput" placeholder="Or type here to simulate voice" 
               style="margin-top: 16px; display: none;">
    </div>
    
    <!-- AI Response -->
    <div id="aiResponse" class="card" style="display: none; background: #E3F2FD;">
        <h4 style="margin-bottom: 8px;">🤖 GoGuard AI:</h4>
        <p id="aiMessage"></p>
        <div id="emergencyActions" style="margin-top: 12px;"></div>
    </div>
    
    <!-- Safety Events -->
    <div class="card">
        <h4 style="margin-bottom: 12px;">Safety Log</h4>
        <div id="safetyEvents">
            <p style="color: #666; font-size: 14px;">✓ All systems normal</p>
        </div>
    </div>
</div>

<!-- Emergency FAB -->
<div class="emergency-fab" onclick="showEmergencyOptions()">
    🚨
</div>

<!-- Emergency Bottom Sheet -->
<div id="emergencySheet" class="bottom-sheet">
    <h3 style="margin-bottom: 20px;">Emergency Options</h3>
    <button onclick="triggerEmergency('contact_emergency')" class="btn btn-danger" style="margin-bottom: 12px;">
        📞 Call Emergency (112)
    </button>
    <button onclick="triggerEmergency('share_location')" class="btn" style="margin-bottom: 12px;">
        📍 Share Live Location
    </button>
    <button onclick="triggerEmergency('silent_alarm')" class="btn btn-secondary">
        🔕 Silent Alarm
    </button>
    <button onclick="hideEmergencyOptions()" class="btn btn-outline" style="margin-top: 20px;">
        Cancel
    </button>
</div>

<script>
const rideId = '{{ ride.id }}';
let updateInterval;
let voiceRecognition = null;
let isListening = false;

const SAFETY_LEVEL = {
  NORMAL: 0,
  CONCERN: 1,
  DISTRESS: 2,
};

let currentSafetyLevel = SAFETY_LEVEL.NORMAL;
let isKeywordTriggered = false;

function updateSafetyLevel(newLevelStr) {
  const newLevel = SAFETY_LEVEL[newLevelStr];
  if (newLevel > currentSafetyLevel) {
    currentSafetyLevel = newLevel;
  }
}

// Initialize speech recognition
function initVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        voiceRecognition = new SpeechRecognition();
        voiceRecognition.continuous = true;
        voiceRecognition.interimResults = true;
        voiceRecognition.lang = 'id';
        
        voiceRecognition.onresult = function(event) {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript;
            console.log(transcript)
            
            document.getElementById('voiceStatus').textContent = `"${transcript}"`;
            
            // Check for final result
            if (event.results[last].isFinal) {
                analyzeVoice(transcript);
            }
        };
        
        voiceRecognition.onerror = function(event) {
            console.error('Voice recognition error:', event.error);
            document.getElementById('voiceStatus').textContent = 'Error: ' + event.error;
            
            // Fallback to text input
            document.getElementById('voiceInput').style.display = 'block';
            document.getElementById('voiceStatus').textContent = 'Voice not available. Type instead.';
        };
        
        voiceRecognition.onend = function() {
            isListening = false;
            document.getElementById('voiceIndicator').classList.remove('active');
            if (document.getElementById('voiceStatus').textContent.includes('Listening')) {
                document.getElementById('voiceStatus').textContent = 'Click microphone to start';
            }
        };
    } else {
        // No speech recognition support
        document.getElementById('voiceInput').style.display = 'block';
        document.getElementById('voiceStatus').textContent = 'Voice not supported. Type instead.';
    }
}

function toggleVoice() {
    if (voiceRecognition) {
        if (isListening) {
            voiceRecognition.stop();
            isListening = false;
            document.getElementById('voiceIndicator').classList.remove('active');
            document.getElementById('voiceStatus').textContent = 'Click microphone to start';
        } else {
            voiceRecognition.start();
            isListening = true;
            document.getElementById('voiceIndicator').classList.add('active');
            document.getElementById('voiceStatus').textContent = '🎤 Listening...';
        }
    } else {
        // Use text input as fallback
        const input = document.getElementById('voiceInput');
        if (input.style.display === 'none') {
            input.style.display = 'block';
            input.focus();
        }
    }
}

// Fallback for text input
document.getElementById('voiceInput')?.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        analyzeVoice(this.value);
        this.value = '';
    }
});

function analyzeVoice(text) {
    fetch('/api/voice-check', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            ride_id: rideId,
            text: text
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('aiMessage').textContent = data.ai_response;
        document.getElementById('aiResponse').style.display = 'block';
        
        updateSafetyLevel(data.distress_level)
        
        if (
            currentSafetyLevel === SAFETY_LEVEL.DISTRESS &&
            data.is_safe_triggered
        ) {
            isKeywordTriggered = true;
            alert("Safety keyword activated. Your ride details is flagged and sent to GoTo team and your personal contact!");
        }
        
        if (isKeywordTriggered) {
            document.getElementById('aiMessage').textContent = "";
            document.getElementById('aiResponse').style.backgroundColor = '#ffe5e5';
            document.getElementById('emergencyActions').innerHTML = `<p class="emergency-text">🚨 Emergency response triggered. GoTo team has been notified.</p>`;
        } else {
            if (data.actions && data.actions.length > 0) {
                const actionsHtml = data.actions.map(action => {
                    const actionLabels = {
                        'contact_emergency': '📞 Emergency',
                        'share_location': '📍 Share Location',
                        'silent_alarm': '🔕 Silent Alarm',
                        'call_support': '☎️ Support'
                    };
                    return `<button onclick="triggerEmergency('${action}')" class="btn btn-danger" style="margin-right: 8px;">
                        ${actionLabels[action] || action}
                    </button>`;
                }).join('');
                
                document.getElementById('emergencyActions').innerHTML = actionsHtml;
            } else {
                document.getElementById('emergencyActions').innerHTML = '';
            }
        }
        
        updateRideStatus();
    });
}

function updateRideStatus() {
    fetch(`/api/ride-status/${rideId}`)
        .then(res => res.json())
        .then(data => {
            // Update progress
            document.getElementById('progressBar').style.width = data.progress + '%';
            document.getElementById('elapsedTime').textContent = Math.round(data.elapsed_minutes);
            
            // Update safety events
            if (data.safety_events.length > 0) {
                const eventsHtml = data.safety_events.map(event => {
                    const eventClass = event.level === 'DISTRESS' ? 'distress' : '';
                    const time = new Date(event.timestamp).toLocaleTimeString();
                    return `
                        <div class="safety-event ${eventClass}">
                            <strong>${event.type}</strong> - ${time}
                            <p style="font-size: 14px; margin-top: 4px;">${event.details || ''}</p>
                        </div>
                    `;
                }).join('');
                document.getElementById('safetyEvents').innerHTML = eventsHtml;
            }
            
            // Check if ride completed
            if (data.progress >= 100) {
                clearInterval(updateInterval);
                setTimeout(() => {
                    fetch(`/api/end-ride/${rideId}`, {method: 'POST'})
                        .then(res => res.json())
                        .then(data => {
                            if (data.status === 'COMPLETED') {
                                window.location.href = `/safety-report/${rideId}`;
                            }
                        });
                }, 2000);
            }
        });
}

function showEmergencyOptions() {
    document.getElementById('emergencySheet').classList.add('active');
}

function hideEmergencyOptions() {
    document.getElementById('emergencySheet').classList.remove('active');
}

function triggerEmergency(action) {
    fetch('/api/emergency-action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            ride_id: rideId,
            action: action
        })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message);
        hideEmergencyOptions();
        updateRideStatus();
    });
}

// Initialize
initVoiceRecognition();
updateInterval = setInterval(updateRideStatus, 3000);
updateRideStatus();

// Periodic AI check-ins
setInterval(() => {
    if (Math.random() < 0.1) {
        document.getElementById('aiResponse').style.display = 'block';
        document.getElementById('aiMessage').textContent = 
            "Hi! Just checking in. Everything going well with your ride?";
    }
}, 45000);
</script>
{% endblock %}'''
    
    # Create safety_report.html
    safety_report_html = '''{% extends "base.html" %}
{% block title %}Safety Report{% endblock %}
{% block content %}
<div class="container">
    <div class="card" style="text-align: center; background: #E8F5E9;">
        <div style="font-size: 60px; margin-bottom: 16px;">✅</div>
        <h2 style="color: #2E7D32; margin-bottom: 8px;">Ride Completed Safely</h2>
        <p style="color: #558B2F;">Thank you for using GoGuard!</p>
    </div>

    <div class="card">
        <h3 style="margin-bottom: 20px;">📊 AI Safety Analysis</h3>
        
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="font-size: 48px; color: #00AA13; font-weight: bold;">
                {{ (report.overall_safety_score * 100)|int }}%
            </div>
            <p style="color: #666;">Overall Safety Score</p>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="text-align: center; padding: 16px; background: #f5f5f5; border-radius: 8px;">
                <h4 style="font-size: 24px; color: #333;">{{ report.duration }}</h4>
                <p style="color: #666; font-size: 14px;">Duration</p>
            </div>
            
            <div style="text-align: center; padding: 16px; background: #f5f5f5; border-radius: 8px;">
                <h4 style="font-size: 24px; color: #333;">{{ report.incidents }}</h4>
                <p style="color: #666; font-size: 14px;">Safety Events</p>
            </div>
            
            <div style="text-align: center; padding: 16px; background: #f5f5f5; border-radius: 8px;">
                <h4 style="font-size: 24px; color: #333;">{{ report.route_compliance }}</h4>
                <p style="color: #666; font-size: 14px;">Route Compliance</p>
            </div>
            
            <div style="text-align: center; padding: 16px; background: #f5f5f5; border-radius: 8px;">
                <h4 style="font-size: 24px; color: #333;">{{ report.ai_interventions }}</h4>
                <p style="color: #666; font-size: 14px;">AI Check-ins</p>
            </div>
            

        </div>
    </div>

    <div class="card">
        <h4 style="margin-bottom: 16px;">🎯 AI Recommendations</h4>
        {% for rec in report.recommendations %}
        <div style="padding: 12px; background: #E3F2FD; border-radius: 8px; margin-bottom: 8px;">
            <p style="color: #1976D2;">• {{ rec }}</p>
        </div>
        {% endfor %}
    </div>
    
    <div class="card">
        <h4 style="margin-bottom: 16px;">🎯 AI Summarization</h4>
        <div style="padding: 12px; background: #E3F2FD; border-radius: 8px; margin-bottom: 8px;">
            <p style="color: #1976D2;">• {{ report.qwen_response }}</p>
        </div>
    </div>

    <div class="card" style="background: #F5F5F5;">
        <h4 style="margin-bottom: 12px;">🔐 Data Security</h4>
        <p style="color: #666; font-size: 14px; line-height: 1.6;">
            All ride data has been encrypted and securely stored. Voice recordings and location data 
            are automatically deleted after 7 days unless saved.
        </p>
        
        <div style="margin-top: 16px;">
            <button id="downloadBtn" data-ride-id="{{ report.ride_id }}" class="btn btn-secondary" style="font-size: 14px; padding: 10px 16px;">
                Download Report
            </button>
        </div>
    </div>

    <div style="padding: 0 20px 20px;">
        <a href="/" class="btn">
            Book Another Safe Ride
        </a>
    </div>
</div>

<script>
const rideId = "{{ report.ride_id }}";

document.getElementById("downloadBtn").addEventListener("click", () => {
    const link = document.createElement("a");
    link.href = `/download-report/${rideId}`;
    link.download = `ride_report_${rideId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
});
</script>
{% endblock %}'''
    
    # Save all templates
    with open('templates/base.html', 'w', encoding='utf-8') as f:
        f.write(base_html)
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    with open('templates/book_ride.html', 'w', encoding='utf-8') as f:
        f.write(book_ride_html)
    
    with open('templates/ride_monitor.html', 'w', encoding='utf-8') as f:
        f.write(ride_monitor_html)
    
    with open('templates/safety_report.html', 'w', encoding='utf-8') as f:
        f.write(safety_report_html)
    
    print("🚀 GoGuard Enhanced Mockup Ready!")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("\n✨ NEW FEATURES:")
    print("- 🎤 Voice recognition with Web Speech API")
    print("- 📱 Gojek-style mobile UI")
    print("- 🤖 Qwen AI integration for intelligent responses")
    print("- 🚨 Emergency FAB and bottom sheet")
    print("- 🗺️ Map visualization")
    print("- 📊 Enhanced safety analytics")
    print("\n📝 DEMO INSTRUCTIONS:")
    print("1. Click microphone and say: 'I feel uncomfortable'")
    print("2. Or type in the input field if voice isn't supported")
    print("3. Try emergency button (red circle) for quick actions")
    print("4. Watch AI responses adapt to context")
    print("\nPress Ctrl+C to stop the server")
    
    #app.run(debug=True, port=5000)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
