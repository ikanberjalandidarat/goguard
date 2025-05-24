"""
GoGuard - AI Guardian Angel for Safe Rides
A Hackathon Mockup Application
"""

from flask import Flask, render_template, request, jsonify, session
import json
import random
from datetime import datetime, timedelta
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import base64
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'goguard-secret-key-hackathon-2025'

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
    start_time: Optional[datetime] = None
    safety_events: List[Dict] = None

# Mock Database
MOCK_DRIVERS = [
    Driver("D001", "Ahmad Rizki", "driver1.jpg", 4.8, 1523, 0.92, "B 1234 ABC", "Honda Vario"),
    Driver("D002", "Budi Santoso", "driver2.jpg", 4.5, 892, 0.85, "B 5678 DEF", "Yamaha NMAX"),
    Driver("D003", "Cahyo Prakoso", "driver3.jpg", 4.2, 234, 0.75, "B 9012 GHI", "Honda Beat"),
]

MOCK_LOCATIONS = {
    "home": {"name": "Home - Apartment Sudirman Park", "coords": (-6.2088, 106.8456), "safety_score": 0.9},
    "office": {"name": "GoTower - Pasaraya", "coords": (-6.2433, 106.7987), "safety_score": 0.95},
    "mall": {"name": "Grand Indonesia Mall", "coords": (-6.1951, 106.8218), "safety_score": 0.88},
    "friend": {"name": "Sarah's Place - Kemang", "coords": (-6.2633, 106.8133), "safety_score": 0.82},
    "restaurant": {"name": "Sate Khas Senayan", "coords": (-6.2275, 106.8007), "safety_score": 0.87},
}

# In-memory storage for active rides
active_rides = {}

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
        
        # Add some standard keys for compatibility with your existing code
        # Map some locations to your original keys
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

# AI Safety Analysis Functions
def calculate_ride_risk_score(driver: Driver, pickup: str, dropoff: str, time_of_day: int) -> Dict:
    """Calculate risk score based on driver, location, and time"""
    base_score = driver.safety_score
    
    # Time factor (late night = higher risk)
    time_factor = 1.0
    if time_of_day >= 22 or time_of_day <= 5:
        time_factor = 0.8
    elif time_of_day >= 19:
        time_factor = 0.9
    
    # Location factor
    pickup_safety = MOCK_LOCATIONS.get(pickup, {}).get("safety_score", 0.8)
    dropoff_safety = MOCK_LOCATIONS.get(dropoff, {}).get("safety_score", 0.8)
    location_factor = (pickup_safety + dropoff_safety) / 2
    
    # Driver experience factor
    experience_factor = min(1.0, driver.total_rides / 1000)
    
    final_score = (base_score * 0.4 + location_factor * 0.3 + 
                   time_factor * 0.2 + experience_factor * 0.1)
    
    risk_level = "LOW"
    if final_score < 0.7:
        risk_level = "HIGH"
    elif final_score < 0.85:
        risk_level = "MEDIUM"
    
    return {
        "score": round(final_score, 2),
        "level": risk_level,
        "factors": {
            "driver": round(base_score, 2),
            "location": round(location_factor, 2),
            "time": round(time_factor, 2),
            "experience": round(experience_factor, 2)
        }
    }

def analyze_voice_sentiment(text: str) -> Dict:
    """Mock voice sentiment analysis"""
    distress_keywords = ["help", "stop", "wrong", "scared", "please", "no", "hurt"]
    concern_keywords = ["uncomfortable", "weird", "strange", "lost", "where"]
    
    text_lower = text.lower()
    
    distress_count = sum(1 for word in distress_keywords if word in text_lower)
    concern_count = sum(1 for word in concern_keywords if word in text_lower)
    
    if distress_count >= 2:
        return {"level": "DISTRESS", "confidence": 0.9}
    elif distress_count >= 1 or concern_count >= 2:
        return {"level": "CONCERN", "confidence": 0.7}
    else:
        return {"level": "NORMAL", "confidence": 0.8}

