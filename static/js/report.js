document.addEventListener("DOMContentLoaded", function () {
    function setupDropdownFilter(tableId, dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        const rows = document.querySelectorAll(`#${tableId} tbody tr`);

        function updateRows() {
            let numRecords = dropdown.value === "all" ? rows.length : parseInt(dropdown.value);
            rows.forEach((row, index) => {
                row.style.display = index < numRecords ? "" : "none";
            });
        }

        dropdown.value = "5"; // Default selection
        updateRows(); // Apply filter on load
        dropdown.addEventListener("change", updateRows);
    }

    setupDropdownFilter("monetaryTable", "monetaryRecords");
    setupDropdownFilter("kindTable", "kindRecords");
});