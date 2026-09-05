import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Modal, Spinner, useToast } from "../components/ui.jsx";

/* ------------------------------------------------------------------ */
/* Import Wizard (6.md §13-17): файл → маппинг → проверка → превью →  */
/* подтверждение.                                                     */
/* ------------------------------------------------------------------ */

const TARGET_FIELDS = [
  { key: "title", label: "Проект" },
  { key: "display_id", label: "ID" },
  { key: "client_legal_name", label: "Юр. лицо" },
  { key: "manager_name", label: "Менеджер" },
  { key: "stage", label: "Этап" },
  { key: "deadline", label: "Дедлайн" },
  { key: "payment_percent", label: "Оплата %" },
  { key: "currency", label: "Валюта" },
  { key: "advance_date", label: "Дата аванса" },
  { key: "final_payment_date", label: "Дата доплаты" },
  { key: "delivery_address", label: "Адрес доставки" },
  { key: "delivery_paid", label: "Доставка оплачена" },
  { key: "next_action", label: "Следующее действие" },
  { key: "next_action_date", label: "Дата след. действия" },
  { key: "risk_level", label: "Риск" },
  { key: "risk_reason", label: "Причина риска" },
  { key: "comment", label: "Комментарий" },
  { key: "item_name", label: "Позиция" },
  { key: "item_quantity", label: "Тираж" },
  { key: "item_mockup_status", label: "Тех. макет" },
  { key: "item_signal_required", label: "Сигнал нужен" },
  { key: "item_signal_status", label: "Сигнал" },
  { key: "item_signal_shipping_date", label: "Дата отгрузки сигнала" },
  { key: "item_signal_feedback", label: "ОС по сигналу" },
  { key: "item_batch_status", label: "Тираж статус" },
  { key: "item_factory", label: "Фабрика" },
];

