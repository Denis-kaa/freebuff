/* Список заказов: фильтр по статусу (Р2), смена статуса, OrderExport (Р1). */

"use strict";

const $ = (sel) => document.querySelector(sel);
const money = (n) => Number(n).toFixed(2);

let currentStatus = "";
let currentSort = "created";
let currentDirection = "desc";
let currentDeadlineFilter = "";
let currentOrder = null;

// Deadline Engine (РОАДМАП_v8 B4): цвет/значок/текст — НЕ только цвет
// (accessibility ТЗ §5). «Без дедлайна» — отдельная нейтральная строка (§18).
const URGENCY_VIEW = {
  normal: { dot: "🟢", cls: "dl-normal" },
  warning: { dot: "🟡", cls: "dl-warning" },
  urgent: { dot: "🟠", cls: "dl-urgent" },
  critical: { dot: "🔴", cls: "dl-critical" },
  very_critical: { dot: "🔴", cls: "dl-critical" },
  overdue: { dot: "⛔", cls: "dl-overdue" },
};

function formatRemaining(seconds) {
  const overdue = seconds < 0;
  const totalMinutes = Math.floor(Math.abs(seconds) / 60);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  let text;
  if (days >= 1) text = `${days} дн. ${hours} ч.`;
  else if (hours >= 1) text = `${hours} ч. ${minutes} мин.`;
  else text = `${minutes} мин.`;
  return overdue ? `Просрочен: ${text}` : text;
}

function deadlineCell(order) {
  const u = order.urgency;
  if (!u) {
    const has = order.customer_deadline || order.internal_deadline;
    return has ? '<span class="muted">финальный</span>' : "⚪ нет";
  }
  const view = URGENCY_VIEW[u.status] || URGENCY_VIEW.normal;
  return `<span class="deadline-pill ${view.cls}" title="Дедлайн ${escapeHtml(u.nearest_deadline)}">` +
    `${view.dot} ${escapeHtml(formatRemaining(u.remaining_seconds))}</span>`;
}

// Класс-пилюля бейджа для каждого статуса (тёмная тема «Печатникъ»).
const STATUS_STYLE = {
  "новый": "st-new",
  "в работе": "st-work",
  "выполнен": "st-done",
  "завершён": "st-closed",
};

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
  const params = new URLSearchParams();
  if (currentStatus) params.set("status", currentStatus);
  if (currentDeadlineFilter) params.set("deadline_filter", currentDeadlineFilter);
  params.set("sort", currentSort);
  params.set("direction", currentDirection);
  const data = await apiFetch("/orders?" + params.toString());
  const body = $("#orders-body");
  body.innerHTML = "";
  data.orders.forEach((order) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${order.id}</td>` +
      `<td>${escapeHtml(order.created_at.replace("T", " ").slice(0, 16))}</td>` +
      `<td>${escapeHtml(order.client_name || "—")}</td>` +
      `<td>${order.items_count}</td>` +
      `<td class="num">${money(order.total)}</td>` +
      `<td>${escapeHtml(order.payment_method)}</td>` +
      `<td><span class="badge ${STATUS_STYLE[order.status] || "st-red"}">${escapeHtml(order.status)}</span></td>` +
      `<td>${deadlineCell(order)}</td>` +
      `<td><button data-open="${order.id}">открыть</button></td>`;
    body.appendChild(tr);
  });
  if (!data.orders.length) {
    body.innerHTML = '<tr><td colspan="9" class="muted">Заказов пока нет</td></tr>';
  }
  loadDeadlineCounters();
}

/* Счётчики шапки (ТЗ §24) + лента событий (ТЗ §30): один endpoint. */
async function loadDeadlineCounters() {
  try {
    const data = await apiFetch("/deadline/summary");
    const s = data.summary;
    $("#deadline-counters").textContent =
      `⛔ ${s.overdue} · 🔴 ${s.critical} · сегодня ${s.today} · ⚪ без дедлайна ${s.no_deadline}`;
    const feed = $("#deadline-events");
    if (data.events.length) {
      feed.innerHTML = data.events
        .map((e) => {
          const kindLabel = { set: "установлен", changed: "изменён", cleared: "удалён", reminder: "напоминание" }[e.kind] || e.kind;
          const extra = e.payload && e.payload.old !== undefined && e.payload.old !== null
            ? `: ${escapeHtml(e.payload.old)} → ${escapeHtml(e.payload.new || "—")}`
            : (e.threshold ? ` (${escapeHtml(e.threshold)})` : "");
          return `<div>#${e.order_id} · ${e.deadline_type} · ${escapeHtml(kindLabel)}${extra} · ${escapeHtml(e.created_at.replace("T", " ").slice(0, 16))}</div>`;
        })
        .join("");
    } else {
      feed.textContent = "Событий пока нет";
    }
  } catch (error) {
    $("#deadline-counters").textContent = "";
  }
}$("#status-filter").addEventListener("click", (event) => {
  const status = event.target.getAttribute && event.target.getAttribute("data-status");
  if (status === null) return;
  currentStatus = status;
  document.querySelectorAll("#status-filter button").forEach((button) => button.classList.toggle("primary", button === event.target));
  loadOrders();
});

