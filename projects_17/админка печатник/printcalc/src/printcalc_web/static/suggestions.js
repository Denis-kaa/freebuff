/* S4: поверхность подсказок Smart Order (РОАДМАП_v7 §5, промт_6 PHASE R4).
 *
 * Правила поведения (анти-правила §6 промт_6):
 *  - НИЧЕГО не применяется само: ✓ добавляет операцию в черновик заказа,
 *    «Изменить» — тоже действие сотрудника; «Нет»/«Уточнить позже» — фиксация.
 *  - Подтверждения логируются в /api/suggestions/decision (кто/когда/что).
 *  - Три разных статуса: факт (Распознано) / предложение / подтверждено.
 *  - Правил во frontend нет: показывается готовый вердикт сервера.
 *
 * Интеграция: глобальная функция window.showSuggestions(verdict, sourceText)
 * вызывается из app.js после разбора текста; операции попадают в черновик
 * через глобальный addItem (объявлен в app.js).
 */

"use strict";

const SUGGEST_API = "/api";

const DECISION_LABEL = {
  accepted: "✓ принято",
  changed: "изменено",
  rejected: "отклонено",
  deferred: "отложено",
};

let currentVerdict = null;

/* S6: явные ответы сотрудника на вопросы вердикта (layout → yes/no).
 * Заполняются кнопками ниже; попадают в /order/bridge только по нажатию
 * «В расчёт» (ничего не применяется само — промт_6 §1). */
const questionAnswers = {};

async function sugFetch(path, options = {}) {
  const response = await fetch(SUGGEST_API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "ошибка запроса");
  return data;
}

async function logDecision(decision, extra) {
  try {
    await sugFetch("/suggestions/decision", {
      method: "POST",
      body: JSON.stringify({
        decision,
        source_text: currentVerdict ? currentVerdict._source_text || "" : "",
        operator: "Денис", // один стенд; учёт сотрудников — отдельный этап
        ...extra,
      }),
    });
  } catch (error) {
    /* аудит не должен ломать приём заказа — ошибка видна в консоли */
    console.warn("аудит подсказок недоступен:", error.message);
  }
}

