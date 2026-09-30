/* Локальный помощник (Assistant v2.0): чат-интерфейс над Smart Order.
 *
 * Архитектура (ТЗ §36): НИКАКОЙ второй логики — чат только рендерит
 * вердикт POST /api/order/analyze; подтверждения → существующий
 * /api/suggestions/decision (аудит, §28); расчёт → существующий
 * /api/order/bridge (цена ТОЛЬКО сервером, §30).
 * A6: 8 режимов ответа (§18-26) — презентационный слой поверх вердикта.
 */

"use strict";

const $ = (sel) => document.querySelector(sel);

/* ---------- утилиты ---------- */

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

/* ---------- состояние чата ---------- */

let lastVerdict = null; // для [Рассчитать] и контекста follow-up

const feed = () => $("#assistant-feed");

function addBubble(role, html) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble chat-${role}`;
  bubble.innerHTML = html;
  feed().appendChild(bubble);
  feed().scrollTop = feed().scrollHeight;
  return bubble;
}

function addUser(text) {
  addBubble("user", `<div class="chat-who">Оператор</div>${esc(text)}`);
}

/* ---------- рендер блоков вердикта (ТЗ §34) ---------- */

function block(title, items, cls = "") {
  if (!items.length) return "";
  return `<div class="chat-block ${cls}">
    <div class="chat-block-title">${esc(title)}</div>
    ${items.map((line) => `<div class="chat-line">${line}</div>`).join("")}
  </div>`;
}

function fmtSize(verdict) {
  if (!verdict.size_mm) return null;
  const [w, h] = verdict.size_mm;
  return `${w}×${h} мм`;
}

function fmtFacts(verdict) {
  const f = verdict.facts || {};
  const parts = [];
  if (f.dpi) parts.push(`${f.dpi} dpi`);
  if (f.thickness_mm) parts.push(`толщина ${f.thickness_mm} мм`);
  if (f.material_hint) parts.push(`материал: ${f.material_hint}`);
  if (f.grommets) parts.push(f.grommets_step_cm ? `люверсы через ${f.grommets_step_cm} см` : "люверсы");
  if (f.cutting_mode === "contour") parts.push("резка по контуру");
  if (f.cutting_mode === "individual") parts.push("резка поштучно");
  if (f.mounting_film) parts.push("монтажная плёнка");
  if (f.duplex) parts.push("двусторонняя");
  if (f.usage) parts.push(`использование: ${f.usage}`);
  if (f.extra_sizes) parts.push(`ещё размеры: ${f.extra_sizes.join(", ")}`);
  return parts;
}

function fmtQty(verdict) {
  return verdict.quantity != null ? `${verdict.quantity} шт` : null;
}

/** Распознано — единая строка-сводка (ТЗ §34). */
function recognizedLines(verdict) {
  const lines = [];
  const who = verdict.product || (verdict.matched_pack ? verdict.matched_pack : "продукт не распознан");
  const bits = [who, fmtSize(verdict), fmtQty(verdict)].filter(Boolean);
  if (bits.length > 1 || verdict.matched_pack) lines.push(bits.join(" · "));
  const extra = fmtFacts(verdict);
  lines.push(...extra);
  if (verdict.finishings && verdict.finishings.length) {
    lines.push(...verdict.finishings.map((x) => `обработка: ${x}`));
  }
  if (!lines.length) lines.push("ничего не распознано — уточните фразу");
  return lines;
}

function missingLines(verdict) {
  return (verdict.missing || []).map((m) =>
    m.blocking ? `${esc(m.question)} <span class="chip chip-block">блокирует расчёт</span>` : esc(m.question)
  );
}

function suggestionLines(verdict) {
  return (verdict.suggestions || []).map((s) =>
    `${esc(s.label || s.kind)}${s.reason ? ` <span class="muted">— ${esc(s.reason)}</span>` : ""}`
  );
}

function operationLines(verdict) {
  return (verdict.proposed_operations || []).map((o) =>
    `${esc(o.label)} <span class="muted">(${esc(o.operation_token)})</span>`
  );
}

function warningLines(verdict) {
  return (verdict.warnings || []).map((w) => `⚠ ${esc(w)}`);
}

/* ---------- Дедлайн-вопросы (ТЗ §26 второй части) ----------
 * Отчёт рендерится из POST /api/deadline/query — тот же вычисляемый
 * слой Deadline Engine, что у списка /orders. Отдельного источника
 * данных помощник не создаёт; LLM нет — закрытый словарь интентов.
 */

const URGENCY_VIEW = {
  overdue: "⛔",
  very_critical: "🔴",
  critical: "🟠",
  urgent: "🟡",
  warning: "🟢",
  normal: "🟢",
};

function renderDeadlineReport(report) {
  const counts = report.counts || {};
  const counterLine = [
    `просрочено: ${counts.overdue || 0}`,
    `критично: ${(counts.very_critical || 0) + (counts.critical || 0)}`,
    `сегодня: ${counts.urgent || 0}`,
    `без дедлайна: ${counts.no_deadline || 0}`,
  ].join(" · ");
  const rows = (report.orders || []).map((o) => {
    const icon = URGENCY_VIEW[o.urgency_status] || "⚪";
    const name = (o.items && o.items.length ? o.items.join(", ") : "заказ");
    const client = o.client_name ? ` — ${esc(o.client_name)}` : "";
    return `<div class="chat-line">${icon} <b>#${o.id}</b> ${esc(name)}${client}
      <span class="muted">· ${esc(o.remaining)} · ${esc(o.status)}</span></div>`;
  });
  return [
    `<div class="chat-block"><div class="chat-block-title">${esc(report.title)}</div>`,
    `<div class="chat-line muted">${esc(counterLine)}</div>`,
    rows.length ? rows.join("") : `<div class="chat-line">ничего не найдено.</div>`,
    `</div>`,
    `<div class="chat-line muted">Источник: Order/Deadline API (ТЗ §26) — тот же расчёт, что у списка заказов.</div>`,
  ].join("");
}

/* ---------- A6: 8 режимов (§18–26) ---------- */

const MODES = {
  /** §19 Быстрый: распознано / сделать / уточнить. */
  quick(v) {
    return [
      block("Распознано", recognizedLines(v)),
      block("Нужно сделать", operationLines(v)),
      block("Нужно уточнить", missingLines(v)),
    ].join("");
  },
  /** §20 Рабочий (default): Распознано / В «Печатнике» / Уточнить / Предложить. */
  work(v) {
    return [
      block("Распознано", recognizedLines(v)),
      block("В «Печатнике»", operationLines(v)),
      block("Нужно уточнить", missingLines(v)),
      block("Можно предложить", suggestionLines(v)),
    ].join("");
  },
  /** §21 Подробный: + правила, unknown, отсутствующие параметры. */
  detailed(v) {
    const rules = (v.fired_rules || []).map((r) =>
      `${esc(r.rule_id || r)}${r.description ? ` — ${esc(r.description)}` : ""}`
    );
    const unknown = (v.unknown_words || []).map((w) => `«${esc(w)}» — не распознано`);
    return [
      block("Распознано", recognizedLines(v)),
      block("Нужно сделать", operationLines(v)),
      block("Сработавшие правила", rules),
      block("Отсутствуют параметры", missingLines(v)),
      block("Не распознано", unknown),
      block("Можно предложить", suggestionLines(v)),
    ].join("");
  },
  /** §22 Обучение: что значит операция, зачем, что спросить/проверить. */
  teach(v) {
    const explain = (v.proposed_operations || []).map(
      (o) => `${esc(o.label)} (${esc(o.operation_token)}) — предложено правилом «${esc(o.reason)}»; подтвердите, если это входит в заказ`
    );
    const ask = (v.missing || []).map((m) => `спросить у клиента: ${esc(m.question)}`);
    return [
      block("Что распознано", recognizedLines(v)),
      block("Что это значит", explain.length ? explain : ["операций не предложено"]),
      block("Что сделать", operationLines(v)),
      block("Что спросить / проверить", ask),
    ].join("");
  },
  /** §23 Только уточнения: только недостающие данные. */
  clarify(v) {
    return block("Нужно уточнить", missingLines(v)) || `<div class="chat-line muted">Всё нужное распознано.</div>`;
  },
  /** §24 Производство: материал/размер/кол-во/технология/операции/макет. */
  production(v) {
    const f = v.facts || {};
    const rows = [
      f.material_hint ? `материал: ${esc(f.material_hint)}` : "материал: не указан",
      fmtSize(v) || "размер: не указан",
      fmtQty(v) || "количество: не указано",
      f.dpi ? `качество: ${f.dpi} dpi` : null,
      f.thickness_mm ? `толщина: ${f.thickness_mm} мм` : null,
      ...(v.finishings || []).map((x) => `обработка: ${esc(x)}`),
      f.cut ? "макет: резка подразумевается" : "макет: уточнить",
    ].filter(Boolean);
    return [
      block("Производственный срез", rows),
      block("Операции", operationLines(v)),
      block("Уточнить", missingLines(v)),
    ].join("");
  },
  /** §25 Продажа: только релевантные допы из suggestions (не всё подряд). */
  sales(v) {
    const upsell = (v.suggestions || []).filter((s) => s.kind !== "question");
    return [
      block("Распознано", recognizedLines(v).slice(0, 1)),
      block("Можно предложить", suggestionLines(upsell.length ? { suggestions: upsell } : v)),
      block("Уточнить", missingLines(v)),
    ].join("");
  },
  /** §26 Проверка: чек-лист перед расчётом. */
  check(v) {
    const ok = (x) => `✓ ${x}`;
    const no = (x) => `✗ ${x}`;
    const rows = [
      v.matched_pack ? ok(`услуга: ${esc(v.product)} (пак «${esc(v.matched_pack)}»)`) : no("услуга: вне паков"),
      v.size_mm ? ok(`размер: ${fmtSize(v)}`) : no("размер отсутствует"),
      v.quantity != null ? ok(`количество: ${v.quantity}`) : no("количество отсутствует"),
      v.facts && v.facts.material_hint ? ok(`материал: ${esc(v.facts.material_hint)}`) : "• материал не указан",
      (v.proposed_operations || []).length ? ok("операции предложены") : "• операции: не предложены",
      ...(v.missing || []).map((m) => (m.blocking ? no(esc(m.question)) : `• ${esc(m.question)}`)),
    ];
    const conflicts = warningLines(v);
    return [
      block("Проверка заказа", rows),
      conflicts.length ? block("Конфликты", conflicts) : "",
      v.ready_for_calculator
        ? `<div class="chat-line ok">Готов к расчёту.</div>`
        : `<div class="chat-line">К расчёту не готов — заполните блокирующие поля.</div>`,
    ].join("");
  },
};

function renderVerdict(v) {
  const mode = $("#assistant-mode").value;
  const render = MODES[mode] || MODES.work;
  let html = render(v);
  if (warningLines(v).length && mode !== "check") {
    html += block("Предупреждения", warningLines(v), "chat-warn");
  }
  html += actionsHtml(v);
  return html;
}

/* ---------- Действия: подтверждения (§28) и расчёт (§30) ---------- */

function actionsHtml(v) {
  const ops = v.proposed_operations || [];
  const canPrice = v.ready_for_calculator === true && v.matched_pack;
  let html = `<div class="chat-actions">`;
  for (const o of ops) {
    html += `<button class="btn btn-sm" type="button" data-decision="accepted" data-kind="operation"
      data-token="${esc(o.operation_token)}" data-label="${esc(o.label)}">[+ ${esc(o.label)}]</button>`;
    html += `<button class="btn btn-sm btn ghost" type="button" data-decision="rejected" data-kind="operation"
      data-token="${esc(o.operation_token)}" data-label="${esc(o.label)}">[без ${esc(o.label)}]</button>`;
  }
  for (const s of v.suggestions || []) {
    if (s.kind === "question") continue; // вопросы — не кнопки, это missing
    html += `<button class="btn btn-sm" type="button" data-decision="accepted" data-kind="${esc(s.kind || "")}"
      data-token="${esc(s.label || "")}">[+ ${esc(s.label || s.kind)}]</button>`;
  }
  if (canPrice) {
    html += `<button class="btn btn-sm btn primary" type="button" id="assistant-price-btn">[Рассчитать]</button>`;
  }
  html += `</div>`;
  return html;
}

async function recordDecision(decision, kind, token, extra = {}) {
  // Существующий аудит-эндпоинт (§28: «не создавать новую систему»).
  await apiFetch("/suggestions/decision", {
    method: "POST",
    body: JSON.stringify({
      decision,
      kind,
      token,
      source_text: lastVerdict ? lastVerdict.text || "" : "",
      payload: extra,
    }),
  });
}

async function showPrice() {
  if (!lastVerdict) return;
  try {
    // Контракт S4: только ПОДТВЕРЖДЁННЫЕ операции (кнопки [+ …]) уезжают в цену.
    const tokens = window.__assistantAcceptedOps || [];
    const bridge = await apiFetch("/order/bridge", {
      method: "POST",
      body: JSON.stringify({ verdict: lastVerdict, accepted_operations: tokens }),
    });
    const body = $("#assistant-price-body");
    body.innerHTML = `
      <p><strong>Калькулятор:</strong> ${esc(bridge.calculator_id)}</p>
      <p><strong>Параметры:</strong> <code>${esc(JSON.stringify(bridge.params))}</code></p>
      <p class="ok"><strong>Цена:</strong> ${esc(String(bridge.result.price))} ₽</p>
      <p class="muted">Расчёт выполнен серверным движком; помощник цену не придумывает (ТЗ §30).</p>`;
    $("#assistant-price-dialog").showModal();
  } catch (err) {
    addBubble("assistant", `<div class="chat-block"><div class="chat-line error">Расчёт не удался: ${esc(err.message)}</div></div>`);
  }
}

/* ---------- отправка фразы ---------- */

async function send(text) {
  const trimmed = text.trim();
  if (!trimmed) return;
  addUser(trimmed);
  $("#assistant-text").value = "";
  try {
    // Дедлайн-вопросы (ТЗ §26) перехватываются ДО analyze: если фраза
    // распознана закрытым словарём интентов — отвечает Deadline API;
    // 404 = «не дедлайн-вопрос» → обычный поток анализа.
    try {
      const report = await apiFetch("/deadline/query", {
        method: "POST",
        body: JSON.stringify({ text: trimmed }),
      });
      addBubble("assistant", renderDeadlineReport(report));
      return;
    } catch (err) {
      if (!/не дедлайн-вопрос/.test(String(err.message))) throw err;
    }
    const verdict = await apiFetch("/order/analyze", { method: "POST", body: JSON.stringify({ text: trimmed }) });
    lastVerdict = verdict;
    window.__assistantAcceptedOps = [];
    addBubble("assistant", renderVerdict(verdict));
  } catch (err) {
    addBubble("assistant", `<div class="chat-line error">Ошибка анализа: ${esc(err.message)}</div>`);
  }
}

/* ---------- события ---------- */

document.addEventListener("DOMContentLoaded", () => {
  $("#assistant-form").addEventListener("submit", (e) => {
    e.preventDefault();
    send($("#assistant-text").value);
  });

  $("#assistant-mode").addEventListener("change", () => {
    if (lastVerdict) {
      // Перерисовать последний ответ в новом режиме (презентационный слой).
      const bubbles = feed().querySelectorAll(".chat-assistant");
      const last = bubbles[bubbles.length - 1];
      if (last) {
        last.innerHTML = renderVerdict(lastVerdict);
      }
    }
  });

  $("#assistant-clear").addEventListener("click", () => {
    feed().innerHTML = "";
    lastVerdict = null;
    window.__assistantAcceptedOps = [];
  });

  feed().addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    if (btn.id === "assistant-price-btn") {
      await showPrice();
      return;
    }
    const decision = btn.dataset.decision;
    if (!decision) return;
    const kind = btn.dataset.kind || "";
    const token = btn.dataset.token || "";
    await recordDecision(decision, kind, token, { label: btn.dataset.label || "" });
    if (decision === "accepted" && kind === "operation") {
      window.__assistantAcceptedOps.push(token);
      btn.disabled = true;
      btn.textContent = `✓ ${btn.dataset.label}`;
    } else {
      btn.disabled = true;
    }
  });

  document.querySelectorAll("[data-close]").forEach((b) =>
    b.addEventListener("click", () => {
      const dlg = document.getElementById(b.dataset.close);
      if (dlg && dlg.close) dlg.close();
    })
  );
});