/* Deadline Engine: сортировка/фильтр/направление (ТЗ §12–17). */
$("#orders-sort").addEventListener("change", (e) => { currentSort = e.target.value; loadOrders(); });
$("#orders-direction").addEventListener("change", (e) => { currentDirection = e.target.value; loadOrders(); });
$("#deadline-filter").addEventListener("change", (e) => { currentDeadlineFilter = e.target.value; loadOrders(); });
$("#btn-deadline-refresh").addEventListener("click", loadOrders);

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
        // Расход материала (Этап 3): краткая строка под названием позиции.
        let consumptionRow = "";
        if (item.consumption) {
          const c = item.consumption;
          const parts = [];
          if (c.production_area_m2) parts.push(`расход ${Number(c.production_area_m2).toFixed(2)} м²`);
          if (c.billing_quantity && c.billing_unit === "lm") parts.push(`${Number(c.billing_quantity).toFixed(2)} пог.м`);
          if (c.pieces_across && c.rows && c.orientation) parts.push(`${c.pieces_across}×${c.rows} (${c.orientation})`);
          if (c.waste_percent) parts.push(`отход ${Number(c.waste_percent).toFixed(1)}%`);
          if (c.remnant && c.remnant.status === "REMNANT") parts.push(`остаток ${Number(c.remnant.width_m).toFixed(2)}×${Number(c.remnant.length_m).toFixed(2)} м`);
          if (parts.length) {
            consumptionRow = `<div class="consumption-line muted">⟶ ${parts.map(escapeHtml).join(" · ")}</div>`;
          }
        }
        // PHASE_UNITS: единица позиции рядом с количеством (NULL — legacy → шт).
        const unit = item.unit || "шт";
        return `<td>${escapeHtml(item.name)}${badge}${consumptionRow}</td><td class="num">${money(item.price)} / ${escapeHtml(unit)}</td>` +
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
  fillDeadlineDialog(currentOrder);
  $("#dlg-order-msg").textContent = "";
  $("#dlg-order").showModal();
}

/* ДЕДЛАЙН в диалоге (ТЗ §22): заполнение + сохранение/удаление. */
function isoToLocalInput(iso) {
  if (!iso) return "";
  return String(iso).slice(0, 16); // YYYY-MM-DDTHH:MM для datetime-local
}

function fillDeadlineDialog(order) {
  $("#dlg-deadline-customer").value = isoToLocalInput(order.customer_deadline);
  $("#dlg-deadline-internal").value = isoToLocalInput(order.internal_deadline);
  const statusBox = $("#dlg-deadline-status");
  const u = order.urgency;
  if (u) {
    statusBox.textContent = `Осталось: ${formatRemaining(u.remaining_seconds)} (ближайший ${u.nearest_deadline.replace("T", " ").slice(0, 16)})`;
  } else if (order.customer_deadline || order.internal_deadline) {
    statusBox.textContent = "Заказ в финальном статусе — напоминания выключены";
  } else {
    statusBox.textContent = "Дедлайн не установлен";
  }
}