function esc(text) {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

/* ---------- рендер вердикта ---------- */

function recognizedHtml(v) {
  const parts = [];
  if (v.product) parts.push(`продукт: <b>${esc(v.product)}</b>`);
  if (v.size_mm && v.size_mm.length === 2) {
    parts.push(`размер: <b>${v.size_mm[0]}×${v.size_mm[1]} мм</b>`);
  }
  if (v.quantity) parts.push(`тираж: <b>${esc(v.quantity)} шт</b>`);
  if (v.finishings && v.finishings.length) parts.push(`отделка: ${esc(v.finishings.join(", "))}`);
  if (v.unknown_words && v.unknown_words.length) {
    parts.push(`<span class="sug-unknown">не распознано: ${esc(v.unknown_words.join(", "))}</span>`);
  }
  if (!parts.length) return "<span class=\"muted\">Ничего не распознано</span>";
  return parts.join(" · ");
}

function proposalsHtml(v) {
  if (!v.proposed_operations || !v.proposed_operations.length) return "";
  const rows = v.proposed_operations.map((op, i) => `
    <div class="sug-row" data-op-idx="${i}">
      <span class="sug-label"><b>${esc(op.label)}</b>
        <span class="muted" title="правило: ${esc(op.reason)}">· ${esc(op.reason)}</span></span>
      <span class="row-actions">
        <button class="btn" data-sug-accept="${i}" type="button" title="Добавить операцию в заказ">✓</button>
        <button class="btn" data-sug-change="${i}" type="button" title="Изменить условие">Изменить</button>
      </span>
    </div>`).join("");
  return `<div class="sug-section"><div class="sug-head">Предложения</div>${rows}</div>`;
}

function suggestionsHtml(v) {
  if (!v.suggestions || !v.suggestions.length) return "";
  const rows = v.suggestions.map((s, i) => `
    <div class="sug-row sug-question">
      <span class="sug-label">${esc(s.label)}
        <div class="muted sug-reason" title="${esc(s.reason)}">${esc(s.reason)}</div></span>
      <span class="row-actions">
        ${s.options.map((opt, j) => `
          <button class="btn" data-sug-answer="${i}" data-opt="${j}" type="button">${esc(opt)}</button>`).join("")}
        <button class="btn" data-sug-defer="${i}" type="button" title="Ответим позже">Уточнить позже</button>
      </span>
    </div>`).join("");
  return `<div class="sug-section"><div class="sug-head">Нужно уточнить</div>${rows}</div>`;
}

function missingHtml(v) {
  if (!v.missing || !v.missing.length) return "";
  const rows = v.missing.map((m) => {
    const isLayout = m.field === "layout" || m.field === "layout_with_cut_contour";
    const answered = questionAnswers[m.field];
    if (isLayout && answered) {
      return `
    <div class="sug-row">
      <span class="sug-label">${esc(m.question)} <b class="sug-answer">→ ${answered === "yes" ? "макет есть" : "макета нет — посчитаем"}</b></span>
    </div>`;
    }
    const noLabel = isLayout ? "Нет, посчитать макет" : "Нет";
    return `
    <div class="sug-row ${m.blocking ? "sug-blocker" : ""}">
      <span class="sug-label">${m.blocking ? "⚠ " : ""}${esc(m.question)}
        <span class="muted">(${esc(m.field)})</span></span>
      <span class="row-actions">
        <button class="btn" data-sug-missing-yes="${esc(m.field)}" type="button" title="Указать вручную">Да, указать</button>
        <button class="btn" data-sug-missing-no="${esc(m.field)}" type="button">${esc(noLabel)}</button>
      </span>
    </div>`;
  });
  return `<div class="sug-section"><div class="sug-head">Не хватает данных</div>${rows.join("")}</div>`;
}

function renderVerdict() {
  const box = document.getElementById("suggest-box");
  if (!box || !currentVerdict) return;
  const v = currentVerdict;
  const ready = v.ready_for_calculator
    ? '<span class="sug-ready">готов к расчёту</span>'
    : '<span class="sug-notready">нужны уточнения</span>';
  const bridgeHtml = v.ready_for_calculator
    ? `<div class="sug-bridge"><button class="btn btn-primary" data-sug-bridge type="button">В расчёт →</button>
       <span class="muted">цена считается сервером; работы — только подтверждённые ✓</span></div>`
    : "";
  box.innerHTML = `
    <div class="sug-head">Распознано ${ready}</div>
    <div class="sug-recognized">${recognizedHtml(v)}</div>
    ${proposalsHtml(v)}
    ${missingHtml(v)}
    ${suggestionsHtml(v)}
    ${bridgeHtml}
    <div class="sug-footer muted">Подсказки — от правил «Печатника». Ничего не применено без вашего решения.</div>`;
  box.classList.remove("hidden");
}

/* ---------- S5-мост: вердикт → расчёт ---------- */

let bridgeBusy = false;

async function bridgeToCalculation() {
  /* «В расчёт»: вердикт + ПОДТВЕРЖДЁННЫЕ операции → сервер считает цену
   * (клиент цен не считает); результат падает в черновик заказа как
   * позиция-калькулятор (та же форма, что у обычного расчёта).
   * Ошибка = честное сообщение (нет размера/тиража/пака). */
  if (bridgeBusy || !currentVerdict) return;
  const btn = document.querySelector("[data-sug-bridge]");
  bridgeBusy = true;
  if (btn) { btn.disabled = true; btn.textContent = "считаем…"; }
  try {
    const accepted = (currentVerdict.proposed_operations || [])
      .filter((op) => op._done === "accepted")
      .map((op) => op.operation_token);
    const bridge = await sugFetch("/order/bridge", {
      method: "POST",
      body: JSON.stringify({
        verdict: currentVerdict,
        accepted_operations: accepted,
        question_answers: { ...questionAnswers },
      }),
    });
    const r = bridge.result || {};
    if (typeof window.addItem === "function") {
      window.addItem({
        kind: "calculator",
        name: `Расчёт: ${currentVerdict.product || bridge.calculator_id}`,
        price: r.price || 0,
        qty: 1,
        calculator_id: bridge.calculator_id,
        params: bridge.params || null,
      });
    }
    /* S6: позиции дизайна из ответов «макета нет» — отдельные позиции. */
    const extras = bridge.extra_positions || [];
    for (const extra of extras) {
      if (typeof window.addItem === "function") {
        window.addItem({
          kind: "calculator",
          name: extra.name,
          price: (extra.result && extra.result.price) || 0,
          qty: 1,
          calculator_id: extra.calculator_id,
          params: extra.params || null,
        });
      }
    }
    const box = document.getElementById("suggest-box");
    if (box) {
      const note = document.createElement("div");
      note.className = "sug-bridge-done";
      note.textContent =
        `Добавлено в заказ: ${bridge.calculator_id} — ${Number(r.price || 0).toFixed(2)} ₽` +
        (accepted.length ? ` (работы: ${accepted.join(", ")})` : "") +
        extras.map((e) => ` · ${e.name} — ${Number(e.result?.price || 0).toFixed(2)} ₽`).join("");
      box.querySelector(".sug-footer")?.before(note);
    }
    logDecision("accepted", { kind: "bridge", token: "order/bridge", payload: { calculator_id: bridge.calculator_id, price: r.price } });
  } catch (error) {
    alert("В расчёт: " + error.message);
    if (btn) { btn.disabled = false; btn.textContent = "В расчёт →"; }
  } finally {
    bridgeBusy = false;
  }
}

/* ---------- публичная точка входа ---------- */

window.showSuggestions = function (verdict, sourceText) {
  currentVerdict = verdict ? { ...verdict, _source_text: sourceText || "" } : null;
  renderVerdict();
};

window.suggestAddOperation = function (op) {
  // Мост в черновик главного экрана (app.js): операция → позиция заказа.
  // Цена НЕ считается на клиенте (S5 свяжет с калькулятором) — позиция
  // добавляется с нулевой ценой и пометкой needs_calc.
  if (typeof window.addItem === "function") {
    window.addItem({
      kind: "calculator",
      name: op.label,
      price: 0,
      qty: 1,
      needs_calc: true,
      suggestion_token: op.operation_token,
    });
  }
};

/* ---------- обработчики решений ---------- */

document.addEventListener("click", (event) => {
  const box = document.getElementById("suggest-box");
  if (!box || !box.contains(event.target) || !currentVerdict) return;

  const bridgeBtn = event.target.closest("[data-sug-bridge]");
  if (bridgeBtn) {
    bridgeToCalculation();
    return;
  }

  const acceptBtn = event.target.closest("[data-sug-accept]");
  if (acceptBtn) {
    const op = currentVerdict.proposed_operations[Number(acceptBtn.dataset.sugAccept)];
    window.suggestAddOperation(op);
    op._done = "accepted";
    acceptBtn.textContent = "✓ в заказе";
    acceptBtn.disabled = true;
    logDecision("accepted", { kind: "operation", token: op.operation_token, payload: { label: op.label } });
    return;
  }

  const changeBtn = event.target.closest("[data-sug-change]");
  if (changeBtn) {
    const op = currentVerdict.proposed_operations[Number(changeBtn.dataset.sugChange)];
    logDecision("changed", { kind: "operation", token: op.operation_token, payload: { label: op.label } });
    changeBtn.closest(".sug-row").querySelector("[data-sug-accept]").focus();
    return;
  }

  const answerBtn = event.target.closest("[data-sug-answer]");
  if (answerBtn) {
    const s = currentVerdict.suggestions[Number(answerBtn.dataset.sugAnswer)];
    const answer = s.options[Number(answerBtn.dataset.opt)];
    logDecision("accepted", { kind: "question", field: s.kind, token: s.rule_id, payload: { question: s.label, answer } });
    const row = answerBtn.closest(".sug-row");
    row.innerHTML = `<span class="sug-label">${esc(s.label)} <b class="sug-answer">→ ${esc(answer)}</b></span>`;
    return;
  }

  const deferBtn = event.target.closest("[data-sug-defer]");
  if (deferBtn) {
    const s = currentVerdict.suggestions[Number(deferBtn.dataset.sugDefer)];
    logDecision("deferred", { kind: "question", field: s.kind, token: s.rule_id, payload: { question: s.label } });
    deferBtn.closest(".sug-row").style.opacity = "0.5";
    return;
  }

  const yesBtn = event.target.closest("[data-sug-missing-yes]");
  if (yesBtn) {
    const field = yesBtn.dataset.sugMissingYes;
    const m = (currentVerdict.missing || []).find((x) => x.field === field);
    logDecision("accepted", { kind: "question", field, payload: { question: m ? m.question : field } });
    const value = window.prompt(m ? m.question : field, "");
    if (value !== null && value.trim()) {
      yesBtn.closest(".sug-row").innerHTML =
        `<span class="sug-label">${esc(m ? m.question : field)} <b class="sug-answer">→ ${esc(value.trim())}</b></span>`;
    }
    return;
  }

  const noBtn = event.target.closest("[data-sug-missing-no]");
  if (noBtn) {
    const field = noBtn.dataset.sugMissingNo;
    const m = (currentVerdict.missing || []).find((x) => x.field === field);
    logDecision("rejected", { kind: "question", field, payload: { question: m ? m.question : field } });
    if (field === "layout" || field === "layout_with_cut_contour") {
      /* S6: «макета нет» — осознанный ответ; в мост уйдёт question_answers
       * и (если OP-22 подтверждена) вернётся позиция дизайна. */
      questionAnswers[field] = "no";
      renderVerdict();
      return;
    }
    noBtn.closest(".sug-row").style.opacity = "0.5";
  }

  const yesBtn2 = event.target.closest("[data-sug-missing-yes]");
  if (yesBtn2) {
    const field = yesBtn2.dataset.sugMissingYes;
    if (field === "layout" || field === "layout_with_cut_contour") {
      /* S6: «макет есть» — факт фиксируется и уходит в мост (без позиции). */
      questionAnswers[field] = "yes";
      renderVerdict();
      return;
    }
  }
});
