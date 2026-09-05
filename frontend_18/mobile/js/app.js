/* Workspace OS Mobile — главный модуль: hash-роутер (§21), экраны, голосовой Whim (§6–7) */
(function () {
  "use strict";

  var store = new Store();
  var sync = new SyncService(store);

  var app = document.getElementById("app");

  /* ---------- Утилиты ---------- */

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtTime(ts) {
    var d = new Date(ts);
    var today = new Date();
    var sameDay = d.toDateString() === today.toDateString();
    var time = d.getHours() + ":" + String(d.getMinutes()).padStart(2, "0");
    return sameDay ? "сегодня, " + time : d.toLocaleDateString("ru-RU") + ", " + time;
  }

  function dayLabel(ts) {
    var d = new Date(ts);
    var today = new Date();
    var yest = new Date(today); yest.setDate(yest.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return "Сегодня";
    if (d.toDateString() === yest.toDateString()) return "Вчера";
    return d.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" });
  }

  function syncBadge(status) {
    var map = {
      local: ["local", "локально"],
      pending_sync: ["pending", "↻ ожидает синхронизации"],
      synced: ["synced", "✓ синхронизирован"],
      conflict: ["conflict", "⚠ конфликт"]
    };
    var m = map[status] || map.local;
    return '<span class="sync-badge sync-badge--' + m[0] + '">' + m[1] + "</span>";
  }

  function toast(text) {
    sync.toast(text);
  }

  /* ---------- Экран: Dashboard (§3–4) ---------- */

  function renderDashboard() {
    var last = store.getLastWhim();
    var wss = store.getWorkspaces();

    var whimHtml = last
      ? '<div class="card whim-card">' +
        '<div class="whim-card__label">WHIM</div>' +
        '<div class="whim-card__text">' + esc(last.text) + "</div>" +
        '<div class="whim-card__meta"><span>' + fmtTime(last.ts) + "</span>" + syncBadge(last.status) + "</div>" +
        '<button class="whim-open-btn" id="openHistory" aria-label="История whims">↗</button>' +
        "</div>"
      : '<div class="card"><div class="whim-card__label">WHIM</div><p class="empty">Пока нет мыслей. Нажмите + WHIM.</p></div>';

    var wsCards = wss.map(function (w) {
      return '<a href="#/workspace/' + w.id + '" style="text-decoration:none;color:inherit">' +
        '<div class="card card--clickable ws-card">' +
        "<h3>🚀 " + esc(w.name) + "</h3>" +
        "<p>" + esc(w.desc) + "</p>" +
        "<p>" + w.projectIds.length + " projects</p>" +
        "</div></a>";
    }).join("");

    app.innerHTML =
      '<div class="screen">' +
      '<div class="screen__header"><h1>Workspace OS</h1>' +
      '<span class="screen__date">' + new Date().toLocaleDateString("ru-RU", { day: "numeric", month: "long" }) + "</span></div>" +
      whimHtml +
      '<div class="section-title">Workspaces</div>' +
      '<div class="ws-grid">' + wsCards + "</div>" +
      "</div>";

    var openBtn = document.getElementById("openHistory");
    if (openBtn) openBtn.onclick = openWhimHistory;
  }

  /* ---------- Экран: Workspace (§11–12) ---------- */

  function renderWorkspace(wsId) {
    var ws = store.getWorkspace(wsId);
    if (!ws) { location.hash = "#/"; return; }
    var projects = store.getProjectsOf(wsId);

    var tiles = projects.map(function (p) {
      return '<a href="#/workspace/' + wsId + "/project/" + p.id + '" style="text-decoration:none;color:inherit">' +
        '<div class="proj-tile card--clickable"><h4>' + esc(p.name) + "</h4><span>" + esc(p.note || "") + "</span></div></a>";
    }).join("");

    app.innerHTML =
      '<div class="screen">' +
      '<div class="screen__header">' +
      '<button class="icon-btn" onclick="location.hash=\'#/\'" aria-label="Назад">←</button>' +
      "<h1>" + esc(ws.name) + "</h1></div>" +
      '<div class="tabs" role="tablist">' +
      ["Projects", "Files", "Whims", "Tasks", "Knowledge", "Chat"].map(function (t, i) {
        return '<button class="tab" role="tab" aria-selected="' + (i === 0) + '">' + t + "</button>";
      }).join("") +
      "</div>" +
      '<div class="proj-grid">' + tiles + "</div>" +
      "</div>";

    // Переключение табов — в v0.1 активны Projects; остальные — заглушки §25
    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (btn) {
      btn.addEventListener("click", function () {
        if (btn.textContent === "Chat") { renderWorkspaceChat(wsId); return; }
        Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
          b.setAttribute("aria-selected", b === btn);
        });
      });
    });
    updatePanelContext("Workspace: " + ws.name);
  }

  /* ---------- Экран: Chat внутри workspace/project (§16) ---------- */

  function chatScreen(title, backHash, contextLine) {
    app.innerHTML =
      '<div class="screen">' +
      '<div class="screen__header">' +
      '<button class="icon-btn" onclick="location.hash=\'' + backHash + '\'" aria-label="Назад">←</button>' +
      "<h1>" + esc(title) + "</h1></div>" +
      '<p class="hint">' + esc(contextLine) + "</p>" +
      '<div class="chat" id="chatLog"></div>' +
      '<div class="chat-input-row">' +
      '<input id="chatInput" type="text" placeholder="Сообщение агенту…" aria-label="Сообщение" />' +
      '<button class="btn btn--primary" id="chatSend">→</button>' +
      "</div></div>";

    var log = document.getElementById("chatLog");
    var input = document.getElementById("chatInput");
    input.focus();

    function send() {
      var text = input.value.trim();
      if (!text) return;
      log.insertAdjacentHTML("beforeend", '<div class="msg msg--user">' + esc(text) + "</div>");
      input.value = "";
      if (typeof log.scrollIntoView === "function") log.scrollIntoView({ block: "end" });
      // v0.1: локальный эхо-ответ. AI подключается через backend/API (§16).
      setTimeout(function () {
        log.insertAdjacentHTML("beforeend",
          '<div class="msg msg--ai">Принял. Контекст: ' + esc(contextLine) + ". (AI backend будет подключён позже.)</div>");
      }, 500);
    }
    document.getElementById("chatSend").onclick = send;
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });
  }

  function renderWorkspaceChat(wsId) {
    var ws = store.getWorkspace(wsId);
    chatScreen(ws.name + " · Chat", "#/workspace/" + wsId, "Workspace «" + ws.name + "»");
  }

  /* ---------- Экран: Project (§15) ---------- */

  function renderProject(wsId, projectId) {
    var p = store.getProject(projectId);
    var ws = store.getWorkspace(wsId);
    if (!p) { location.hash = "#/workspace/" + wsId; return; }

    app.innerHTML =
      '<div class="screen">' +
      '<div class="screen__header">' +
      '<button class="icon-btn" onclick="location.hash=\'#/workspace/' + wsId + '\'" aria-label="Назад">←</button>' +
      "<h1>" + esc(p.name) + "</h1></div>" +
      '<p class="hint">Проект в workspace «' + esc(ws.name) + "» · " + esc(p.note || "") + "</p>" +
      '<div class="card"><div class="section-title" style="margin-top:0">Overview</div>' +
      "<p>Контекст проекта. В v0.1 — заглушка: Overview / Tasks / Files / Agents добавляются по мере подключения backend.</p></div>" +
      '<button class="btn" id="projChat">Открыть Chat проекта</button>' +
      "</div>";

    document.getElementById("projChat").onclick = function () {
      chatScreen(p.name + " · Chat", "#/workspace/" + wsId + "/project/" + projectId,
        "Проект «" + p.name + "»");
    };
    updatePanelContext("Проект: " + p.name);
  }

  /* ---------- Экраны-заглушки (§14) ---------- */

  function renderStub(title) {
    app.innerHTML =
      '<div class="screen">' +
      '<div class="screen__header">' +
      '<button class="icon-btn" onclick="location.hash=\'#/\'" aria-label="Назад">←</button>' +
      "<h1>" + esc(title) + "</h1></div>" +
      '<div class="empty">Секция будет реализована после подключения backend (ТЗ §25).</div>' +
      "</div>";
  }

  /* ---------- Settings: конфигурация SyncService (§9) ---------- */

  function renderSettings() {
    app.innerHTML =
      '<div class="screen">' +
      '<div class="screen__header">' +
      '<button class="icon-btn" onclick="location.hash=\'#/\'" aria-label="Назад">←</button>' +
      "<h1>Settings</h1></div>" +
      '<div class="card">' +
      '<div class="section-title" style="margin-top:0">Backend / Sync</div>' +
      '<label class="hint" for="cfgBase">API base URL</label>' +
      '<input id="cfgBase" type="text" placeholder="http://127.0.0.1:8765" />' +
      '<div style="height:10px"></div>' +
      '<label class="hint" for="cfgToken">Bearer token (FREEBUFF_MCP_TOKEN)</label>' +
      '<input id="cfgToken" type="password" placeholder="token…" />' +
      '<div class="row row--end">' +
      '<button class="btn btn--ghost" id="cfgTest">Проверить</button>' +
      '<button class="btn btn--primary" id="cfgSave">Сохранить</button>' +
      "</div>" +
      '<p class="hint" style="margin-top:10px">Без токена Whims остаются только локально. Токен хранится в localStorage этого устройства и никогда не уходит на другие домены.</p>' +
      "</div></div>";

    var baseEl = document.getElementById("cfgBase");
    var tokenEl = document.getElementById("cfgToken");
    baseEl.value = localStorage.getItem("wsos.apiBase") || "http://127.0.0.1:8765";
    tokenEl.value = localStorage.getItem("wsos.mcpToken") || "";

    document.getElementById("cfgSave").onclick = function () {
      localStorage.setItem("wsos.apiBase", baseEl.value.trim().replace(/\/$/, ""));
      localStorage.setItem("wsos.mcpToken", tokenEl.value.trim());
      toast("Настройки сохранены");
      sync.flush(); // попробовать отправить накопленную очередь
    };

    document.getElementById("cfgTest").onclick = function () {
      localStorage.setItem("wsos.apiBase", baseEl.value.trim().replace(/\/$/, ""));
      localStorage.setItem("wsos.mcpToken", tokenEl.value.trim());
      sync.pull().then(function (items) {
        toast(items.length ? "Backend OK · whims на сервере: " + items.length : "Backend недоступен или нет данных");
      });
    };
  }

  /* ---------- Quick Whim (§6–7): текст + голос ---------- */

  var mediaRecorder = null;
  var chunks = [];
  var voiceBlobUrl = null;

  function openWhimModal() {
    document.getElementById("whimModal").hidden = false;
    document.getElementById("whimText").value = "";
    resetVoiceUI();
    document.getElementById("whimText").focus();
  }

  function closeWhimModal() {
    stopRecording(true);
    document.getElementById("whimModal").hidden = true;
  }

  function resetVoiceUI() {
    var st = document.getElementById("voiceState");
    st.hidden = true;
    st.classList.remove("voice-state--recording");
    st.textContent = "";
    document.getElementById("voicePlayback").hidden = true;
  }

  function startRecording() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      toast("Микрофон недоступен — запишите текстом");
      return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      chunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = function (e) { chunks.push(e.data); };
      mediaRecorder.onstop = function () {
        stream.getTracks().forEach(function (t) { t.stop(); });
        var blob = new Blob(chunks, { type: "audio/webm" });
        if (voiceBlobUrl) URL.revokeObjectURL(voiceBlobUrl);
        voiceBlobUrl = URL.createObjectURL(blob);
        var player = document.getElementById("voicePlayback");
        player.src = voiceBlobUrl;
        player.hidden = false;
        var st = document.getElementById("voiceState");
        st.classList.remove("voice-state--recording");
        st.textContent = "Записано ✓ (транскрипция появится с AI backend)";
      };
      mediaRecorder.start();
      var st = document.getElementById("voiceState");
      st.hidden = false;
      st.classList.add("voice-state--recording");
      st.textContent = "Идёт запись…";
    }).catch(function () {
      toast("Нет доступа к микрофону");
    });
  }

  function stopRecording(silentCancel) {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      if (silentCancel) {
        // Отмена: не сохраняем blob
        mediaRecorder.onstop = null;
        mediaRecorder.stream && mediaRecorder.stream.getTracks().forEach(function (t) { t.stop(); });
        mediaRecorder.stop();
      } else {
        mediaRecorder.stop();
      }
    }
    mediaRecorder = null;
  }

  function saveWhim() {
    var textEl = document.getElementById("whimText");
    var text = textEl.value.trim();
    if (!text) {
      // Голосовой Whim без транскрипции пока сохраняем как заметку о записи
      var hasVoice = !document.getElementById("voicePlayback").hidden;
      if (!hasVoice) { toast("Пустой Whim — не сохранён"); return; }
      text = "🎙 Голосовая заметка (" + new Date().toLocaleTimeString("ru-RU") + ")";
    }
    var whim = store.addWhim(text);
    closeWhimModal();
    sync.send(whim).then(function (res) {
      if (res.status === "pending_sync") toast("Офлайн — Whim сохранён локально");
    });
    if (location.hash === "#/" || location.hash === "") renderDashboard();
  }

  /* ---------- История Whims (§5) ---------- */

  function openWhimHistory() {
    document.getElementById("whimHistory").hidden = false;
    document.getElementById("historySearch").value = "";
    renderHistory("");
  }

  function closeWhimHistory() {
    document.getElementById("whimHistory").hidden = true;
  }

  function renderHistory(query) {
    var list = document.getElementById("historyList");
    var q = query.trim().toLowerCase();
    var items = store.data.whims.filter(function (w) {
      return !q || w.text.toLowerCase().indexOf(q) !== -1;
    });

    if (!items.length) {
      list.innerHTML = '<div class="empty">Ничего не найдено</div>';
      return;
    }

    var html = "";
    var lastDay = null;
    items.forEach(function (w) {
      var day = new Date(w.ts).toDateString();
      if (day !== lastDay) {
        lastDay = day;
        html += '<div class="day-label">' + esc(dayLabel(w.ts)) + "</div>";
      }
      html +=
        '<div class="card whim-item" data-id="' + w.id + '">' +
        '<div class="whim-item__body">' +
        '<p class="whim-item__text">' + esc(w.text) + "</p>" +
        '<div class="whim-item__meta"><span>' + fmtTime(w.ts) + "</span>" + syncBadge(w.status) + "</div>" +
        "</div>" +
        '<div class="whim-item__actions">' +
        '<button class="icon-btn act-edit" title="Редактировать">✏️</button>' +
        '<button class="icon-btn act-del" title="Удалить">🗑</button>' +
        "</div></div>";
    });
    list.innerHTML = html;

    Array.prototype.forEach.call(list.querySelectorAll(".whim-item"), function (el) {
      var id = el.getAttribute("data-id");
      el.querySelector(".act-del").onclick = function () {
        store.deleteWhim(id);
        renderHistory(query);
        refreshCurrentRoute();
      };
      el.querySelector(".act-edit").onclick = function () {
        var w = store.data.whims.find(function (x) { return x.id === id; });
        var newText = prompt("Редактировать мысль:", w.text);
        if (newText && newText.trim()) {
          store.updateWhim(id, newText.trim());
          renderHistory(query);
          refreshCurrentRoute();
          sync.flush();
        }
      };
    });
  }

  /* ---------- Правая панель (§13) ---------- */

  function updatePanelContext(line) {
    document.getElementById("panelContext").textContent = line || "";
  }

  function setPanel(open) {
    var panel = document.getElementById("sidePanel");
    var backdrop = document.getElementById("panelBackdrop");
    var toggle = document.getElementById("panelToggle");
    panel.classList.toggle("open", open);
    panel.setAttribute("aria-hidden", String(!open));
    backdrop.hidden = !open;
    toggle.textContent = open ? "←" : "›";
    toggle.setAttribute("aria-expanded", String(open));
  }

  /* ---------- Роутер (§21) ---------- */

  function route() {
    var h = location.hash.replace(/^#\/?/, "");
    var parts = h.split("/").filter(Boolean);

    if (parts.length === 0) {
      renderDashboard();
      updatePanelContext("");
    } else if (parts[0] === "workspace" && parts.length >= 2) {
      if (parts[2] === "project" && parts[3]) renderProject(parts[1], parts[3]);
      else renderWorkspace(parts[1]);
    } else if (parts[0] === "files") {
      renderStub("Files");
    } else if (parts[0] === "settings") {
      renderSettings();
    } else {
      renderDashboard();
    }
    window.scrollTo(0, 0);
  }

  function refreshCurrentRoute() {
    route();
  }

  /* ---------- Инициализация ---------- */

  document.getElementById("quickWhim").onclick = openWhimModal;
  document.getElementById("whimCancel").onclick = closeWhimModal;
  document.getElementById("whimSave").onclick = saveWhim;

  document.getElementById("voiceBtn").onclick = function () {
    if (mediaRecorder && mediaRecorder.state === "recording") stopRecording(false);
    else startRecording();
  };

  document.getElementById("historyBack").onclick = closeWhimHistory;
  document.getElementById("historySearch").addEventListener("input", function (e) {
    renderHistory(e.target.value);
  });

  document.getElementById("panelToggle").onclick = function () {
    setPanel(!document.getElementById("sidePanel").classList.contains("open"));
  };
  document.getElementById("panelClose").onclick = function () { setPanel(false); };
  document.getElementById("panelBackdrop").onclick = function () { setPanel(false); };

  // Swipe-to-close панели (§13: touch-friendly, gesture)
  (function () {
    var panel = document.getElementById("sidePanel");
    var startX = null;
    panel.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; }, { passive: true });
    panel.addEventListener("touchend", function (e) {
      if (startX !== null && e.changedTouches[0].clientX - startX > 60) setPanel(false);
      startX = null;
    }, { passive: true });
  })();

  document.addEventListener("sync:update", refreshCurrentRoute);
  window.addEventListener("hashchange", route);
  route();
})();
