import requests
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)  # Logger for debugging

def get_address_from_coordinates(coordinates):
    """Convert latitude, longitude to a human-readable address using Google Maps API with caching."""
    if not coordinates:
        return "No pickup location provided"

    try:
        # Normalize cache key to avoid invalid characters
        safe_key = hashlib.md5(coordinates.encode()).hexdigest()  # Generates a safe hash key

        # Check cache first
        cached_address = cache.get(safe_key)
        if cached_address:
            return cached_address  # ✅ Return cached address instead of making an API call

        # Split latitude & longitude safely
        lat, lng = map(str.strip, coordinates.split(","))

        google_maps_api_key = settings.GOOGLE_API_KEY
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={google_maps_api_key}"

        # Set a timeout to avoid long waits
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raise an error if request fails

        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            address = data["results"][0]["formatted_address"]
            # ✅ Cache result for 24 hours
            cache.set(safe_key, address, timeout=86400)
            return address
        else:
            logger.warning(f"Google Maps API failed: {data.get('status')}")
            return "Address not found"
    
    except requests.exceptions.Timeout:
        logger.error("Google Maps API request timed out")
        return "Address lookup timed out"
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Google Maps API error: {e}")
        return "Error retrieving address"
    
    except Exception as e:
        logger.exception(f"Unexpected error in address lookup: {e}")
        return "Address lookup failed"

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    """
    # Radius of the Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Difference in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Distance in kilometers
    distance = R * c
    return distance