import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import {
  DEFAULT_VISIBLE,
  SYSTEM_COLUMNS,
  FIELD_TYPES,
  FILTERABLE_SYSTEM,
  OPERATORS_BY_KIND,
  OPERATOR_LABEL,
  fieldKindForCustom,
  FIELD_TYPE_LABEL,
} from "../columns.js";
import { Drawer, EmptyState, Field, Modal, Spinner, useToast } from "../components/ui.jsx";
import ProjectForm from "./ProjectForm.jsx";
import ProjectDetail from "./ProjectDetail.jsx";
import CustomFieldDialog from "./CustomFieldDialog.jsx";
import ColumnSettings from "./ColumnSettings.jsx";
import ImportWizard from "../import/ImportWizard.jsx";
import ImportHistoryModal from "../import/ImportHistoryModal.jsx";
import ExportModal from "../export/ExportModal.jsx";

const PAGE_SIZES = [20, 50, 100];

export default function ProjectsView() {
  const toast = useToast();

  // Данные
  const [projects, setProjects] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Системные поля + custom fields
  const [customFields, setCustomFields] = useState([]);
  const [itemCustomFields, setItemCustomFields] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});

  // Окно/представление
  const [views, setViews] = useState([]);
  const [activeView, setActiveView] = useState(null); // null = «Все проекты» (встроенное)

  // Конфигурация представления
  const [visibleKeys, setVisibleKeys] = useState(DEFAULT_VISIBLE);
  const [filters, setFilters] = useState([]);
  const [sortBy, setSortBy] = useState("deadline");
  const [sortDir, setSortDir] = useState("asc");

  // Запрос
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [includeArchived, setIncludeArchived] = useState(false);

  // UI
  const [showArchived, setShowArchived] = useState(false);
  const [selected, setSelected] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerProject, setDrawerProject] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editedProject, setEditedProject] = useState(null);
  const [cfDialogOpen, setCfDialogOpen] = useState(false);
  const [colSettingsOpen, setColSettingsOpen] = useState(false);
  const [viewMenuOpen, setViewMenuOpen] = useState(false);
  const [bulkMenuOpen, setBulkMenuOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importHistoryOpen, setImportHistoryOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  // Комбинированные колонки: система + пользовательские
  const allColumns = useMemo(() => {
    const custom = customFields.map((cf) => ({
      key: `cf_${cf.slug}`,
      label: cf.name,
      slug: cf.slug,
      kind: fieldKindForCustom(cf),
      fieldType: cf.field_type,
      custom: true,
      options: cf.options || [],
    }));
    return [...SYSTEM_COLUMNS, ...custom];
  }, [customFields]);

  const visibleColumns = useMemo(
    () => allColumns.filter((c) => visibleKeys.includes(c.key)),
    [allColumns, visibleKeys]
  );

  const loadAll = async (cfg) => {
    setLoading(true);
    setError(null);
    try {
      const [proj, cf, opts, vws] = await Promise.all([
        api.listProjects({
          search: cfg?.search || search,
          page: cfg?.page ?? page,
          page_size: pageSize,
          sort_by: sortBy,
          sort_dir: sortDir,
          include_archived: showArchived,
          filters: filters.length ? JSON.stringify(filters) : undefined,
        }),
        api.listCustomFields(),
        api.filterOptions(),
        api.listViews(),
      ]);
      setProjects(proj.items);
      setTotal(proj.total);
      setCustomFields(cf);
      setFilterOptions(opts);
      setViews(vws);
      // поля для позиций (PROJECT_ITEM)
      api.listCustomFields()
        .then((all) => setItemCustomFields(all.filter((f) => f.entity_type === "PROJECT_ITEM")))
        .catch(() => {});
    } catch (e) {
      setError(e.message);
      toast(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // Первичная загрузка
  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, sortBy, sortDir, showArchived, filters]);

  // Apply фильтров из активного представления
  const applyViewConfig = (view) => {
    if (!view?.config) return;
    const cfg = view.config;
    setVisibleKeys(cfg.visible_columns || cfg.visibleColumns || DEFAULT_VISIBLE);
    setFilters(cfg.filters || []);
    if (cfg.sorting?.length) {
      setSortBy(cfg.sorting[0].field || "deadline");
      setSortDir(cfg.sorting[0].direction || "asc");
    }
    setPage(1);
  };

  // Встроенные представления + сохранённые
  const builtinViews = useMemo(
    () => [
      { key: "all", name: "Все проекты" },
      { key: "my", name: "Мои проекты" },
      { key: "production", name: "Производство" },
      { key: "finance", name: "Финансы" },
      { key: "archive", name: "Архив" },
    ],
    []
  );

  const currentViewName = activeView
    ? views.find((v) => v.id === activeView)?.name
    : builtinViews.find((v) => v.key === "all")?.name;

  const submitSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  // Bulk: изменить этап
  const bulkSetStage = async (value) => {
    if (!selected.length || !value) return;
    try {
      await api.bulkUpdate({ ids: selected, stage: value });
      toast(`Обновлено ${selected.length} проектов`);
      setSelected([]);
      setBulkMenuOpen(false);
      loadAll();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const bulkSetManager = async (value) => {
    if (!selected.length) return;
    try {
      await api.bulkUpdate({ ids: selected, manager_name: value });
      toast(`Обновлено ${selected.length} проектов`);
      setSelected([]);
      setBulkMenuOpen(false);
      loadAll();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const bulkArchive = async () => {
    if (!selected.length) return;
    try {
      for (const id of selected) await api.archiveProject(id);
      toast(`Заархивировано ${selected.length} проектов`);
      setSelected([]);
      setBulkMenuOpen(false);
      loadAll();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const openProject = (p) => {
    setDrawerProject(p);
    setDrawerOpen(true);
  };

  const toggleRow = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const toggleSelectAll = () => {
    if (selected.length === projects.length && projects.length > 0) setSelected([]);
    else setSelected(projects.map((p) => p.id));
  };

  const createViewFromCurrent = async () => {
    const name = window.prompt("Имя представления:");
    if (!name) return;
    try {
      await api.createView({
        name,
        config: {
          visible_columns: visibleKeys,
          filters,
          sorting: [{ field: sortBy, direction: sortDir }],
        },
      });
      toast(`Представление «${name}» создано`);
      loadAll();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const selectView = async (view) => {
    setViewMenuOpen(false);
    if (view.key === "all") { setActiveView(null); setVisibleKeys(DEFAULT_VISIBLE); setFilters([]); setSortBy("deadline"); setSortDir("asc"); return; }
    if (view.key === "archive") { setShowArchived(true); return; }
    // Билт-ин фильтры
    const builtinConfig = {
      my: { filters: [{ field: "manager_name", operator: "not_empty", value: null }] },
      production: { filters: [{ field: "stage", operator: "equals", value: "Производство" }] },
      finance: { filters: [{ field: "payment_percent", operator: "lt", value: 100 }] },
    };
    setShowArchived(false);
    const cfg = builtinConfig[view.key] || {};
    setActiveView(null);
    if (cfg.filters) setFilters(cfg.filters);
    setVisibleKeys(DEFAULT_VISIBLE);
  };

  // Сохранённое представление
  const selectSavedView = async (view) => {
    setActiveView(view.id);
    setViewMenuOpen(false);
    setShowArchived(false);
    applyViewConfig(view);
  };

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      {/* Заголовок */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Проекты</h1>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary" onClick={() => setImportOpen(true)}>
            ⬆ Импорт
          </button>
          <button className="btn btn-secondary" onClick={() => setExportOpen(true)}>
            ⬇ Экспорт
          </button>
          <button className="btn btn-ghost" onClick={() => setImportHistoryOpen(true)} title="История импортов">
            🕘 История
          </button>
          <button className="btn btn-primary" onClick={() => { setEditedProject(null); setFormOpen(true); }}>
            + Новый проект
          </button>
        </div>
      </div>

      {/* Панель инструментов */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {/* Поиск */}
        <div className="flex items-center gap-1.5">
          <input
            className="input !w-56"
            placeholder="Поиск..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitSearch()}
          />
          <button className="btn btn-secondary" onClick={submitSearch}>Найти</button>
        </div>

        {/* Представление */}
        <div className="relative">
          <button
            className="btn btn-secondary"
            onClick={() => setViewMenuOpen((v) => !v)}
          >
            Представление: {currentViewName} ▾
          </button>
          {viewMenuOpen && (
            <div className="absolute left-0 top-full z-40 mt-1 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
              {builtinViews.map((v) => (
                <button
                  key={v.key}
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                  onClick={() => selectView(v)}
                >
                  {v.name}
                </button>
              ))}
              <div className="my-1 border-t border-slate-100" />
              {views.map((v) => (
                <button
                  key={v.id}
                  className={`block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 ${activeView === v.id ? "font-semibold text-indigo-600" : ""}`}
                  onClick={() => selectSavedView(v)}
                >
                  {v.name}
                </button>
              ))}
              <div className="my-1 border-t border-slate-100" />
              <button
                className="block w-full px-3 py-2 text-left text-sm text-indigo-600 hover:bg-slate-50"
                onClick={() => { setViewMenuOpen(false); createViewFromCurrent(); }}
              >
                + Создать представление
              </button>
            </div>
          )}
        </div>

        {/* Настроить таблицу */}
        <button className="btn btn-secondary" onClick={() => setColSettingsOpen(true)}>
          Настроить таблицу
        </button>

        {/* Добавить поле */}
        <button className="btn btn-secondary" onClick={() => setCfDialogOpen(true)}>
          + Добавить колонку
        </button>

        {/* Архив-тумблер */}
        <label className="ml-auto flex items-center gap-1.5 text-sm text-slate-600">
          <input
            type="checkbox"
            className="accent-indigo-600"
            checked={showArchived}
            onChange={(e) => { setShowArchived(e.target.checked); setPage(1); }}
          />
          Показывать архив
        </label>
      </div>

      {/* Bulk actions */}
      {selected.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2">
          <span className="text-sm font-semibold text-indigo-700">
            {selected.length} выбрано
          </span>
          <BulkStageSelect options={filterOptions.stages || []} onApply={bulkSetStage} />
          <BulkManagerSelect options={filterOptions.managers || []} onApply={bulkSetManager} />
          <button className="btn btn-danger !py-1" onClick={bulkArchive}>
            Архив
          </button>
          <button className="btn btn-ghost !py-1" onClick={() => setSelected([])}>
            Сброс
          </button>
        </div>
      )}

      {/* Ошибка */}
      {error && (
        <div className="mb-3 flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
          <button className="btn btn-secondary !py-1" onClick={() => loadAll()}>Повторить</button>
        </div>
      )}

      {/* Таблица */}
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        {loading && !projects.length ? (
          <Spinner />
        ) : projects.length === 0 ? (
          <EmptyState
            title={showArchived ? "В архиве пусто" : "Проектов пока нет"}
            subtitle="Создайте первый проект, чтобы начать работу."
            action={
              <button className="btn btn-primary" onClick={() => { setEditedProject(null); setFormOpen(true); }}>
                + Новый проект
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2">
                    <input type="checkbox" className="accent-indigo-600" checked={selected.length === projects.length} onChange={toggleSelectAll} />
                  </th>
                  {visibleColumns.map((c) => (
                    <th key={c.key} className="th-col">
                      <div className="flex items-center gap-1">
                        {c.label}
                        {c.custom && <span className="rounded bg-amber-100 px-1 text-[10px] text-amber-700">поле</span>}
                        {c.sortable && (
                          <span className="cursor-pointer text-slate-400" onClick={() => toggleSort(c.field)}>
                            {sortBy === c.field ? (sortDir === "asc" ? "↑" : "↓") : "↕"}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => (
                  <tr
                    key={p.id}
                    className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                    onClick={() => openProject(p)}
                  >
                    <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" className="accent-indigo-600" checked={selected.includes(p.id)} onChange={() => toggleRow(p.id)} />
                    </td>
                    {visibleColumns.map((c) => (
                      <td key={c.key} className="td-col">
                        <CellValue column={c} project={p} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Пагинация */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-sm text-slate-600">
          <span>Показано:</span>
          {PAGE_SIZES.map((s) => (
            <button
              key={s}
              className={`rounded px-2 py-0.5 ${pageSize === s ? "bg-indigo-600 text-white" : "bg-white border border-slate-300"}`}
              onClick={() => { setPageSize(s); setPage(1); }}
            >
              {s}
            </button>
          ))}
          <span className="ml-2">Всего: {total}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <button className="btn btn-secondary !py-1" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>←</button>
          <span>Стр. {page} / {Math.max(1, Math.ceil(total / pageSize))}</span>
          <button className="btn btn-secondary !py-1" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>→</button>
        </div>
      </div>

      {/* Диалоги */}
      {formOpen && (
        <Modal open onClose={() => setFormOpen(false)} title={editedProject ? `Редактировать: ${editedProject.title}` : "Новый проект"} wide>
          <ProjectForm
            existing={editedProject}
            customFields={customFields}
            onSaved={() => { setFormOpen(false); loadAll(); toast("Проект сохранён"); }}
            onCancel={() => setFormOpen(false)}
          />
        </Modal>
      )}

      <CustomFieldDialog open={cfDialogOpen} onClose={() => setCfDialogOpen(false)} onSaved={() => { setCfDialogOpen(false); loadAll(); }} />

      {colSettingsOpen && (
        <ColumnSettings
          open={colSettingsOpen}
          onClose={() => setColSettingsOpen(false)}
          columns={allColumns}
          visibleKeys={visibleKeys}
          setVisibleKeys={setVisibleKeys}
          customFields={customFields}
          onAddField={() => { setColSettingsOpen(false); setCfDialogOpen(true); }}
          filters={filters}
          setFilters={setFilters}
          sortBy={sortBy}
          setSortBy={setSortBy}
          sortDir={sortDir}
          setSortDir={setSortDir}
          customFieldsAll={customFields}
        />
      )}

      {drawerOpen && drawerProject && (
        <ProjectDetail
          project={drawerProject}
          onClose={() => setDrawerOpen(false)}
          onSaved={(updated) => { setDrawerProject(updated); loadAll(); }}
          onArchived={() => { setDrawerOpen(false); loadAll(); toast("Проект заархивирован"); }}
          customFields={customFields}
          itemCustomFields={itemCustomFields}
        />
      )}

      {/* Этап 6: Import / Export */}
      <ImportWizard open={importOpen} onClose={() => setImportOpen(false)} onImported={() => loadAll()} />
      <ImportHistoryModal open={importHistoryOpen} onClose={() => setImportHistoryOpen(false)} />
      <ExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        managers={filterOptions.managers || []}
      />
    </div>
  );

  function toggleSort(field) {
    if (sortBy === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(field); setSortDir("asc"); }
  }
}

// Cell: значение системного/пользовательского поля
function CellValue({ column, project }) {
  if (column.custom && column.slug) {
    const val = project.custom_values?.[column.slug];
    return <CellRendered column={column} value={val} />;
  }
  return <CellRendered column={column} value={project[column.field]} />;
}

function CellRendered({ column, value }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-slate-300">—</span>;
  }
  if (column.fieldType === "BOOLEAN") return value ? "✓ Да" : "— Нет";
  if (column.fieldType === "URL") return <a href={value} target="_blank" rel="noreferrer" className="text-indigo-600 underline">{value}</a>;
  if (column.fieldType === "DATE" && typeof value === "string") return value.slice(0, 10);
  if (column.kind === "date" && value) return String(value).slice(0, 10);
  if (column.fieldType === "MULTI_SELECT" && Array.isArray(value)) return value.join(", ");
  return String(value);
}

// Bulk селекты
function BulkStageSelect({ options, onApply }) {
  return (
    <select className="input !w-auto" defaultValue="" onChange={(e) => e.target.value && onApply(e.target.value)}>
      <option value="">Этап...</option>
      {(options.length ? options : ["Макет", "Сигнал", "Тираж", "Завершён"]).map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );
}

function BulkManagerSelect({ options, onApply }) {
  return (
    <select className="input !w-auto" defaultValue="" onChange={(e) => e.target.value && onApply(e.target.value)}>
      <option value="">Менеджер...</option>
      {options.map((o) => (<option key={o} value={o}>{o}</option>))}
    </select>
  );
}
