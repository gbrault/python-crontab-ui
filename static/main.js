// JavaScript vanilla moderne - pas de jQuery nécessaire
document.addEventListener("DOMContentLoaded", function () {
  // Toggle pour activer/désactiver les jobs
  document.querySelectorAll(".job-toggle").forEach((toggle) => {
    toggle.addEventListener("change", function () {
      const jobId = this.getAttribute("data-job-id");
      const isChecked = this.checked;
      const row = this.closest("tr");
      const runButton = row.querySelector(".ui.grey.basic.button");

      console.log(
        `Toggling job ${jobId} to ${isChecked ? "active" : "inactive"}`
      );

      fetch(`/toggle_job/${jobId}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            console.log(`Job ${jobId} toggled successfully:`, data);

            // Mettre à jour l'apparence de la ligne
            if (data.is_active) {
              row.classList.remove("disabled-job");
              if (runButton) runButton.disabled = false;
            } else {
              row.classList.add("disabled-job");
              if (runButton) runButton.disabled = true;
            }

            // Recharger pour mettre à jour le "Next Run"
            setTimeout(() => location.reload(), 500);
          } else {
            alert(`❌ ${data.message || "Unknown error"}`);
            // Remettre le toggle à son état précédent
            toggle.checked = !isChecked;
          }
        })
        .catch((error) => {
          console.error("Error toggling job:", error);
          alert(`❌ Error: ${error.message}`);
          // Remettre le toggle à son état précédent
          toggle.checked = !isChecked;
        });
    });
  });

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

  // Fonction pour fermer le modal
  function closeModal() {
    const modal = document.querySelector(".ui.modal");
    if (modal) {
      modal.classList.remove("visible", "active");
      document.body.classList.remove("dimmable", "dimmed");
    }
  }

  // Bouton de fermeture (X) du modal
  const closeIcon = document.querySelector(".ui.modal .close.icon");
  if (closeIcon) {
    closeIcon.addEventListener("click", closeModal);
  }

  // Fermer en cliquant en dehors du modal (sur le fond sombre)
  document.addEventListener("click", function (e) {
    const modal = document.querySelector(".ui.modal");
    if (modal && modal.classList.contains("visible")) {
      // Si le clic est sur le body.dimmed mais pas sur le modal
      if (
        document.body.classList.contains("dimmed") &&
        !modal.contains(e.target) &&
        e.target !== addJobBtn
      ) {
        closeModal();
      }
    }
  });

  // Fermer avec la touche Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeModal();
    }
  });

  // Boutons "Delete" (poubelle)
  document.querySelectorAll(".delete-btn").forEach((button) => {
    button.addEventListener("click", function () {
      if (confirm("Are you sure you want to delete this job?")) {
        const id = this.value;
        fetch(`job/${id}/`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
        })
          .then(() => {
            alert("✅ Job deleted!");
            location.reload();
          })
          .catch((error) => alert(`❌ Error: ${error.message}`));
      }
    });
  });

  // Boutons "Run Now" (play)
  document.querySelectorAll(".run-btn").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      const id = this.value;
      console.log(`Attempting to run job ${id}`);

      if (!id) {
        console.error("No job ID found");
        alert("❌ Error: Job ID not found");
        return;
      }

      fetch(`/run_job/${id}/`, {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        cache: "no-cache",
        credentials: "same-origin",
      })
        .then((response) => {
          console.log("Response status:", response.status);
          if (!response.ok && response.status !== 409) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
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
            alert(`❌ Job not found`);
          } else if (status === 500) {
            alert(`❌ Server error: ${data.detail || "Internal error"}`);
          } else {
            alert(`❌ ${data.message || data.detail || "Unknown error"}`);
          }
        })
        .catch((error) => {
          console.error("Fetch error:", error);
          alert(
            `❌ Network error: ${error.message}\n\nCheck the console (F12) for more details.`
          );
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
            closeModal();
            location.reload(); // Recharger pour voir le nouveau job
          })
          .catch((error) => console.error("Error:", error));
      }
    });
  }

  // Bouton "Cancel" - fermer le modal
  const cancelBtn = document.getElementById("cancel");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", closeModal);
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

  // Popups "Show Command" - toggle visibility
  document.querySelectorAll(".custom.button").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation();

      // Trouver le popup qui suit directement ce bouton
      const popup = this.nextElementSibling;

      if (
        popup &&
        popup.classList.contains("custom") &&
        popup.classList.contains("popup")
      ) {
        // Fermer tous les autres popups
        document.querySelectorAll(".custom.popup.visible").forEach((p) => {
          if (p !== popup) {
            p.classList.remove("visible");
          }
        });

        // Toggle ce popup
        popup.classList.toggle("visible");

        // Positionner le popup
        const rect = this.getBoundingClientRect();
        popup.style.position = "absolute";
        popup.style.top = rect.bottom + 5 + "px";
        popup.style.left = rect.left + "px";
        popup.style.zIndex = "1000";
      }
    });
  });

  // Fermer les popups si on clique ailleurs
  document.addEventListener("click", function (e) {
    if (
      !e.target.classList.contains("custom") ||
      !e.target.classList.contains("button")
    ) {
      document.querySelectorAll(".custom.popup.visible").forEach((popup) => {
        popup.classList.remove("visible");
      });
    }
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
