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

reload().catch((e) => alert(e.message));
