"""
DATA LOADER: Data Loading Functions
====================================

Handles loading and preparing geographic data for analysis.

Functions:
    - load_sample_data(): Load demo/mock data
    - create_test_isochrones(): Create circular isochrone approximations
    - load_osm_data(): Load real data from OpenStreetMap (optional)

Author: Marita R. Botin
"""

from typing import Dict, Tuple, Optional
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pandas as pd


def load_sample_data() -> Dict:
    """
    Load sample geographic data (demonstration).
    
    In production, this would load from:
    - OpenStreetMap (OSMNX)
    - Overture Maps (GeoJSON)
    - Makati Open Data (shapefiles)
    
    Returns:
        Dictionary with 'places' GeoDataFrame
        
    Example:
        >>> data = load_sample_data()
        >>> places_gdf = data["places"]
        >>> print(len(places_gdf))  # Number of places
    """
    places_data = {
        "geometry": [
            Point(121.0186, 14.5794),
            Point(121.0200, 14.5800),
            Point(121.0150, 14.5750),
            Point(121.0210, 14.5760),
            Point(121.0170, 14.5810),
            Point(121.0180, 14.5780),
            Point(121.0195, 14.5805),
            Point(121.0165, 14.5765),
        ],
        "name": [
            "Makati City Hall",
            "Ayala Park",
            "SM City Makati",
            "Ospital ng Makati",
            "Makati Science High School",
            "Makati Public Library",
            "Greenbelt",
            "Glorietta",
        ],
        "category_label": [
            "government",
            "recreation",
            "commerce",
            "healthcare",
            "education",
            "education",
            "commerce",
            "commerce",
        ],
        "lens_id": [
            "living",
            "enjoying",
            "supplying",
            "caring",
            "learning",
            "learning",
            "supplying",
            "supplying",
        ],
    }
    
    places_gdf = gpd.GeoDataFrame(places_data, crs="EPSG:4326")
    return {"places": places_gdf}


def create_test_isochrones(center: Tuple[float, float]) -> Dict[int, Polygon]:
    """
    Create test isochrone polygons (circular approximation).
    
    In production, this would call:
    - Mapbox Isochrone API
    - OSRM (Open Source Routing Machine)
    - GIS tools with network analysis
    
    This function creates circular buffers as a simple approximation.
    Assumes walking speed of ~4.8 km/hr:
    - 5 min = 0.4 km
    - 10 min = 0.8 km
    - 15 min = 1.2 km
    
    Args:
        center: (lng, lat) coordinates
    
    Returns:
        Dictionary {5: Polygon, 10: Polygon, 15: Polygon}
        
    Example:
        >>> isochrones = create_test_isochrones((121.0186, 14.5794))
        >>> iso_5min = isochrones[5]
        >>> print(iso_5min.area)  # Square degrees
    """
    lng, lat = center
    
    # Approximate travel distances (in km)
    # Walking: ~4.8 km/hr = 0.08 km/min
    radii_km = {5: 0.4, 10: 0.8, 15: 1.2}
    
    isochrones = {}
    for minutes, radius_km in radii_km.items():
        # Convert km to degrees (~111 km per degree latitude)
        radius_deg = radius_km / 111.0
        
        center_point = Point(lng, lat)
        iso_polygon = center_point.buffer(radius_deg)
        isochrones[minutes] = iso_polygon
    
    return isochrones


