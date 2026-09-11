/* Аналитика: маржинальность прайса vs себестоимость (cost↔каталог). */

"use strict";

const $ = (sel) => document.querySelector(sel);

async function apiFetch(path) {
  const response = await fetch("/api" + path);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "ошибка запроса");
  return data;
}

const fmt = (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(2));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function marginBadge(pct) {
  if (pct === null || pct === undefined) return '<span class="badge">—</span>';
  const cls = pct < 0 ? "badge danger" : pct < 20 ? "badge warn" : "badge ok";
  return `<span class="${cls}">${pct.toFixed(1)}%</span>`;
}

function renderSummary(summary) {
  $("#summary").innerHTML = `
    <div><b>${summary.routed}</b> услуг с маршрутом · <b>${summary.gaps}</b> gaps</div>
    <div>Средняя маржа: <b>${summary.avg_margin_pct}%</b></div>
    <div class="${summary.below_markup > 0 ? 'text-danger' : ''}">Ниже наценки: <b>${summary.below_markup}</b></div>`;
}

function renderServices(rows) {
  const tbody = $("#services-table tbody");
  tbody.innerHTML = rows
    .map((r) => {
      const route = esc(`${r.equipment} · ${r.material}`);
      const batch = r.batch_qty > 1 ? ` (партия ${r.batch_qty} шт)` : "";
      return `<tr>
        <td>${esc(r.name)}<span class="muted">${batch}</span></td>
        <td class="num">${fmt(r.price)}</td>
        <td class="num">${fmt(r.cost_unit)}</td>
        <td class="num">${fmt(r.price_with_markup)}</td>
        <td class="num">${fmt(r.margin_abs)}</td>
        <td class="num">${marginBadge(r.margin_pct)}</td>
        <td class="muted">${route}</td>
        <td>${r.below_markup ? '<span class="badge danger">ниже наценки</span>' : ""}</td>
      </tr>`;
    })
    .join("");
}

function renderMaterials(rows) {
  const tbody = $("#materials-table tbody");
  tbody.innerHTML = rows
    .map((m) => `<tr>
        <td>${esc(m.name)}</td>
        <td class="num ${m.needs_fill ? "text-danger" : ""}">${fmt(m.purchase_cost)}${m.needs_fill ? ' <span class="badge warn">заполнить</span>' : ""}</td>
        <td class="num">${fmt(m.config_cost_unit)}</td>
        <td class="num ${m.delta < 0 ? "text-danger" : ""}">${fmt(m.delta)}</td>
        <td class="muted">${esc(m.equipment)} · ${esc(m.config_material)}</td>
      </tr>`)
    .join("");
}

function renderGaps(services, materials) {
  const tbody = $("#gaps-table tbody");
  const rows = services.map((g) => `<tr>
      <td>${esc(g.name)}</td>
      <td class="num">${fmt(g.price)}</td>
      <td class="muted">${esc(g.reason || "маршрут не задан")}</td>
    </tr>`);
  rows.push(
    ...materials.map((g) => `<tr>
      <td>${esc(g.name)} <span class="badge">материал</span></td>
      <td class="num">—</td>
      <td class="muted">нет материала в конфиге станков</td>
    </tr>`)
  );
  tbody.innerHTML = rows.join("");
}

async function refresh() {
  try {
    const report = await apiFetch("/margin/report");
    renderSummary(report.summary);
    renderServices(report.services);
    renderMaterials(report.materials);
    renderGaps(report.service_gaps, report.material_gaps);
  } catch (err) {
    $("#summary").innerHTML = `<span class="text-danger">Ошибка: ${esc(err.message)}</span>`;
  }
}

$("#btn-refresh").addEventListener("click", refresh);
refresh();
