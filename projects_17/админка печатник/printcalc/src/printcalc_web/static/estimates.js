/* Сметы: список, создание, статусы, snapshot, заказ из сметы (Этап 2). */

"use strict";

const $ = (sel) => document.querySelector(sel);

let estimates = [];
let currentEstimate = null; // открытая в диалоге просмотра смета
let estDraft = []; // черновик позиций в диалоге создания

async function apiFetch(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "ошибка запроса");
  return data;
}

const money = (n) => Number(n).toFixed(2);
const esc = (text) => {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
};

const STATUS_LABELS = {
  draft: "черновик",
  sent: "отправлена",
  viewed: "просмотрена",
  accepted: "принята",
  rejected: "отказ",
  expired: "просрочена",
};

function statusBadge(status) {
  return `<span class="pill pill-${esc(status)}">${STATUS_LABELS[status] || esc(status)}</span>`;
}

/* ---------- список ---------- */

async function loadEstimates() {
  const filter = $("#estimate-status-filter").value;
  const params = filter ? "?status=" + encodeURIComponent(filter) : "";
  const data = await apiFetch("/estimates" + params);
  estimates = data.estimates;
  renderEstimates();
}

function renderEstimates() {
  const body = $("#estimates-body");
  if (!estimates.length) {
    body.innerHTML = '<tr><td colspan="8" class="muted">Смет пока нет — создайте первую</td></tr>';
    return;
  }
  body.innerHTML = estimates
    .map(
      (e) => `<tr data-id="${e.id}" style="cursor:pointer">
        <td><b>${e.id}</b></td>
        <td>${esc((e.created_at || "").slice(0, 10))}</td>
        <td>${esc(e.client_name || "—")}</td>
        <td>${e.items_count}</td>
        <td class="num">${money(e.total)} ₽</td>
        <td>${esc((e.valid_until || "").slice(0, 10) || "—")}</td>
        <td>${statusBadge(e.status)}</td>
        <td><button class="icon" data-open="${e.id}" title="Открыть">›</button></td>
      </tr>`
    )
    .join("");
}

$("#estimate-status-filter").addEventListener("change", () => loadEstimates().catch(showListError));

document.addEventListener("click", (event) => {
  const openId = event.target.getAttribute && event.target.getAttribute("data-open");
  if (openId) openEstimate(Number(openId));
  if (event.target.matches("[data-close]")) event.target.closest("dialog").close();
});

function showListError(error) {
  $("#estimates-error").textContent = error.message;
}

/* ---------- создание сметы ---------- */

$("#btn-new-estimate").addEventListener("click", async () => {
  estDraft = [];
  $("#est-note").value = "";
  $("#est-valid-until").value = "";
  $("#est-error").textContent = "";
  await Promise.all([loadEstClients(), loadPaymentMethods()]);
  renderEstItems();
  $("#estimate-dialog").showModal();
});

async function loadEstClients() {
  const data = await apiFetch("/clients");
  $("#est-client").innerHTML =
    '<option value="">— без клиента —</option>' +
    data.clients.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
}

async function loadPaymentMethods() {
  const data = await apiFetch("/settings/payment-methods");
  $("#estord-payment").innerHTML = data.methods.map((m) => `<option>${esc(m)}</option>`).join("");
}

$("#est-add-price").addEventListener("click", async () => {
  $("#est-price-search").value = "";
  await searchPrice("");
  $("#est-price-dialog").showModal();
});

$("#est-price-search").addEventListener("input", async (event) => {
  await searchPrice(event.target.value);
});

async function searchPrice(query) {
  const data = await apiFetch("/price-list" + (query ? "?query=" + encodeURIComponent(query) : ""));
  $("#est-price-results").innerHTML = data.items.length
    ? data.items
        .map(
          (i) =>
            `<button class="plain-item" data-pick="${i.id}" data-name="${esc(i.name)}" data-price="${i.price}" type="button">
              <b>${esc(i.name)}</b><span class="muted"> · ${money(i.price)} ₽${i.unit ? " / " + esc(i.unit) : ""}</span>
            </button>`
        )
        .join("")
    : '<p class="muted">Ничего не найдено</p>';
}

