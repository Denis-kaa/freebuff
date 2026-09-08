/* Список заказов: фильтр по статусу (Р2), смена статуса, OrderExport (Р1). */

"use strict";

const $ = (sel) => document.querySelector(sel);
const money = (n) => Number(n).toFixed(2);

let currentStatus = "";
let currentOrder = null;

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

async function loadOrders() {
  const suffix = currentStatus ? "?status=" + encodeURIComponent(currentStatus) : "";
  const data = await apiFetch("/orders" + suffix);
  const body = $("#orders-body");
  body.innerHTML = "";
  data.orders.forEach((order) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${order.id}</td>` +
      `<td>${escapeHtml(order.created_at.replace("T", " ").slice(0, 16))}</td>` +
      `<td>${order.items_count}</td>` +
      `<td class="num">${money(order.total)}</td>` +
      `<td>${escapeHtml(order.payment_method)}</td>` +
      `<td><span class="badge status-${escapeHtml(order.status)}">${escapeHtml(order.status)}</span></td>` +
      `<td><button data-open="${order.id}">открыть</button></td>`;
    body.appendChild(tr);
  });
  if (!data.orders.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Заказов пока нет</td></tr>';
  }
}

$("#status-filter").addEventListener("click", (event) => {
  const status = event.target.getAttribute && event.target.getAttribute("data-status");
  if (status === null) return;
  currentStatus = status;
  document.querySelectorAll("#status-filter button").forEach((button) => button.classList.toggle("primary", button === event.target));
  loadOrders();
});

document.addEventListener("click", async (event) => {
  if (event.target.matches("[data-close]")) {
    event.target.closest("dialog").close();
    return;
  }
  const openId = event.target.getAttribute && event.target.getAttribute("data-open");
  if (openId) await openOrder(Number(openId));
});

async function openOrder(orderId) {
  currentOrder = await apiFetch("/orders/" + orderId);
  $("#dlg-order-id").textContent = orderId;
  const itemsTable = $("#dlg-order-items");
  itemsTable.innerHTML =
    "<thead><tr><th>Позиция</th><th class='num'>Цена</th><th class='num'>Кол-во</th><th class='num'>Сумма</th></tr></thead><tbody>" +
    currentOrder.items
      .map((item) => {
        const badge = item.saved_to_catalog ? "" : ' <span class="badge unverified">мимо каталога</span>';
        return `<td>${escapeHtml(item.name)}${badge}</td><td class="num">${money(item.price)}</td>` +
          `<td class="num">${item.qty}</td><td class="num">${money(item.price * item.qty)}</td>`;
      })
      .map((cells) => "<tr>" + cells + "</tr>")
      .join("") +
    "</tbody>";
  $("#dlg-order-status").value = currentOrder.status;
  // Пожелания заказчика (свободная форма).
  const wishes = String(currentOrder.wishes || "").trim();
  if (wishes) {
    $("#dlg-order-wishes").classList.remove("hidden");
    $("#dlg-order-wishes-text").textContent = wishes;
  } else {
    $("#dlg-order-wishes").classList.add("hidden");
  }
  // Значения динамических разделов.
  const sectionsData = await apiFetch(`/orders/${orderId}/sections`);
  const filled = sectionsData.sections.filter((s) => String(s.value).trim() !== "");
  $("#dlg-order-sections").innerHTML = filled.length
    ? filled.map((s) => `<div><b>${escapeHtml(s.title)}:</b> ${escapeHtml(s.value)}</div>`).join("")
    : "";
  $("#btn-order-export").href = `/api/orders/${orderId}/export.txt`;
  $("#dlg-order-msg").textContent = "";
  $("#dlg-order").showModal();
}

$("#btn-order-status-save").addEventListener("click", async () => {
  try {
    currentOrder = await apiFetch("/orders/" + currentOrder.id, {
      method: "PATCH",
      body: JSON.stringify({ status: $("#dlg-order-status").value }),
    });
    $("#dlg-order-msg").textContent = "Статус сохранён";
    loadOrders();
  } catch (error) {
    $("#dlg-order-msg").textContent = "Ошибка: " + error.message;
  }
});

$("#btn-order-copy").addEventListener("click", async () => {
  const response = await fetch(`/api/orders/${currentOrder.id}/export.txt`);
  const text = await response.text();
  await navigator.clipboard.writeText(text).catch(() => {});
  $("#dlg-order-msg").textContent = "Текст заказа скопирован — вставьте в WF";
});

loadOrders();
