$(document).ready(function () {
  $("#add_job").click(function () {
    $(".ui.modal").modal("show");
  });

  $(".ui.inverted.red.button").click(function () {
    if (confirm("Are you sure you want delete this job?")) {
      const id = $(this).val();
      $.ajax({
        url: `job/${id}/`,
        type: "DELETE",
        contentType: "application/json",
      });
      alert("Job Deleted!. Please Reload");
    }
  });

  $(".ui.grey.basic.button").click(function (e) {
    e.preventDefault(); // Empêcher tout comportement par défaut
    const id = $(this).val();
    console.log(`Attempting to run job ${id}`);
    console.log(`URL: ${window.location.origin}/run_job/${id}/`);

    // Utiliser fetch au lieu de $.ajax pour meilleure compatibilité Firefox
    fetch(`/run_job/${id}/`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      cache: "no-cache",
    })
      .then((response) => {
        console.log("Response status:", response.status);
        console.log("Response headers:", response.headers);
        
        // Lire le JSON même en cas d'erreur
        return response.json().then((data) => {
          return { status: response.status, data: data, ok: response.ok };
        });
      })
      .then(({ status, data, ok }) => {
        console.log("Parsed response:", { status, data, ok });
        
        if (ok && data.success) {
          alert(`✅ ${data.message}`);
        } else if (status === 409) {
          alert(`⚠️ ${data.detail || "Job already running"}`);
        } else if (status === 404) {
          alert(`❌ Job non trouvé`);
        } else if (status === 500) {
          alert(`❌ Erreur serveur: ${data.detail || "Erreur interne"}`);
        } else {
          alert(`❌ ${data.message || data.detail || "Erreur inconnue"}`);
        }
      })
      .catch((error) => {
        console.error("Fetch error:", error);
        alert(`❌ Erreur réseau: ${error.message}`);
      });
  });

  $("#save").click(function () {
    const command = $("#command").val();
    const command_name = $("#command_name").val();
    const schedule = $("#schedule").val();

    if (command === "" || command_name === "" || schedule === "") {
      alert("You must fill out all fields");
    } else {
      $.ajax({
        url: "/create_job/",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
          command: command,
          name: command_name,
          schedule: schedule,
        }),
        statusCode: {
          404: function () {
            // No content found (404)
            // This code will be executed if the server returns a 404 response
            alert("Make sure the cron expression is valid.");
          },
        },
        dataType: "json",
      });
    }

    $(".ui.modal").modal("hide");
  });

  $("#update").click(function () {
    const id = $(this).val();
    const command = $("#command").val();
    const command_name = $("#command_name").val();
    const schedule = $("#schedule").val();

    if (command === "" || command_name === "" || schedule === "") {
      alert("You must fill out all fields");
    } else {
      $.ajax({
        url: `/update_job/${id}/`,
        type: "PUT",
        contentType: "application/json",
        data: JSON.stringify({
          command: command,
          name: command_name,
          schedule: schedule,
        }),
        statusCode: {
          500: function () {
            // No content found (404)
            // This code will be executed if the server returns a 404 response
            alert("Make sure the cron expression is valid.");
          },
        },
        dataType: "json",
      });
    }
  });

  $(".custom.button").popup({
    popup: $(".custom.popup"),
    on: "click",
    inline: true,
  });
});
