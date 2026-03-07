
// followup reminder
let followupData = {};
let activeTab = "today";

function openFollowup() {
    document.getElementById("followupPanel").classList.add("open");
    loadFollowups();
}

function closeFollowup() {
    document.getElementById("followupPanel").classList.remove("open");
}

function loadFollowups() {
    fetch("/followups/data/")
        .then(res => res.json())
        .then(data => {
            followupData = data;
            document.getElementById("followupTotal").innerText = data.counts.total;
            document.getElementById("countOverdue").innerText = data.counts.overdue;
            document.getElementById("countToday").innerText = data.counts.today;
            document.getElementById("countUpcoming").innerText = data.counts.upcoming;
            renderList();
        });
}

function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll(".followup-tabs button").forEach(b => b.classList.remove("active"));
    event.target.classList.add("active");
    renderList();
}

function renderList() {
    const list = document.getElementById("followupList");
    list.innerHTML = "";

    const items = followupData[activeTab];

    if (!items.length) {
        list.innerHTML = `<div class="followup-empty">🎉 No follow-ups here</div>`;
        return;
    }

    items.forEach(lead => {
        list.innerHTML += `
            <div class="followup-card">
                <h4>${lead.client_name}</h4>
                <p>📞 ${lead.phone}</p>
                <p>📅 ${lead.event_type}</p>
                <p>⏰ ${lead.follow_up_date}</p>
                <div class="card-actions">
                    <button onclick="openEditLead(${lead.id})">Open Lead</button>
                    <button onclick="markDone(${lead.id})">Mark Done</button>
                </div>
            </div>
        `;
    });
}

function markDone(id) {
    fetch("/followups/done/", {
        method: "POST",
        headers: {
            "X-CSRFToken": document.getElementById("csrf_token").value,
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({ lead_id: id })
    }).then(() => loadFollowups());
}


// notification badge
function loadFollowups() {
    fetch("/followups/data/")
        .then(res => res.json())
        .then(data => {
            followupData = data;

            // PANEL COUNTS
            document.getElementById("followupTotal").innerText = data.counts.total;
            document.getElementById("countOverdue").innerText = data.counts.overdue;
            document.getElementById("countToday").innerText = data.counts.today;
            document.getElementById("countUpcoming").innerText = data.counts.upcoming;

            // 🔔 BADGE UPDATE
            const badge = document.getElementById("followupBadge");
            const total = data.counts.total;

            if (total > 0) {
                badge.innerText = total > 9 ? "9+" : total;
                badge.classList.add("show");
            } else {
                badge.classList.remove("show");
            }

            renderList();
        });
}
// Load badge immediately when page loads
document.addEventListener("DOMContentLoaded", () => {
    loadFollowups();
});

