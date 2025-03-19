document.addEventListener("DOMContentLoaded", function () {
    const searchBox = document.getElementById("searchBox");
    const statusFilter = document.getElementById("statusFilter");
    const numRecordsDropdown = document.getElementById("numRecords");
    const tableRows = document.querySelectorAll("tbody tr");

    function filterTable() {
        const searchText = searchBox.value.toLowerCase();
        const status = statusFilter.value;
        const numRecords = numRecordsDropdown.value === "all" ? tableRows.length : parseInt(numRecordsDropdown.value);

        let visibleCount = 0;
        tableRows.forEach(row => {
            const donor = row.cells[1].textContent.toLowerCase();
            const pickup = row.cells[2].textContent.toLowerCase();
            const item = row.cells[3].textContent.toLowerCase();
            const statusText = row.cells[4].textContent.trim().toLowerCase();

            const matchesSearch = donor.includes(searchText) || pickup.includes(searchText) || item.includes(searchText);
            const matchesStatus = status === "" || statusText === status;

            if (matchesSearch && matchesStatus && visibleCount < numRecords) {
                row.style.display = "";
                visibleCount++;
            } else {
                row.style.display = "none";
            }
        });
    }

    searchBox.addEventListener("keyup", filterTable);
    statusFilter.addEventListener("change", filterTable);
    numRecordsDropdown.addEventListener("change", filterTable);

    filterTable(); // Initial filtering
});