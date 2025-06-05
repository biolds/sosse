function selectTab(fieldset, tabButton) {
  const form = document.getElementById("content-main").childNodes[3];
  const fields = form.childNodes[3];
  fields.childNodes.forEach((fields, fieldNo) => {
    if (fields.tagName !== "FIELDSET") {
      return;
    }
    fields.style = "display: none";
  });
  const tabs = document.getElementById("tabs");
  tabs.childNodes.forEach((node) => {
    if (node.tagName !== "A") {
      return;
    }
    node.setAttribute("href", "#");
    node.removeAttribute("id");
  });

  tabButton.removeAttribute("href");
  tabButton.id = "tab_selected";
  fieldset.style = "display: block";

  // Update the height of ManyToMany fields
  // This is based on django/contrib/admin/static/admin/js/SelectFilter2.js
  document.querySelectorAll("select.filtered").forEach(function (el) {
    const field_id = el.id.substr(0, el.id.length - 5); // drop the suffix from "<element_id>_from"
    const j_from_box = document.getElementById(field_id + "_from");
    const j_to_box = document.getElementById(field_id + "_to");
    const filter_p = document.getElementById(field_id + "_filter");
    if (filter_p === null) {
      return;
    }
    let height = filter_p.offsetHeight + j_from_box.offsetHeight;

    const j_to_box_style = window.getComputedStyle(j_to_box);
    if (j_to_box_style.getPropertyValue("box-sizing") === "border-box") {
      // Add the padding and border to the final height.
      height +=
        parseInt(j_to_box_style.getPropertyValue("padding-top"), 10) +
        parseInt(j_to_box_style.getPropertyValue("padding-bottom"), 10) +
        parseInt(j_to_box_style.getPropertyValue("border-top-width"), 10) +
        parseInt(j_to_box_style.getPropertyValue("border-bottom-width"), 10);
    }

    j_to_box.style.height = height + "px";
  });
}

document.addEventListener("DOMContentLoaded", function (event) {
  if (document.getElementsByTagName("fieldset").length > 1) {
    let fieldsetToSelect = null;
    let tabToSelect = null;

    const form = document.getElementById("content-main").childNodes[3];
    if (form) {
      const fields = form.childNodes[2];

      // Move the "Authentication fields" under the Authentication fieldset
      const authfields = document.getElementById("authfield_set-group");
      if (authfields) {
        authfields.remove(); // removed here, it is re-added at the end of the loop below
      }

      // Create tabs
      const tabs = document.createElement("div");
      tabs.id = "tabs";
      tabs.style = "margin: 20px 0px 20px 0px";

      let fieldsetsCount = 0;
      const fieldsets = [];
      fields.childNodes.forEach((fieldset) => {
        if (fieldset.tagName === "FIELDSET") {
          fieldsets.push(fieldset);
        }
      });

      fieldsets.forEach((fieldset, fieldNo) => {
        const h2 = fieldset.getElementsByTagName("h2")[0];
        const tabButton = document.createElement("a");
        tabButton.setAttribute("href", "#");
        tabButton.classList.add("tab_link");
        tabButton.innerText = h2.innerText;
        tabButton.onclick = () => {
          selectTab(fieldset, tabButton);
        };
        h2.remove();
        tabs.append(tabButton);

        if (
          fieldsetToSelect === null &&
          fieldset.getElementsByClassName("errors").length
        ) {
          fieldsetToSelect = fieldset;
          tabToSelect = tabButton;
        }

        if (tabButton.innerText === "🔒 Authentication" && authfields) {
          fieldset.append(authfields);
        }
      });

      form.prepend(tabs);
      if (fieldsetToSelect === null) {
        fieldsetToSelect = fieldsets[0];
        tabToSelect = tabs.childNodes[0];
      }
      selectTab(fieldsetToSelect, tabToSelect);
    }
  }
});
