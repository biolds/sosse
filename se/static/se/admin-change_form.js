// Warn on unsaved changes

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("content-main");
  if (!form) return;

  const initialData = {};
  const inputs = form.querySelectorAll("input, textarea, select");

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

  const changed = (input) => {
    if (input.getAttribute("placeholder") === "Filter") {
      // Ignore the "Filter" input fields of ManyToManyFields
      return false;
    }

    if (input.type === "checkbox") {
      return input.checked !== initialData[input.name];
    } else if (input.tagName === "SELECT" && input.multiple) {
      // For forms.ModelMultipleChoiceField, the initial widget is renamed into
      // <name>_old, since JS code transforms the initial <select> into 2 separate
      if (input.name.endsWith("_old")) {
        return false;
      }

      const newElem = document.getElementsByName(input.name)[0];
      let currentValues = Array.from(newElem.options)
        .map((option) => option.value)
        .sort();

      return (
        JSON.stringify(currentValues) !==
        JSON.stringify(initialData[input.name])
      );
    }
    return input.value !== initialData[input.name];
  };
  const hasUnsavedChanges = () => {
    const inputs = form.querySelectorAll("input, textarea, select");
    return Array.from(inputs).some((input) => {
      return changed(input);
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
