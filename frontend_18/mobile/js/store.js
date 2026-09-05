/* Store (ТЗ §20) — persistent local state: Whims, Workspaces, Projects.
   Хранится в localStorage. UI state живёт в app.js, данные — здесь. */
(function () {
  "use strict";

  var KEY = "wsos.mobile.v1";

  function seed() {
    var now = Date.now();
    return {
      workspaces: [
        { id: "w1", name: "WHIMCO", desc: "Workspace OS", projectIds: ["p1", "p2", "p3"] },
        { id: "w2", name: "Дом", desc: "Ремонт, быт, личное", projectIds: ["p4"] }
      ],
      projects: {
        p1: { id: "p1", workspaceId: "w1", name: "Mobile Client", note: "Этот фронт" },
        p2: { id: "p2", workspaceId: "w1", name: "Sync Relay", note: "Backend relay" },
        p3: { id: "p3", workspaceId: "w1", name: "Whim Engine", note: "Захват мыслей" },
        p4: { id: "p4", workspaceId: "w2", name: "Ремонт кухни", note: "Смета" }
      },
      whims: [
        { id: "h_seed1", text: "А что если пользователи смогут делиться идеями…", ts: now - 3600e3, status: "synced" }
      ]
    };
  }

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* повреждённые данные — пересидируем */ }
    var data = seed();
    save(data);
    return data;
  }

  function save(data) {
    localStorage.setItem(KEY, JSON.stringify(data));
  }

  function Store() {
    this.data = load();
  }

  Store.prototype.persist = function () { save(this.data); };

  /* ---- Workspaces ---- */
  Store.prototype.getWorkspaces = function () {
    return this.data.workspaces;
  };
  Store.prototype.getWorkspace = function (id) {
    return this.data.workspaces.find(function (w) { return w.id === id; }) || null;
  };
  Store.prototype.getProject = function (id) {
    return this.data.projects[id] || null;
  };
  Store.prototype.getProjectsOf = function (wsId) {
    var self = this;
    return (this.getWorkspace(wsId) || { projectIds: [] }).projectIds
      .map(function (pid) { return self.getProject(pid); })
      .filter(Boolean);
  };

  /* ---- Whims ---- */
  Store.prototype.addWhim = function (text) {
    var whim = {
      id: "h_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7),
      text: text,
      ts: Date.now(),
      status: "local" // §8: local → pending_sync → synced
    };
    this.data.whims.unshift(whim);
    this.persist();
    return whim;
  };
  Store.prototype.updateWhim = function (id, text) {
    var w = this.data.whims.find(function (x) { return x.id === id; });
    if (w) { w.text = text; w.status = "pending_sync"; w.edited = true; this.persist(); }
    return w;
  };
  Store.prototype.deleteWhim = function (id) {
    this.data.whims = this.data.whims.filter(function (x) { return x.id !== id; });
    this.persist();
  };
  Store.prototype.setStatus = function (id, status) {
    var w = this.data.whims.find(function (x) { return x.id === id; });
    if (w) { w.status = status; this.persist(); }
  };
  Store.prototype.markSynced = function (id) {
    this.setStatus(id, "synced");
  };
  Store.prototype.getPendingSync = function () {
    return this.data.whims.filter(function (w) {
      return w.status === "pending_sync" || w.status === "conflict";
    });
  };

  /* ---- Двусторонний sync: merge серверных whims ---- */

  Store.prototype.findWhim = function (id) {
    return this.data.whims.find(function (x) { return x.id === id; }) || null;
  };

  /* upsertServerWhim(sw) — вносит Whim с сервера в локальную историю.
     sw: {id, text, client_id, source, status, created_at}.
     Правила:
       - если server.client_id совпадает с id локального Whim — это
         ОНО и есть: помечаем synced, текст НЕ перезаписываем
         (локальные правки важнее);
       - если серверный id уже есть — дубликат, пропускаем;
       - иначе добавляем как новую запись со статусом synced.
     Возврат: "updated" | "added" | "skip". */
  Store.prototype.upsertServerWhim = function (sw) {
    if (!sw || !sw.id) return "skip";
    var localByClient = sw.client_id ? this.findWhim(sw.client_id) : null;
    if (localByClient) {
      if (localByClient.status !== "synced") {
        localByClient.status = "synced";
        this.persist();
        return "updated";
      }
      return "skip";
    }
    if (this.findWhim(sw.id)) return "skip";
    this.data.whims.push({
      id: sw.id,
      text: sw.text,
      ts: Date.parse(sw.created_at) || Date.now(),
      status: "synced",
      from_server: true
    });
    // Новые сверху: история рендерится по массиву как есть
    this.data.whims.sort(function (a, b) { return b.ts - a.ts; });
    this.persist();
    return "added";
  };
  Store.prototype.getLastWhim = function () {
    return this.data.whims[0] || null;
  };

  window.Store = Store;
})();
