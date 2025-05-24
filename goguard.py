"""
GoGuard - AI Guardian Angel for Safe Rides
Enhanced Hackathon Mockup with Voice Support and Gojek-like UI
"""

from flask import Flask, render_template, request, jsonify, session
import json
import random
from datetime import datetime, timedelta
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import os
import base64
import hashlib

# Import Qwen AI integration
try:
    from qwen_ai import QwenSafetyAI
    ai_assistant = QwenSafetyAI()
except:
    print("Qwen AI module not found. Using fallback AI simulation.")
    ai_assistant = None

app = Flask(__name__)
app.secret_key = 'goguard-secret-key-hackathon-2024'

# Mock Data Classes
@dataclass
class Driver:
    id: str
    name: str
    photo: str
    rating: float
    total_rides: int
    safety_score: float
    vehicle_number: str
    vehicle_type: str

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
active_rides = {}

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

def analyze_voice_sentiment(text: str, context: Dict = None) -> Dict:
    """Analyze voice sentiment using Qwen AI or fallback"""
    if ai_assistant:
        return ai_assistant.analyze_voice_distress(text, context or {})
    
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
        "safe_route_available": risk_analysis.get('risk_level', 'LOW') != 'LOW'
    })

@app.route('/api/start-ride', methods=['POST'])
def start_ride():
    """Start a ride and initialize GoGuard monitoring"""
    data = request.json
    ride_id = f"RIDE_{int(time.time())}"
    
    driver = MOCK_DRIVERS[0]  # Use Yadi Riyadi for demo
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
    elapsed = (datetime.now() - ride.start_time).seconds / 60
    
    context = {
        "location": "En route",
        "duration": round(elapsed)
    }
    
    sentiment = analyze_voice_sentiment(voice_text, context)
    
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
    report = generate_safety_report(ride)
    
    del active_rides[ride_id]
    session.pop('current_ride', None)
    
    return jsonify({
        "status": "COMPLETED",
        "safety_report": report
    })

@app.route('/safety-report/<ride_id>')
def safety_report(ride_id):
    """Display post-ride safety report"""
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

def generate_safety_report(ride):
    """Generate post-ride safety report"""
    if ai_assistant:
        ride_data = {
            "duration": f"{(datetime.now() - ride.start_time).seconds // 60} minutes",
            "route_type": ride.route_type,
            "events": ride.safety_events,
            "driver_behavior": "Normal"
        }
        return ai_assistant.summarize_ride_safety(ride_data)
    
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
    
    # Create base template with enhanced styling
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

<script>
let currentRiskData = null;

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
        currentRiskData = data;
        showSafetyModal(data);
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
<div class="map-container">
    <img src="https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/pin-s+00AA13({{ ride.pickup_coords[1] }},{{ ride.pickup_coords[0] }}),pin-s+ff4444({{ ride.dropoff_coords[1] }},{{ ride.dropoff_coords[0] }})/{{ ride.pickup_coords[1] }},{{ ride.pickup_coords[0] }},12,0/400x300?access_token=pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjazlwYzlhMDEwMDEzM2xwY2E3MzY5NTY5In0.0aS1iUm0n0a0a0a0a0a0aA" 
         style="width: 100%; height: 100%; object-fit: cover;">
    <div style="position: absolute; top: 10px; left: 10px; background: white; padding: 8px 12px; border-radius: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <span class="status-pill">● On the way with you</span>
    </div>
</div>

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

// Initialize speech recognition
function initVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        voiceRecognition = new SpeechRecognition();
        voiceRecognition.continuous = true;
        voiceRecognition.interimResults = true;
        voiceRecognition.lang = 'en-US';
        
        voiceRecognition.onresult = function(event) {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript;
            
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

    <div class="card" style="background: #F5F5F5;">
        <h4 style="margin-bottom: 12px;">🔐 Data Security</h4>
        <p style="color: #666; font-size: 14px; line-height: 1.6;">
            All ride data has been encrypted and securely stored. Voice recordings and location data 
            are automatically deleted after 7 days unless saved.
        </p>
        
        <div style="margin-top: 16px;">
            <button class="btn btn-secondary" style="font-size: 14px; padding: 10px 16px;">
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
    
    app.run(debug=True, port=5000)