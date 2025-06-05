function getUnit(nb) {
  const units = ["", "k", "M", "G", "T", "P"];
  let unitIdx = 0;

  while (nb > 1000) {
    nb /= 1000;
    unitIdx++;
  }
  return Math.round(nb) + " " + units[unitIdx];
}

function sum(data) {
  return Object.values(data).reduce((partialSum, a) => partialSum + a, 0);
}

function getCookie(name) {
  // Copy of the code at https://docs.djangoproject.com/fr/3.2/ref/csrf/
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function showChart(elemId, cb, data) {
  const id = elemId + "_loader";
  const loader = document.getElementById(id);
  loader.style.display = "none";
  const chart = document.getElementById(elemId);
  if (chart) {
    chart.style.display = "block";
  }
  if (cb) {
    cb(data);
  }
}

function loadChart(elemId, apiPath, cb) {
  const headers = {
    Accept: "application/json,text/plain",
    "Content-Type": "application/json",
    "X-CSRFToken": getCookie("csrftoken"),
  };

  const response = fetch(apiPath, {
    method: "GET",
    body: null,
    headers,
  })
    .then((response) => response.json())
    .then(function (response) {
      if (document.readyState === "complete") {
        return showChart(elemId, cb, response);
      }
      document.addEventListener("DOMContentLoaded", function (event) {
        return showChart(elemId, cb, response);
      });
    });
}

const colors = ["#253dffd0", "#e71d36d0", "#00d111d0"];
const colorsTransparent = ["#253dff80", "#e71d3680", "#00d11180"];

loadChart("hdd_chart", "/api/hdd_stats/", function (data) {
  const ctx = document.getElementById("hdd_chart");
  const total = sum(data);
  new Chart(ctx, {
    type: "pie",
    data: {
      labels: ["Database", "Screens", "HTML", "Other", "Free"],
      datasets: [
        {
          label: "HDD usage",
          data: [data.db, data.screenshots, data.html, data.other, data.free],
          backgroundColor: colorsTransparent,
          borderColor: colors,
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              return getUnit(context.raw) + "B";
            },
          },
        },
        title: {
          display: true,
          text: `HDD usage (total ${getUnit(total)}B)`,
        },
      },
    },
  });
});

loadChart("lang_chart", "/api/lang_stats/", function (data) {
  showChart("doc_count_panel");

  const langs = data.filter((l) => l.doc_count).slice(0, 8);
  const chart = document.getElementById("lang_chart");
  const langChartJS = new Chart(chart, {
    type: "bar",
    data: {
      labels: langs.map((l) => l.lang),
      datasets: [
        {
          label: "Doc count",
          data: langs.map((l) => l.doc_count),
          backgroundColor: colorsTransparent,
          borderColor: colors,
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      aspectRatio: 1,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              return getUnit(context.raw);
            },
          },
        },
        title: {
          display: true,
          text: "Languages",
        },
      },
    },
  });

  // https://stackoverflow.com/questions/45980436/chart-js-link-to-other-page-when-click-on-specific-section-in-chart
  document.getElementById("lang_chart").onclick = function (e) {
    let bars = langChartJS.getElementsAtEventForMode(
      e,
      "nearest",
      { intersect: true },
      true,
    );
    if (bars.length) {
      const bar = bars[0];
      const lang = langs[bar.index];
      const isoLang = lang.lang.replace(/ .*/, "").toLowerCase();
      window.location = `/admin/se/document/?lang_iso_639_1=${isoLang}`;
    }
  };
});

