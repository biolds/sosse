document.addEventListener("DOMContentLoaded", function () {
  var queueToAny = document.getElementById("id_queue_to_any_collection");
  var queueToSelectionsField = document.querySelector(
    ".field-queue_to_collections",
  );

  if (queueToAny && queueToSelectionsField) {
    function toggleQueueToSelections() {
      if (queueToAny.checked) {
        // Disable the field visually and functionally
        queueToSelectionsField.style.opacity = "0.5";
        queueToSelectionsField.style.pointerEvents = "none";

        // Disable all inputs in the field
        var inputs = queueToSelectionsField.querySelectorAll("input, select");
        inputs.forEach(function (input) {
          input.disabled = true;
        });
      } else {
        // Enable the field visually and functionally
        queueToSelectionsField.style.opacity = "1";
        queueToSelectionsField.style.pointerEvents = "auto";

        // Enable all inputs in the field
        var inputs = queueToSelectionsField.querySelectorAll("input, select");
        inputs.forEach(function (input) {
          input.disabled = false;
        });
      }
    }

    // Initial state
    toggleQueueToSelections();

    // Listen for changes
    queueToAny.addEventListener("change", toggleQueueToSelections);
  }
});
