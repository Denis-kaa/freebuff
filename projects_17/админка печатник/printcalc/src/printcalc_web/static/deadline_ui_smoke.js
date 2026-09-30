/**
 * Живая проверка страницы /orders (Deadline Engine UI, РОАДМАП_v8 B4).
 *
 * Запуск: google-chrome --headless=new --disable-gpu --dump-dom
 *         --virtual-time-budget=15000 "<url>#deadline-ui-smoke"
 * Скрипт красит <body data-deadline-smoke="ok|fail" data-deadline-errors="…">
 * по итогу проверок; dump-dom читаем grep'ом.
 *
 * Проверки (ТЗ §12–18, §22, §28):
 *  - колонка «Дедлайн» есть; в строках — пилюли с remaining-текстом (не пустые);
 *  - «без дедлайна» → ⚪ (§18);
 *  - счётчики шапки отрисованы (§24);
 *  - фильтр «без дедлайна» перезагружает список и находит заказ (§17/§18);
 *  - сортировка «По срочности» применяется (sort=urgency в запросе);
 *  - диалог заказа: блок ДЕДЛАЙН с datetime-local заполняется из ISO (§22),
 *    сохранение через PUT /deadline обновляет remaining в карточке;
 *  - «отменён» в статусном фильтре (решение владельца).
 */

"use strict";