loadChart("mime_chart", "/api/mime_stats/", function (data) {
  const docCount = sum(data.map((l) => l.doc_count));
  const panel = document.getElementById("doc_count");
  panel.innerHTML = `<div>${docCount}</div><div>🔤 Documents</div>`;

  const mimes = data.filter((m) => m.doc_count);
  const chart = document.getElementById("mime_chart");
  const mimeChartJS = new Chart(chart, {
    type: "pie",
    data: {
      labels: mimes.map((m) => m.mimetype),
      datasets: [
        {
          label: "Mimetype",
          data: mimes.map((m) => m.doc_count),
          backgroundColor: colorsTransparent,
          borderColor: colors,
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function (context) {
              return getUnit(context.raw);
            },
          },
        },
        title: {
          display: true,
          text: "Mimetypes",
        },
        legend: {
          labels: {
            filter: (legendItem, chartData) => legendItem.index < 4,
          },
        },
      },
    },
  });

  // https://stackoverflow.com/questions/45980436/chart-js-link-to-other-page-when-click-on-specific-section-in-chart
  document.getElementById("mime_chart").onclick = function (e) {
    let slices = mimeChartJS.getElementsAtEventForMode(
      e,
      "nearest",
      { intersect: true },
      true,
    );
    if (slices.length) {
      const slice = slices[0];
      const mime = mimes[slice.index];
      const mimeStr = mime.mimetype.replace(/.* /, "").toLowerCase();

      if (mimeStr === "<none>") {
        window.location = `/admin/se/document/?mimetype=`;
      } else {
        const mimeParam = encodeURIComponent(mimeStr);
        window.location = `/admin/se/document/?mimetype=${mimeParam}`;
      }
    }
  };
});

function loadDocCharts(dt) {
  const freq = dt === 24 ? "M" : "D";
  loadChart(
    `doc_count_${dt}_chart`,
    `/api/stats/?freq=${freq}&limit=2000`,
    function (data) {
      if (dt === 24) {
        let urlQueued = 0;
        if (data.results.length) {
          urlQueued = data.results[data.results.length - 1].queued_url;
        }
        const panel = document.getElementById("url_queued");
        panel.innerHTML = `<div>${urlQueued}</div><div><span style="color: #0b0">✔</span> URLs queued</div>`;
        showChart("url_queued_panel");
      }

      const docCount = data.results.map((d) => {
        return { x: luxon.DateTime.fromISO(d.t), y: d.doc_count };
      });
      const docCountChart = document.getElementById(`doc_count_${dt}_chart`);
      new Chart(docCountChart, {
        type: "line",
        data: {
          datasets: [
            {
              label: "Documents",
              data: docCount,
              borderWidth: 1,
              backgroundColor: colorsTransparent[1],
              borderColor: colors[1],
              pointStyle: false,
            },
          ],
        },
        options: {
          scales: {
            x: {
              type: "timeseries",
            },
          },
          aspectRatio: 1,
          maintainAspectRatio: false,
        },
      });

      showChart(`speed_${dt}_chart`);
      const speed = data.results.map((d) => {
        return { x: luxon.DateTime.fromISO(d.t), y: d.indexing_speed };
      });
      const speedChart = document.getElementById(`speed_${dt}_chart`);
      new Chart(speedChart, {
        type: "line",
        data: {
          datasets: [
            {
              label: "Indexing speed",
              data: speed,
              borderWidth: 1,
              backgroundColor: colorsTransparent[2],
              borderColor: colors[2],
              pointStyle: false,
            },
          ],
        },
        options: {
          scales: {
            x: {
              type: "timeseries",
            },
          },
          aspectRatio: 1,
          maintainAspectRatio: false,
          plugins: {
            tooltip: {
              callbacks: {
                label: function (context) {
                  const dtUnit = dt === 24 ? "min" : "day";
                  return `${context.raw.y} doc / ${dtUnit}`;
                },
              },
            },
          },
        },
      });

      showChart(`queue_${dt}_chart`);
      const queue = data.results.map((d) => {
        return { x: luxon.DateTime.fromISO(d.t), y: d.queued_url };
      });
      const queueChart = document.getElementById(`queue_${dt}_chart`);
      new Chart(queueChart, {
        type: "line",
        data: {
          datasets: [
            {
              label: "Crawler queue",
              data: queue,
              borderWidth: 1,
              backgroundColor: colorsTransparent[0],
              borderColor: colors[0],
              pointStyle: false,
            },
          ],
        },
        options: {
          scales: {
            x: {
              type: "timeseries",
            },
          },
          aspectRatio: 1,
          maintainAspectRatio: false,
          plugins: {
            tooltip: {
              callbacks: {
                label: function (context) {
                  return `${context.raw.y} URLs`;
                },
              },
            },
          },
        },
      });
    },
  );
}

loadDocCharts(24);
loadDocCharts(365);