def check_route_deviation(ride_id: str) -> Dict:
    """Mock route deviation check"""
    # Simulate random route events
    if random.random() < 0.1:
        return {
            "deviation": True,
            "type": "ROUTE_CHANGE",
            "severity": "MEDIUM",
            "description": "Driver took alternative route - 2km longer"
        }
    return {"deviation": False}

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
    """API endpoint for risk calculation"""
    data = request.json
    driver = random.choice(MOCK_DRIVERS)
    
    risk_analysis = calculate_ride_risk_score(
        driver,
        data['pickup'],
        data['dropoff'],
        datetime.now().hour
    )
    
    return jsonify({
        "driver": {
            "name": driver.name,
            "rating": driver.rating,
            "rides": driver.total_rides,
            "vehicle": driver.vehicle_number
        },
        "risk_analysis": risk_analysis,
        "safe_route_available": risk_analysis['level'] != 'LOW'
    })

@app.route('/api/start-ride', methods=['POST'])
def start_ride():
    """Start a ride and initialize GoGuard monitoring"""
    data = request.json
    ride_id = f"RIDE_{int(time.time())}"
    
    driver = random.choice(MOCK_DRIVERS)
    ride = Ride(
        id=ride_id,
        driver=driver,
        pickup_location=MOCK_LOCATIONS[data['pickup']]['name'],
        dropoff_location=MOCK_LOCATIONS[data['dropoff']]['name'],
        pickup_coords=MOCK_LOCATIONS[data['pickup']]['coords'],
        dropoff_coords=MOCK_LOCATIONS[data['dropoff']]['coords'],
        estimated_duration=random.randint(15, 45),
        route_type=data.get('route_type', 'standard'),
        status='ACTIVE',
        start_time=datetime.now(),
        safety_events=[]
    )
    
    active_rides[ride_id] = ride
    session['current_ride'] = ride_id
    
    # Start monitoring thread (in real app, this would be more sophisticated)
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
    
    # Simulate ride progress
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
    
    sentiment = analyze_voice_sentiment(voice_text)
    
    if sentiment['level'] in ['DISTRESS', 'CONCERN']:
        # Log safety event
        active_rides[ride_id].safety_events.append({
            "timestamp": datetime.now().isoformat(),
            "type": "VOICE_ALERT",
            "level": sentiment['level'],
            "details": f"Voice analysis detected {sentiment['level']}"
        })
        
        # Generate AI response
        if sentiment['level'] == 'DISTRESS':
            ai_response = "I've detected you might be in distress. Would you like me to contact emergency services or your trusted contacts?"
            actions = ["contact_emergency", "share_location", "silent_alarm"]
        else:
            ai_response = "Hi! Just checking in. Is everything okay with your ride?"
            actions = ["share_location", "call_support"]
    else:
        ai_response = "Your ride is progressing smoothly. I'm here if you need anything!"
        actions = []
    
    return jsonify({
        "sentiment": sentiment,
        "ai_response": ai_response,
        "suggested_actions": actions
    })

@app.route('/api/emergency-action', methods=['POST'])
def emergency_action():
    """Handle emergency actions"""
    data = request.json
    ride_id = data.get('ride_id')
    action = data.get('action')
    
    if ride_id not in active_rides:
        return jsonify({"error": "Ride not found"}), 404
    
    ride = active_rides[ride_id]
    
    # Log emergency action
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
    report = generate_safety_report(ride)
    
    # Clean up
    del active_rides[ride_id]
    session.pop('current_ride', None)
    
    return jsonify({
        "status": "COMPLETED",
        "safety_report": report
    })

@app.route('/safety-report/<ride_id>')
def safety_report(ride_id):
    """Display post-ride safety report"""
    # In a real app, this would fetch from database
    mock_report = {
        "ride_id": ride_id,
        "overall_safety_score": 0.92,
        "duration": "23 minutes",
        "route_compliance": "98%",
        "driver_behavior": "Excellent",
        "incidents": 0,
        "ai_interventions": 1,
        "recommendations": [
            "Consider using Safe Route mode for late-night rides",
            "Your trusted contacts were successfully notified"
        ]
    }
    
    return render_template('safety_report.html', report=mock_report)

