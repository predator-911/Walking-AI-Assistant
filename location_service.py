"""
Location services for OpenStreetMap and routing
"""
import os
import json
import requests
import geopy
import geopy.distance
from shapely.geometry import Point, Polygon, LineString, shape
import geopandas as gpd

class OpenStreetMapService:
    """Service to interact with OpenStreetMap via Overpass API"""
    
    def __init__(self, cache_dir):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_pois_around_point(self, lat, lon, radius=500, poi_types=None):
        """
        Get points of interest around a specific location
        """
        if poi_types is None:
            # Default POI types that are interesting for walking
            poi_types = [
                'leisure=park', 
                'natural=wood',
                'amenity=cafe', 
                'amenity=restaurant',
                'tourism=attraction',
                'historic=monument',
                'shop=bakery',
                'amenity=bench'
            ]
        
        # Create cache key from parameters
        cache_key = f"{lat}_{lon}_{radius}_{'_'.join(poi_types)}"
        cache_file = f"{self.cache_dir}/{cache_key}.json"
        
        # Check if we have cached results
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # Build the Overpass query
        overpass_query = """
        [out:json];
        (
        """
        
        for poi_type in poi_types:
            key, value = poi_type.split('=')
            overpass_query += f"""
            node["{key}"="{value}"](around:{radius},{lat},{lon});
            way["{key}"="{value}"](around:{radius},{lat},{lon});
            relation["{key}"="{value}"](around:{radius},{lat},{lon});
            """
        
        overpass_query += """
        );
        out body geom;
        """
        
        # Send request to Overpass API
        response = requests.post(self.overpass_url, data={"data": overpass_query})
        data = response.json()
        
        # Convert to GeoJSON format
        features = []
        
        for element in data.get('elements', []):
            if element['type'] == 'node':
                geometry = {
                    'type': 'Point',
                    'coordinates': [element['lon'], element['lat']]
                }
            elif element['type'] == 'way' and 'geometry' in element:
                coords = [[node['lon'], node['lat']] for node in element['geometry']]
                geometry = {
                    'type': 'LineString',
                    'coordinates': coords
                }
            elif element['type'] == 'relation':
                # Relations are complex, simplified handling here
                continue
            else:
                continue
            
            properties = element.get('tags', {})
            properties['osm_id'] = element['id']
            properties['osm_type'] = element['type']
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': properties
            })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(geojson, f)
        
        return geojson
    
    def generate_walkable_isochrone(self, lat, lon, walking_time_minutes=15):
        """
        Generate a polygon representing the area reachable within a given walking time
        """
        # Very rough approximation: average walking speed is about 5km/h or ~83m/min
        walking_distance_meters = walking_time_minutes * 83
        
        # Create a point
        center = Point(lon, lat)
        
        # Create a GeoSeries with the point
        gs = gpd.GeoSeries([center], crs="EPSG:4326")
        
        # Convert to a projected CRS for accurate distance calculation
        gs_proj = gs.to_crs(epsg=3857)
        
        # Create a buffer around the point in meters
        buffer = gs_proj.buffer(walking_distance_meters)
        
        # Convert back to WGS84
        buffer_wgs84 = buffer.to_crs(epsg=4326)
        
        # Convert to GeoJSON
        geojson_polygon = json.loads(buffer_wgs84.to_json())
        
        return geojson_polygon


