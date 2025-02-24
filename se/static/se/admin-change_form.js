// Warn on unsaved changes

document.addEventListener("DOMContentLoaded", function () {
  let form = document.getElementById("content-main");
  if (!form) return;

  let initialData = {};
  let inputs = form.querySelectorAll("input, textarea, select");

  inputs.forEach((input) => {
    if (input.type === "checkbox") {
      initialData[input.name] = input.checked;
    } else if (input.tagName === "SELECT" && input.multiple) {
      initialData[input.name] = Array.from(input.options)
        .filter((option) => option.selected)
        .map((option) => option.value)
        .sort();
    } else {
      initialData[input.name] = input.value;
    }
  });

  let hasUnsavedChanges = () => {
    return Array.from(inputs).some((input) => {
      if (input.type === "checkbox") {
        return input.checked !== initialData[input.name];
      } else if (input.tagName === "SELECT" && input.multiple) {
        // For forms.ModelMultipleChoiceField, the initial widget is renamed into
        // <name>_old, since JS code transforms the initial <select> into 2 separate
        const name = input.name.substr(0, input.name.length - 4);
        const newElem = document.getElementsByName(name)[0];
        let currentValues = Array.from(newElem.options)
          .map((option) => option.value)
          .sort();

        return (
          JSON.stringify(currentValues) !== JSON.stringify(initialData[name])
        );
      }
      return input.value !== initialData[input.name];
    });
  };

  let warnOnUnsavedChanges = (event) => {
    if (hasUnsavedChanges()) {
      event.preventDefault();
      event.returnValue = "";
    }
  };

  window.addEventListener("beforeunload", warnOnUnsavedChanges);

  // Save buttons should not warn about unsaved changes
  form.addEventListener("submit", function (event) {
    let submitButton = event.submitter;

    if (submitButton && submitButton.name === "action") {
      // Action buttons should trigger the warning
      return;
    }

    window.removeEventListener("beforeunload", warnOnUnsavedChanges);
  });
});
