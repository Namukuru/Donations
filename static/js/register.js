document.addEventListener("DOMContentLoaded", function () {
    let roleField = document.querySelector("#id_role");
    let locationField = document.querySelector("#agent-location-field");
    let locationInput = document.querySelector("#id_location");
    let locationChoice = document.querySelector("#location-choice");
    let mapContainer = document.querySelector("#map");
    let registerForm = document.querySelector("form"); // Get the form

    let map, marker;

    function toggleLocationField() {
        if (roleField.value !== "donor") {
            locationField.style.display = "block";
            locationChoice.value = "current";  // Default to current location
            handleLocationChoice();
        } else {
            locationField.style.display = "none";
            locationInput.value = "";
            locationInput.disabled = true;
        }
    }

    function initializeMap(lat, lng) {
        if (!map) {
            map = L.map("map").setView([lat, lng], 13);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
            marker = L.marker([lat, lng], { draggable: true }).addTo(map);
            
            marker.on("dragend", function () {
                let pos = marker.getLatLng();
                locationInput.value = `${pos.lat}, ${pos.lng}`;
            });
        } else {
            map.setView([lat, lng], 13);
            marker.setLatLng([lat, lng]);
        }
    }

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
                function () {
                    alert("Unable to retrieve location.");
                }
            );
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    }

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

    // ✅ Enable the input before submitting
    registerForm.addEventListener("submit", function () {
        locationInput.disabled = false;
    });

    roleField.addEventListener("change", toggleLocationField);
    locationChoice.addEventListener("change", handleLocationChoice);

    toggleLocationField();
});
