// JavaScript vanilla moderne - pas de jQuery nécessaire
document.addEventListener("DOMContentLoaded", function () {
  // Bouton "Add Job" - ouvre le modal
  const addJobBtn = document.getElementById("add_job");
  if (addJobBtn) {
    addJobBtn.addEventListener("click", function () {
      const modal = document.querySelector(".ui.modal");
      if (modal) {
        modal.classList.add("visible", "active");
        document.body.classList.add("dimmable", "dimmed");
      }
    });
  }

  // Boutons "Delete" (rouge)
  document.querySelectorAll(".ui.inverted.red.button").forEach((button) => {
    button.addEventListener("click", function () {
      if (confirm("Are you sure you want delete this job?")) {
        const id = this.value;
        fetch(`job/${id}/`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
        })
          .then(() => alert("Job Deleted!. Please Reload"))
          .catch((error) => alert(`Error: ${error.message}`));
      }
    });
  });

  // Boutons "Run Now" (gris)
  document.querySelectorAll(".ui.grey.basic.button").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const id = this.value;
      console.log(`Attempting to run job ${id}`);
      console.log(`URL: ${window.location.origin}/run_job/${id}/`);

      fetch(`/run_job/${id}/`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-cache",
      })
        .then((response) => {
          console.log("Response status:", response.status);
          return response.json().then((data) => ({
            status: response.status,
            data: data,
            ok: response.ok,
          }));
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
  });

  // Bouton "Save" - créer un job
  const saveBtn = document.getElementById("save");
  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      const command = document.getElementById("command").value;
      const command_name = document.getElementById("command_name").value;
      const schedule = document.getElementById("schedule").value;

      if (command === "" || command_name === "" || schedule === "") {
        alert("You must fill out all fields");
      } else {
        fetch("/create_job/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            command: command,
            name: command_name,
            schedule: schedule,
          }),
        })
          .then((response) => {
            if (response.status === 404) {
              alert("Make sure the cron expression is valid.");
            }
            return response.json();
          })
          .then(() => {
            // Fermer le modal
            const modal = document.querySelector(".ui.modal");
            if (modal) {
              modal.classList.remove("visible", "active");
              document.body.classList.remove("dimmable", "dimmed");
            }
            location.reload(); // Recharger pour voir le nouveau job
          })
          .catch((error) => console.error("Error:", error));
      }
    });
  }

  // Bouton "Update" - mettre à jour un job
  const updateBtn = document.getElementById("update");
  if (updateBtn) {
    updateBtn.addEventListener("click", function () {
      const id = this.value;
      const command = document.getElementById("command").value;
      const command_name = document.getElementById("command_name").value;
      const schedule = document.getElementById("schedule").value;

      if (command === "" || command_name === "" || schedule === "") {
        alert("You must fill out all fields");
      } else {
        fetch(`/update_job/${id}/`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            command: command,
            name: command_name,
            schedule: schedule,
          }),
        })
          .then((response) => {
            if (response.status === 500) {
              alert("Make sure the cron expression is valid.");
            }
            return response.json();
          })
          .then(() => location.reload())
          .catch((error) => console.error("Error:", error));
      }
    });
  }

  // Popups pour les custom buttons (si nécessaire)
  document.querySelectorAll(".custom.button").forEach((button) => {
    button.addEventListener("click", function () {
      const popup = this.nextElementSibling;
      if (popup && popup.classList.contains("custom.popup")) {
        popup.classList.toggle("visible");
      }
    });
  });

  // Bouton "Clear Logs" - efface les logs
  const clearLogsBtn = document.getElementById("clear-logs");
  if (clearLogsBtn) {
    clearLogsBtn.addEventListener("click", function () {
      if (!confirm("Are you sure you want to clear all logs for this job?")) {
        return;
      }

      const jobId = this.getAttribute("data-job-id");
      console.log(`Clearing logs for job ${jobId}`);

      fetch(`/clear_logs/${jobId}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            alert("✅ " + data.message);
            // Vider l'affichage des logs
            const logOutput = document.getElementById("log-output");
            if (logOutput) {
              logOutput.textContent = "";
            }
          } else {
            alert("❌ Failed to clear logs");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert(`❌ Error: ${error.message}`);
        });
    });
  }

  // Bouton "Refresh Logs" - recharge les logs
  const refreshLogsBtn = document.getElementById("refresh-logs");
  if (refreshLogsBtn) {
    refreshLogsBtn.addEventListener("click", function () {
      const jobId = this.getAttribute("data-job-id");
      console.log(`Refreshing logs for job ${jobId}`);

      fetch(`/refresh_logs/${jobId}/`, {
        method: "GET",
        headers: { Accept: "application/json" },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            // Mettre à jour l'affichage des logs
            const logOutput = document.getElementById("log-output");
            if (logOutput) {
              logOutput.textContent = data.log_content;
            }
            console.log("Logs refreshed successfully");
          } else {
            alert("❌ Failed to refresh logs");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert(`❌ Error: ${error.message}`);
        });
    });
  }
});
