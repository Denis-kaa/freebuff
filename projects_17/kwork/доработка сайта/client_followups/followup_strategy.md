# Follow-up стратегия — после отправки письма заказчику

> **Версия:** v1 · **Дата:** 2026-08-11
> **Назначение:** автоматизированный конвейер трёх точек контакта после отправки `client_questions_v1.md`.
> **Триггер:** созвон или e-mail/TG отправка письма Q-B1..B10 → запускается таймер.

**Связанные документы:**
- [`../client_questions_v1.md`***REMOVED***(../client_questions_v1.md) — отправленное письмо с Q-B1..B10.
- [`defaults_q_b.md`***REMOVED***(defaults_q_b.md) — таблица дефолтов (что выбираем, если клиент не отвечает).
- [`email_day3_reminder.md`***REMOVED***(email_day3_reminder.md) — мягкое напоминание.
- [`email_day7_contact_lost.md`***REMOVED***(email_day7_contact_lost.md) — формальный «срыв контакта» + дефолты.
- [`/tmp/make_roadmap_v01.py`***REMOVED***(/tmp/make_roadmap_v01.py) — генератор roadmap v0.1 (→ [`../rokus_master_roadmap_v01.md`***REMOVED***(../rokus_master_roadmap_v01.md)).
- [`../rokus_master_roadmap_v0.md`***REMOVED***(../rokus_master_roadmap_v0.md) — источник для трансформации v0 → v0.1.

---

## ⏰ ТАЙМЛАЙН — 3 точки контакта

```
ДЕНЬ 0  ────────────────────────────────────────────────────────
  📧 Отправка письма [client_questions_v1.md***REMOVED***
  • Тема: «Старт Рокус-Спорт — 10 блокирующих вопросов»
  • Получатель: заказчик / ЛПР
  • Канал: TG (приоритет) + e-mail дубль
  • Ожидание: ответ в течение 5 рабочих дней (Пн–Пт)

ДЕНЬ 3 (рабочий) ──────────────────────────────────────────────
  💬 Мягкое напоминание [email_day3_reminder.md***REMOVED***
  • Тон: дружеский, без давления
  • Содержание: «Привет! Вспомнил про Q-B… некоторые получили?»
  • Призыв: «Если есть 20 минут — давайте созвон»
  • Если клиент в TG — короткое сообщение; иначе короткое e-mail

ДЕНЬ 7 (рабочий) ──────────────────────────────────────────────
  📜 Формальный «срыв контакта» [email_day7_contact_lost.md***REMOVED***
  • Тон: конструктивный, не угрожающий
  • Содержание: «Не дождался — двигаюсь по плану Б»
  • Приложение: [defaults_q_b.md***REMOVED*** — что я выбираю по умолчанию
  • Приложение: [rokus_master_roadmap_v01.md***REMOVED*** — сгенерированный roadmap
  • Призыв: «Если что-то не так — скажите, я откачу (стоимость указана)»
```

---

## 🚦 ЧТО ПРОИСХОДИТ НА КАЖДОМ ЭТАПЕ

### ДЕНЬ 0 — отправка

1. Скопировать `client_questions_v1.md` в TG/e-mail → отправить.
2. Установить напоминание в календаре: **ДЕНЬ 3 09:00** → триггер на `email_day3_reminder.md`.
3. Установить напоминание: **ДЕНЬ 7 09:00** → триггер на `email_day7_contact_lost.md`.
4. Записать в `rokus_session_summary.json` поле `client_letter_sent_at: <ISO>`.

### ДЕНЬ 3 — мягкое напоминание

1. Открыть `email_day3_reminder.md`.
2. **Если клиент дал ответ хотя бы на 1 Q-B** → напоминание оставляем нейтральным: «Жду остальные».
3. **Если клиент молчит полностью** → напоминание активное: «Привет, можно 20 минут на созвон? Покажу на экране, всё станет проще».
4. **НЕ отправляем напоминание, если клиент явно ответил "вернусь позже"** — wait-режим.

### ДЕНЬ 7 — формальный + дефолты

1. Запустить генератор: `python3 /tmp/make_roadmap_v01.py` → создаётся `rokus_master_roadmap_v01.md`.
2. Открыть `email_day7_contact_lost.md`.
3. Подставить в письмо ссылку на свежий `rokus_master_roadmap_v01.md` + `defaults_q_b.md`.
4. Отправить с конструктивным тоном: «Вот план Б. Если что — любую строку переиграем, я указал стоимость отката».

---

## ⚖️ КАКИЕ ДЕФОЛТЫ ВЫБРАНЫ (резюме)

> Полная таблица с обоснованием — в [`defaults_q_b.md`***REMOVED***(defaults_q_b.md).

| Q | Default | Status |
|---|---------|--------|
| Q-B1 Hockey | **B** (Remove + 301 redirect) | 🟢 SAFE |
| Q-B2 Content | **B** (Client provides later, use placeholders) | 🟢 SAFE |
| Q-B3 Leads | **C** (Email to sales@rokus-sport.ru) | 🟢 SAFE |
| Q-B4 Payment | **D** (No online payment, manual callback) | 🟢 SAFE |
| Q-B5 Map | **B** (Active link) | 🟢 SAFE |
| Q-B6 Contacts | **current values** (из текущего сайта) | 🟢 SAFE |
| Q-B7 DDoS | **C** (Leave as is, не трогаем хостинг) | 🟢 SAFE |
| Q-B8 Hero | **A** (image1.png на все 5 страниц, TASK-095) | 🟡 ASSUMPTION |
| Q-B9 Origin | **TEMP** (image6_q95_temp.jpg) | 🔴 BLOCKING-UNTIL-ORIGIN |
| Q-B10 ICC | **Accept color drift** (используем текущие файлы) | 🟠 RISKY |
| Q-I1..Q-I6 | дефолты из контекста | 🟢 SAFE |

**Total rollback cost (если клиент на все 10 скажет «нет, по-другому»):** ~16-22 ч переделки. Что покрывается 2-3-дневным авансом Phase 3.

---

## 🔧 ГЕНЕРАТОР ROADMAP v0.1

`/tmp/make_roadmap_v01.py` — **простой markdown-трансформер** (~100 LOC):

### Вход
- v0 источник: `rokus_master_roadmap_v0.md` (~30 KB)
- Дефолты: inline Python dict (`DEFAULTS = {...***REMOVED***`) — чтобы будущие версии менялись одной правкой.

### Логика
1. **Header bump**: `v0` → `v0.1` + добавить строку «Scope locked YYYY-MM-DD, defaults applied per [defaults_q_b.md***REMOVED***».
2. **Section 1** (Executive Summary): вставить параграф «Defaults applied — locked scope, см. Section 16».
3. **Section 2.4** (10 блоков главной): убрать `[NEEDS VERIFICATION***REMOVED***` на блоке «Виды материалов», заменить на «`image6_q95_temp.jpg` (TEMP до origin из Q-B9)».
4. **Section 2.5** (12 блоков sport-страницы): добавить явный параметр Hero=`image1.png` (default Q-B8=A).
5. **Section 4** (Gap Analysis): добавить колонку «Locked?» для каждой строки на основе дефолта.
6. **Section 11** (Master Task List): для каждой TASK пометить `[ASSUMPTION***REMOVED***` + ссылку на конкретный дефолт.
7. **Section 16** (Questions for Client → **SCOPE LOCKED**): полная переделка — таблица «10 Q-B → 1 default + 1 status + 1 rollback cost».
8. **Section 18** (Estimate): обновить effort на основе дефолтов (если Q-B8=B был бы +2 недели, то A не влияет; если Q-B4=D → -8 ч; etc.).

### Выход
- `rokus_master_roadmap_v01.md` (~30 KB, готов к проверке).
- Консольный summary: «10 Q-B resolved, 6 Q-I resolved, X hours added/removed to estimate».

---

## 📋 EDGE CASES

### Edge case 1: клиент ответил только на Q-B8 (image1 hero)
→ Принять ответ. Частично применить defaults для остальных Q.
→ В Day 7 письме: «Спасибо за Q-B8! По остальным — двигаюсь по плану Б, см. defaults_q_b.md».

### Edge case 2: клиент ответил, но «вернусь позже»
→ Не отправлять Day 7 — подождать явно.
→ Созвон в режиме «hold» — дату обсуждаем, roadmap заморожен.

### Edge case 3: клиент прислал контент, но без ответов на Q-B
→ Контент собран → Phase 2 можно стартовать.
→ Day 7 письмо отправляем: «Контент получен! По остальным вопросам — двигаюсь по плану Б».

### Edge case 4: клиент отказался отвечать в принципе («решайте сами»)
→ Все Q-B → default. Спасибо. Двигаемся.
→ Day 7 письмо упрощается: «Получил карт-бланш — стартую фазу 3, дефолты зафиксированы».

---

## 📊 МЕТРИКИ УСПЕХА (KPI follow-up)

| Метрика | Цель | Как измерять |
|---------|------|--------------|
| **Доля Q-B с явным ответом за 5 р.д.** | ≥ 60% (6 из 10) | Manual count в `rokus_session_summary.json` `client_responses` |
| **Доля дефолтов которые клиент НЕ отменил** | ≥ 80% (8 из 10) | Track which defaults survived v0.1 → v0.2 upgrade |
| **Время от Day 0 до Day 7** | 5-7 р.д. | Calendar агрегирует |
| **Cost of rollback** | ≤ 16 ч | Estimate sum в defaults_q_b.md |
| **Доля Phase 2 стартовала к Day 10** | ≥ 50% | TASK-060 started? |

---

## ✅ CHECKLIST ДЛЯ ИСПОЛНЕНИЯ

- [ ***REMOVED*** **ДЕНЬ 0** — письмо отправлено, напоминания в календаре установлены
- [ ***REMOVED*** **ДЕНЬ 3** — напоминание отправлено (если клиент не ответил)
- [ ***REMOVED*** **ДЕНЬ 7** — генератор запущен, v0.1 записан
- [ ***REMOVED*** **ДЕНЬ 7** — формальное письмо с v0.1 + defaults отправлено
- [ ***REMOVED*** **ДЕНЬ 10** — Phase 2 запущен (если Q-B2=B resolved) ИЛИ hold (если клиент вернулся с другими вводами)
- [ ***REMOVED*** **ДЕНЬ 14+** — следующие письма по мере прихода ответов

---

_Версия: v1 · 2026-08-11 · Buffy · конвейерная автоматизация follow-up после Q-B письма_
