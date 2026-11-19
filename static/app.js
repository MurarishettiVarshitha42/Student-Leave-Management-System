document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("sidebar-open");
    });
  }

  document.querySelectorAll(".flash-close").forEach(function (button) {
    button.addEventListener("click", function () {
      button.closest(".flash").remove();
    });
  });

  const showPassword = document.getElementById("showPassword");
  const password = document.getElementById("password");
  if (showPassword && password) {
    showPassword.addEventListener("click", function () {
      const visible = password.type === "text";
      password.type = visible ? "password" : "text";
      showPassword.textContent = visible ? "Show" : "Hide";
    });
  }

  document.querySelectorAll("[data-email]").forEach(function (button) {
    button.addEventListener("click", function () {
      const email = document.getElementById("email");
      const passwordInput = document.getElementById("password");
      if (email && passwordInput) {
        email.value = button.dataset.email;
        passwordInput.value = button.dataset.password;
      }
    });
  });

  const start = document.getElementById("start_date");
  const end = document.getElementById("end_date");
  if (start && end) {
    const today = new Date();
    const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 10);
    start.min = localToday;
    end.min = localToday;
    start.addEventListener("change", function () {
      end.min = start.value || localToday;
      if (end.value && end.value < start.value) {
        end.value = start.value;
      }
    });
  }

  const reason = document.getElementById("reason");
  const charCount = document.getElementById("charCount");
  if (reason && charCount) {
    const updateCount = function () {
      charCount.textContent = reason.value.length + " / 500";
    };
    reason.addEventListener("input", updateCount);
    updateCount();
  }
});

function drawLeaveChart(pending, approved, rejected) {
  const canvas = document.getElementById("leaveChart");
  if (!canvas || typeof Chart === "undefined") return;
  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Pending", "Approved", "Rejected"],
      datasets: [{
        data: [pending, approved, rejected],
        backgroundColor: ["#f5b544", "#2db783", "#ef6b73"],
        borderColor: ["#ffffff", "#ffffff", "#ffffff"],
        borderWidth: 4,
        hoverOffset: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      plugins: {
        legend: { display: false },
        tooltip: { padding: 12, backgroundColor: "#17223b", titleFont: { family: "DM Sans" }, bodyFont: { family: "DM Sans" } }
      }
    }
  });
}