$("#est-price-results").addEventListener("click", (event) => {
  const pick = event.target.closest("[data-pick]");
  if (!pick) return;
  estDraft.push({
    kind: "price_list",
    price_list_item_id: Number(pick.dataset.pick),
    name: pick.dataset.name,
    price: Number(pick.dataset.price),
    qty: 1,
  });
  renderEstItems();
  $("#est-price-dialog").close();
});

$("#est-add-manual").addEventListener("click", () => {
  estDraft.push({ kind: "manual", name: "", price: 0, qty: 1, save_to_catalog: false });
  renderEstItems();
});

function renderEstItems() {
  const body = $("#est-items-body");
  body.innerHTML = estDraft
    .map(
      (item, index) => `<tr>
        <td>${
          item.kind === "price_list"
            ? esc(item.name)
            : `<input class="field-input" type="text" data-name-idx="${index}" value="${esc(item.name)}" placeholder="Наименование">`
        }</td>
        <td class="num">${
          item.kind === "price_list"
            ? money(item.price)
            : `<input class="field-input" type="number" min="0" step="any" data-price-idx="${index}" value="${item.price}" style="width:90px">`
        }</td>
        <td class="num"><input class="field-input" type="number" min="0.001" step="any" data-qty-idx="${index}" value="${item.qty}" style="width:70px"></td>
        <td class="num">${money(item.price * item.qty)}</td>
        <td><button class="icon danger" data-est-remove="${index}" type="button">✕</button></td>
      </tr>`
    )
    .join("");
  $("#est-total").textContent = money(estDraft.reduce((sum, i) => sum + i.price * i.qty, 0));
}

$("#est-items-body").addEventListener("input", (event) => {
  const t = event.target;
  if (t.hasAttribute("data-name-idx")) estDraft[Number(t.dataset.nameIdx)].name = t.value;
  if (t.hasAttribute("data-price-idx")) estDraft[Number(t.dataset.priceIdx)].price = Number(t.value) || 0;
  if (t.hasAttribute("data-qty-idx")) estDraft[Number(t.dataset.qtyIdx)].qty = Number(t.value) || 0.001;
  $("#est-total").textContent = money(estDraft.reduce((sum, i) => sum + i.price * i.qty, 0));
});

$("#est-items-body").addEventListener("click", (event) => {
  const removeIdx = event.target.getAttribute && event.target.getAttribute("data-est-remove");
  if (removeIdx !== null) {
    estDraft.splice(Number(removeIdx), 1);
    renderEstItems();
  }
});

$("#est-save").addEventListener("click", async () => {
  $("#est-error").textContent = "";
  if (!estDraft.length) {
    $("#est-error").textContent = "Добавьте хотя бы одну позицию";
    return;
  }
  try {
    const est = await apiFetch("/estimates", {
      method: "POST",
      body: JSON.stringify({
        items: estDraft,
        client_id: $("#est-client").value ? Number($("#est-client").value) : null,
        note: $("#est-note").value,
        valid_until: $("#est-valid-until").value || null,
      }),
    });
    $("#estimate-dialog").close();
    await loadEstimates();
    openEstimate(est.id);
  } catch (error) {
    $("#est-error").textContent = error.message;
  }
});

/* ---------- просмотр / статусы / заказ ---------- */

