document.addEventListener('DOMContentLoaded', function() {
    const locationSelect = document.getElementById('location-select');
    const locationInput = document.getElementById('location-input');
    const mapContainer = document.getElementById('map');

    let map;
    let marker;
    let isMapInitialized = false; // Flag to track if the map is already initialized

    // Initialize the map
    function initMap(lat, lng) {
        if (isMapInitialized) return; // If the map is already initialized, do nothing

        console.log('Initializing map...'); // Debugging

        map = L.map('map').setView([lat, lng], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        marker = L.marker([lat, lng], { draggable: true }).addTo(map);

        marker.on('dragend', function(event) {
            const position = marker.getLatLng();
            locationInput.value = `${position.lat}, ${position.lng}`;
        });

        isMapInitialized = true; // Set the flag to true after initialization
    }

    // Destroy the map
    function destroyMap() {
        if (map) {
            console.log('Destroying map...'); // Debugging
            map.remove(); // Remove the map instance
            map = null;
            marker = null;
            isMapInitialized = false; // Reset the flag
        }
    }

    // Handle dropdown change
    locationSelect.addEventListener('change', function() {
        if (this.value === 'another') {
            mapContainer.style.display = 'block';
            locationInput.disabled = false;

            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    initMap(position.coords.latitude, position.coords.longitude);
                }, function(error) {
                    console.error("Geolocation failed: ", error);
                    initMap(40.7128, -74.0060); // Default to New York if geolocation fails
                });
            } else {
                console.error("Geolocation is not supported by this browser.");
                initMap(40.7128, -74.0060); // Default to New York
            }
        } else {
            mapContainer.style.display = 'none';
            locationInput.disabled = true;
            locationInput.value = ''; // Clear the input
            destroyMap(); // Destroy the map when switching back
        }
    });

    // If the page is reloaded and "another" is selected, show the map
    if (locationSelect.value === 'another') {
        mapContainer.style.display = 'block';
        locationInput.disabled = false;

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function(position) {
                initMap(position.coords.latitude, position.coords.longitude);
            }, function(error) {
                console.error("Geolocation failed: ", error);
                initMap(40.7128, -74.0060); // Default to New York if geolocation fails
            });
        } else {
            console.error("Geolocation is not supported by this browser.");
            initMap(40.7128, -74.0060); // Default to New York
        }
    }
});