class RoutingService:
    """Service to get walking routes using OSRM public endpoints"""
    
    def __init__(self, cache_dir, osm_service):
        # Using the public OSRM demo server - In production, you'd want to self-host this
        self.osrm_url = "https://router.project-osrm.org/route/v1/foot"
        self.cache_dir = cache_dir
        self.osm_service = osm_service
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_walking_route(self, start_lat, start_lon, end_lat, end_lon):
        """
        Get a walking route between two points
        """
        # Check cache first
        cache_key = f"{start_lat}_{start_lon}_{end_lat}_{end_lon}"
        cache_file = f"{self.cache_dir}/{cache_key}.json"
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # Construct the API URL
        url = f"{self.osrm_url}/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {
            "steps": "true",
            "geometries": "geojson",
            "overview": "full"
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data["code"] != "Ok":
                print(f"Error getting route: {data.get('message', 'Unknown error')}")
                return None
            
            # Extract the route geometry
            route = data["routes"][0]
            geometry = route["geometry"]
            distance = route["distance"]  # in meters
            duration = route["duration"]  # in seconds
            
            result = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "distance": distance,
                    "duration": duration,
                    "duration_minutes": int(duration / 60)
                }
            }
            
            # Cache the results
            with open(cache_file, 'w') as f:
                json.dump(result, f)
            
            return result
        
        except Exception as e:
            print(f"Error getting walking route: {str(e)}")
            return None
    
    def generate_scenic_route(self, start_lat, start_lon, max_distance_km=3):
        """
        Generate a scenic circular walking route starting and ending at the same point
        """
        # First, get POIs around the starting point
        pois = self.osm_service.get_pois_around_point(
            start_lat, 
            start_lon, 
            radius=max_distance_km * 1000,
            poi_types=['leisure=park', 'natural=wood', 'tourism=attraction', 'historic=monument']
        )
        
        # If we don't have enough POIs, return None
        if len(pois['features']) < 2:
            print("Not enough POIs found for a scenic route")
            return None
        
        # Pick some interesting POIs to visit (at most 3-4 points to keep the route manageable)
        selected_pois = []
        parks = [p for p in pois['features'] if 'leisure' in p['properties'] and p['properties']['leisure'] == 'park']
        attractions = [p for p in pois['features'] if 'tourism' in p['properties'] or 'historic' in p['properties']]
        
        # Prioritize parks and attractions
        if parks:
            selected_pois.append(parks[0])
        if attractions:
            selected_pois.append(attractions[0])
        
        # Add more POIs if needed
        while len(selected_pois) < 3 and len(pois['features']) > len(selected_pois):
            # Add a point that's not already selected
            for poi in pois['features']:
                if poi not in selected_pois:
                    selected_pois.append(poi)
                    break
        
        # Create a circular route starting and ending at the provided point
        route_points = [(start_lat, start_lon)]
        
        # Add the POIs
        for poi in selected_pois:
            coords = poi['geometry']['coordinates']
            route_points.append((coords[1], coords[0]))  # Convert from [lon, lat] to (lat, lon)
        
        # Close the loop by returning to start
        route_points.append((start_lat, start_lon))
        
        # Now get the walking directions for each segment
        combined_route = {
            "type": "FeatureCollection",
            "features": [],
            "properties": {
                "total_distance": 0,
                "total_duration": 0,
                "pois": []
            }
        }
        
        for i in range(len(route_points) - 1):
            start = route_points[i]
            end = route_points[i + 1]
            
            route_segment = self.get_walking_route(start[0], start[1], end[0], end[1])
            
            if route_segment:
                combined_route["features"].append(route_segment)
                combined_route["properties"]["total_distance"] += route_segment["properties"]["distance"]
                combined_route["properties"]["total_duration"] += route_segment["properties"]["duration"]
        
        # Add POI information
        for poi in selected_pois:
            combined_route["properties"]["pois"].append({
                "name": poi["properties"].get("name", "Unnamed location"),
                "type": next((k for k, v in poi["properties"].items() if k in ["leisure", "natural", "tourism", "historic"]), "point of interest"),
                "location": poi["geometry"]["coordinates"]
            })
        
        # Convert to human-readable values
        combined_route["properties"]["total_distance_km"] = round(combined_route["properties"]["total_distance"] / 1000, 2)
        combined_route["properties"]["total_duration_minutes"] = int(combined_route["properties"]["total_duration"] / 60)
        
        return combined_route
