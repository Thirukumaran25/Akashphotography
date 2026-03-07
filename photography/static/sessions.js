let currentProjectId = null;

/* ===============================
   TAB SWITCHING (SESSIONS)
================================ */
document.addEventListener("DOMContentLoaded", () => {

  document.querySelectorAll(".session-tabs span").forEach(tab => {
    tab.addEventListener("click", () => {
      window.location.href = `/sessions/?tab=${tab.dataset.tab}`;
    });
  });

  const refreshBtn = document.querySelector(".refresh-btn");
  if (refreshBtn) {
    refreshBtn.onclick = () => window.location.href = "/sessions/";
  }
});

/* ===============================
   ASSIGN TEAM CLICK (SAFE)
================================ */
document.addEventListener("click", e => {
  const btn = e.target.closest(".assign-link");
  if (!btn) return;

  e.preventDefault();

  currentProjectId = btn.dataset.project;
  if (!currentProjectId) return;

  openTeamPopupFromSessions(currentProjectId);
});

/* ===============================
   OPEN TEAM POPUP
================================ */
function openTeamPopupFromSessions(projectId) {

  const wrapper = document.querySelector(".team-assign-inline");
  const popup   = document.getElementById("teamAssignPopup");
  const sessionsWrapper = document.querySelector(".sessions-wrapper");

  if (!wrapper || !popup || !sessionsWrapper) {
    console.error("❌ Required popup elements not found");
    return;
  }

  /* 🔥 HIDE SESSIONS */
  sessionsWrapper.style.display = "none";

  /* 🔥 SHOW POPUP */
  wrapper.classList.add("show");
  popup.style.display = "flex";

  fetch(`/projects/details/${projectId}/`)
    .then(res => res.json())
    .then(data => {

      document.getElementById("popupClient").innerText =
        data.client_name || "";

      document.getElementById("popupLocation").innerText =
        data.location || "";

      document.getElementById("popupTime").innerText =
        data.start_session || "";

      document.getElementById("popupDuration").innerText =
        data.event_type || "";

      document.getElementById("popupDates").innerText =
        `${data.start_date} — ${data.end_date}`;
 popup.style.display = "flex";
 console.log(data);
  renderTeamMembers(data);
         document
        .querySelectorAll(".member-pill.selectable:not(.booked)")
        .forEach(pill => {
            console.log(pill.dataset.name)
          const name = pill.dataset.name || "";
          const role = pill.dataset.role || "";
          
          pill.dataset.tooltip = `${name}\n${role}`;
        });
     

      
    
    })
    .catch(err => console.error("❌ Project fetch failed", err));
}
const roleGroupMap = {
  ASSISTANT: "general",
  PHOTOGRAPHER: "pre",
  VIDEOGRAPHER: "pre",
  EDITOR: "post"
};

