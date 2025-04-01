function test_webhook() {
  var webhookData = {};
  var form = document.getElementById("webhook_form");

  form.querySelectorAll("input, select, textarea").forEach(function (input) {
    if (input.name && input.id.substr(0, 3) === "id_") {
      webhookData[input.name] = input.value;
    }
  });

  var resultDiv = document.getElementById("webhook_test_result");
  if (!resultDiv) {
    resultDiv = document.createElement("div");
    resultDiv.id = "webhook_test_result";
    resultDiv.style.width = "100%";
    resultDiv.style.marginTop = "10px";

    var webhookTestField = document.getElementById("webhook_test_button");
    webhookTestField.parentElement.appendChild(resultDiv);
  }

  resultDiv.innerHTML = "Processing request...";
  var payload = JSON.stringify(webhookData);

  fetch("/api/webhook/test_trigger/?as_html=1", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
    body: payload,
  })
    .then((response) => {
      console.log(response);
      if (response.status !== 200) {
        throw new Error(
          `HTTP error! status: ${response.status} : ${response.statusText}`,
        );
      }
      response.text().then((body) => {
        resultDiv.innerHTML = body;
      });
    })
    .catch((error) => {
      resultDiv.value = `Error: ${error}`;
      console.error("Error:", error);
    });
}