# Helper Functions
def monitor_ride(ride_id):
    """Background thread to monitor ride (mock implementation)"""
    while ride_id in active_rides and active_rides[ride_id].status == 'ACTIVE':
        time.sleep(10)  # Check every 10 seconds
        
        # Random safety checks
        if random.random() < 0.05:  # 5% chance of route deviation
            deviation = check_route_deviation(ride_id)
            if deviation['deviation']:
                active_rides[ride_id].safety_events.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "ROUTE_DEVIATION",
                    "details": deviation['description']
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

def generate_safety_report(ride):
    """Generate post-ride safety report"""
    incident_count = len([e for e in ride.safety_events if e['type'] != 'VOICE_CHECK'])
    f
    safety_score = 1.0
    if incident_count > 0:
        safety_score -= (incident_count * 0.1)
    
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
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    
    # Load the data
    MOCK_DRIVERS, MOCK_LOCATIONS, location_mapping = load_csv_data()
    
    # Create base template
    base_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoGuard - {% block title %}{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #00AA13; color: white; padding: 20px 0; margin-bottom: 30px; }
        .header h1 { text-align: center; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .btn { display: inline-block; padding: 12px 24px; background: #00AA13; color: white; text-decoration: none; border-radius: 8px; border: none; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #008810; }
        .btn-secondary { background: #666; }
        .btn-danger { background: #ff4444; }
        .risk-score { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; }
        .risk-low { background: #4CAF50; color: white; }
        .risk-medium { background: #FF9800; color: white; }
        .risk-high { background: #f44336; color: white; }
        .safety-event { padding: 12px; margin: 8px 0; border-left: 4px solid #FF9800; background: #FFF3E0; }
        .safety-event.distress { border-left-color: #f44336; background: #FFEBEE; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .progress-bar { width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: #00AA13; transition: width 0.3s; }
        .voice-input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; }
        .emergency-panel { background: #FFF3E0; border: 2px solid #FF9800; border-radius: 8px; padding: 20px; margin-top: 20px; }
        .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-active { background: #4CAF50; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    {% block extra_style %}{% endblock %}
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🛡️ GoGuard - AI Guardian Angel</h1>
        </div>
    </div>
    <div class="container">
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
<div class="card">
    <h2>Welcome to GoGuard 🛡️</h2>
    <p style="font-size: 18px; margin: 20px 0; line-height: 1.6;">
        Your AI-powered safety companion for Gojek rides. GoGuard uses advanced AI to monitor your rides in real-time, 
        ensuring you get home safely every time.
    </p>
    
    <div class="grid" style="margin: 30px 0;">
        <div class="card" style="background: #E8F5E9;">
            <h3>🤖 AI-Powered Monitoring</h3>
            <p>Real-time voice and behavior analysis to detect potential safety concerns</p>
        </div>
        <div class="card" style="background: #E3F2FD;">
            <h3>🗺️ Smart Route Planning</h3>
            <p>Choose safer routes with better lighting and surveillance</p>
        </div>
        <div class="card" style="background: #FFF3E0;">
            <h3>🚨 Instant Emergency Response</h3>
            <p>One-touch emergency alerts and automatic location sharing</p>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 40px;">
        <a href="/book-ride" class="btn" style="font-size: 20px; padding: 16px 32px;">
            Start Safe Ride Demo →
        </a>
    </div>
</div>

<div class="card">
    <h3>How It Works</h3>
    <ol style="line-height: 2;">
        <li><strong>Pre-Ride Safety Check:</strong> AI analyzes driver profile, route, and timing to calculate risk score</li>
        <li><strong>Real-Time Guardian:</strong> Voice AI monitors conversations and detects distress signals</li>
        <li><strong>Smart Interventions:</strong> Contextual check-ins and emergency options when needed</li>
        <li><strong>Post-Ride Report:</strong> Encrypted safety logs and insights for continuous improvement</li>
    </ol>
</div>
{% endblock %}'''
    
    # Create book_ride.html
    book_ride_html = '''{% extends "base.html" %}
{% block title %}Book Safe Ride{% endblock %}
{% block content %}
<div class="card">
    <h2>Book Your Safe Ride</h2>
    
    <div class="grid">
        <div>
            <label style="display: block; margin-bottom: 8px; font-weight: bold;">Pickup Location</label>
            <select id="pickup" class="voice-input" style="width: 100%;">
                {% for key, loc in locations.items() %}
                <option value="{{ key }}">{{ loc.name }}</option>
                {% endfor %}
            </select>
        </div>
        
        <div>
            <label style="display: block; margin-bottom: 8px; font-weight: bold;">Dropoff Location</label>
            <select id="dropoff" class="voice-input" style="width: 100%;">
                {% for key, loc in locations.items() %}
                <option value="{{ key }}">{{ loc.name }}</option>
                {% endfor %}
            </select>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <button onclick="calculateRisk()" class="btn">Calculate Safety Score</button>
    </div>
</div>

<div id="riskAnalysis" style="display: none;">
    <div class="card">
        <h3>AI Safety Analysis</h3>
        <div id="riskContent"></div>
    </div>
</div>

<div id="rideOptions" style="display: none;">
    <div class="card">
        <h3>Choose Your Ride Mode</h3>
        <div class="grid">
            <div class="card" style="border: 2px solid #00AA13; cursor: pointer;" onclick="startRide('standard')">
                <h4>Standard Route</h4>
                <p>Fastest route to destination</p>
                <p style="color: #666; margin-top: 8px;">ETA: <span id="etaStandard">15 mins</span></p>
            </div>
            <div class="card" style="border: 2px solid #2196F3; cursor: pointer;" onclick="startRide('safe')">
                <h4>🛡️ Safe Route Mode</h4>
                <p>Well-lit streets with higher surveillance</p>
                <p style="color: #666; margin-top: 8px;">ETA: <span id="etaSafe">18 mins</span></p>
                <p style="color: #2196F3; font-weight: bold;">+3 mins for extra safety</p>
            </div>
        </div>
    </div>
</div>

<script>
function calculateRisk() {
    const pickup = document.getElementById('pickup').value;
    const dropoff = document.getElementById('dropoff').value;
    
    fetch('/api/calculate-risk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pickup, dropoff})
    })
    .then(res => res.json())
    .then(data => {
        displayRiskAnalysis(data);
    });
}

function displayRiskAnalysis(data) {
    const riskClass = data.risk_analysis.level.toLowerCase();
    const riskHtml = `
        <div style="text-align: center; margin-bottom: 20px;">
            <h2>Safety Score: ${data.risk_analysis.score}</h2>
            <span class="risk-score risk-${riskClass}">${data.risk_analysis.level} RISK</span>
        </div>
        
        <div class="grid">
            <div>
                <h4>Driver Profile</h4>
                <p><strong>${data.driver.name}</strong></p>
                <p>Rating: ⭐ ${data.driver.rating}</p>
                <p>Completed Rides: ${data.driver.rides}</p>
                <p>Vehicle: ${data.driver.vehicle}</p>
            </div>
            
            <div>
                <h4>Safety Factors</h4>
                <p>Driver Score: ${data.risk_analysis.factors.driver}</p>
                <p>Location Safety: ${data.risk_analysis.factors.location}</p>
                <p>Time Factor: ${data.risk_analysis.factors.time}</p>
                <p>Experience: ${data.risk_analysis.factors.experience}</p>
            </div>
        </div>
        
        ${data.risk_analysis.level !== 'LOW' ? `
        <div class="emergency-panel">
            <strong>⚠️ GoGuard Recommendation:</strong> Consider using Safe Route Mode for this ride.
            Additional safety features will be activated.
        </div>
        ` : ''}
    `;
    
    document.getElementById('riskContent').innerHTML = riskHtml;
    document.getElementById('riskAnalysis').style.display = 'block';
    document.getElementById('rideOptions').style.display = 'block';
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
</script>
{% endblock %}'''
    
    # Create ride_monitor.html
    ride_monitor_html = '''{% extends "base.html" %}
{% block title %}Ride Monitor{% endblock %}
{% block content %}
<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>GoGuard Active <span class="status-indicator status-active"></span></h2>
        <button onclick="endRide()" class="btn btn-secondary">End Ride</button>
    </div>
    
    <div class="grid" style="margin-top: 20px;">
        <div>
            <p><strong>From:</strong> {{ ride.pickup_location }}</p>
            <p><strong>To:</strong> {{ ride.dropoff_location }}</p>
        </div>
        <div>
            <p><strong>Driver:</strong> {{ ride.driver.name }}</p>
            <p><strong>Vehicle:</strong> {{ ride.driver.vehicle_number }}</p>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <p><strong>Ride Progress</strong></p>
        <div class="progress-bar">
            <div class="progress-fill" id="progressBar" style="width: 0%;"></div>
        </div>
        <p style="text-align: center; margin-top: 8px;">
            <span id="elapsedTime">0</span> / {{ ride.estimated_duration }} minutes
        </p>
    </div>
</div>

<div class="card">
    <h3>🎤 Voice Guardian</h3>
    <p>I'm listening for your safety. Just speak naturally if you need help.</p>
    
    <div style="margin-top: 16px;">
        <input type="text" id="voiceInput" class="voice-input" 
               placeholder="Simulate voice input: Try saying 'I feel uncomfortable' or 'Help'">
        <button onclick="checkVoice()" class="btn" style="margin-top: 8px;">Analyze Voice</button>
    </div>
    
    <div id="aiResponse" style="margin-top: 16px; display: none;">
        <div class="card" style="background: #E3F2FD;">
            <h4>🤖 GoGuard AI:</h4>
            <p id="aiMessage"></p>
            <div id="emergencyActions" style="margin-top: 12px;"></div>
        </div>
    </div>
</div>

<div class="card">
    <h3>Safety Events Log</h3>
    <div id="safetyEvents">
        <p style="color: #666;">No events detected - Your ride is progressing safely</p>
    </div>
</div>

<div class="emergency-panel" style="display: none;" id="emergencyPanel">
    <h3>🚨 Emergency Options</h3>
    <div class="grid">
        <button onclick="triggerEmergency('contact_emergency')" class="btn btn-danger">
            Call Emergency
        </button>
        <button onclick="triggerEmergency('share_location')" class="btn btn-danger">
            Share Location
        </button>
        <button onclick="triggerEmergency('silent_alarm')" class="btn btn-danger">
            Silent Alarm
        </button>
    </div>
</div>

<script>
const rideId = '{{ ride.id }}';
let updateInterval;

function updateRideStatus() {
    fetch(`/api/ride-status/${rideId}`)
        .then(res => res.json())
        .then(data => {
            // Update progress bar
            document.getElementById('progressBar').style.width = data.progress + '%';
            document.getElementById('elapsedTime').textContent = Math.round(data.elapsed_minutes);
            
            // Update safety events
            if (data.safety_events.length > 0) {
                const eventsHtml = data.safety_events.map(event => {
                    const eventClass = event.level === 'DISTRESS' ? 'distress' : '';
                    return `
                        <div class="safety-event ${eventClass}">
                            <strong>${event.type}</strong> - ${new Date(event.timestamp).toLocaleTimeString()}
                            <p>${event.details || ''}</p>
                        </div>
                    `;
                }).join('');
                document.getElementById('safetyEvents').innerHTML = eventsHtml;
            }
            
            // Check if ride completed
            if (data.progress >= 100) {
                clearInterval(updateInterval);
                setTimeout(() => endRide(), 2000);
            }
        });
}

function checkVoice() {
    const voiceText = document.getElementById('voiceInput').value;
    
    fetch('/api/voice-check', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            ride_id: rideId,
            text: voiceText
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('aiMessage').textContent = data.ai_response;
        document.getElementById('aiResponse').style.display = 'block';
        
        if (data.suggested_actions.length > 0) {
            const actionsHtml = data.suggested_actions.map(action => {
                const actionLabels = {
                    'contact_emergency': '📞 Contact Emergency',
                    'share_location': '📍 Share Location',
                    'silent_alarm': '🔕 Silent Alarm',
                    'call_support': '☎️ Call Support'
                };
                return `<button onclick="triggerEmergency('${action}')" class="btn btn-danger" style="margin-right: 8px;">
                    ${actionLabels[action] || action}
                </button>`;
            }).join('');
            
            document.getElementById('emergencyActions').innerHTML = actionsHtml;
            document.getElementById('emergencyPanel').style.display = 'block';
        }
        
        // Clear input
        document.getElementById('voiceInput').value = '';
    });
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
        updateRideStatus();
    });
}

function endRide() {
    fetch(`/api/end-ride/${rideId}`, {method: 'POST'})
        .then(res => res.json())
        .then(data => {
            if (data.status === 'COMPLETED') {
                window.location.href = `/safety-report/${rideId}`;
            }
        });
}

// Start monitoring
updateInterval = setInterval(updateRideStatus, 3000);
updateRideStatus();

// Simulate automatic voice checks
setInterval(() => {
    if (Math.random() < 0.1) {  // 10% chance
        document.getElementById('aiResponse').style.display = 'block';
        document.getElementById('aiMessage').textContent = 
            "Hi! Just checking in. Everything going well with your ride?";
    }
}, 30000);  // Every 30 seconds
</script>
{% endblock %}'''
    
    # Create safety_report.html
    safety_report_html = '''{% extends "base.html" %}
{% block title %}Safety Report{% endblock %}
{% block content %}
<div class="card" style="text-align: center;">
    <h1>✅ Ride Completed Safely</h1>
    <p style="font-size: 20px; margin-top: 20px;">Thank you for using GoGuard!</p>
</div>

<div class="card">
    <h2>📊 Safety Report</h2>
    
    <div style="text-align: center; margin: 30px 0;">
        <h3>Overall Safety Score</h3>
        <div style="font-size: 48px; color: #4CAF50;">{{ report.overall_safety_score * 100 }}%</div>
    </div>
    
    <div class="grid">
        <div class="card" style="background: #E8F5E9;">
            <h4>Ride Duration</h4>
            <p style="font-size: 24px;">{{ report.duration }}</p>
        </div>
        
        <div class="card" style="background: #E3F2FD;">
            <h4>Route Compliance</h4>
            <p style="font-size: 24px;">{{ report.route_compliance }}</p>
        </div>
        
        <div class="card" style="background: #FFF3E0;">
            <h4>Safety Incidents</h4>
            <p style="font-size: 24px;">{{ report.incidents }}</p>
        </div>
        
        <div class="card" style="background: #F3E5F5;">
            <h4>AI Interventions</h4>
            <p style="font-size: 24px;">{{ report.ai_interventions }}</p>
        </div>
    </div>
</div>

<div class="card">
    <h3>🎯 Recommendations</h3>
    <ul style="line-height: 2;">
        {% for rec in report.recommendations %}
        <li>{{ rec }}</li>
        {% endfor %}
    </ul>
</div>

<div class="card">
    <h3>🔐 Security Notice</h3>
    <p>All ride data has been encrypted and securely stored on Alibaba Cloud. 
    Voice recordings and location data are automatically deleted after 7 days unless you choose to save them.</p>
    
    <div style="margin-top: 20px;">
        <button class="btn">Download Full Report</button>
        <button class="btn btn-secondary">Report Issue</button>
    </div>
</div>

<div style="text-align: center; margin-top: 40px;">
    <a href="/" class="btn" style="font-size: 18px;">Book Another Safe Ride</a>
</div>
{% endblock %}'''
    
    # Save all templates
    with open('templates/base.html', 'w') as f:
        f.write(base_html)
    
    with open('templates/index.html', 'w') as f:
        f.write(index_html)
    
    with open('templates/book_ride.html', 'w') as f:
        f.write(book_ride_html)
    
    with open('templates/ride_monitor.html', 'w') as f:
        f.write(ride_monitor_html)
    
    with open('templates/safety_report.html', 'w') as f:
        f.write(safety_report_html)
    
    print("GoGuard Mockup Application Ready!")
    print("Starting server on http://localhost:5000")
    print("\nFeatures Demonstrated:")
    print("- Pre-ride AI risk assessment")
    print("- Real-time ride monitoring dashboard")
    print("- Voice sentiment analysis simulation")
    print("- Emergency action triggers")
    print("- Post-ride safety reports")
    print("\nPress Ctrl+C to stop the server")
    
    app.run(debug=True, port=5000)