(async () => {
  const errors = [];
  const ok = (cond, name) => { if (!cond) errors.push(name); };

  const api = async (path, options = {}) => {
    const response = await fetch("/api" + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || response.statusText);
    return data;
  };
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  try {
    // --- подготовка: чистый заказ с дедлайном «сегодня вечером» и без дедлайна ---
    const created = await api("/orders", {
      method: "POST",
      body: JSON.stringify({
        status: "в работе",
        payment_method: "наличные",
        items: [{ kind: "price_list", price_list_item_id: 6, qty: 1 }],
      }),
    });
    const withDeadline = created.id;
    const plain = (await api("/orders", {
      method: "POST",
      body: JSON.stringify({
        status: "новый",
        payment_method: "наличные",
        items: [{ kind: "price_list", price_list_item_id: 6, qty: 1 }],
      }),
    })).id;
    const tonight = new Date(Date.now() + 5 * 3600 * 1000).toISOString();
    await api(`/orders/${withDeadline}/deadline`, {
      method: "PUT",
      body: JSON.stringify({ deadline_type: "customer", value: tonight }),
    });

    // --- 1. Стартовая загрузка: колонка и пилюли ---
    for (let i = 0; i < 40 && document.body.dataset.ordersReady !== "1"; i++) {
      await sleep(250); // ждём первичный loadOrders() из orders.js
    }
    // Дефолтная выдача отсортирована по id desc — целевые заказы «сегодня
    // вечером» могли вытеснить строки из viewport-подмножества списка.
    // Ставим сортировку «По срочности» (сам смоук её и проверяет).
    $("#orders-sort").value = "urgency";
    $("#orders-sort").dispatchEvent(new Event("change"));
    await sleep(800);
    const headers = [...document.querySelectorAll("#orders-table th")].map((th) => th.textContent.trim());
    ok(headers.includes("Дедлайн"), "нет колонки «Дедлайн» в шапке таблицы");

    let bodyRow = [...document.querySelectorAll("#orders-body tr")].find((tr) =>
      tr.querySelector(`button[data-open="${withDeadline}"]`)
    );
    ok(!!bodyRow, "строка заказа с дедлайном не отрисована");
    let cell = bodyRow && bodyRow.cells[7];
    ok(!!cell && /ч\.|мин\.|дн\./.test(cell.textContent), "нет remaining-текста в пилюле дедлайна");
    ok(!!cell && !!cell.querySelector(".deadline-pill"), "пилюля .deadline-pill не отрисована");

    // --- 2. «Без дедлайна» → ⚪, не «Просрочен» (§18) ---
    bodyRow = [...document.querySelectorAll("#orders-body tr")].find((tr) =>
      tr.querySelector(`button[data-open="${plain}"]`)
    );
    cell = bodyRow && bodyRow.cells[7];
    ok(!!cell && cell.textContent.includes("⚪"), "без дедлайна нет ⚪");
    ok(!!cell && !cell.textContent.includes("Просрочен"), "«без дедлайна» показан как просрочен");

    // --- 3. Счётчики шапки (§24) ---
    ok(($("#deadline-counters") || {}).textContent !== undefined, "нет #deadline-counters");
    ok(!!($("#deadline-counters") || {}).textContent, "счётчики шапки пустые");

    // --- 4. Сортировка «По срочности»: запрос уходит с sort=urgency ---
    const sortSelect = $("#orders-sort");
    ok(!!sortSelect, "нет селекта сортировки");
    const fetchSpy = window.fetch;
    let sawUrgencySort = false;
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input.url;
      if (String(url).includes("sort=urgency")) sawUrgencySort = true;
      return fetchSpy.apply(window, [input, init]);
    };
    sortSelect.value = "urgency";
    sortSelect.dispatchEvent(new Event("change"));
    await sleep(800);
    window.fetch = fetchSpy;
    ok(sawUrgencySort, "sort=urgency не ушёл в запрос при смене селекта");

    // --- 5. Фильтр «без дедлайна» находит чистый заказ (§18) ---
    const filterSelect = $("#deadline-filter");
    ok(!!filterSelect, "нет селекта фильтра дедлайнов");
    filterSelect.value = "no_deadline";
    filterSelect.dispatchEvent(new Event("change"));
    await sleep(800);
    const visibleIds = [...document.querySelectorAll("#orders-body button[data-open]")].map((b) => Number(b.dataset.open));
    ok(visibleIds.includes(plain), "фильтр «без дедлайна» не показал чистый заказ");
    ok(!visibleIds.includes(withDeadline), "фильтр «без дедлайна» показал заказ с дедлайном");

    // --- 6. Диалог: блок ДЕДЛАЙН заполнен из ISO, сохранение работает (§22) ---
    // Шаг 5 включил фильтр «без дедлайна» и скрыл заказ с дедлайном — сбрасываем.
    filterSelect.value = "";
    filterSelect.dispatchEvent(new Event("change"));
    await sleep(800);
    const openBtn = [...document.querySelectorAll("#orders-body button[data-open]")].find((b) => Number(b.dataset.open) === withDeadline);
    if (!openBtn) throw new Error("кнопка заказа с дедлайном не найдена после сброса фильтра");
    openBtn.click();
    await sleep(600);
    const dlg = $("#dlg-order");
    ok(dlg.open, "диалог заказа не открылся");
    ok(!!$("#dlg-deadline-customer"), "нет поля customer в блоке ДЕДЛАЙН");
    const localValue = $("#dlg-deadline-customer").value;
    ok(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(localValue), "datetime-local не заполнен из ISO: " + localValue);
    ok(/Осталось:/.test(($("#dlg-deadline-status") || {}).textContent || ""), "нет «Осталось:» в статусе диалога");

    // Сдвигаем дедлайн на +1 час и сохраняем через UI-обработчик.
    const shifted = new Date(Date.now() + 6 * 3600 * 1000);
    $("#dlg-deadline-customer").value = shifted.toISOString().slice(0, 16);
    $("#btn-order-deadline-save").click();
    await sleep(1000);
    const stored = (await api("/orders/" + withDeadline)).customer_deadline;
    ok(Math.abs(new Date(stored).getTime() - shifted.getTime()) < 90 * 1000,
      "PUT /deadline не применил значение из диалога: " + stored);
    ok(/Дедлайны сохранены|сохранены/i.test($("#dlg-order-msg").textContent), "нет подтверждения сохранения в диалоге");
    dlg.close();

    // --- 7. «отменён» в статусном фильтре (решение владельца 09-29) ---
    ok(!!document.querySelector('#status-filter button[data-status="отменён"]'), "нет кнопки фильтра «отменён»");
  } catch (error) {
    errors.push("EXCEPTION: " + error.message);
  }

  const body = document.body;
  body.dataset.deadlineSmoke = errors.length ? "fail" : "ok";
  body.dataset.deadlineErrors = errors.join(" | ");
  console.log("[deadline-smoke]", errors.length ? "FAIL: " + errors.join(" | ") : "OK");
})();