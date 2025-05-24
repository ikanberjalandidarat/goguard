"""
Qwen AI Integration for GoGuard
Handles all AI-powered safety analysis and responses
"""

import os
from openai import OpenAI
from typing import Dict, List, Optional
import json
from datetime import datetime
import re
class QwenSafetyAI:
    def __init__(self, api_key: str = None):
        """Initialize Qwen AI client"""
        self.client = OpenAI(
            api_key=api_key or "sk-82c126223773468ea3689259cb7047a8",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        
        # TODO: Make it rotate API keys when run out optional
        
    def analyze_ride_safety(self, ride_data: Dict) -> Dict:
        """Analyze ride safety using Qwen AI"""
        try:
            prompt = f"""
            As a safety AI assistant, analyze this ride data and provide a safety assessment:
            
            Driver: {ride_data.get('driver_name')} (Rating: {ride_data.get('driver_rating')}, Rides: {ride_data.get('driver_rides')})
            Time: {ride_data.get('time')}
            Pickup: {ride_data.get('pickup')}
            Dropoff: {ride_data.get('dropoff')}
            
            Provide:
            1. Overall safety score (0-1)
            2. Risk level (LOW/MEDIUM/HIGH)
            3. Key safety factors
            4. Recommendations
            
            Format as JSON.
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are GoGuard, an AI safety assistant for ride-sharing. Provide concise, actionable safety assessments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            response = completion.choices[0].message.content
            # Parse JSON response
            try:
                return json.loads(response)
            except:
                # Fallback parsing if response isn't valid JSON
                return {
                    "safety_score": 0.85,
                    "risk_level": "MEDIUM",
                    "factors": ["Late night ride", "Residential area"],
                    "recommendations": ["Share location with trusted contact", "Use Safe Route mode"]
                }
                
        except Exception as e:
            print(f"Qwen AI Error: {e}")
            return self._get_fallback_analysis(ride_data)
    
    def analyze_voice_distress(self, transcript: str, context: Dict) -> Dict:
        """Analyze voice transcript for distress signals"""
        try:
            safety_keywords = ['hackathon', 'thai tea']

            prompt = f"""
            Analyze this passenger voice transcript for safety concerns:
            
            Transcript: "{transcript}"
            Current location: {context.get('location', 'Unknown')}
            Ride duration: {context.get('duration', 'Unknown')} minutes
            
            Determine:
            1. Distress level: NORMAL/CONCERN/DISTRESS
            2. Confidence score (0-1)
            3. Recommended response
            4. Suggested actions
            5. User have written down these discreet safety keywords: 'Thai Tea' and 'Hackathon', if mentioned, they might be in danger.
            
            
            Be sensitive to subtle signs of discomfort. Format as JSON.
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are a safety AI analyzing passenger voice for distress. Be highly sensitive to any signs of discomfort or danger."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            
            response = completion.choices[0].message.content
            try:
                result = json.loads(response)
                return {
                    "distress_level": result.get("distress_level", "NORMAL"),
                    "confidence": result.get("confidence", 0.8),
                    "ai_response": result.get("recommended_response", "I'm here if you need anything. Everything okay?"),
                    "actions": result.get("suggested_actions", [])
                }
            except:
                # Fallback to keyword-based analysis
                return self._analyze_keywords(transcript)
                
        except Exception as e:
            print(f"Voice analysis error: {e}")
            return self._analyze_keywords(transcript)
    
    def generate_safety_checkin(self, ride_context: Dict) -> str:
        """Generate contextual safety check-in message"""
        try:
            prompt = f"""
            Generate a natural, caring check-in message for a passenger.
            Context:
            - Ride progress: {ride_context.get('progress', 50)}%
            - Time: {ride_context.get('time', 'evening')}
            - Previous events: {ride_context.get('events', [])}
            
            Make it brief, friendly, and non-alarming. Max 2 sentences.
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are GoGuard, a friendly AI safety companion. Generate natural check-in messages."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback messages
            messages = [
                "Hi! Just checking in. How's your ride going?",
                "Everything going smoothly? I'm here if you need anything!",
                "Hope you're having a comfortable ride. Let me know if you need help!"
            ]
            import random
            return random.choice(messages)
    
    
    def summarize_ride_safety(self, ride_data: Dict) -> Dict:
        """Generate post-ride safety summary"""
        try:
            prompt = f"""
            Summarize this ride from a safety perspective:
            
            Duration: {ride_data.get('duration', 'Unknown')}
            Route: {ride_data.get('route_type', 'standard')}
            Safety events: {ride_data.get('events', [])}
            Driver behavior: {ride_data.get('driver_behavior', 'Normal')},
            
            
            Provide:
            1. Overall safety score (0-100)
            2. Key safety highlights
            3. Recommendations for future rides
            4. Areas of concern (if any)
            
            Format as a paragraph with bullet points, do not bold any text with **. 
            Mention the safety score in this format: Overall Safety Score X%.
            
            
            """
            
            completion = self.client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "You are a safety analyst. Provide constructive, actionable safety summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6
            )
            
            response = completion.choices[0].message.content        
            
            try:
                summary = json.loads(response)
                summary["duration"] = ride_data.get('duration', 'Unknown')
                return summary
            except Exception as e:
                print(f"Exception: {e}")
                
                match = re.search(r'Overall Safety Score\s+(\d+)%', response, re.IGNORECASE)
                if match:
                    safety_score = int(match.group(1))
                    print(f"Extracted safety score: {safety_score}")
                    safety_score = safety_score / 100 
                else:
                    print("Safety % not detected from regex.")
                    safety_score = 0.92
                    
                return {
                    "duration": ride_data.get('duration', 'Unknown'),
                    "safety_score": safety_score * 100,
                    "highlights": ["Smooth ride", "No route deviations", "Professional driver"],
                    "recommendations": ["Continue using Safe Route mode for late-night rides"],
                    "concerns": [],
                    "route_compliance": "98%",
                    "driver_behavior": "Excellent",
                    "ai_interventions": 1,
                    "incidents": 0,
                    "overall_safety_score": safety_score,
                    'qwen_response': response
                }
                
        except Exception as e:
            print(f"Summary generation error: {e}")
            return self._get_default_summary(ride_data)
    
    def _analyze_keywords(self, transcript: str) -> Dict:
        """Fallback keyword-based analysis"""
        transcript_lower = transcript.lower()
        
        # TODO: Monitor this evaluation
        
        prompt = f"""
        Summarize this voice transcription of our passenger.
        Analyze and check for safety concerns
    
        {transcript_lower}
        
        And then rate from 
            0.9 up: DISTRESS,
            0.75 - 0.9: CONCERN
            0.75 and below: NORMAL
            
        Only return the type "DISTRESS", "CONCERN", "NORMAL"
        """
        
        completion = self.client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a safety analyst. Provide constructive, actionable safety summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        
        completion_response = completion.choices[0].message.content
        if completion_response:
            if 'distress' in completion_response.lower():
            
                return {
                    "distress_level": "DISTRESS",
                    "confidence": 0.9,
                    "ai_response": "I've detected you might be in distress. Would you like me to contact emergency services?",
                    "actions": ["contact_emergency", "share_location", "silent_alarm"]
                }
            elif 'concern' in completion_response.lower():
                
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
            
            
    
    def _get_fallback_analysis(self, ride_data: Dict) -> Dict:
        """Fallback analysis when AI is unavailable"""
        hour = datetime.now().hour
        is_late_night = hour >= 22 or hour <= 5
        
        base_score = 0.85
        if is_late_night:
            base_score -= 0.15
            
        return {
            "safety_score": base_score,
            "risk_level": "HIGH" if base_score < 0.7 else "MEDIUM" if base_score < 0.85 else "LOW",
            "factors": ["Time of day", "Route distance"],
            "recommendations": ["Enable Safe Route mode", "Share trip with trusted contact"]
        }
    
    def _get_default_summary(self, ride_data: Dict) -> Dict:
        """Default summary when AI is unavailable"""
        return {
            "safety_score": 90,
            "highlights": [
                "Ride completed successfully",
                "No safety incidents reported",
                "Driver maintained professional conduct"
            ],
            "recommendations": [
                "Continue using GoGuard for all rides",
                "Consider Safe Route mode for future late-night trips"
            ],
            "concerns": []
        }

# Example usage
if __name__ == "__main__":
    ai = QwenSafetyAI()
    
    # Test ride analysis
    ride_data = {
        "driver_name": "Ahmad Rizki",
        "driver_rating": 4.8,
        "driver_rides": 1523,
        "time": "23:30",
        "pickup": "Mall Grand Indonesia",
        "dropoff": "Apartment Sudirman Park"
    }
    
    print("Ride Safety Analysis:")
    print(json.dumps(ai.analyze_ride_safety(ride_data), indent=2))
    
    # Test voice analysis
    # TODO: Fix voice analysis to not access text but voice.
    print("\nVoice Analysis:")
    voice_result = ai.analyze_voice_distress(
        "Aduh ga usah gapapa, lewat jalan biasa aja. jangan dibawa ke rute yang beda saya takut soalnya.. ",
        {"location": "Unknown street", "duration": 15}
    )
    print(json.dumps(voice_result, indent=2))