/* ===============================
   RENDER TEAM MEMBERS
================================ */
function renderTeamMembers(data) {
// const container = document.querySelector('.member-pill selectable');
//   data.general_team.forEach(m => {
//     const pill = document.createElement("span");
//     pill.className = "member-pill selectable";
//     pill.dataset.id = m.id;
//     pill.dataset.name = m.name;
//     pill.dataset.role = m.role;

//     console.log(m.name)

//     pill.innerText = m.name.slice(0,2).toUpperCase();
//     container.appendChild(pill);
//   });
const groups = {
    general: document.querySelector('.pill-row[data-group="general"]'),
    pre: document.querySelector('.pill-row[data-group="pre"]'),
    post: document.querySelector('.pill-row[data-group="post"]')
  };

  // Clear all rows first
  Object.values(groups).forEach(row => row.innerHTML = "");

  if (!data.general_team || data.general_team.length === 0) {
    Object.values(groups).forEach(row => {
      row.innerHTML = `<span class="no-member">No members</span>`;
    });
    return;
  }

  data.general_team.forEach(m => {
    const targetGroup = roleGroupMap[m.role];

    // If role not mapped, skip safely
    if (!targetGroup || !groups[targetGroup]) return;

    const initials = m.name.slice(0, 2).toUpperCase();

    const pill = document.createElement("span");
    pill.className = "member-pill selectable";
    pill.dataset.id = m.id;
    pill.dataset.role = m.role;
    pill.dataset.name = m.name;
    pill.textContent = initials;

    groups[targetGroup].appendChild(pill);
  });

  // Show "No members" only if column is empty
  Object.entries(groups).forEach(([key, row]) => {
    if (!row.children.length) {
      row.innerHTML = `<span class="no-member">No members</span>`;
    }
  });
//       const generalRow = document.querySelector('.pill-row[data-group="general"]');
//   generalRow.innerHTML = "";

//   if (!data.general_team || data.general_team.length === 0) {
//     generalRow.innerHTML = `<span class="no-member">No members</span>`;
//   } else {
//     data.general_team.forEach(m => {
//       const initials = m.name.slice(0, 2).toUpperCase();

//       const pill = document.createElement("span");
//       pill.className = "member-pill selectable";
//       pill.dataset.id = m.id;
//       pill.dataset.role = m.role;
//       pill.dataset.name = m.name;
//       pill.textContent = initials;

//       generalRow.appendChild(pill);
//     });
//   }
//     const post = document.querySelector('.pill-row[data-group="post"]');
//   post.innerHTML = "";

//   if (!data.general_team || data.general_team.length === 0) {
//     post.innerHTML = `<span class="no-member">No members</span>`;
//   } else {
//     data.general_team.forEach(m => {
//       const initials = m.name.slice(0, 2).toUpperCase();

//       const pill = document.createElement("span");
//       pill.className = "member-pill selectable";
//       pill.dataset.id = m.id;
//       pill.dataset.role = m.role;
//       pill.dataset.name = m.name;
//       pill.textContent = initials;

//       post.appendChild(pill);
//     });
//   }
//       const pre = document.querySelector('.pill-row[data-group="pre"]');
//   pre.innerHTML = "";

//   if (!data.general_team || data.general_team.length === 0) {
//     pre.innerHTML = `<span class="no-member">No members</span>`;
//   } else {
//     data.general_team.forEach(m => {
//       const initials = m.name.slice(0, 2).toUpperCase();

//       const pill = document.createElement("span");
//       pill.className = "member-pill selectable";
//       pill.dataset.id = m.id;
//       pill.dataset.role = m.role;
//       pill.dataset.name = m.name;
//       pill.textContent = initials;

//       pre.appendChild(pill);
//     });
//   }
  const bookedRow = document.querySelector(".team-booked .pill-row");
  if (!bookedRow) return;

  bookedRow.innerHTML = "";

  if (!data.booked_members || !data.booked_members.length) {
    bookedRow.innerHTML = `<span class="no-member">No members</span>`;
    return;
  }

  data.booked_members.forEach(m => {
    const pill = document.createElement("span");
    pill.className = "member-pill booked selectable";
    pill.dataset.id = m.id;
    pill.dataset.name = m.name;
    pill.dataset.role = m.role;
    pill.title = m.booked_info || "";

    pill.innerText = m.name
      .split(" ")
      .map(w => w[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

    bookedRow.appendChild(pill);
  });
}
// function renderTeamMembers(data) {
//   const bookedBox = document.querySelector(".team-booked .pill-row");
//   bookedBox.innerHTML = "";

//   data.booked_members.forEach(m => {
//     const pill = document.createElement("span");
//     pill.className = "member-pill booked selectable";
//     pill.dataset.id = m.id;

//     pill.title = `${m.name}\n${m.role}\n${m.booked_info || ""}`;

//     // 👇 initials computed here
//     pill.innerText = m.name
//       .split(" ")
//       .map(w => w[0])
//       .join("")
//       .slice(0, 2)
//       .toUpperCase();

//     bookedBox.appendChild(pill);
//   });
// }
/* ===============================
   TEAM TAB SWITCH
================================ */
document.addEventListener("click", e => {
  const tab = e.target.closest(".figma-tabs span");
  if (!tab) return;

  document.querySelectorAll(".figma-tabs span")
    .forEach(t => t.classList.remove("active"));

  tab.classList.add("active");

  const available = document.querySelector(".team-available");
  const booked = document.querySelector(".team-booked");

  if (!available || !booked) return;

  if (tab.dataset.tab === "available") {
    available.style.display = "block";
    booked.style.display = "none";
  } else {
    available.style.display = "none";
    booked.style.display = "block";
  }
});

/* ===============================
   MEMBER SELECT
================================ */
document.addEventListener("click", e => {
  if (!e.target.classList.contains("member-pill")) return;

  if (e.target.classList.contains("booked")) {
    showWarningToast("⚠ This member is booked on another session");
    return;
  }

  e.target.classList.toggle("selected");
});

/* ===============================
   SEND NOTIFICATION → TASK POPUP
================================ */
function validateAndProceed() {

  const selected = document.querySelectorAll(".member-pill.selected");
  const date = document.querySelector(".figma-date")?.value;

  if (!selected.length) {
    showWarningToast("Please select team members");
    return;
  }

  if (!date) {
    showWarningToast("Date is required");
    return;
  }

  proceedToTasksFromSessions();
}

/* ===============================
   SAVE TEAM → OPEN TASKS
================================ */
function proceedToTasksFromSessions() {

  const members = Array.from(
    document.querySelectorAll(".member-pill.selected")
  ).map(pill => pill.dataset.id);

  fetch("/projects/assign-team/", {
    method: "POST",
    headers: {
      "X-CSRFToken": document.getElementById("csrf_token").value,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      project_id: currentProjectId,
      members: members.join(",")
    })
  })
    .then(data => {
    closeTeamPopup();
     updateSessionCardUI(data.project_id, data);

    document.getElementById("taskPopup").style.display = "flex";
    loadTasks(currentProjectId);
  });
}
function updateSessionCardUI(projectId, data) {
  const card = document.querySelector(
    `.session-card[data-project-id="${projectId}"]`
  );
  if (!card) return;

  card.classList.remove("pending");
  card.classList.add("assigned");

  const badge = card.querySelector(".status-badge");
  if (badge) badge.innerText = "In Progress";

  const assignBox = card.querySelector(".assign-now");
  if (assignBox && data.assigned_team) {
    assignBox.innerHTML = data.assigned_team
      .map(m => `<span class="avatar">${m.name[0]}</span>`)
      .join("");
  }
}



/* ===============================
   CLOSE POPUPS
================================ */
function closeTeamPopup() {

  const wrapper = document.querySelector(".team-assign-inline");
  const popup = document.getElementById("teamAssignPopup");
  const sessionsWrapper = document.querySelector(".sessions-wrapper");

  if (wrapper) wrapper.classList.remove("show");
  if (popup) popup.style.display = "none";
  if (sessionsWrapper) sessionsWrapper.style.display = "block";
}

function closeTaskPopup() {
  document.getElementById("taskPopup").style.display = "none";
}

/* ===============================
   WARNING TOAST
================================ */
function showWarningToast(message) {

  let toast = document.getElementById("warnToast");

  if (!toast) {
    toast = document.createElement("div");
    toast.id = "warnToast";
    toast.style.position = "fixed";
    toast.style.top = "20px";
    toast.style.left = "50%";
    toast.style.transform = "translateX(-50%)";
    toast.style.background = "#b3261e";
    toast.style.color = "#fff";
    toast.style.padding = "10px 18px";
    toast.style.borderRadius = "10px";
    toast.style.zIndex = "10000";
    document.body.appendChild(toast);
  }

  toast.innerText = message;
  toast.style.opacity = "1";

  setTimeout(() => toast.style.opacity = "0", 2000);
}

// function finishAssignment() {
//   closeTaskPopup();
//   window.location.reload();
// }
function finishAssignment() {
  fetch("/projects/update-status/", {
    method: "POST",
    headers: {
      "X-CSRFToken": document.getElementById("csrf_token").value,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      project_id: currentProjectId,
      status: "PRE"
    })
  })
  .then(() => {
    closeTaskPopup();
    window.location.reload(); // UI sync
  });
}





