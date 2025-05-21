"""
FastAPI server for the Walking AI Assistant
"""
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from models import User, Location, RouteRequest, WalkRecord
from assistant_service import WalkingAssistant
import os

# Initialize the app
app = FastAPI(title="Walking AI Assistant API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables with defaults
DB_PATH = os.getenv("DB_PATH", "walking_assistant.db")
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-2-7b-chat-hf")

# Initialize assistant
assistant = WalkingAssistant(DB_PATH, CACHE_DIR, MODEL_NAME)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Walking AI Assistant API is running"}

@app.post("/users/", response_model=User)
async def create_user(user_id: str, name: Optional[str] = None):
    """Register a new user"""
    return assistant.register_user(user_id, name)

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """Get user information"""
    user_data = assistant.db_service.get_user(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user_data)

@app.put("/users/{user_id}/preferences", response_model=User)
async def update_user_preferences(
    user_id: str, 
    walking_speed: Optional[float] = None, 
    max_distance: Optional[float] = None
):
    """Update user preferences"""
    return assistant.update_preferences(user_id, walking_speed, max_distance)

@app.post("/users/{user_id}/favorite-locations/")
async def add_favorite_location(user_id: str, location: Location):
    """Add a favorite location for a user"""
    location_id = assistant.add_favorite_location(user_id, location)
    return {"id": location_id, "message": "Location added successfully"}

@app.get("/users/{user_id}/favorite-locations/", response_model=List[Location])
async def get_favorite_locations(user_id: str):
    """Get all favorite locations for a user"""
    return assistant.get_favorite_locations(user_id)

@app.post("/routes/suggest")
async def suggest_route(route_request: RouteRequest):
    """Suggest a walking route based on user parameters"""
    route = assistant.suggest_route(route_request)
    
    # Add a natural language description
    description = assistant.generate_route_description(route)
    route["properties"]["description"] = description
    
    return route

@app.post("/walks/record")
async def record_walk(walk_record: WalkRecord):
    """Record a completed walk"""
    walk_id = assistant.record_completed_walk(walk_record)
    return {"id": walk_id, "message": "Walk recorded successfully"}

@app.get("/users/{user_id}/walks/history")
async def get_walking_history(user_id: str, limit: int = 10):
    """Get walking history for a user"""
    return assistant.get_walking_history(user_id, limit)

@app.get("/users/{user_id}/walks/stats")
async def get_walking_stats(user_id: str):
    """Get aggregate walking statistics for a user"""
    return assistant.get_walking_stats(user_id)

@app.get("/users/{user_id}/analysis")
async def analyze_walking_behavior(user_id: str):
    """Analyze user's walking behavior"""
    analysis = assistant.analyze_walking_behavior(user_id)
    return {"analysis": analysis}

@app.get("/pois")
async def get_points_of_interest(latitude: float, longitude: float, radius: int = 500):
    """Get points of interest around a location"""
    pois = assistant.osm_service.get_pois_around_point(latitude, longitude, radius)
    return pois

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources on shutdown"""
    assistant.close()
