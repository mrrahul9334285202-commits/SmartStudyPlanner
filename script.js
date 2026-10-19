
const API_URL = "http://127.0.0.1:8000/api";

let sessions = [];
let tasks = [];
let selectedMonth = new Date();
let weeklyChart = null;
let subjectChart = null;

const $ = (id) => document.getElementById(id);

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatMinutes(minutes = 0) {
  const value = Number(minutes) || 0;
  const hours = Math.floor(value / 60);
  const mins = value % 60;
  if (hours && mins) return `${hours}h ${mins}m`;
  if (hours) return `${hours}h`;
  return `${mins} min`;
}

function prettyDate(value) {
  if (!value) return "No date";
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
}

function escapeHTML(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers
      }
    });
  } catch {
    throw new Error("Cannot connect to the backend. Make sure FastAPI is running on port 8000.");
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const detail = data && data.detail
      ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))
      : `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return data;
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 3000);
}

function showMessage(id, message, isError = false) {
  const element = $(id);
  element.textContent = message;
  element.style.color = isError ? "#c34251" : "#16865b";
}

function emptyState(message) {
  return `<div class="empty-state">${escapeHTML(message)}</div>`;
}

async function refreshAll() {
  try {
    const results = await Promise.all([
      api("/sessions"),
      api(`/dashboard?date=${localDateString()}`),
      api(`/calendar?month=${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, "0")}`),
      api("/tasks"),
      api("/analytics/subjects"),
      api("/analytics/daily?days=7"),
      api("/recommendations")
    ]);

    sessions = Array.isArray(results[0]) ? results[0] : [];
    tasks = Array.isArray(results[3]) ? results[3] : [];

    renderDashboard(results[1]);
    renderCalendar(results[2]);
    renderSessions();
    renderTasks();
    renderSubjectAnalytics(results[4]);
    renderWeeklyAnalytics(results[5]);
    renderRecommendations(results[6]);
  } catch (error) {
    showToast(error.message);
    console.error(error);
  }
}

function renderDashboard(data = {}) {
  $("todayLabel").textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric"
  });

  $("todayMinutes").textContent = formatMinutes(data.today_minutes);
  $("totalMinutes").textContent = formatMinutes(data.total_minutes);
  $("totalSessions").textContent = data.total_sessions ?? 0;
  $("activeDays").textContent = data.active_days ?? 0;
}

function renderCalendar(rows = []) {
  const monthName = selectedMonth.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric"
  });
  $("monthLabel").textContent = monthName;

  if (!rows.length) {
    $("calendarSummary").innerHTML = emptyState("No study activity recorded this month.");
    return;
  }

  const normalized = rows.map((row) => ({
    date: row.date,
    minutes: Number(row.minutes ?? row.total_minutes ?? 0)
  }));

  const total = normalized.reduce((sum, row) => sum + row.minutes, 0);
  const activeDays = normalized.length;

  $("calendarSummary").innerHTML = `
    <div class="calendar-row"><span>Monthly study time</span><strong>${formatMinutes(total)}</strong></div>
    <div class="calendar-row"><span>Active study days</span><strong>${activeDays}</strong></div>
    <div class="calendar-row"><span>Daily average (active days)</span><strong>${formatMinutes(Math.round(total / activeDays))}</strong></div>
    <div class="item-list">
      ${normalized.slice(-5).reverse().map((row) => `
        <div class="calendar-row"><span>${prettyDate(row.date)}</span><strong>${formatMinutes(row.minutes)}</strong></div>
      `).join("")}
    </div>
  `;
}

function renderSessions() {
  const container = $("sessionsList");

  if (!sessions.length) {
    container.innerHTML = emptyState("No study sessions yet. Log your first session!");
    return;
  }

  container.innerHTML = sessions.map((session) => `
    <div class="item-row">
      <div class="item-main">
        <div class="item-title">${escapeHTML(session.subject)}</div>
        <div class="item-meta">${formatMinutes(session.minutes)} · ${prettyDate(session.date)}</div>
      </div>
      <div class="item-actions">
        <button class="small-btn" data-action="edit-session" data-id="${session.id}">Edit</button>
        <button class="small-btn danger-btn" data-action="delete-session" data-id="${session.id}">Delete</button>
      </div>
    </div>
  `).join("");
}

function renderTasks() {
  $("taskCount").textContent = `${tasks.length} task${tasks.length === 1 ? "" : "s"}`;

  const pending = tasks.filter((task) => !task.completed);
  const overdue = pending.filter((task) => task.due_date < localDateString());
  $("pendingTasks").textContent = pending.length;
  $("overdueTasks").textContent = overdue.length;

  const container = $("tasksList");
  if (!tasks.length) {
    container.innerHTML = emptyState("No tasks yet. Add your first task to get organized.");
    return;
  }

  container.innerHTML = tasks.map((task) => {
    const isOverdue = !task.completed && task.due_date < localDateString();
    return `
      <div class="item-row ${task.completed ? "done" : ""}">
        <div class="item-main">
          <div class="item-title">${escapeHTML(task.title)}</div>
          <div class="item-meta">${escapeHTML(task.subject)} · Due ${prettyDate(task.due_date)}
            ${isOverdue ? " · OVERDUE" : ""}
          </div>
          <div style="margin-top:7px"><span class="priority ${escapeHTML(task.priority)}">${escapeHTML(task.priority)}</span></div>
        </div>
        <div class="item-actions">
          <button class="small-btn" data-action="toggle-task" data-id="${task.id}" data-completed="${task.completed}">
            ${task.completed ? "Undo" : "Complete"}
          </button>
          <button class="small-btn danger-btn" data-action="delete-task" data-id="${task.id}">Delete</button>
        </div>
      </div>
    `;
  }).join("");
}

function renderSubjectAnalytics(rows = []) {
  const subjects = Array.isArray(rows) ? rows : [];
  const labels = subjects.map((row) => row.subject);
  const values = subjects.map((row) => Number(row.total_minutes) || 0);

  if (subjectChart) subjectChart.destroy();

  const canvas = $("subjectChart");
  if (canvas && window.Chart) {
    subjectChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Study minutes",
          data: values,
          backgroundColor: "#7169ed",
          borderRadius: 6,
          maxBarThickness: 38
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  const container = $("subjectList");
  if (!subjects.length) {
    container.innerHTML = emptyState("Study sessions by subject will appear here.");
    return;
  }

  const maxValue = Math.max(...values, 1);
  container.innerHTML = subjects.map((row) => `
    <div class="item-row">
      <div class="item-main">
        <div class="item-title">${escapeHTML(row.subject)}</div>
        <div class="item-meta">${formatMinutes(row.total_minutes)} · ${row.total_sessions} sessions</div>
        <div class="subject-progress"><span style="width:${Math.max(2, (row.total_minutes / maxValue) * 100)}%"></span></div>
      </div>
    </div>
  `).join("");
}

function renderWeeklyAnalytics(rows = []) {
  const data = Array.isArray(rows) ? rows : [];
  const labels = data.map((row) => {
    const [year, month, day] = row.date.split("-").map(Number);
    return new Date(year, month - 1, day).toLocaleDateString(undefined, { weekday: "short" });
  });
  const values = data.map((row) => Number(row.total_minutes ?? row.minutes) || 0);
  const total = values.reduce((sum, value) => sum + value, 0);
  const activeDays = values.filter((value) => value > 0).length;

  $("weekMinutes").textContent = formatMinutes(total);
  $("dailyAverage").textContent = formatMinutes(activeDays ? Math.round(total / activeDays) : 0);

  if (weeklyChart) weeklyChart.destroy();

  const canvas = $("weeklyChart");
  if (canvas && window.Chart) {
    weeklyChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Minutes studied",
          data: values,
          borderColor: "#5c55df",
          backgroundColor: "rgba(92,85,223,0.12)",
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: "#5c55df"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } },
          x: { grid: { display: false } }
        }
      }
    });
  }
}

function renderRecommendations(data = {}) {
  const recommendations = data.recommendations || [];
  const icons = {
    priority: "!",
    deadline: "◷",
    consistency: "↗",
    progress: "✓",
    subject: "✦"
  };

  $("recommendationsList").innerHTML = recommendations.length
    ? recommendations.map((item) => `
      <article class="recommendation-card">
        <div class="recommendation-icon">${icons[item.type] || "✦"}</div>
        <div><h3>${escapeHTML(
          item.type === "priority" ? "Prioritize overdue work" :
          item.type === "deadline" ? "Deadlines to remember" :
          item.type === "consistency" ? "Build a routine" :
          item.type === "progress" ? "Keep it up" :
          item.type === "subject" ? "Subject suggestion" : "Study tip"
        )}</h3><p>${escapeHTML(item.message)}</p></div>
      </article>
    `).join("")
    : emptyState("Add study sessions and tasks to receive recommendations.");
}

function resetSessionForm() {
  $("sessionForm").reset();
  $("sessionId").value = "";
  $("studyDate").value = localDateString();
  $("sessionFormTitle").textContent = "Log a study session";
  $("saveSessionBtn").textContent = "Save session";
  $("cancelEditBtn").classList.add("hidden");
  showMessage("sessionMessage", "");
}

function beginSessionEdit(id) {
  const session = sessions.find((item) => item.id === Number(id));
  if (!session) return;

  $("sessionId").value = session.id;
  $("subject").value = session.subject;
  $("minutes").value = session.minutes;
  $("studyDate").value = session.date;
  $("sessionFormTitle").textContent = "Edit study session";
  $("saveSessionBtn").textContent = "Update session";
  $("cancelEditBtn").classList.remove("hidden");
  $("sessions").scrollIntoView({ behavior: "smooth" });
}

$("sessionForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const id = $("sessionId").value;
  const payload = {
    subject: $("subject").value.trim(),
    minutes: Number($("minutes").value),
    date: $("studyDate").value
  };

  if (!payload.subject || !payload.date || !Number.isInteger(payload.minutes) ||
      payload.minutes < 1 || payload.minutes > 1440) {
    showMessage("sessionMessage", "Enter a subject, valid date, and 1–1440 minutes.", true);
    return;
  }

  try {
    await api(id ? `/sessions/${id}` : "/sessions", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload)
    });

    resetSessionForm();
    showToast(id ? "Study session updated." : "Study session saved.");
    await refreshAll();
  } catch (error) {
    showMessage("sessionMessage", error.message, true);
  }
});

$("cancelEditBtn").addEventListener("click", resetSessionForm);

$("sessionsList").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit-session") {
    beginSessionEdit(id);
    return;
  }

  if (button.dataset.action === "delete-session") {
    if (!confirm("Delete this study session?")) return;
    try {
      await api(`/sessions/${id}`, { method: "DELETE" });
      showToast("Study session deleted.");
      await refreshAll();
    } catch (error) {
      showToast(error.message);
    }
  }
});

$("taskForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    title: $("taskTitle").value.trim(),
    subject: $("taskSubject").value.trim(),
    due_date: $("dueDate").value,
    priority: $("priority").value
  };

  if (!payload.title || !payload.subject || !payload.due_date) {
    showMessage("taskMessage", "Complete all task fields.", true);
    return;
  }

  try {
    await api("/tasks", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    $("taskForm").reset();
    $("priority").value = "Medium";
    showMessage("taskMessage", "Task created successfully.");
    showToast("Task added.");
    await refreshAll();
  } catch (error) {
    showMessage("taskMessage", error.message, true);
  }
});

$("tasksList").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const id = Number(button.dataset.id);

  try {
    if (button.dataset.action === "toggle-task") {
      const completed = button.dataset.completed === "true";
      await api(`/tasks/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: !completed })
      });
      showToast(completed ? "Task marked as pending." : "Task completed!");
    } else if (button.dataset.action === "delete-task") {
      if (!confirm("Delete this task?")) return;
      await api(`/tasks/${id}`, { method: "DELETE" });
      showToast("Task deleted.");
    }
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
});

$("quickAddBtn").addEventListener("click", () => {
  $("sessions").scrollIntoView({ behavior: "smooth" });
  $("subject").focus({ preventScroll: true });
});

$("prevMonth").addEventListener("click", async () => {
  selectedMonth = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() - 1, 1);
  try {
    const month = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, "0")}`;
    const rows = await api(`/calendar?month=${month}`);
    renderCalendar(rows);
  } catch (error) {
    showToast(error.message);
  }
});

$("nextMonth").addEventListener("click", async () => {
  selectedMonth = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1, 1);
  try {
    const month = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, "0")}`;
    const rows = await api(`/calendar?month=${month}`);
    renderCalendar(rows);
  } catch (error) {
    showToast(error.message);
  }
});

$("refreshRecommendations").addEventListener("click", async () => {
  try {
    renderRecommendations(await api("/recommendations"));
    showToast("Recommendations refreshed.");
  } catch (error) {
    showToast(error.message);
  }
});

document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-link").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

$("studyDate").value = localDateString();
$("dueDate").value = localDateString();
refreshAll();