let projectTeam = [];
let pendingTaskUpdates = {};    


function closeTaskPopup() {
    document.getElementById("taskPopup").style.display = "none";
}

/* ================= LOAD TASKS ================= */
function loadTasks(projectId) {
    fetch(`/projects/${projectId}/tasks/`)
        .then(res => res.json())
        .then(data => {
            projectTeam = data.team_members || [];
            renderTasks(data.tasks || {});
        });
}
function setText(element, html) {
  if (!element) return;
  element.innerHTML = html;
}
function updateStatusUI(taskId, status) {
  const statusBox = document.getElementById(`status-${taskId}`);
  if (!statusBox) return;

  // reset classes
  statusBox.className = `dropdown status ${status}`;

  // update label
  statusBox.querySelector(".dropdown-trigger").innerText =
    status.replace("_", " ");
}

function renderTasks(taskGroups) {
  const container = document.getElementById("taskContainer");

  container.innerHTML = `
    <div class="task-table-header">
      <span>Task ID</span>
      <span>Task Name</span>
      <span>Assigned To</span>
      <span>Status</span>
      <span>Start Date</span>
      <span>Due Date</span>
      <span>Progress</span>
      <span>Actions</span>
    </div>
  `;

  Object.keys(taskGroups).forEach(phase => {
    const tasks = taskGroups[phase];

    container.innerHTML += `
      <div class="task-phase-strip">
        📁 ${formatPhase(phase)} (${tasks.length})
      </div>
    `;

    tasks.forEach(task => {
      const assigned = projectTeam.find(m => m.id === task.assigned_to_id);
      const progress = task.progress || 40;

      container.innerHTML += `
        <div class="task-row" data-task-id="${task.id}">

          <!-- ID -->
          <div>${task.code}</div>

          <!-- TITLE -->
          <div>
            <span class="task-title" contenteditable
              oninput="queueUpdate(${task.id},{title:this.innerText})">
              ${task.title}
            </span>
          </div>

          <!-- ASSIGNED -->
          <div>
            <div class="dropdown">
              <div class="dropdown-trigger assigned-box" id="assign-${task.id}">
                ${assigned
                  ? `<span class="avatar">${assigned.name[0]}</span><span>${assigned.name}</span>`
                  : `<span class="unassigned">Unassigned</span>`
                }
              </div>

              <div class="dropdown-menu">
                <div onclick="
                  queueUpdate(${task.id},{assigned_to:''});
                  setText(
                    document.getElementById('assign-${task.id}'),
                    '<span class=unassigned>Unassigned</span>'
                  );
                ">Unassigned</div>

                ${projectTeam.map(m => `
                  <div onclick="
                    queueUpdate(${task.id},{assigned_to:${m.id}});
                    setText(
                      document.getElementById('assign-${task.id}'),
                      '<span class=avatar>${m.name[0]}</span><span>${m.name}</span>'
                    );
                  ">
                    <span class="avatar">${m.name[0]}</span>${m.name}
                  </div>
                `).join("")}
              </div>
            </div>
          </div>

          <!-- STATUS -->
          <div>
            <div class="dropdown status ${task.status}" id="status-${task.id}">
              <div class="dropdown-trigger">
                ${task.status.replace("_"," ")}
              </div>
              <div class="dropdown-menu">
                <div onclick="
                  queueUpdate(${task.id},{status:'OPEN'});
                  updateStatusUI(${task.id}, 'OPEN');
                ">Open</div>

                <div onclick="
                  queueUpdate(${task.id},{status:'ON_HOLD'});
                  updateStatusUI(${task.id}, 'ON_HOLD');
                ">On Hold</div>

                <div onclick="
                  queueUpdate(${task.id},{status:'COMPLETED'});
                  updateStatusUI(${task.id}, 'COMPLETED');
                ">Completed</div>
              </div>
            </div>
          </div>

          <!-- START -->
          <div>
            <input type="date"
              value="${task.start_date || ""}"
              onchange="queueUpdate(${task.id},{start_date:this.value})">
          </div>

          <!-- DUE -->
          <div>
            <input type="date"
              value="${task.due_date || ""}"
              onchange="queueUpdate(${task.id},{due_date:this.value})">
          </div>

          <!-- PROGRESS -->
          <div>
            <div class="progress">
              <span style="width:${progress}%"></span>
            </div>
          </div>

          <!-- ACTIONS -->
          <div class="task-actions">
            <button class="save-btn" onclick="saveTask(${task.id})">✔</button>
            <button class="delete-btn" onclick="deleteTask(${task.id})">🗑</button>
          </div>

        </div>
      `;
    });

    container.innerHTML += `
      <button class="task-add-btn" onclick="addTask('${phase}')">
        + Add Task
      </button>
    `;
  });
}


