function editing_tags() {
  return Array.from(document.querySelectorAll("#editing_tags .tag.tag-select"))
    .filter((tag) => tag.style.display !== "none")
    .map((tag) => tag.id.split("-")[2])
    .map((tag) => parseInt(tag));
}

async function show_tags(tags_url = null) {
  const tags = document.getElementById("tags");
  const tagsContent = document.getElementById("tags-content");
  const tagsOverlay = document.getElementById("tags-overlay");

  // Show the tags modal
  tags.style.display = "block";
  tags.classList.add("fadeIn");
  tags.classList.remove("fadeOut");
  tagsOverlay.classList.add("fadeIn");
  tagsOverlay.classList.remove("fadeOut");
  tagsOverlay.style.display = "block";
  document.body.style.overflow = "hidden";

  try {
    const _tags_url = tags_url || "/search_tags/" + window.location.search;
    const response = await fetch(_tags_url);
    if (!response.ok) {
      throw new Error("Error loading tags");
    }

    const data = await response.text();

    tagsContent.innerHTML = data;
  } catch (error) {
    console.error("Error:", error);
    tagsContent.innerHTML = "Failed to load tags.";
  }

  // Display tags that are currently selected in the edit bar
  if (tags_url) {
    const django_admin = window.location.pathname.startsWith("/admin/se/");
    const selectedTags = django_admin
      ? document.querySelectorAll(".field-tags .tag.tag-select")
      : document.querySelectorAll("#document_tags .tag.tag-select");
    selectedTags.forEach((tag) => {
      const tagId = tag.id.split("-")[2];
      const tagElement = document.getElementById(`tag-${tagId}`);
      tagElement.style.fontWeight = "bold";
      const activeTag = document.getElementById(`tag-edit-${tagId}`);
      activeTag.style.fontWeight = "bold";
      activeTag.style.display = "inline-block";
    });
  } else {
    // Set a bold font-weight on all tags that are active
    const activeTags = document.getElementById("editing_tags");
    activeTags.childNodes.forEach((activeTag) => {
      if (
        activeTag.nodeName === "SPAN" &&
        activeTag.className.includes("tag") &&
        !activeTag.className.includes("tag-action")
      ) {
        if (activeTag.style.display !== "none") {
          const tagId = activeTag.id.split("-")[2];
          const tag = document.getElementById(`tag-${tagId}`);
          tag.style.fontWeight = "bold";
        }
      }
    });
  }

  // Set the return url for Create button
  document.querySelectorAll(".create-tag").forEach((createButton) => {
    const link = createButton.getElementsByTagName("a")[0];
    link.href = `${link.href}?return_url=${encodeURIComponent(
      window.location.pathname + window.location.search,
    )}`;
  });

  const counts_url = "/api/tag/tree_doc_counts/";
  const response = await fetch(counts_url);
  if (!response.ok) {
    throw new Error("Error loading counters");
  }

  const data = await response.json();

  const tagsList = document.querySelectorAll("#tags_list span.tag");
  tagsList.forEach((tag) => {
    const tagId = tag.id.split("-")[1];
    const count = data[tagId];
    if (count !== undefined) {
      const counter = tag.querySelectorAll("span.tag-counter")[0];
      counter.innerHTML = count.human_count;
    }
  });
}

async function switch_tag(tagId) {
  const tagEdit = document.evaluate(
    `//div[@id='tags-content']//span[@id='tag-edit-${tagId}']`,
    document,
    null,
    XPathResult.FIRST_ORDERED_NODE_TYPE,
    null,
  ).singleNodeValue;
  const tag = document.evaluate(
    `//div[@id='tags-content']//span[@id='tag-${tagId}']`,
    document,
    null,
    XPathResult.FIRST_ORDERED_NODE_TYPE,
    null,
  ).singleNodeValue;

  if (tagEdit.style.display === "none") {
    tagEdit.style.display = "inline-block";
    tag.style.fontWeight = "bold";
  } else {
    tagEdit.style.display = "none";
    tag.style.removeProperty("font-weight");
  }
}

async function clear_tags() {
  editing_tags().forEach((tag) => {
    switch_tag(tag);
  });
}

function submit_search() {
  const tags = editing_tags();
  const searchParams = new URLSearchParams(window.location.search);
  searchParams.delete("tag");

  // Remove all existing tags from the search query
  let params = searchParams.toString();
  if (params) {
    params += "&";
  }
  params += tags.map((tag) => `tag=${tag}`).join("&");

  window.location.href = `/s/?${params}`;
}

async function save_tags(_tagsListUrl = null, saveUrl = null) {
  const tags = editing_tags();
  const tagsParam = tags.length
    ? "&" + tags.map((tag) => `tag=${tag}`).join("&")
    : "";
  const tagsListUrl = `${_tagsListUrl}${tagsParam}`;

  const admin_ui = window.location.pathname.startsWith("/admin/se/");
  const target = admin_ui
    ? document.evaluate(
        "//div[@class='form-row field-tags']/div/div",
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null,
      ).singleNodeValue
    : document.getElementById("document_tags");

  try {
    const response = await fetch(tagsListUrl);
    if (!response.ok) {
      throw new Error("Error loading tags");
    }
    const data = await response.text();

    target.innerHTML = data;
  } catch (error) {
    console.error("Error:", error);
    target.innerHTML = "Failed to load tags.";
  }

  if (saveUrl) {
    const csrfToken = document
      .querySelector('meta[name="csrf-token"]')
      .getAttribute("content");
    const response = await fetch(saveUrl, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        tags,
      }),
    });

    if (!response.ok) {
      throw new Error("Error saving tags");
    }
  }
  close_modal();
}

function close_modal() {
  const tags = document.getElementById("tags");
  const tagsOverlay = document.getElementById("tags-overlay");
  let animationDuration = getComputedStyle(document.body).getPropertyValue(
    "--animation-duration",
  );

  if (animationDuration.endsWith("ms")) {
    animationDuration = parseFloat(animationDuration);
  } else if (animationDuration.endsWith("s")) {
    animationDuration = parseFloat(animationDuration) * 1000;
  }

  setTimeout(() => {
    tags.style.display = "none";
    tagsOverlay.style.display = "none";
    document.body.style.overflow = "";
  }, animationDuration);
  tags.classList.remove("fadeIn");
  tags.classList.add("fadeOut");
  tagsOverlay.classList.remove("fadeIn");
  tagsOverlay.classList.add("fadeOut");
}

document.addEventListener("DOMContentLoaded", function () {
  window.onclick = function (event) {
    const tagsOverlay = document.getElementById("tags-overlay");

    if (event.target == tagsOverlay) {
      close_modal();
    }
  };
});