$("#btn-order-deadline-save").addEventListener("click", async () => {
  try {
    const customer = $("#dlg-deadline-customer").value;
    const internal = $("#dlg-deadline-internal").value;
    // PUT идемпотентен; пустое поле = удалить дедлайн (value=null).
    await apiFetch(`/orders/${currentOrder.id}/deadline`, {
      method: "PUT",
      body: JSON.stringify({ deadline_type: "customer", value: customer || null }),
    });
    await apiFetch(`/orders/${currentOrder.id}/deadline`, {
      method: "PUT",
      body: JSON.stringify({ deadline_type: "internal", value: internal || null }),
    });
    currentOrder = await apiFetch("/orders/" + currentOrder.id);
    // urgency в GET /orders/{id} не входит — подтягиваем из списка.
    const listData = await apiFetch("/orders?sort=urgency");
    const fresh = listData.orders.find((o) => o.id === currentOrder.id);
    if (fresh) { currentOrder.urgency = fresh.urgency; }
    fillDeadlineDialog(currentOrder);
    $("#dlg-order-msg").textContent = "Дедлайны сохранены";
    loadOrders();
  } catch (error) {
    $("#dlg-order-msg").textContent = "Ошибка: " + error.message;
  }
});

$("#btn-order-deadline-clear").addEventListener("click", async () => {
  try {
    await apiFetch(`/orders/${currentOrder.id}/deadline`, {
      method: "PUT",
      body: JSON.stringify({ deadline_type: "customer", value: null }),
    });
    await apiFetch(`/orders/${currentOrder.id}/deadline`, {
      method: "PUT",
      body: JSON.stringify({ deadline_type: "internal", value: null }),
    });
    $("#dlg-deadline-customer").value = "";
    $("#dlg-deadline-internal").value = "";
    $("#dlg-deadline-status").textContent = "Дедлайн не установлен";
    $("#dlg-order-msg").textContent = "Дедлайны удалены";
    loadOrders();
  } catch (error) {
    $("#dlg-order-msg").textContent = "Ошибка: " + error.message;
  }
});

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

/* Производство: генерация заданий заказа (Этап 4). */
$("#btn-order-produce").addEventListener("click", async () => {
  try {
    const result = await apiFetch(`/orders/${currentOrder.id}/production/generate`, { method: "POST" });
    $("#dlg-order-msg").textContent = result.created.length
      ? `Создано заданий: ${result.created.length} — раздел «Производство»`
      : `Задания уже существуют (${result.progress.total} шт) — раздел «Производство»`;
  } catch (error) {
    $("#dlg-order-msg").textContent = "Ошибка: " + error.message;
  }
});

/* Склад (Этап 5): резерв и списание по рассчитанному расходу заказа. */
$("#btn-order-reserve").addEventListener("click", async () => {
  try {
    const result = await apiFetch(`/orders/${currentOrder.id}/materials/reserve`, { method: "POST" });
    $("#dlg-order-msg").textContent = `Зарезервировано позиций: ${result.reserved.length} — страница «Материалы», блок «Склад»`;
  } catch (error) {
    $("#dlg-order-msg").textContent = "Ошибка: " + error.message;
  }
});

$("#btn-order-consume").addEventListener("click", async () => {
  if (!window.confirm("Списать материалы по заказу со склада? После списания резерв снять нельзя.")) return;
  try {
    const result = await apiFetch(`/orders/${currentOrder.id}/materials/consume`, { method: "POST" });
    $("#dlg-order-msg").textContent = `Списано позиций: ${result.consumed.length}`;
  } catch (error) {
    $("#dlg-order-msg").textContent = "Ошибка: " + error.message;
  }
});

loadOrders();
