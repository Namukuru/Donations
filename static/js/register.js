document.addEventListener("DOMContentLoaded", function () {
    // Fields for role selection and location
    let roleField = document.querySelector("#id_role");
    let locationField = document.querySelector("#agent-location-field");
    let locationInput = document.querySelector("#id_location");
    let locationChoice = document.querySelector("#location-choice");
    let mapContainer = document.querySelector("#map");
    let registerForm = document.querySelector("form");

    // Fields specific to recipients
    let recipientFields = document.querySelector("#recipient-fields");

    let map, marker;

    // Toggle location and recipient fields based on role
    function toggleFields() {
        if (roleField.value === "recipient" || roleField.value === "agent") {
            // Show location field for recipients and agents
            locationField.style.display = "block";
            locationChoice.value = "current";  // Default to current location
            handleLocationChoice();

            // Show recipient-specific fields only for recipients
            if (roleField.value === "recipient") {
                recipientFields.style.display = "block";
            } else {
                recipientFields.style.display = "none";
            }
        } else {
            // Hide location and recipient fields for donors
            locationField.style.display = "none";
            recipientFields.style.display = "none";
            locationInput.value = "";
            locationInput.disabled = true;
        }
    }

    // Initialize or update the map
    function initializeMap(lat, lng) {
        if (!map) {
            // Initialize the map
            map = L.map("map", {
                center: [lat, lng],
                zoom: 13
            });

            // Add the tile layer (map tiles)
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            // Add a draggable marker
            marker = L.marker([lat, lng], { draggable: true }).addTo(map);

            // Update the location input when the marker is dragged
            marker.on("dragend", function () {
                let pos = marker.getLatLng();
                locationInput.value = `${pos.lat}, ${pos.lng}`;
            });

            // Update the marker position when the map is clicked
            map.on("click", function (e) {
                marker.setLatLng(e.latlng);
                locationInput.value = `${e.latlng.lat}, ${e.latlng.lng}`;
            });
        } else {
            // Update the map view and marker position
            map.setView([lat, lng], 13);
            marker.setLatLng([lat, lng]);
        }
    }

    // Get the user's current location
    function getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    let lat = position.coords.latitude;
                    let lng = position.coords.longitude;
                    locationInput.value = `${lat}, ${lng}`;
                    locationInput.disabled = false; // Enable input before submitting
                    initializeMap(lat, lng);
                },
                function (error) {
                    alert("Unable to retrieve location. Please allow location access or choose another location.");
                    locationChoice.value = "manual"; // Fallback to manual location
                    handleLocationChoice();
                }
            );
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    }

    // Handle location choice (current or manual)
    function handleLocationChoice() {
        if (locationChoice.value === "current") {
            locationInput.disabled = false; // Enable before submission
            mapContainer.style.display = "none";
            getCurrentLocation();
        } else {
            locationInput.disabled = false; // Enable before submission
            mapContainer.style.display = "block";
            initializeMap(-1.2921, 36.8219); // Default to Nairobi, Kenya
        }
    }

    // Enable the input before submitting
    registerForm.addEventListener("submit", function () {
        locationInput.disabled = false;
    });

    // Event listeners
    roleField.addEventListener("change", toggleFields);
    locationChoice.addEventListener("change", handleLocationChoice);

    // Initial setup
    toggleFields();
});