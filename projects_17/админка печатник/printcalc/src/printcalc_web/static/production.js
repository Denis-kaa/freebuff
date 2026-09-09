/* Производство: доска заданий, выполнение с обязательным чек-листом (Этап 4). */

"use strict";

const $ = (sel) => document.querySelector(sel);

let tasks = [];
let currentTask = null;
let currentFilter = "";

async function apiFetch(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "ошибка запроса");
  return data;
}

const esc = (text) => {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
};

const STATUS = {
  pending: "ожидает",
  in_progress: "в работе",
  done: "готово",
  blocked: "блок",
};

function statusPill(status) {
  return `<span class="pill pill-${status === "in_progress" ? "sent" : status === "done" ? "accepted" : status === "blocked" ? "rejected" : "draft"}">${STATUS[status] || status}</span>`;
}

async function loadTasks() {
  const params = currentFilter ? "?status=" + currentFilter : "";
  const data = await apiFetch("/production/tasks" + params);
  tasks = data.tasks;
  renderTasks();
  // подсветка активного фильтра
  document.querySelectorAll(".pill-filter").forEach((b) =>
    b.classList.toggle("active", (b.dataset.filter || "") === currentFilter)
  );
}

function renderTasks() {
  const body = $("#tasks-body");
  if (!tasks.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Заданий нет — они создаются кнопкой «В производство» из карточки заказа</td></tr>';
    return;
  }
  body.innerHTML = tasks
    .map(
      (t) => `<tr data-id="${t.id}" style="cursor:pointer">
        <td><b>${t.order_id}</b></td>
        <td>${t.sequence}</td>
        <td>${esc(t.operation ? t.operation.name : "?")}</td>
        <td class="muted">${esc((t.operation && t.operation.equipment) || "—")}</td>
        <td class="num">${t.operation ? t.operation.minutes : "—"}</td>
        <td>${statusPill(t.status)}</td>
        <td><button class="icon" data-open="${t.id}" title="Открыть">›</button></td>
      </tr>`
    )
    .join("");
}

document.querySelectorAll(".pill-filter").forEach((button) =>
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter || "";
    loadTasks().catch(showError);
  })
);

document.addEventListener("click", (event) => {
  const openId = event.target.getAttribute && event.target.getAttribute("data-open");
  if (openId) openTask(Number(openId));
  if (event.target.matches("[data-close]")) event.target.closest("dialog").close();
});

function showError(error) {
  $("#tasks-error").textContent = error.message;
}

/* ---------- диалог задания ---------- */

async function openTask(id) {
  try {
    currentTask = tasks.find((t) => t.id === id) || (await apiFetch("/production/tasks")).tasks.find((t) => t.id === id);
  } catch (error) {
    showError(error);
    return;
  }
  const t = currentTask;
  $("#task-order").textContent = t.order_id;
  $("#task-op-name").textContent = t.operation ? t.operation.name : "";
  const steps = t.operation && t.operation.steps ? t.operation.steps : [];
  const checklist = t.operation && t.operation.checklist ? t.operation.checklist : [];
  $("#task-body").innerHTML =
    (steps.length ? "<ol>" + steps.map((s) => `<li>${esc(s)}</li>`).join("") + "</ol>" : "") +
    `<p class="muted" style="margin:0">Статус: ${STATUS[t.status] || t.status}${t.started_at ? " · начато " + esc(t.started_at.slice(0, 16).replace("T", " ")) : ""}${t.completed_at ? " · завершено " + esc(t.completed_at.slice(0, 16).replace("T", " ")) : ""}</p>`;

  // Чек-лист: чекбоксы; уже завершённое задание показывает результат.
  const saved = t.checklist || [];
  $("#task-checklist").innerHTML = checklist.length
    ? "<b>Чек-лист (§10: всё обязано быть отмечено):</b>" +
      checklist
        .map(
          (item, i) =>
            `<label class="check"><input type="checkbox" data-check="${i}" ${saved[i] ? "checked" : ""} ${t.status === "done" ? "disabled" : ""}> ${esc(item)}</label>`
        )
        .join("")
    : "";
  $("#task-notes").value = t.notes || "";
  $("#task-error").textContent = "";
  const isDone = t.status === "done";
  $("#task-start").disabled = isDone || t.status === "in_progress";
  $("#task-complete").disabled = isDone || t.status === "pending";
  $("#task-block").disabled = isDone;
  $("#task-dialog").showModal();
}

function readChecklist() {
  return Array.from(document.querySelectorAll("#task-checklist [data-check]")).map((el) => el.checked);
}

$("#task-start").addEventListener("click", async () => {
  try {
    await apiFetch(`/production/tasks/${currentTask.id}/start`, { method: "POST" });
    $("#task-dialog").close();
    await loadTasks();
  } catch (error) {
    $("#task-error").textContent = error.message;
  }
});

$("#task-complete").addEventListener("click", async () => {
  try {
    const task = await apiFetch(`/production/tasks/${currentTask.id}/complete`, {
      method: "POST",
      body: JSON.stringify({ checklist: readChecklist(), notes: $("#task-notes").value }),
    });
    $("#task-dialog").close();
    // Этап 5b: последнее задание заказа списывает материалы со склада автоматически
    if (task.stock_auto_consume) {
      const n = (task.stock_auto_consume.consumed || []).length;
      window.alert(`Задание завершено. Все работы по заказу готовы — материалы списаны со склада (позиций: ${n}).`);
    }
    await loadTasks();
  } catch (error) {
    $("#task-error").textContent = error.message;
  }
});

$("#task-block").addEventListener("click", async () => {
  if (!$("#task-notes").value.trim()) {
    $("#task-error").textContent = "Укажите причину блокировки в заметке";
    return;
  }
  try {
    await apiFetch(`/production/tasks/${currentTask.id}/block`, {
      method: "POST",
      body: JSON.stringify({ reason: $("#task-notes").value }),
    });
    $("#task-dialog").close();
    await loadTasks();
  } catch (error) {
    $("#task-error").textContent = error.message;
  }
});

loadTasks().catch(showError);
