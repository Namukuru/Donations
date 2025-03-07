import requests
from django.core.cache import cache
from django.conf import settings

def get_address_from_coordinates(coordinates):
    """Convert latitude, longitude to a human-readable address using Google Maps API with caching."""
    if not coordinates:
        return "No pickup location provided"

    # Check cache first
    cache_key = f"address_{coordinates}"
    cached_address = cache.get(cache_key)

    if cached_address:
        return cached_address  # ✅ Return cached address instead of making an API call

    try:
        # Split latitude & longitude
        lat, lng = coordinates.split(", ")
        google_maps_api_key = settings.GOOGLE_API_KEY
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={google_maps_api_key}"

        # Set a timeout to avoid long waits
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raise an error if request fails

        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            address = data["results"][0]["formatted_address"]
            # ✅ Cache result for 1 day
            cache.set(cache_key, address, timeout=86400)
            return address
        else:
            return "Address not found"
    except (requests.RequestException, KeyError, IndexError) as e:
        return f"Error retrieving address: {e}"
