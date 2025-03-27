document.addEventListener("DOMContentLoaded", function () {
    const numRecordsDropdown = document.getElementById("numRecords");
    const tableRows = document.querySelectorAll("#donationsTable tbody tr");

    function updateTableRows() {
      let numRecords = numRecordsDropdown.value === "all" ? tableRows.length : parseInt(numRecordsDropdown.value);
      
      tableRows.forEach((row, index) => {
        row.style.display = index < numRecords ? "" : "none";
      });
    }

    // Initial table filtering
    updateTableRows();

    // Listen for dropdown changes
    numRecordsDropdown.addEventListener("change", updateTableRows);
  });