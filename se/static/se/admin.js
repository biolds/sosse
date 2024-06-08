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
        authfields.remove(); // removed here, it is re-added at the end of the loop beolw
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

        if (fieldNo === fieldsets.length - 1 && authfields) {
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
