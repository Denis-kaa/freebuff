/* PrintCalc Pro — клиентская логика главного экрана (Р5б) и каталога.
Без фреймворков: fetch + DOM. Черновик заказа живёт в localStorage,
чтобы случайная перезагрузка не потеряла ввод на стойке. */

"use strict";

const API = "/api";
const $ = (sel) => document.querySelector(sel);
const money = (n) => Number(n).toFixed(2);

/* ---------- черновик заказа ---------- */

let draft = [];
try {
  draft = JSON.parse(localStorage.getItem("printcalc_draft") || "[]");
} catch { draft = []; }

function saveDraft() {
  localStorage.setItem("printcalc_draft", JSON.stringify(draft));
}

function draftTotal() {
  return draft.reduce((sum, item) => sum + item.price * item.qty, 0);
}

function renderDraft() {
  const body = $("#draft-body");
  body.innerHTML = "";
  if (!draft.length) {
    body.innerHTML = '<tr id="draft-empty"><td colspan="5" class="muted">Пусто — добавьте позиции кнопкой «+»</td></tr>';
  }
  draft.forEach((item, index) => {
    const tr = document.createElement("tr");
    const badge = item.kind === "manual" ? ' <span class="badge unverified">не в прайсе</span>' : "";
    tr.innerHTML =
      `<td>${escapeHtml(item.name)}${badge}</td>` +
      `<td class="num">${money(item.price)}</td>` +
      `<td class="num"><input type="number" min="0.001" step="any" value="${item.qty}" data-qty="${index}" style="width:70px"></td>` +
      `<td class="num">${money(item.price * item.qty)}</td>` +
      `<td><button class="icon danger" data-remove="${index}" title="Убрать позицию">✕</button></td>`;
    body.appendChild(tr);
  });
  $("#draft-total").textContent = money(draftTotal());
  saveDraft();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

function addItem(item) {
  draft.push(item);
  renderDraft();
}

document.addEventListener("click", (event) => {
  const removeIndex = event.target.getAttribute && event.target.getAttribute("data-remove");
  if (removeIndex !== null && removeIndex !== undefined && event.target.hasAttribute("data-remove")) {
    draft.splice(Number(removeIndex), 1);
    renderDraft();
  }
  if (event.target.matches("[data-close]")) {
    event.target.closest("dialog").close();
  }
});

document.addEventListener("input", (event) => {
  const qtyAttr = event.target.getAttribute && event.target.getAttribute("data-qty");
  if (qtyAttr !== null && qtyAttr !== undefined && event.target.hasAttribute("data-qty")) {
    const value = parseFloat(event.target.value);
    if (value > 0) {
      draft[Number(qtyAttr)].qty = value;
      renderDraft();
    }
  }
});

/* ---------- API-хелперы ---------- */

async function apiFetch(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    const data = await response.json().catch(() => null);
    if (data) {
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
    throw new Error(detail);
  }
  return response.json();
}

/* ---------- быстрый ввод (Р6, ступень 1) ---------- */

$("#quick-parse").addEventListener("click", async () => {
  const text = $("#quick-input").value.trim();
  if (!text) return;
  $("#parse-unknown").classList.add("hidden");
  try {
    const data = await apiFetch("/parse", { method: "POST", body: JSON.stringify({ text }) });
    data.items.forEach((parsed) => {
      if (parsed.type === "price") {
        addItem({ kind: "price_list", name: parsed.name, price: parsed.price, qty: parsed.qty, price_list_item_id: parsed.price_list_item_id });
      } else {
        addItem({ kind: "calculator", name: parsed.name, price: 0, qty: 1, calculator_id: parsed.calculator_id, needs_calc: true });
      }
    });
    if (data.unknown.length) {
      const box = $("#parse-unknown");
      box.textContent = "Не распознано: " + data.unknown.join(", ") + " — добавьте вручную через «+» (позиция запомнится)";
      box.classList.remove("hidden");
    }
    $("#quick-input").value = "";
  } catch (error) {
    alert("Ошибка разбора: " + error.message);
  }
});

/* ---------- добавление из прайса ---------- */

const dlgPrice = $("#dlg-price");

async function loadPriceList(query = "") {
  const data = await apiFetch("/price-list?q=" + encodeURIComponent(query));
  const body = $("#price-pick-body");
  body.innerHTML = "";
  data.items.forEach((item) => {
    const tr = document.createElement("tr");
    const badge = item.unverified ? ' <span class="badge unverified">не проверено</span>' : "";
    tr.innerHTML =
      `<td>${escapeHtml(item.name)}${badge}</td>` +
      `<td class="num">${money(item.price)}${item.unit ? " / " + escapeHtml(item.unit) : ""}</td>` +
      `<td class="num"><input type="number" min="0.001" step="any" value="1" data-pick-qty style="width:70px"></td>` +
      `<td><button data-pick="${item.id}">+</button></td>`;
    body.appendChild(tr);
  });
}

dlgPrice.addEventListener("click", async (event) => {
  const pickId = event.target.getAttribute && event.target.getAttribute("data-pick");
  if (pickId) {
    const row = event.target.closest("tr");
    const qty = parseFloat(row.querySelector("[data-pick-qty]").value) || 1;
    const nameCell = row.querySelector("td").textContent.trim();
    const priceCell = row.querySelectorAll("td")[1].textContent;
    addItem({ kind: "price_list", name: nameCell.replace(/не проверено$/, "").trim(), price: parseFloat(priceCell), qty, price_list_item_id: Number(pickId) });
    dlgPrice.close();
  }
});

$("#btn-add-price").addEventListener("click", async () => {
  await loadPriceList();
  dlgPrice.showModal();
});

$("#price-search").addEventListener("input", (event) => {
  clearTimeout(window.__priceSearchTimer);
  window.__priceSearchTimer = setTimeout(() => loadPriceList(event.target.value), 250);
});

/* «Похожее уже есть» (идея №8) при вводе названия новой позиции */
$("#new-item-name").addEventListener("input", async (event) => {
  const query = event.target.value.trim();
  const box = $("#price-similar");
  if (query.length < 3) { box.classList.add("hidden"); return; }
  const data = await apiFetch("/price-list/similar?q=" + encodeURIComponent(query));
  if (data.items.length) {
    box.innerHTML = "Похоже, уже есть: " +
      data.items.map((item) => `${escapeHtml(item.name)} — ${money(item.price)}₽`).join("; ") +
      ". Всё равно добавить новую?";
    box.classList.remove("hidden");
  } else {
    box.classList.add("hidden");
  }
});

/* ---------- новая позиция (Р5а) ---------- */

const dlgNewItem = $("#dlg-new-item");
let pendingManual = null;

$("#btn-add-manual").addEventListener("click", () => {
  pendingManual = null;
  $("#new-item-name").value = "";
  $("#new-item-price").value = "";
  $("#new-item-error").textContent = "";
  dlgNewItem.showModal();
});

$("#btn-new-item").addEventListener("click", () => {
  dlgPrice.close();
  $("#btn-add-manual").click();
});

$("#btn-new-item-save").addEventListener("click", () => {
  const name = $("#new-item-name").value.trim();
  const price = parseFloat($("#new-item-price").value);
  const unit = $("#new-item-unit").value || null;
  if (!name || isNaN(price) || price < 0) {
    $("#new-item-error").textContent = "Нужны название и цена ≥ 0";
    return;
  }
  const save = $("#new-item-save").checked;
  if (save) {
    // Идея №2: цена, введённая для клиента, становится позицией каталога.
    apiFetch("/price-list", { method: "POST", body: JSON.stringify({ name, price, unit }) })
      .then((created) => {
        addItem({ kind: "price_list", name: created.name, price: created.price, qty: 1, price_list_item_id: created.id });
        dlgNewItem.close();
      })
      .catch((error) => { $("#new-item-error").textContent = error.message; });
  } else {
    // Идея №10: позиция остаётся «мимо каталога» и попадёт в отчёт.
    addItem({ kind: "manual", name, price, qty: 1, save_to_catalog: false });
    dlgNewItem.close();
  }
});

/* ---------- калькулятор ---------- */

const dlgCalc = $("#dlg-calc");
let calcSpecs = [];
let lastResult = null;

function fieldHtml(field) {
  const id = "calc-" + field.name;
  let control;
  if (field.kind === "boolean") {
    return `<div class="calc-field"><label for="${id}">${escapeHtml(field.title)}</label>` +
      `<input type="checkbox" id="${id}" ${field.default ? "checked" : ""}></div>`;
  }
  if (field.options && field.options.length) {
    const options = field.options.map((opt) =>
      `<option value="${escapeHtml(opt)}" ${opt === field.default ? "selected" : ""}>${escapeHtml(opt)}</option>`).join("");
    control = `<select id="${id}">${options}</select>`;
  } else {
    const type = field.kind === "integer" ? "number" : field.kind === "number" ? "number" : "text";
    const step = field.kind === "number" ? "any" : "1";
    control = `<input type="${type}" id="${id}" step="${step}" value="${field.default !== null && field.default !== undefined ? escapeHtml(field.default) : ""}">`;
  }
  return `<div class="calc-field"><label for="${id}">${escapeHtml(field.title)}</label>${control}</div>`;
}

$("#btn-add-calc").addEventListener("click", async () => {
  const data = await apiFetch("/calculators");
  calcSpecs = data.calculators;
  const select = $("#calc-select");
  select.innerHTML = calcSpecs.map((spec) => `<option value="${spec.id}">${escapeHtml(spec.title)}</option>`).join("");
  renderCalcForm();
  dlgCalc.showModal();
});

function renderCalcForm() {
  const spec = calcSpecs.find((s) => s.id === $("#calc-select").value);
  $("#calc-form").innerHTML = spec ? spec.fields.map(fieldHtml).join("") : "";
  $("#calc-result").classList.add("hidden");
  $("#calc-error").textContent = "";
  $("#btn-calc-add").disabled = true;
  lastResult = null;
}

$("#calc-select").addEventListener("change", renderCalcForm);

$("#btn-calc-run").addEventListener("click", async () => {
  const spec = calcSpecs.find((s) => s.id === $("#calc-select").value);
  if (!spec) return;
  const params = {};
  spec.fields.forEach((field) => {
    const el = document.getElementById("calc-" + field.name);
    if (field.kind === "boolean") params[field.name] = el.checked;
    else if (field.kind === "number" || field.kind === "integer") {
      if (el.value !== "") params[field.name] = Number(el.value);
    } else if (el.value !== "") params[field.name] = el.value;
  });
  $("#calc-error").textContent = "";
  try {
    lastResult = await apiFetch("/calculate", {
      method: "POST",
      body: JSON.stringify({ calculator_id: spec.id, params }),
    });
    const box = $("#calc-result");
    const lines = lastResult.lines.map((line) => `${escapeHtml(line.label)}: ${money(line.amount)}₽`).join("<br>");
    const warnings = lastResult.warnings.length ? "<div>" + lastResult.warnings.map(escapeHtml).join("; ") + "</div>" : "";
    box.innerHTML = `<b>Цена: ${money(lastResult.price)} ₽</b><div class="calc-lines">${lines}</div>${warnings}`;
    // Расход материала (Этап 3) — только для позиций, где он считается.
    const consumption = lastResult.details && lastResult.details.consumption;
    if (consumption && consumption.production_area_m2) {
      const c = consumption;
      box.innerHTML += `<div class="calc-lines muted">Расход: ${Number(c.production_area_m2).toFixed(2)} м² · ${c.pieces_across}×${c.rows} (${escapeHtml(c.orientation)}) · отход ${Number(c.waste_percent).toFixed(1)}%</div>`;
    }
    box.classList.remove("hidden");
    $("#btn-calc-add").disabled = false;
  } catch (error) {
    $("#calc-error").textContent = error.message;
  }
});

$("#btn-calc-add").addEventListener("click", () => {
  if (!lastResult) return;
  const spec = calcSpecs.find((s) => s.id === lastResult.calculator_id);
  // Ручная ширина рулона (правило владельца): передаётся серверу вместе с
  // параметрами, чтобы расход считался по фактическому рулону.
  const params = lastResult.details && lastResult.details.inputs ? { ...lastResult.details.inputs } : {};
  const rollWidth = Number($("#calc-roll-width").value);
  if (rollWidth > 0) params.roll_width_mm = rollWidth;
  addItem({
    kind: "calculator",
    name: spec ? spec.title : lastResult.calculator_id,
    price: lastResult.price,
    qty: 1,
    calculator_id: lastResult.calculator_id,
    params: Object.keys(params).length ? params : null,
  });
  dlgCalc.close();
});

/* ---------- динамические разделы (конструктор) + пожелания ---------- */

let orderSections = [];

function sectionControlHtml(section) {
  const id = "section-" + section.id;
  let control;
  if (section.kind === "textarea") {
    control = `<textarea id="${id}" rows="2" style="width:100%"></textarea>`;
  } else if (section.kind === "select") {
    const options = section.options.map((opt) => `<option value="${escapeHtml(opt)}">${escapeHtml(opt)}</option>`).join("");
    control = `<select id="${id}"><option value="">—</option>${options}</select>`;
  } else if (section.kind === "checkbox") {
    return `<div class="calc-field"><label><input type="checkbox" id="${id}"> ${escapeHtml(section.title)}${section.required ? " *" : ""}</label></div>`;
  } else if (section.kind === "number") {
    control = `<input type="number" id="${id}" step="any">`;
  } else if (section.kind === "date") {
    control = `<input type="date" id="${id}">`;
  } else {
    control = `<input type="text" id="${id}">`;
  }
  return `<div class="calc-field"><label for="${id}">${escapeHtml(section.title)}${section.required ? " *" : ""}</label>${control}</div>`;
}

async function loadOrderSections() {
  const data = await apiFetch("/sections");
  orderSections = data.sections;
  $("#dynamic-sections").innerHTML = orderSections.map(sectionControlHtml).join("");
}

function collectSectionValues() {
  const values = {};
  orderSections.forEach((section) => {
    const el = document.getElementById("section-" + section.id);
    if (!el) return;
    if (section.kind === "checkbox") values[String(section.id)] = el.checked ? "да" : "";
    else values[String(section.id)] = el.value;
  });
  return values;
}

/* ---------- клиент заказа (Этап 1) ---------- */

async function loadClients() {
  const data = await apiFetch("/clients");
  const select = $("#order-client");
  const current = select.value;
  select.innerHTML =
    '<option value="">— без клиента —</option>' +
    data.clients.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
  if (current) select.value = current;
}

/* ---------- сохранение заказа («Добавить») ---------- */

async function loadPaymentMethods() {
  const data = await apiFetch("/settings/payment-methods");
  $("#payment-method").innerHTML = data.methods.map((m) => `<option>${escapeHtml(m)}</option>`).join("");
}

$("#btn-client-new").addEventListener("click", () => { window.location.href = "/clients"; });

$("#btn-save").addEventListener("click", async () => {
  $("#draft-error").textContent = "";
  if (!draft.length) {
    $("#draft-error").textContent = "Добавьте хотя бы одну позицию";
    return;
  }
  const body = {
    status: $("#order-status").value,
    payment_method: $("#payment-method").value,
    items: draft.map((item) => ({
      kind: item.kind,
      price_list_item_id: item.price_list_item_id || null,
      qty: item.qty,
      calculator_id: item.calculator_id || null,
      params: item.params || null,
      name: item.name,
      price: item.price,
      save_to_catalog: item.save_to_catalog !== false,
    })),
    wishes: $("#order-wishes").value,
    section_values: collectSectionValues(),
    client_id: $("#order-client").value ? Number($("#order-client").value) : null,
  };
  try {
    const order = await apiFetch("/orders", { method: "POST", body: JSON.stringify(body) });
    draft = [];
    renderDraft();
    window.location.href = "/orders#" + order.id;
  } catch (error) {
    $("#draft-error").textContent = error.message;
  }
});

loadPaymentMethods();
renderDraft();
loadOrderSections();
loadClients().catch(() => {}); // сев/список клиентов не блокирует приём заказа
