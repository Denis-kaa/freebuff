/* Клиенты: список/поиск, диалог клиента, контакты (Этап 1). */

"use strict";

const $ = (sel) => document.querySelector(sel);

let clients = [];
let editId = null;
let editContacts = [];

async function apiFetch(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "ошибка запроса");
  return data;
}

function esc(text) {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

const CHANNEL_LABELS = {
  phone: "телефон", telegram: "telegram", vk: "vk",
  max: "max", email: "email", web: "web",
};

async function reload() {
  const q = $("#client-search").value.trim();
  const includeArchived = $("#client-archived").checked;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (includeArchived) params.set("include_archived", "true");
  const data = await apiFetch("/clients?" + params.toString());
  clients = data.clients;
  render();
}

function render() {
  const body = $("#clients-body");
  body.innerHTML = clients.map((c) => `
    <tr data-id="${c.id}">
      <td>${esc(c.name)}${c.archived ? ' <span class="soon">архив</span>' : ""}</td>
      <td>${esc(c.kind)}</td>
      <td class="muted" data-contacts=" — ">…</td>
      <td class="muted">${esc(c.note)}</td>
      <td class="row-actions"><button class="btn btn-ghost" data-open>открыть</button></td>
    </tr>`).join("");
  // контакты догружаются лениво (иначе N+1)
  clients.forEach(async (c, i) => {
    const detail = await apiFetch("/clients/" + c.id);
    const labels = detail.contacts
      .map((ct) => `${CHANNEL_LABELS[ct.channel] || ct.channel}: ${esc(ct.value)}`)
      .join(", ");
    const cell = body.querySelector(`tr[data-id="${c.id}"] [data-contacts]`);
    if (cell) cell.innerHTML = labels || "—";
  });
}

function openNew() {
  editId = null;
  editContacts = [];
  $("#client-modal-title").textContent = "Новый клиент";
  $("#client-name").value = "";
  $("#client-kind").value = "физлицо";
  $("#client-note").value = "";
  $("#client-contacts-block").classList.add("hidden");
  $("#client-archive").classList.add("hidden");
  $("#client-modal").classList.remove("hidden");
}

async function openEdit(id) {
  const detail = await apiFetch("/clients/" + id);
  editId = id;
  editContacts = detail.contacts;
  $("#client-modal-title").textContent = detail.name;
  $("#client-name").value = detail.name;
  $("#client-kind").value = detail.kind;
  $("#client-note").value = detail.note;
  $("#client-contacts-block").classList.remove("hidden");
  $("#client-archive").classList.remove("hidden");
  renderContacts();
  $("#client-modal").classList.remove("hidden");
}

function renderContacts() {
  $("#contacts-list").innerHTML = editContacts.map((ct) => `
    <li data-id="${ct.id}">
      <span class="badge">${CHANNEL_LABELS[ct.channel] || ct.channel}</span>
      ${esc(ct.value)}
      <button class="btn btn-ghost" data-del-contact="${ct.id}" title="удалить">✕</button>
    </li>`).join("") || "<li class='muted'>контактов нет</li>";
}

async function save() {
  const payload = {
    name: $("#client-name").value,
    kind: $("#client-kind").value,
    note: $("#client-note").value,
  };
  if (editId === null) {
    const created = await apiFetch("/clients", { method: "POST", body: JSON.stringify(payload) });
    editId = created.id;
    $("#client-modal-title").textContent = created.name;
    $("#client-contacts-block").classList.remove("hidden");
    $("#client-archive").classList.remove("hidden");
  } else {
    await apiFetch("/clients/" + editId, { method: "PATCH", body: JSON.stringify(payload) });
    $("#client-modal-title").textContent = payload.name;
  }
  await reload();
}

async function archiveCurrent() {
  if (editId === null) return;
  const current = clients.find((c) => c.id === editId);
  await apiFetch("/clients/" + editId, {
    method: "PATCH",
    body: JSON.stringify({ archived: !(current && current.archived) }),
  });
  $("#client-modal").classList.add("hidden");
  await reload();
}

$("#btn-new-client").addEventListener("click", openNew);
$("#client-close").addEventListener("click", () => $("#client-modal").classList.add("hidden"));
$("#client-save").addEventListener("click", () => save().catch((e) => alert(e.message)));
$("#client-archive").addEventListener("click", () => archiveCurrent().catch((e) => alert(e.message)));
$("#btn-add-contact").addEventListener("click", async () => {
  if (editId === null) return;
  const channel = $("#contact-channel").value;
  const value = $("#contact-value").value;
  const created = await apiFetch(`/clients/${editId}/contacts`, {
    method: "POST",
    body: JSON.stringify({ channel, value }),
  });
  editContacts.push(created);
  $("#contact-value").value = "";
  renderContacts();
});
$("#contacts-list").addEventListener("click", async (event) => {
  const btn = event.target.closest("[data-del-contact]");
  if (!btn) return;
  await apiFetch(`/clients/${editId}/contacts/${btn.dataset.delContact}`, { method: "DELETE" });
  editContacts = editContacts.filter((ct) => ct.id !== Number(btn.dataset.delContact));
  renderContacts();
});
$("#clients-body").addEventListener("click", (event) => {
  const btn = event.target.closest("[data-open]");
  if (!btn) return;
  const id = Number(btn.closest("tr").dataset.id);
  openEdit(id).catch((e) => alert(e.message));
});
$("#client-search").addEventListener("input", () => reload().catch((e) => alert(e.message)));
$("#client-archived").addEventListener("change", () => reload().catch((e) => alert(e.message)));

reload().catch((e) => alert(e.message));
