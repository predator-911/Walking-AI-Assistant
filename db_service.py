"""
Database service for user data
"""
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

class DatabaseService:
    """Database service for user preferences and history"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.initialize_db()
    
    def initialize_db(self):
        """Create necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
            name TEXT,
            preferred_walking_speed REAL DEFAULT 5.0,
            preferred_max_distance REAL DEFAULT 5.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create favorite locations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorite_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Create walking history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS walking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            start_latitude REAL,
            start_longitude REAL,
            end_latitude REAL,
            end_longitude REAL,
            distance_km REAL,
            duration_minutes INTEGER,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        self.conn.commit()
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT user_id, name, preferred_walking_speed, preferred_max_distance
        FROM users WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'user_id': row[0],
            'name': row[1],
            'preferred_walking_speed': row[2],
            'preferred_max_distance': row[3]
        }
    
    def create_user(self, user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO users (user_id, name)
            VALUES (?, ?)
            ''', (user_id, name))
            self.conn.commit()
            return self.get_user(user_id)
        except sqlite3.IntegrityError:
            # User already exists
            return self.get_user(user_id)
    
    def update_user_preferences(self, user_id: str, walking_speed: Optional[float] = None, 
                                max_distance: Optional[float] = None) -> Dict[str, Any]:
        """Update user preferences"""
        cursor = self.conn.cursor()
        
        # Build the update query based on provided parameters
        updates = []
        params = []
        
        if walking_speed is not None:
            updates.append("preferred_walking_speed = ?")
            params.append(walking_speed)
        
        if max_distance is not None:
            updates.append("preferred_max_distance = ?")
            params.append(max_distance)
        
        if not updates:
            return self.get_user(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        params.append(user_id)
        
        cursor.execute(query, params)
        self.conn.commit()
        
        return self.get_user(user_id)
    
    def add_favorite_location(self, user_id: str, name: str, latitude: float, 
                              longitude: float, notes: Optional[str] = None) -> int:
        """Add a favorite location for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO favorite_locations (user_id, name, latitude, longitude, notes)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, latitude, longitude, notes))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_favorite_locations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all favorite locations for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT id, name, latitude, longitude, notes
        FROM favorite_locations
        WHERE user_id = ?
        ''', (user_id,))
        
        locations = []
        for row in cursor.fetchall():
            locations.append({
                'id': row[0],
                'name': row[1],
                'latitude': row[2],
                'longitude': row[3],
                'notes': row[4]
            })
        
        return locations
    
    def record_walk(self, user_id: str, start_lat: float, start_lon: float,
                   end_lat: float, end_lon: float, distance_km: float, 
                   duration_minutes: int, started_at: datetime.datetime,
                   completed_at: datetime.datetime, notes: Optional[str] = None) -> int:
        """Record a completed walk"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO walking_history 
        (user_id, start_latitude, start_longitude, end_latitude, end_longitude, 
         distance_km, duration_minutes, started_at, completed_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, start_lat, start_lon, end_lat, end_lon, 
              distance_km, duration_minutes, started_at, completed_at, notes))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_walking_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get walking history for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT id, start_latitude, start_longitude, end_latitude, end_longitude,
               distance_km, duration_minutes, started_at, completed_at, notes
        FROM walking_history
        WHERE user_id = ?
        ORDER BY completed_at DESC
        LIMIT ?
        ''', (user_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'start_location': {'latitude': row[1], 'longitude': row[2]},
                'end_location': {'latitude': row[3], 'longitude': row[4]},
                'distance_km': row[5],
                'duration_minutes': row[6],
                'started_at': row[7],
                'completed_at': row[8],
                'notes': row[9]
            })
        
        return history
    
    def get_walking_stats(self, user_id: str) -> Dict[str, Any]:
        """Get aggregate walking statistics for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT 
            COUNT(*) as total_walks,
            SUM(distance_km) as total_distance,
            SUM(duration_minutes) as total_duration,
            AVG(distance_km) as avg_distance,
            AVG(duration_minutes) as avg_duration,
            MAX(distance_km) as max_distance,
            MAX(duration_minutes) as max_duration
        FROM walking_history
        WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if not row or row[0] == 0:
            return {
                'total_walks': 0,
                'total_distance_km': 0,
                'total_duration_minutes': 0,
                'avg_distance_km': 0,
                'avg_duration_minutes': 0,
                'max_distance_km': 0,
                'max_duration_minutes': 0
            }
        
        return {
            'total_walks': row[0],
            'total_distance_km': row[1],
            'total_duration_minutes': row[2],
            'avg_distance_km': row[3],
            'avg_duration_minutes': row[4],
            'max_distance_km': row[5],
            'max_duration_minutes': row[6]
        }
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
