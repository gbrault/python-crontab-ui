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

  $(".ui.grey.basic.button").click(function () {
    const id = $(this).val();
    console.log(`Attempting to run job ${id}`);

    $.ajax({
      url: `/run_job/${id}/`,
      type: "GET",
      contentType: "application/json",
      dataType: "json",
      success: function (response) {
        console.log("Success response:", response);
        if (response.success) {
          alert(`✅ ${response.message}`);
        } else {
          alert(`❌ ${response.message}`);
        }
      },
      error: function (xhr, status, error) {
        console.log("Error details:", {
          status: xhr.status,
          statusText: xhr.statusText,
          responseText: xhr.responseText,
          responseJSON: xhr.responseJSON,
          error: error,
          ajaxStatus: status,
        });

        if (xhr.status === 409) {
          // Job already running
          const errorMsg = xhr.responseJSON?.detail || "Job is already running";
          alert(`⚠️ ${errorMsg}`);
        } else if (xhr.status === 404) {
          alert(`❌ Job non trouvé`);
        } else if (xhr.status === 500) {
          const errorMsg = xhr.responseJSON?.detail || "Erreur serveur interne";
          alert(`❌ Erreur serveur: ${errorMsg}`);
        } else if (xhr.status === 0) {
          alert(
            `❌ Erreur réseau: Impossible de contacter le serveur. Vérifiez que l'application est démarrée.`
          );
        } else {
          alert(
            `❌ Une erreur est survenue lors du lancement du job (${xhr.status})`
          );
        }
      },
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
