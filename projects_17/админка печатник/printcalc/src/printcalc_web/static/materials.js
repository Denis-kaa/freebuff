/* Материалы: реестр, диалог создания/правки (Этап 1). */

"use strict";

const $ = (sel) => document.querySelector(sel);

let materials = [];
let editId = null;

async function apiFetch(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "ошибка запроса");
  return data;
}

function esc(text) {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

const MODE_LABELS = {
  AREA: "м²", LINEAR: "пог.м", SHEET: "лист", PIECE: "шт",
  ROLL_NESTING: "рулон", SHEET_NESTING: "раскрой листа", COUNT: "счёт", CUSTOM: "своё",
};

async function reload() {
  const activeOnly = $("#materials-active").checked;
  const data = await apiFetch("/materials" + (activeOnly ? "?active_only=true" : ""));
  materials = data.materials;
  render();
}

function render() {
  $("#materials-body").innerHTML = materials.map((m) => `
    <tr data-id="${m.id}">
      <td>${esc(m.name)}</td>
      <td class="muted">${esc((m.aliases || []).join(", "))}</td>
      <td><span class="badge">${MODE_LABELS[m.consumption_mode] || esc(m.consumption_mode)}</span></td>
      <td>${esc(m.base_unit)}</td>
      <td>${m.purchase_cost} ₽/${esc(m.price_unit)}</td>
      <td class="muted">${m.roll_width ? "рулон " + m.roll_width + " мм" : (m.sheet_width ? `лист ${m.sheet_width}×${m.sheet_height}` : "—")}</td>
      <td class="row-actions"><button class="btn btn-ghost" data-open>править</button></td>
    </tr>`).join("");
}

function fillForm(m) {
  $("#material-name").value = m ? m.name : "";
  $("#material-aliases").value = m ? (m.aliases || []).join(", ") : "";
  $("#material-mode").value = m ? m.consumption_mode : "AREA";
  $("#material-unit").value = m ? m.base_unit : "m2";
  $("#material-cost").value = m ? m.purchase_cost : 0;
  $("#material-minstock").value = m ? m.min_stock : 0;
  $("#material-rollwidth").value = m && m.roll_width != null ? m.roll_width : "";
  $("#material-rolllength").value = m && m.roll_length != null ? m.roll_length : "";
  $("#material-sheetw").value = m && m.sheet_width != null ? m.sheet_width : "";
  $("#material-sheth").value = m && m.sheet_height != null ? m.sheet_height : "";
  $("#material-supplier").value = m && m.supplier != null ? m.supplier : "";
}

function openNew() {
  editId = null;
  $("#material-modal-title").textContent = "Новый материал";
  fillForm(null);
  $("#material-modal").classList.remove("hidden");
}

async function openEdit(id) {
  const m = await apiFetch("/materials/" + id);
  editId = id;
  $("#material-modal-title").textContent = m.name;
  fillForm(m);
  $("#material-modal").classList.remove("hidden");
}

async function save() {
  const numOrNull = (sel) => {
    const v = $(sel).value;
    return v === "" ? null : Number(v);
  };
  const payload = {
    name: $("#material-name").value,
    aliases: $("#material-aliases").value.split(",").map((s) => s.trim()).filter(Boolean),
    consumption_mode: $("#material-mode").value,
    base_unit: $("#material-unit").value,
    purchase_cost: Number($("#material-cost").value || 0),
    min_stock: Number($("#material-minstock").value || 0),
    roll_width: numOrNull("#material-rollwidth"),
    roll_length: numOrNull("#material-rolllength"),
    sheet_width: numOrNull("#material-sheetw"),
    sheet_height: numOrNull("#material-sheth"),
    supplier: $("#material-supplier").value || null,
  };
  if (editId === null) {
    await apiFetch("/materials", { method: "POST", body: JSON.stringify(payload) });
  } else {
    await apiFetch("/materials/" + editId, { method: "PATCH", body: JSON.stringify(payload) });
  }
  $("#material-modal").classList.add("hidden");
  await reload();
}

$("#btn-new-material").addEventListener("click", openNew);
$("#material-close").addEventListener("click", () => $("#material-modal").classList.add("hidden"));
$("#material-save").addEventListener("click", () => save().catch((e) => alert(e.message)));
$("#materials-body").addEventListener("click", (event) => {
  const btn = event.target.closest("[data-open]");
  if (!btn) return;
  openEdit(Number(btn.closest("tr").dataset.id)).catch((e) => alert(e.message));
});
$("#materials-active").addEventListener("change", () => reload().catch((e) => alert(e.message)));

/* ---------- Склад (Этап 5): позиции, движения, инвентаризация, план закупок ---------- */

const KIND_LABELS = {
  PURCHASE: "закупка", RESERVE: "резерв", RELEASE: "снятие резерва",
  CONSUME: "списание", ADJUST: "инвентаризация",
};

async function loadStock() {
  const data = await apiFetch("/stock");
  $("#stock-body").innerHTML = data.positions.map((p) => `
    <tr data-id="${p.material_id}">
      <td>${esc(p.material_name)}</td>
      <td class="num">${p.estimated}</td>
      <td class="num">${p.reserved}</td>
      <td class="num">${p.physical}</td>
      <td class="num">${p.min_stock}</td>
      <td class="row-actions">
        <button class="btn btn-ghost" data-adjust>инвентаризация</button>
        <button class="btn btn-ghost" data-purchase>закупка</button>
      </td>
    </tr>`).join("");
  const moves = await apiFetch("/stock/movements?limit=15");
  $("#stock-movements-body").innerHTML = moves.movements.length
    ? moves.movements.map((m) => `
      <tr>
        <td class="muted">${esc((m.created_at || "").replace("T", " ").slice(0, 16))}</td>
        <td>${esc(m.material_name)}</td>
        <td><span class="badge">${KIND_LABELS[m.kind] || esc(m.kind)}</span></td>
        <td class="num">${m.quantity}</td>
        <td>${m.order_id ? "№" + m.order_id : "—"}</td>
        <td class="muted">${esc(m.note)}</td>
      </tr>`).join("")
    : `<tr><td colspan="6" class="muted">Движений пока нет</td></tr>`;
}

$("#btn-stock-refresh").addEventListener("click", () => loadStock().catch((e) => alert(e.message)));

$("#stock-body").addEventListener("click", (event) => {
  const adjustBtn = event.target.closest("[data-adjust]");
  const purchaseBtn = event.target.closest("[data-purchase]");
  if (!adjustBtn && !purchaseBtn) return;
  const id = Number(event.target.closest("tr").dataset.id);
  const pos = materials.find((m) => m.id === id);
  const unit = pos ? pos.base_unit : "";
  const prompt_text = adjustBtn
    ? `Инвентаризация: сколько ${unit} фактически на складе?`
    : `Приёмка закупки: сколько ${unit} пришло?`;
  const value = window.prompt(prompt_text, "0");
  if (value === null) return;
  const num = Number(value);
  if (Number.isNaN(num) || num < 0) { alert("Введите неотрицательное число"); return; }
  const request = adjustBtn
    ? apiFetch(`/stock/adjust?material_id=${id}`, { method: "POST", body: JSON.stringify({ counted: num }) })
    : apiFetch(`/materials/${id}/purchase`, { method: "POST", body: JSON.stringify({ quantity: num }) });
  request.then(() => loadStock().catch(() => {})).catch((e) => alert(e.message));
});

$("#btn-purchase-plan").addEventListener("click", async () => {
  try {
    const data = await apiFetch("/stock/purchase-plan", { method: "POST", body: JSON.stringify({ required: {} }) });
    const box = $("#purchase-plan-box");
    box.classList.toggle("hidden", data.plan.length === 0);
    $("#purchase-plan-body").innerHTML = data.plan.map((row) => `
      <tr>
        <td>${esc(row.material_name)}</td>
        <td class="num">${row.deficit}</td>
        <td class="num"><b>${row.recommendation}</b></td>
        <td>${esc(row.unit)}</td>
        <td>${row.rounded_to_pack ? "до упаковки " + row.pack_size : "—"}</td>
      </tr>`).join("");
    if (!data.plan.length) alert("Дефицита нет — закупать нечего");
  } catch (e) { alert(e.message); }
});

reload().catch((e) => alert(e.message));
loadStock().catch((e) => alert(e.message));
