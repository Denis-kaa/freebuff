/* Админка прайс-каталога: CRUD, фильтр непроверенных, импорт списком. */

"use strict";

const $ = (sel) => document.querySelector(sel);
const money = (n) => Number(n).toFixed(2);

let editingId = null;

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

async function loadItems() {
  const query = $("#search").value.trim();
  const unverified = $("#only-unverified").checked ? "&unverified=true" : "";
  const data = await apiFetch("/price-list?q=" + encodeURIComponent(query) + unverified);
  const body = $("#items-body");
  body.innerHTML = "";
  data.items.forEach((item) => {
    const tr = document.createElement("tr");
    const badge = item.unverified ? ' <span class="badge unverified">не проверено</span>' : "";
    const synonyms = item.synonyms.length ? `<div class="muted">синонимы: ${escapeHtml(item.synonyms.join(", "))}</div>` : "";
    tr.innerHTML =
      `<td>${escapeHtml(item.name)}${badge}${synonyms}</td>` +
      `<td class="num">${money(item.price)}</td>` +
      `<td>${escapeHtml(item.unit || "шт")}</td>` +
      `<td>${escapeHtml(item.category || "")}</td>` +
      `<td class="num">${item.usage_count}</td>` +
      `<td><button data-edit="${item.id}">править</button></td>`;
    body.appendChild(tr);
  });
  if (!data.items.length) {
    body.innerHTML = '<tr><td colspan="6" class="muted">Каталог пуст — добавьте первую позицию кнопкой «+ позиция»</td></tr>';
  }
}

let searchTimer;
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadItems, 250);
});
$("#only-unverified").addEventListener("change", loadItems);

document.addEventListener("click", (event) => {
  if (event.target.matches("[data-close]")) event.target.closest("dialog").close();
  const editId = event.target.getAttribute && event.target.getAttribute("data-edit");
  if (editId) openEdit(Number(editId));
});

function openDialog(title, item) {
  $("#dlg-title").textContent = title;
  $("#item-name").value = item ? item.name : "";
  $("#item-price").value = item ? item.price : "";
  $("#item-unit").value = item && item.unit ? item.unit : "";
  $("#item-category").value = item && item.category ? item.category : "";
  $("#item-error").textContent = "";
  $("#dlg-item").showModal();
}

$("#btn-add").addEventListener("click", () => {
  editingId = null;
  openDialog("Новая позиция", null);
});

async function openEdit(id) {
  const data = await apiFetch("/price-list?q=");
  const item = data.items.find((entry) => entry.id === id);
  if (!item) return;
  editingId = id;
  openDialog("Правка позиции", item);
}

$("#btn-item-save").addEventListener("click", async () => {
  const payload = {
    name: $("#item-name").value.trim(),
    price: parseFloat($("#item-price").value),
    unit: $("#item-unit").value.trim() || null,
    category: $("#item-category").value.trim() || null,
  };
  if (!payload.name || isNaN(payload.price) || payload.price < 0) {
    $("#item-error").textContent = "Нужны название и цена ≥ 0";
    return;
  }
  try {
    if (editingId === null) {
      await apiFetch("/price-list", { method: "POST", body: JSON.stringify(payload) });
    } else {
      await apiFetch("/price-list/" + editingId, { method: "PATCH", body: JSON.stringify(payload) });
    }
    $("#dlg-item").close();
    loadItems();
  } catch (error) {
    $("#item-error").textContent = error.message;
  }
});

$( "#btn-import").addEventListener("click", async () => {
  const text = $("#import-text").value;
  if (!text.trim()) return;
  try {
    // «;»-формат (шаблон из Excel) — обновляет цены; старый «-»-формат — только добавляет.
    const isTemplate = text.includes(";");
    const endpoint = isTemplate ? "/price-list/import-template" : "/price-list/import";
    const result = await apiFetch(endpoint, { method: "POST", body: JSON.stringify({ text }) });
    if (isTemplate) {
      $("#import-result").textContent =
        `Обновлено: ${result.updated}; создано: ${result.created}`;
    } else {
      $("#import-result").textContent =
        `Создано: ${result.created}` +
        (result.skipped.length ? `; пропущено: ${result.skipped.length} (${result.skipped[0].line.slice(0, 30)}…)` : "");
    }
    $("#import-text").value = "";
    loadItems();
  } catch (error) {
    $("#import-result").textContent = "Ошибка: " + error.message;
  }
});

loadItems();
