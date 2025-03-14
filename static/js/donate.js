document.addEventListener("DOMContentLoaded", function () {
    const donationType = document.querySelector("#donation-type");
    const monetaryFields = document.querySelector("#monetary-fields");
    const inKindFields = document.querySelector("#in-kind-fields");
    const pickupSection = document.querySelector("#pickup-section");
    const pickupChoice = document.querySelector("select[name='pickup_choice']");
    const pickupLocation = document.querySelector("input[name='pickup_location']");
    const mapContainer = document.createElement("div");
    
    let map, marker;

    // Create map container and insert after pickup location field
    mapContainer.id = "map";
    mapContainer.style = "height: 300px; border-radius: 8px; margin-top: 10px;";
    mapContainer.classList.add("hidden");
    pickupLocation.parentNode.insertBefore(mapContainer, pickupLocation.nextSibling);

    // Function to toggle fields and handle required attributes
    function toggleFields() {
        if (donationType.value === "monetary") {
            monetaryFields.classList.remove("hidden");
            inKindFields.classList.add("hidden");
            pickupSection.classList.add("hidden");
            mapContainer.classList.add("hidden");
        } else {
            monetaryFields.classList.add("hidden");
            inKindFields.classList.remove("hidden");
            pickupSection.classList.remove("hidden");
            messageField.classList.add("hidden");
        }
    }

    // Handle donation type change
    donationType.addEventListener("change", toggleFields);

    // Function to initialize the map
    function initializeMap(lat = 0, lng = 0) {
        if (!map) {
            map = L.map("map").setView([lat, lng], 15);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: "© OpenStreetMap contributors"
            }).addTo(map);

            marker = L.marker([lat, lng], { draggable: true }).addTo(map);

            // Update location field when marker is moved
            marker.on("dragend", function (event) {
                const position = marker.getLatLng();
                updateAddress(position.lat, position.lng);
            });

            // Allow user to click on the map to set location
            map.on("click", function (event) {
                marker.setLatLng(event.latlng);
                updateAddress(event.latlng.lat, event.latlng.lng);
            });
        } else {
            map.setView([lat, lng], 15);
            marker.setLatLng([lat, lng]);
        }
    }

    // Handle pickup choice logic
    pickupChoice.addEventListener("change", function () {
        if (pickupChoice.value === "current") {
            pickupLocation.disabled = false;
            getCurrentLocation();
            mapContainer.classList.add("hidden");
        } else {
            pickupLocation.disabled = false;
            pickupLocation.value = "";
            pickupLocation.placeholder = "Enter preferred address";
            mapContainer.classList.remove("hidden");

            // Get current location to start the map
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => initializeMap(position.coords.latitude, position.coords.longitude),
                    () => initializeMap(0, 0) // Default to (0,0) if location not available
                );
            } else {
                initializeMap(0, 0);
            }
        }
    });

    // Function to get current location
    function getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    pickupLocation.value = `${position.coords.latitude}, ${position.coords.longitude}`;
                    initializeMap(position.coords.latitude, position.coords.longitude);
                },
                (error) => {
                    alert("Error getting location. Please allow location access.");
                }
            );
        } else {
            alert("Geolocation is not supported by your browser.");
        }
    }

    // Function to update the address field when location changes
    function updateAddress(lat, lon) {
        pickupLocation.value = `${lat}, ${lon}`;
    }

    // Update map marker when user types an address
    pickupLocation.addEventListener("change", function () {
        let address = pickupLocation.value;
        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`)
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    let lat = data[0].lat;
                    let lon = data[0].lon;
                    initializeMap(lat, lon);
                } else {
                    alert("Address not found!");
                }
            });
    });

    // Call toggleFields initially to set the correct state
    toggleFields();
});

// Custom form validation
function validateForm() {
    const donationType = document.querySelector("#donation-type").value;

    if (donationType === "monetary") {
        const amount = document.querySelector("#{{ form.amount.id_for_label }}").value;
        const message = document.querySelector("#{{ form.message.id_for_label }}").value;

        if (!amount || !message) {
            alert("Please fill out all required fields for monetary donations.");
            return false;
        }
    } else {
        const itemName = document.getElementById("item-name").value;
        const itemDescription = document.getElementById("item-description").value;
        const itemQuantity = document.getElementById("item-quantity").value;

        if (!itemName || !itemDescription || !itemQuantity) {
            alert("Please fill out all required fields for in-kind donations.");
            return false;
        }
    }

    return true;
}