async function openEstimate(id) {
  try {
    currentEstimate = await apiFetch("/estimates/" + id);
  } catch (error) {
    showListError(error);
    return;
  }
  const e = currentEstimate;
  $("#estv-number").textContent = e.id;
  const badge = $("#estv-status");
  badge.className = "pill pill-" + e.status;
  badge.textContent = STATUS_LABELS[e.status] || e.status;
  $("#estv-body").innerHTML =
    `<p class="muted">${esc(e.client_name || "без клиента")} · создана ${(e.created_at || "").slice(0, 10)}${
      e.valid_until ? " · годна до " + esc(e.valid_until.slice(0, 10)) : ""
    }${e.note ? " · " + esc(e.note) : ""}</p>` +
    `<div class="table-wrap"><table class="table"><thead><tr><th>Наименование</th><th class="num">Цена</th><th class="num">Кол-во</th><th class="num">Сумма</th></tr></thead><tbody>` +
    e.items
      .map(
        (i) =>
          `<tr><td>${esc(i.name)}${i.kind === "manual" ? ' <span class="pill pill-draft">не в прайсе</span>' : ""}</td>` +
          `<td class="num">${money(i.price)}</td><td class="num">${i.qty}</td><td class="num">${money(i.price * i.qty)}</td></tr>`
      )
      .join("") +
    `</tbody></table></div><div class="est-total-row">Итого: <b>${money(e.total)} ₽</b></div>`;

  $("#estv-snapshot").textContent = e.snapshot
    ? `Snapshot §49: движок ${e.snapshot.engine_version}, реестр ${e.snapshot.registry_checksum.slice(0, 8)}…, каталог ${e.snapshot.catalog_checksum.slice(0, 8)}…, от ${e.snapshot.created_at}`
    : "Snapshot ещё не снят (снимется при принятии)";

  const isActive = ["draft", "sent", "viewed"].includes(e.status);
  $("#estv-sent").disabled = e.status !== "draft";
  $("#estv-viewed").disabled = !["draft", "sent"].includes(e.status);
  $("#estv-accept").disabled = !isActive;
  $("#estv-reject").disabled = !isActive;
  $("#estv-to-order").disabled = e.status !== "accepted";
  $("#estv-error").textContent = "";
  $("#est-view-dialog").showModal();
}


$("#estv-sent").addEventListener("click", async () => {
  try {
    currentEstimate = await apiFetch(`/estimates/${currentEstimate.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "sent" }),
    });
    $("#est-view-dialog").close();
    await loadEstimates();
    openEstimate(currentEstimate.id);
  } catch (error) {
    $("#estv-error").textContent = error.message;
  }
});

$("#estv-viewed").addEventListener("click", async () => {
  try {
    currentEstimate = await apiFetch(`/estimates/${currentEstimate.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "viewed" }),
    });
    $("#est-view-dialog").close();
    await loadEstimates();
    openEstimate(currentEstimate.id);
  } catch (error) {
    $("#estv-error").textContent = error.message;
  }
});

$( "#estv-accept").addEventListener("click", async () => {
  try {
    currentEstimate = await apiFetch(`/estimates/${currentEstimate.id}/accept`, { method: "POST" });
    $("#est-view-dialog").close();
    await loadEstimates();
    openEstimate(currentEstimate.id);
  } catch (error) {
    $("#estv-error").textContent = error.message;
  }
});

$("#estv-reject").addEventListener("click", async () => {
  try {
    currentEstimate = await apiFetch(`/estimates/${currentEstimate.id}/status`, {
      method: "POST",
      body: JSON.stringify({ status: "rejected" }),
    });
    $("#est-view-dialog").close();
    await loadEstimates();
    openEstimate(currentEstimate.id);
  } catch (error) {
    $("#estv-error").textContent = error.message;
  }
});

$("#estv-to-order").addEventListener("click", () => {
  $("#estord-number").textContent = currentEstimate.id;
  $("#estord-error").textContent = "";
  $("#est-order-dialog").showModal();
});

$("#estord-create").addEventListener("click", async () => {
  try {
    const order = await apiFetch(`/estimates/${currentEstimate.id}/order`, {
      method: "POST",
      body: JSON.stringify({ payment_method: $("#estord-payment").value }),
    });
    $("#est-order-dialog").close();
    $("#est-view-dialog").close();
    await loadEstimates();
    window.location.href = "/orders#" + order.id;
  } catch (error) {
    $("#estord-error").textContent = error.message;
  }
});

/* ---------- старт ---------- */

loadEstimates().catch(showListError);
