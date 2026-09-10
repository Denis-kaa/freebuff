/* Входящие и заявки (Этап 6): сообщения → заявка → смета. */

"use strict";

const $ = (sel) => document.querySelector(sel);

let messages = [];
let inquiries = [];
let clients = [];
let currentInquiry = null;

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

const MESSAGE_STATUS = { new: "новое", inquiry: "с заявкой", archived: "архив" };
const INQUIRY_STATUS = { new: "новая", estimated: "со сметой", archived: "архив" };
const MATCH_LABEL = { auto: "авто", manual: "вручную", none: "—" };

function timeShort(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 16);
}

async function loadMessages() {
  const status = $("#inbox-status-filter").value;
  const params = status ? `?status=${status}` : "";
  const data = await apiFetch(`/inbox${params}`);
  messages = data.messages;
  const body = $("#inbox-body");
  if (!messages.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Пока пусто</td></tr>';
    return;
  }
  body.innerHTML = messages.map((m) => {
    const parsed = m.parsed || {};
    const recognized = (parsed.items || [])
      .map((it) => `${esc(it.name)} × ${it.qty}`)
      .join(", ");
    const unknown = (parsed.unknown || []).join(", ");
    const parsedHtml = recognized
      ? `${recognized}${unknown ? ` <span class="muted">не распознано: ${esc(unknown)}</span>` : ""}`
      : `<span class="muted">${unknown ? `не распознано: ${esc(unknown)}` : "—"}</span>`;
    // R10: машина сигнализирует, что заявку должен принять человек.
    const operator = parsed.needs_operator
      ? `<div class="muted" title="${esc((parsed.reasons || []).join("; "))}">⚠ передать оператору: ${esc((parsed.reasons || []).join("; "))}</div>`
      : "";
    const actions = [];
    if (m.status === "new") {
      actions.push(`<button class="btn" data-inquiry="${m.id}" type="button">В заявку</button>`);
    }
    if (m.status !== "archived") {
      actions.push(`<button class="btn" data-archive="${m.id}" type="button">В архив</button>`);
    }
    return `<tr>
      <td>${timeShort(m.received_at)}</td>
      <td>${esc(m.channel)}</td>
      <td>${esc(m.sender_name || m.sender_handle || "—")}</td>
      <td>${esc(m.text).slice(0, 120)}</td>
      <td>${parsedHtml}${operator}</td>
      <td><span class="pill">${MESSAGE_STATUS[m.status] || esc(m.status)}</span></td>
      <td class="row-actions">${actions.join(" ")}</td>
    </tr>`;
  }).join("");
}

async function loadInquiries() {
  const status = $("#inquiry-status-filter").value;
  const params = status ? `?status=${status}` : "";
  const data = await apiFetch(`/inquiries${params}`);
  inquiries = data.inquiries;
  const clientById = new Map(clients.map((c) => [c.id, c]));
  const body = $("#inquiries-body");
  if (!inquiries.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Пока пусто</td></tr>';
    return;
  }
  body.innerHTML = inquiries.map((q) => {
    const client = q.client_id ? (clientById.get(q.client_id) || {}) : null;
    const estimateCell = q.estimate_id
      ? `<a href="/estimates">смета №${q.estimate_id}</a>`
      : '<span class="muted">—</span>';
    return `<tr>
      <td>${q.id}</td>
      <td>${timeShort(q.created_at)}</td>
      <td>${client ? esc(client.name) : '<span class="muted">не найден</span>'}
          <span class="muted">(${MATCH_LABEL[q.client_match] || q.client_match})</span></td>
      <td>${esc(q.summary).slice(0, 80)}</td>
      <td>${estimateCell}</td>
      <td><span class="pill">${INQUIRY_STATUS[q.status] || esc(q.status)}</span></td>
      <td class="row-actions">
        <button class="btn" data-open-inquiry="${q.id}" type="button">Открыть</button>
      </td>
    </tr>`;
  }).join("");
}

async function loadClients() {
  const data = await apiFetch("/clients");
  clients = data.clients || data;
  const options = clients.map(
    (c) => `<option value="${c.id}">${esc(c.name)}</option>`
  ).join("");
  $("#inq-client").innerHTML = '<option value="">— не выбран —</option>' + options;
}

function openInquiryDialog(inquiry) {
  currentInquiry = inquiry;
  $("#inquiry-dialog-title").textContent = `Заявка №${inquiry.id}`;
  $("#inq-client").value = inquiry.client_id || "";
  $("#inq-summary").value = inquiry.summary || "";
  $("#inquiry-error").textContent = "";
  $("#inquiry-dialog").showModal();
}

async function createInquiryFromMessage(messageId) {
  try {
    const inquiry = await apiFetch(`/inbox/${messageId}/inquiry`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    await Promise.all([loadMessages(), loadInquiries()]);
    openInquiryDialog(inquiry);
  } catch (error) {
    $("#inbox-error").textContent = error.message;
  }
}

async function saveInquiry() {
  if (!currentInquiry) return;
  try {
    const payload = { summary: $("#inq-summary").value };
    const clientValue = $("#inq-client").value;
    payload.client_id = clientValue ? Number(clientValue) : null;
    await apiFetch(`/inquiries/${currentInquiry.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    await loadInquiries();
    $("#inquiry-dialog").close();
  } catch (error) {
    $("#inquiry-error").textContent = error.message;
  }
}

async function createEstimateFromInquiry() {
  if (!currentInquiry) return;
  try {
    const payload = { client_id: currentInquiry.client_id };
    const note = `Из заявки №${currentInquiry.id}: ${currentInquiry.summary}`;
    const estimate = await apiFetch("/estimates", {
      method: "POST",
      body: JSON.stringify({ items: [{ kind: "manual", name: "Позиция (уточнить)", qty: 1, price: 0 }], client_id: payload.client_id, note }),
    });
    await apiFetch(`/inquiries/${currentInquiry.id}/estimate`, {
      method: "POST",
      body: JSON.stringify({ estimate_id: estimate.id }),
    });
    await Promise.all([loadInquiries(), loadMessages()]);
    $("#inquiry-dialog").close();
    window.location.href = "/estimates";
  } catch (error) {
    $("#inquiry-error").textContent = error.message;
  }
}

document.addEventListener("click", (event) => {
  const inquiryBtn = event.target.closest("[data-inquiry]");
  if (inquiryBtn) return createInquiryFromMessage(Number(inquiryBtn.dataset.inquiry));
  const archiveBtn = event.target.closest("[data-archive]");
  if (archiveBtn) {
    return apiFetch(`/inbox/${archiveBtn.dataset.archive}/archive`, { method: "POST" })
      .then(loadMessages)
      .catch((e) => ($("#inbox-error").textContent = e.message));
  }
  const openBtn = event.target.closest("[data-open-inquiry]");
  if (openBtn) {
    const inquiry = inquiries.find((q) => q.id === Number(openBtn.dataset.openInquiry));
    if (inquiry) openInquiryDialog(inquiry);
  }
});

$("#inbox-status-filter").addEventListener("change", loadMessages);
$("#inquiry-status-filter").addEventListener("change", loadInquiries);
$("#btn-inbox-refresh").addEventListener("click", () => {
  Promise.all([loadMessages(), loadInquiries()]).catch(
    (e) => ($("#inbox-error").textContent = e.message)
  );
});
$("#inq-save").addEventListener("click", saveInquiry);
$("#inq-to-estimate").addEventListener("click", createEstimateFromInquiry);

Promise.all([loadClients(), loadMessages(), loadInquiries()]).catch(
  (e) => ($("#inbox-error").textContent = e.message)
);
