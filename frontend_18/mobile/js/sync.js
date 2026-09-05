/* SyncService (ТЗ §9) — абстракция над backend.
   Реальная реализация: REST POST/GET http://127.0.0.1:8765/api/v1/whims
   (scripts_01/mcp_fastapi.py, Bearer auth). При недоступности backend
   или офлайне — offline-first поведение (§8): статус pending_sync,
   авто-flush по событию online.

   Конфигурация (localStorage):
     wsos.apiBase  — базовый URL backend (default http://127.0.0.1:8765)
     wsos.mcpToken — Bearer token (FREEBUFF_MCP_TOKEN на стороне сервера)
*/
(function () {
  "use strict";

  var REQUEST_TIMEOUT_MS = 5000;

  function apiBase() {
    return localStorage.getItem("wsos.apiBase") || "http://127.0.0.1:8765";
  }

  function apiToken() {
    return localStorage.getItem("wsos.mcpToken") || "";
  }

  function isOnline() {
    return navigator.onLine !== false;
  }

  function configured() {
    return Boolean(apiToken());
  }

  /* fetch с таймаутом и Bearer auth */
  function request(method, path, body) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, REQUEST_TIMEOUT_MS);
    return fetch(apiBase() + path, {
      method: method,
      headers: Object.assign(
        { "Content-Type": "application/json" },
        apiToken() ? { "Authorization": "Bearer " + apiToken() } : {}
      ),
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal
    }).then(function (res) {
      clearTimeout(timer);
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).finally(function () { clearTimeout(timer); });
  }

  var listeners = [];

  function notifyFlushed(sent) {
    listeners.forEach(function (cb) { cb(sent); });
  }

  function renderTick() {
    document.dispatchEvent(new CustomEvent("sync:update"));
  }

  /* Отправка одного Whim в backend. Возвращает Promise<{ok,status}>.
     Ошибки сети НЕ роняют UI — Whim остаётся локальным со pending_sync. */
  function relaySend(whim) {
    return request("POST", "/api/v1/whims", {
      text: whim.text,
      client_id: whim.id,
      status: "synced"
    }).then(function (json) {
      if (!json || json.success !== true) throw new Error(json && json.error);
      return { ok: true };
    }).catch(function () {
      return { ok: false };
    });
  }

  function flushQueue(store) {
    if (!isOnline()) return Promise.resolve(0);
    var pending = store.getPendingSync().filter(function (w) {
      // conflict требует ручного разрешения — автоматически не отправляем
      return w.status === "pending_sync";
    });
    var sent = 0;
    var chain = Promise.resolve();
    pending.forEach(function (whim) {
      chain = chain.then(function () {
        return relaySend(whim).then(function (res) {
          if (res.ok) {
            store.markSynced(whim.id);
            sent++;
            renderTick();
          }
        });
      });
    });
    return chain.then(function () {
      if (sent > 0) notifyFlushed(sent);
      return sent;
    });
  }

  function SyncService(store) {
    this.store = store;
    var self = this;

    window.addEventListener("online", function () {
      self.toast("Соединение восстановлено — синхронизация…");
      flushQueue(self.store);
    });
    window.addEventListener("offline", function () {
      self.toast("Офлайн — Whims сохраняются локально");
    });

    // Авто-попытка при старте (незавершённая очередь)
    flushQueue(this.store);
  }

  SyncService.prototype.send = function (whim) {
    var store = this.store;
    if (!isOnline()) {
      store.setStatus(whim.id, "pending_sync");
      return Promise.resolve({ ok: false, status: "pending_sync" });
    }
    if (!configured()) {
      // Backend не настроен — работаем как раньше (локальный мок-режим)
      store.setStatus(whim.id, "local");
      return Promise.resolve({ ok: true, status: "local" });
    }
    store.setStatus(whim.id, "pending_sync");
    return relaySend(whim).then(function (res) {
      if (res.ok) {
        store.markSynced(whim.id);
        renderTick();
        return { ok: true, status: "synced" };
      }
      store.setStatus(whim.id, "conflict");
      return { ok: false, status: "conflict" };
    });
  };

  SyncService.prototype.flush = function () {
    return flushQueue(this.store);
  };

  SyncService.prototype.pull = function () {
    /* Тянет историю whims с backend (GET /api/v1/whims).
       Возвращает Promise<Array> — пустой массив при ошибке. */
    if (!isOnline() || !configured()) return Promise.resolve([]);
    return request("GET", "/api/v1/whims?limit=100")
      .then(function (json) {
        return (json && json.success && json.data.whims) || [];
      })
      .catch(function () { return []; });
  };

  SyncService.prototype.onFlushed = function (cb) { listeners.push(cb); };

  SyncService.prototype.toast = function (text) {
    var t = document.getElementById("toast");
    t.textContent = text;
    t.hidden = false;
    clearTimeout(this._tt);
    this._tt = setTimeout(function () { t.hidden = true; }, 2600);
  };

  window.SyncService = SyncService;
})();
