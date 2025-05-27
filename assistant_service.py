"""
Walking AI Assistant service combining all components
"""
import os
import datetime
from typing import Dict, Any, List, Optional
from models import User, Location, RouteRequest, WalkRecord
from llm_service import setup_llm, generate_text
from location_service import OpenStreetMapService, RoutingService
from db_service import DatabaseService

class WalkingAssistant:
    """Main Walking AI Assistant service"""
    
    def __init__(self, db_path, cache_dir, model_name="meta-llama/Llama-2-7b-chat-hf"):
        """Initialize the walking assistant"""
        # Create necessary directories
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize services
        self.db_service = DatabaseService(db_path)
        self.osm_service = OpenStreetMapService(os.path.join(cache_dir, "osm"))
        self.routing_service = RoutingService(os.path.join(cache_dir, "routes"), self.osm_service)
        
        # Initialize LLM
        self.model, self.tokenizer = setup_llm(model_name)
    
    def register_user(self, user_id: str, name: Optional[str] = None) -> User:
        """Register a new user or return existing user"""
        user_data = self.db_service.create_user(user_id, name)
        return User(**user_data)
    
    def update_preferences(self, user_id: str, walking_speed: Optional[float] = None,
                           max_distance: Optional[float] = None) -> User:
        """Update user preferences"""
        user_data = self.db_service.update_user_preferences(user_id, walking_speed, max_distance)
        return User(**user_data)
    
    def add_favorite_location(self, user_id: str, location: Location) -> int:
        """Add a favorite location for a user"""
        return self.db_service.add_favorite_location(
            user_id, 
            location.name or "Unnamed location", 
            location.latitude, 
            location.longitude,
            location.notes
        )
    
    def get_favorite_locations(self, user_id: str) -> List[Location]:
        """Get all favorite locations for a user"""
        locations_data = self.db_service.get_favorite_locations(user_id)
        return [
            Location(
                latitude=loc['latitude'],
                longitude=loc['longitude'],
                name=loc['name'],
                notes=loc['notes']
            ) for loc in locations_data
        ]
    
    def suggest_route(self, route_request: RouteRequest) -> Dict[str, Any]:
        """Suggest a walking route based on user parameters"""
        # Get user preferences
        user_data = self.db_service.get_user(route_request.user_id)
        if not user_data:
            # Create user if doesn't exist
            user_data = self.db_service.create_user(route_request.user_id)
        
        # Use user preferences if request doesn't specify
        max_distance = route_request.max_distance_km or user_data['preferred_max_distance']
        
        if route_request.scenic:
            # Generate a scenic circular route
            route = self.routing_service.generate_scenic_route(
                route_request.start_location.latitude,
                route_request.start_location.longitude,
                max_distance_km=max_distance
            )
        elif route_request.end_location:
            # Generate a route from start to end
            route = self.routing_service.get_walking_route(
                route_request.start_location.latitude,
                route_request.start_location.longitude,
                route_request.end_location.latitude,
                route_request.end_location.longitude
            )
        else:
            # Generate a circular route based on isochrone (time-based)
            isochrone = self.osm_service.generate_walkable_isochrone(
                route_request.start_location.latitude,
                route_request.start_location.longitude,
                walking_time_minutes=int(max_distance * 12)  # Rough estimate: 5km/h = 12min/km
            )
            
            # For circular routes, we'll return the isochrone as a suggestion area
            route = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": isochrone["features"][0]["geometry"],
                        "properties": {
                            "type": "walkable_area",
                            "estimated_walking_time_minutes": int(max_distance * 12)
                        }
                    }
                ],
                "properties": {
                    "total_distance_km": max_distance,
                    "total_duration_minutes": int(max_distance * 12)
                }
            }
            
            # Also get POIs within this area
            pois = self.osm_service.get_pois_around_point(
                route_request.start_location.latitude,
                route_request.start_location.longitude,
                radius=max_distance * 1000
            )
            
            # Add POIs to the route
            route["features"].extend(pois["features"])
        
        return route
    
    def record_completed_walk(self, walk_record: WalkRecord) -> int:
        """Record a completed walk"""
        now = datetime.datetime.now()
        # Estimate start time based on duration
        started_at = now - datetime.timedelta(minutes=walk_record.duration_minutes)
        
        return self.db_service.record_walk(
            walk_record.user_id,
            walk_record.start_location.latitude,
            walk_record.start_location.longitude,
            walk_record.end_location.latitude,
            walk_record.end_location.longitude,
            walk_record.distance_km,
            walk_record.duration_minutes,
            started_at,
            now,
            None  # No notes for now
        )
    
    def get_walking_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get walking history for a user"""
        return self.db_service.get_walking_history(user_id, limit)
    
    def get_walking_stats(self, user_id: str) -> Dict[str, Any]:
        """Get aggregate walking statistics for a user"""
        return self.db_service.get_walking_stats(user_id)
    
    def analyze_walking_behavior(self, user_id: str) -> str:
        """Analyze user's walking behavior using LLM"""
        # Get user data
        user_data = self.db_service.get_user(user_id)
        if not user_data:
            return "No user data available."
        
        # Get walking history
        history = self.db_service.get_walking_history(user_id, limit=20)
        if not history:
            return "Not enough walking data to analyze behavior."
        
        # Get stats
        stats = self.db_service.get_walking_stats(user_id)
        
        # Prepare recent walks data
        recent_walks_text = ""
        for i, walk in enumerate(history[:5]):
            recent_walks_text += f"- {i+1}. Date: {walk['completed_at']}, Distance: {walk['distance_km']:.2f} km, Duration: {walk['duration_minutes']} min\n"
        
        # Prepare prompt for LLM - using single quotes and proper formatting
        prompt = f'''Analyze the following walking data for a user:

User preferences:
- Preferred walking speed: {user_data['preferred_walking_speed']} km/h
- Preferred maximum distance: {user_data['preferred_max_distance']} km

Walking statistics:
- Total walks: {stats['total_walks']}
- Total distance: {stats['total_distance_km']:.2f} km
- Total duration: {stats['total_duration_minutes']} minutes
- Average walk distance: {stats['avg_distance_km']:.2f} km
- Average walk duration: {stats['avg_duration_minutes']:.2f} minutes
- Longest walk: {stats['max_distance_km']:.2f} km
- Longest walk duration: {stats['max_duration_minutes']} minutes

Recent walks:
{recent_walks_text}

Please provide a brief analysis of this user's walking behavior and habits.
Include personalized suggestions for improvements and motivation.
Keep your response concise and friendly.'''
        
        try:
            # Generate analysis with LLM
            analysis = generate_text(self.model, self.tokenizer, prompt, max_length=1024)
            return analysis
        except Exception as e:
            return f"Error generating analysis: {str(e)}"
    
    def generate_route_description(self, route: Dict[str, Any]) -> str:
        """Generate a natural language description of a route using LLM"""
        # Extract key information from the route
        distance = route["properties"].get("total_distance_km", 0)
        duration = route["properties"].get("total_duration_minutes", 0)
        
        # Extract POIs if available
        pois = route["properties"].get("pois", [])
        poi_descriptions = []
        
        for poi in pois:
            poi_descriptions.append(f"- {poi.get('name', 'Unnamed location')} ({poi.get('type', 'point of interest')})")
        
        # Fix: Extract the newline join outside the f-string
        poi_text = '\n'.join(poi_descriptions) if poi_descriptions else "No specific points of interest."
        
        # Prepare prompt for LLM
        prompt = f"""Describe the following walking route in a friendly, conversational way:
        
Route details:
- Total distance: {distance:.2f} km
- Estimated duration: {duration} minutes

Points of interest along the route:
{poi_text}

Provide a brief, engaging description of this route that would encourage someone to try it.
Include practical information like distance and time, as well as highlighting any interesting features.
Keep your response concise and conversational."""
        
        try:
            # Generate description with LLM
            description = generate_text(self.model, self.tokenizer, prompt, max_length=768)
            return description
        except Exception as e:
            return f"Error generating route description: {str(e)}"
    
    def close(self):
        """Clean up resources"""
        self.db_service.close()
