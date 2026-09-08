/* Конструктор разделов заказа: CRUD + сортировка (вверх/вниз + сохранить порядок). */

"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

let sections = [];
let editId = null;
let pendingOrder = null; // порядок после стрелок, ещё не сохранённый

async function apiFetch(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data && data.detail ? String(data.detail) : response.statusText);
  }
  return response.json();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

const KIND_LABELS = {
  textarea: "текст (многострочный)",
  text: "текст (одна строка)",
  select: "выбор из вариантов",
  checkbox: "галочка",
  number: "число",
  date: "дата",
};

function sectionExtra(section) {
  if (section.kind === "select") return section.options.join(", ");
  if (section.kind === "textarea") return "свободная форма";
  return "—";
}

async function loadSections() {
  const data = await apiFetch("/sections?include_archived=true");
  sections = data.sections;
  pendingOrder = null;
  $("#btn-reorder-save").disabled = true;
  $("#btn-reorder-reset").disabled = true;
  renderSections();
}

function renderSections() {
  const body = $("#sections-body");
  body.innerHTML = "";
  const active = pendingOrder
    ? pendingOrder.map((id) => sections.find((s) => s.id === id)).filter(Boolean)
    : sections;
  active.forEach((section, index) => {
    const tr = document.createElement("tr");
    if (section.archived) tr.classList.add("archived");
    tr.innerHTML =
      `<td>` +
      (section.archived ? "" :
        `<button class="icon" data-up="${section.id}" ${index === 0 ? "disabled" : ""}>↑</button>` +
        `<button class="icon" data-down="${section.id}" ${index === active.length - 1 ? "disabled" : ""}>↓</button>`) +
      `</td>` +
      `<td>${escapeHtml(section.title)}${section.archived ? ' <span class="badge unverified">в архиве</span>' : ""}</td>` +
      `<td>${KIND_LABELS[section.kind] || escapeHtml(section.kind)}</td>` +
      `<td class="muted">${escapeHtml(sectionExtra(section))}</td>` +
      `<td>${section.required ? "да" : "—"}</td>` +
      `<td>` +
      (section.archived
        ? `<button data-restore="${section.id}">вернуть</button>`
        : `<button data-edit="${section.id}">править</button>`) +
      `</td>`;
    body.appendChild(tr);
  });
  if (!active.length) {
    body.innerHTML = '<tr><td colspan="6" class="muted">Разделов нет — добавьте первый ниже</td></tr>';
  }
}

function moveSection(id, delta) {
  const ids = pendingOrder ? [...pendingOrder] : sections.filter((s) => !s.archived).map((s) => s.id);
  const index = ids.indexOf(id);
  const target = index + delta;
  if (index < 0 || target < 0 || target >= ids.length) return;
  ids.splice(index, 1);
  ids.splice(target, 0, id);
  pendingOrder = ids;
  $("#btn-reorder-save").disabled = false;
  $("#btn-reorder-reset").disabled = false;
  renderSections();
}

$("#sections-table").addEventListener("click", (event) => {
  const up = event.target.getAttribute && event.target.getAttribute("data-up");
  const down = event.target.getAttribute && event.target.getAttribute("data-down");
  const edit = event.target.getAttribute && event.target.getAttribute("data-edit");
  const restore = event.target.getAttribute && event.target.getAttribute("data-restore");
  if (up) moveSection(Number(up), -1);
  else if (down) moveSection(Number(down), 1);
  else if (edit) openEdit(Number(edit));
  else if (restore) restoreSection(Number(restore));
});

$("#btn-reorder-save").addEventListener("click", async () => {
  if (!pendingOrder) return;
  $("#sections-error").textContent = "";
  try {
    const data = await apiFetch("/sections/reorder", {
      method: "POST",
      body: JSON.stringify({ ids: pendingOrder }),
    });
    sections = data.sections;
    pendingOrder = null;
    $("#btn-reorder-save").disabled = true;
    $("#btn-reorder-reset").disabled = true;
    renderSections();
  } catch (error) {
    $("#sections-error").textContent = error.message;
  }
});

$("#btn-reorder-reset").addEventListener("click", () => {
  pendingOrder = null;
  $("#btn-reorder-save").disabled = true;
  $("#btn-reorder-reset").disabled = true;
  renderSections();
});

$("#btn-add-section").addEventListener("click", async () => {
  $("#new-section-error").textContent = "";
  const kind = $("#new-section-kind").value;
  const optionsRaw = $("#new-section-options").value;
  const body = {
    title: $("#new-section-title").value,
    kind,
    required: $("#new-section-required").checked,
    options: kind === "select" ? optionsRaw.split(",").map((o) => o.trim()).filter(Boolean) : [],
  };
  try {
    await apiFetch("/sections", { method: "POST", body: JSON.stringify(body) });
    $("#new-section-title").value = "";
    $("#new-section-options").value = "";
    $("#new-section-required").checked = false;
    await loadSections();
  } catch (error) {
    $("#new-section-error").textContent = error.message;
  }
});

function openEdit(id) {
  const section = sections.find((s) => s.id === id);
  if (!section) return;
  editId = id;
  $("#edit-section-title").value = section.title;
  $("#edit-section-kind").value = section.kind;
  $("#edit-section-options").value = section.options.join(", ");
  $("#edit-section-required").checked = section.required;
  $("#edit-section-error").textContent = "";
  $("#dlg-section").showModal();
}

$("#btn-section-save").addEventListener("click", async () => {
  $("#edit-section-error").textContent = "";
  const kind = $("#edit-section-kind").value;
  const optionsRaw = $("#edit-section-options").value;
  const body = {
    title: $("#edit-section-title").value,
    kind,
    required: $("#edit-section-required").checked,
    options: kind === "select" ? optionsRaw.split(",").map((o) => o.trim()).filter(Boolean) : [],
  };
  try {
    await apiFetch("/sections/" + editId, { method: "PATCH", body: JSON.stringify(body) });
    $("#dlg-section").close();
    await loadSections();
  } catch (error) {
    $("#edit-section-error").textContent = error.message;
  }
});

async function restoreSection(id) {
  await apiFetch("/sections/" + id, { method: "PATCH", body: JSON.stringify({ archived: false }) });
  await loadSections();
}

$("#btn-section-archive").addEventListener("click", async () => {
  await apiFetch("/sections/" + editId, { method: "PATCH", body: JSON.stringify({ archived: true }) });
  $("#dlg-section").close();
  await loadSections();
});

document.addEventListener("click", (event) => {
  if (event.target.matches("[data-close]")) event.target.closest("dialog").close();
});

loadSections();