def load_osm_data(
    center: Tuple[float, float],
    distance_m: int = 2000,
    place_types: Optional[Dict[str, list]] = None,
) -> Optional[Dict]:
    """
    Load real data from OpenStreetMap using OSMNX.
    
    This function requires: pip install osmnx
    
    Args:
        center: (lng, lat) coordinates
        distance_m: Radius in meters to fetch data
        place_types: Dict mapping lens_id to OSM tags
            Example: {"living": ["transit_station"], "working": ["office"]}
    
    Returns:
        Dictionary with 'places' GeoDataFrame, or None if OSMNX not available
        
    Example:
        >>> center = (121.0186, 14.5794)
        >>> data = load_osm_data(center, distance_m=1500)
        >>> if data:
        ...     places = data["places"]
        ...     print(f"Found {len(places)} places")
    
    Note:
        Requires internet connection and OSMNX library.
        First run may be slow (downloads OSM data).
    """
    try:
        import osmnx as ox
    except ImportError:
        print("Error: OSMNX not installed. Run: pip install osmnx")
        return None
    
    try:
        # Default place types if not provided
        if place_types is None:
            place_types = {
                "living": ["transit_station"],
                "working": ["office", "government"],
                "supplying": ["supermarket", "market"],
                "caring": ["hospital", "pharmacy"],
                "learning": ["school"],
                "enjoying": ["restaurant", "park"],
            }
        
        # Flatten the place types into a single query
        all_tags = {}
        for lens_id, tags in place_types.items():
            all_tags[lens_id] = tags
        
        # Create GeoDataFrame from multiple queries
        all_places = []
        
        for lens_id, tags in all_tags.items():
            for tag in tags:
                try:
                    features = ox.features_from_point(
                        center,
                        dist=distance_m,
                        tags={tag: True}
                    )
                    if len(features) > 0:
                        features["lens_id"] = lens_id
                        features["category_label"] = tag
                        all_places.append(features)
                except Exception as e:
                    print(f"Warning: Could not fetch {tag}: {e}")
                    continue
        
        if all_places:
            places_gdf = pd.concat(all_places, ignore_index=True)
            # Ensure geometry column exists
            if "geometry" not in places_gdf.columns:
                return None
            places_gdf = gpd.GeoDataFrame(places_gdf, geometry="geometry", crs="EPSG:4326")
            # Add name column if missing
            if "name" not in places_gdf.columns:
                places_gdf["name"] = places_gdf.index.astype(str)
            return {"places": places_gdf}
        else:
            return None
    
    except Exception as e:
        print(f"Error loading OSM data: {e}")
        return None


def load_overture_data(
    bbox: Tuple[float, float, float, float],
    api_key: Optional[str] = None,
) -> Optional[Dict]:
    """
    Load real data from Overture Maps.
    
    This function requires: pip install overturemap
    
    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) bounding box
        api_key: Optional API key for Overture Maps
    
    Returns:
        Dictionary with 'places' GeoDataFrame, or None if API not available
        
    Note:
        Requires Overture Maps API access.
        See: https://overturemap.org/
    """
    try:
        import overturemaps  # hypothetical library
    except ImportError:
        print("Error: overturemap not installed")
        return None
    
    # Implementation would depend on Overture Maps API
    # This is a placeholder
    return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_geodataframe(gdf: gpd.GeoDataFrame) -> bool:
    """
    Validate that a GeoDataFrame has required columns.
    
    Required columns:
        - geometry (Point)
        - lens_id (str)
        - category_label (str)
        - name (str)
    
    Args:
        gdf: GeoDataFrame to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_columns = ["geometry", "lens_id", "category_label", "name"]
    
    for col in required_columns:
        if col not in gdf.columns:
            print(f"Error: Missing column '{col}'")
            return False
    
    if gdf.geometry.geom_type.unique().tolist() != ["Point"]:
        print("Error: All geometries must be Points")
        return False
    
    return True


def sample_geodataframe(
    gdf: gpd.GeoDataFrame,
    n: int = 100,
    random_state: Optional[int] = None,
) -> gpd.GeoDataFrame:
    """
    Sample n random rows from a GeoDataFrame.
    
    Args:
        gdf: Source GeoDataFrame
        n: Number of rows to sample
        random_state: Random seed for reproducibility
    
    Returns:
        Sampled GeoDataFrame
    """
    return gdf.sample(min(n, len(gdf)), random_state=random_state)


def filter_by_bbox(
    gdf: gpd.GeoDataFrame,
    bbox: Tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    """
    Filter GeoDataFrame to points within a bounding box.
    
    Args:
        gdf: Source GeoDataFrame
        bbox: (min_lon, min_lat, max_lon, max_lat)
    
    Returns:
        Filtered GeoDataFrame
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    bounds = Polygon([
        (min_lon, min_lat),
        (max_lon, min_lat),
        (max_lon, max_lat),
        (min_lon, max_lat),
    ])
    return gdf[gdf.geometry.within(bounds)]