export default function ImportWizard({ open, onClose, onImported }) {
  const toast = useToast();
  const [step, setStep] = useState(1); // 1 файл, 2 маппинг+превью, 3 результат
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState({});
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [duplicateMode, setDuplicateMode] = useState("update");
  const [partial, setPartial] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    if (open) {
      setStep(1); setFile(null); setJob(null); setPreview(null);
      setResult(null); setMapping({});
    }
  }, [open]);

  if (!open) return null;

  const upload = async (f) => {
    setBusy(true);
    try {
      const ext = (f.name || "").split(".").pop().toLowerCase();
      const sourceType = ext === "csv" ? "csv" : "excel";
      const body = await api.importUpload(f, sourceType);
      setJob(body.job);
      setPreview(body.preview);
      setMapping(body.preview?.mapping || {});
      setStep(2);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const applyMapping = async () => {
    setBusy(true);
    try {
      const body = await api.importSetMapping(job.id, mapping);
      setPreview(body.preview);
      setJob(body.job);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      const body = await api.importConfirm(job.id, {
        mapping,
        duplicate_mode: duplicateMode,
        partial,
      });
      setResult(body);
      setStep(3);
      if (body.rolled_back) toast("Импорт отменён: ошибки валидации", "error");
      else toast(`Импортировано: +${body.result?.created || 0} создано`);
      onImported?.();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const downloadTemplate = () => {
    window.location.href = "/api/imports/templates?kind=projects_items";
  };

  const headers = preview?.headers || [];

  return (
    <Modal open onClose={onClose} title="Импорт из Excel / CSV" wide>
      {/* Шаги */}
      <div className="mb-4 flex items-center gap-1 text-sm">
        {["Файл", "Маппинг и проверка", "Результат"].map((s, i) => (
          <React.Fragment key={s}>
            {i > 0 && <span className="text-slate-300">→</span>}
            <span className={step === i + 1 ? "font-semibold text-indigo-600" : "text-slate-400"}>
              {i + 1}. {s}
            </span>
          </React.Fragment>
        ))}
      </div>

      {/* Шаг 1: файл */}
      {step === 1 && (
        <div className="flex flex-col gap-3">
          <div
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 py-12 text-center hover:border-indigo-400 hover:bg-indigo-50/50"
            onClick={() => fileRef.current?.click()}
          >
            <div className="text-3xl">📥</div>
            <div className="text-sm font-medium text-slate-600">
              {file ? file.name : "Выберите файл .xlsx, .xls или .csv"}
            </div>
            <div className="text-xs text-slate-400">до 20 МБ, до 10 000 строк</div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) { setFile(f); upload(f); }
            }}
          />
          <div className="flex items-center justify-center gap-2">
            <button className="btn btn-primary" onClick={() => fileRef.current?.click()} disabled={busy}>
              Выбрать файл
            </button>
            <button className="btn btn-secondary" onClick={downloadTemplate} disabled={busy}>
              ⬇ Скачать шаблон Excel
            </button>
          </div>
          {busy && <Spinner label="Загрузка и проверка файла..." />}
        </div>
      )}

      {/* Шаг 2: маппинг + превью */}
      {step === 2 && preview && (
        <div className="flex flex-col gap-4">
          {/* Сводка */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat label="Строк" value={preview.total} />
            <Stat label="Будет создано" value={preview.will_create} tone="emerald" />
            <Stat label="Обновится" value={preview.will_update} tone="indigo" />
            <Stat label="Ошибок" value={preview.errors} tone={preview.errors ? "red" : ""} />
          </div>
          {preview.warnings > 0 && (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
              ⚠ {preview.warnings} предупреждений (менеджеры/устаревшие колонки — будут созданы справочники)
            </div>
          )}
          {preview.legacy_notes?.length > 0 && (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
              {preview.legacy_notes.map((n, i) => (
                <div key={i}>• {n}</div>
              ))}
            </div>
          )}

          {/* Маппинг */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="label !mb-0">Сопоставление колонок</label>
              <button className="btn btn-ghost !py-0.5 text-xs" onClick={applyMapping} disabled={busy}>
                Перепроверить
              </button>
            </div>
            <div className="max-h-56 space-y-1 overflow-auto rounded-lg border border-slate-200 p-2">
              {headers.length === 0 && <div className="text-sm text-slate-400">Нет колонок</div>}
              {headers.map((h) => (
                <div key={h} className="flex items-center gap-2">
                  <span className="w-1/3 truncate text-xs text-slate-500" title={h}>{h || "(пустой заголовок)"}</span>
                  <span className="text-slate-300">→</span>
                  <select
                    className="input !w-1/2 !py-1 !text-xs"
                    value={mapping[h] || ""}
                    onChange={(e) => setMapping((m) => ({ ...m, [h]: e.target.value }))}
                  >
                    <option value="">— не импортировать —</option>
                    <option value="__ignore__">Пропустить</option>
                    {TARGET_FIELDS.map((f) => (
                      <option key={f.key} value={f.key}>{f.label}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          {/* Опции */}
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <label className="flex items-center gap-1.5">
              Дубликаты:
              <select className="input !w-auto !py-1" value={duplicateMode} onChange={(e) => setDuplicateMode(e.target.value)}>
                <option value="update">Обновлять</option>
                <option value="skip">Пропускать</option>
                <option value="copy">Копировать (новый ID)</option>
              </select>
            </label>
            <label className="flex items-center gap-1.5 text-slate-600">
              <input type="checkbox" className="accent-indigo-600" checked={partial} onChange={(e) => setPartial(e.target.checked)} />
              Импортировать только корректные строки
            </label>
          </div>

          {/* Ошибки */}
          {preview.issues?.length > 0 && (
            <div className="max-h-40 overflow-auto rounded-lg border border-slate-200">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-2 py-1 text-left">Строка</th>
                    <th className="px-2 py-1 text-left">Поле</th>
                    <th className="px-2 py-1 text-left">Значение</th>
                    <th className="px-2 py-1 text-left">Проблема</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.issues.map((iss, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-2 py-1">{iss.row}</td>
                      <td className="px-2 py-1">{iss.field}</td>
                      <td className="px-2 py-1">{String(iss.value ?? "")}</td>
                      <td className={`px-2 py-1 ${iss.level === "ERROR" ? "text-red-600" : "text-amber-600"}`}>
                        {iss.error}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Кнопки */}
          <div className="flex items-center justify-end gap-2">
            <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
            <button
              className="btn btn-primary"
              onClick={confirm}
              disabled={busy || (preview.errors > 0 && !partial)}
              title={preview.errors > 0 && !partial ? "Исправьте ошибки или включите частичный импорт" : ""}
            >
              {busy ? "Импортируем..." : `Импортировать (${preview.ok})`}
            </button>
          </div>
        </div>
      )}

      {/* Шаг 3: результат */}
      {step === 3 && result && (
        <div className="flex flex-col gap-4">
          <div
            className={`rounded-xl px-4 py-6 text-center text-sm ${
              result.rolled_back ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
            }`}
          >
            <div className="mb-1 text-2xl">{result.rolled_back ? "⛔" : "✅"}</div>
            <div className="font-semibold">
              {result.rolled_back ? "Импорт отменён (ошибки валидации)" : "Импорт завершён"}
            </div>
            <div className="mt-2 flex justify-center gap-4 text-xs">
              <span>Создано: <b>{result.result?.created ?? 0}</b></span>
              <span>Обновлено: <b>{result.result?.updated ?? 0}</b></span>
              <span>Пропущено: <b>{result.result?.skipped ?? 0}</b></span>
            </div>
          </div>
          {result.job?.errors?.length > 0 && (
            <div className="max-h-40 overflow-auto rounded-lg border border-slate-200">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-2 py-1 text-left">Строка</th>
                    <th className="px-2 py-1 text-left">Поле</th>
                    <th className="px-2 py-1 text-left">Проблема</th>
                  </tr>
                </thead>
                <tbody>
                  {result.job.errors.slice(0, 50).map((e, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-2 py-1">{e.row}</td>
                      <td className="px-2 py-1">{e.field}</td>
                      <td className="px-2 py-1 text-amber-600">{e.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button className="btn btn-primary" onClick={onClose}>Готово</button>
          </div>
        </div>
      )}

      {busy && step === 2 && <Spinner label="Проверка..." />}
    </Modal>
  );
}

function Stat({ label, value, tone }) {
  const color = tone === "emerald" ? "text-emerald-600" : tone === "red" ? "text-red-600" : tone === "indigo" ? "text-indigo-600" : "text-slate-700";
  return (
    <div className="rounded-lg border border-slate-200 px-3 py-2">
      <div className={`text-lg font-bold ${color}`}>{value ?? 0}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}