function queueUpdate(taskId, data) {
  if (!pendingTaskUpdates[taskId]) {
    pendingTaskUpdates[taskId] = {};
  }
  Object.assign(pendingTaskUpdates[taskId], data);
}

/* SAVE ON ✔ CLICK */
function saveTask(taskId) {
  if (!pendingTaskUpdates[taskId]) {
    return;
  }

  fetch("/projects/tasks/update/", {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken(),
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      task_id: taskId,
      ...pendingTaskUpdates[taskId]
    })
  })
  .then(res => res.json())
 .then(() => {
  delete pendingTaskUpdates[taskId];

  const toast = document.getElementById("saveToast");
  toast.classList.add("show");

  setTimeout(() => toast.classList.remove("show"), 1500);

  loadTasks(currentProjectId);
});
}
function applyImmediateUI(taskId, field, value, labelHTML) {
  const row = document.querySelector(`[data-task-id="${taskId}"]`);
  if (!row) return;

  if (field === "assigned_to") {
    row.querySelector(".assigned-box").innerHTML = labelHTML;
  }

  if (field === "status") {
    const statusBox = row.querySelector(".status");
    statusBox.className = `dropdown status ${value}`;
    statusBox.querySelector(".dropdown-trigger").innerText =
      value.replace("_", " ");
  }
}



/* ================= TASK ACTIONS ================= */
function addTask(phase) {
    fetch("/projects/tasks/add/", {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken(),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
            project_id: currentProjectId,
            title: "New Task",
            phase: phase
        })
    }).then(() => loadTasks(currentProjectId));
}

function editTask(id, title) {
    updateTask(id, { title });
}

function assignTask(id, member) {
    updateTask(id, { assigned_to: member });
}

function updateTask(id, data) {
  fetch("/projects/tasks/update/", {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken(),
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      task_id: id,
      ...data
    })
  });
}

function deleteTask(id) {
  fetch("/projects/tasks/delete/", {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken(),
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({ task_id: id })
  }).then(() => loadTasks(currentProjectId));
}



/* ================= HELPERS ================= */
function csrfToken() {
    return document.getElementById("csrf_token").value;
}

function formatPhase(phase) {
    return phase.replace(/_/g, " ")
                .toLowerCase()
                .replace(/\b\w/g, c => c.toUpperCase());
}

