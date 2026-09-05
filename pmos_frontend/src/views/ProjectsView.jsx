import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../rbac/AuthContext.jsx";
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
import ViewBuilder from "./ViewBuilder.jsx";

const PAGE_SIZES = [20, 50, 100];

export default function ProjectsView() {
  const toast = useToast();
  const { can } = useAuth();
  const canCreate = can("project.create");
  const canBulk = can("project.bulk_update");
  const canFinance = can("finance.read");
  const canViewCreate = can("view.create");
  const canViewDelete = can("view.delete");
  const canImport = can("project.import") || canCreate;

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
  const [viewMode, setViewMode] = useState("TABLE");

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
  const [viewBuilderOpen, setViewBuilderOpen] = useState(false);
  const [editingView, setEditingView] = useState(null);

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
      const [legacyProj, cf, opts, vws] = await Promise.all([
        api.listProjects({
          search: cfg?.search || search,
          page: cfg?.page ?? page,
          page_size: pageSize,
          sort_by: sortBy,
          sort_dir: sortDir,
          include_archived: showArchived,
          filters: !activeView && filters.length ? JSON.stringify(filters) : undefined,
        }),
        api.listCustomFields("PROJECT"),
        api.filterOptions(),
        api.listViews("projects"),
      ]);
      let proj = legacyProj;
      if (activeView) {
        const saved = await api.queryView(activeView, {
          search: cfg?.search || search || undefined,
          page: cfg?.page ?? page,
          page_size: pageSize,
        });
        proj = saved;
      }
      setProjects(proj.items || []);
      setTotal(proj.total || 0);
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

  // Первичная загрузка и обновление данных
  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, sortBy, sortDir, showArchived, filters, activeView]);

  // URL state: /projects?view=<id> (7.md §34)
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("view");
    if (fromUrl && views.some((v) => v.id === fromUrl) && activeView !== fromUrl) {
      const selectedView = views.find((v) => v.id === fromUrl);
      setActiveView(fromUrl);
      applyViewConfig(selectedView);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [views]);

  // Apply фильтров из активного представления
  const applyViewConfig = (view) => {
    if (!view?.config) return;
    const cfg = view.config;
    const savedColumns = cfg.column_order || cfg.visible_columns || cfg.visibleColumns;
    setVisibleKeys(savedColumns ? savedColumns.map((key) => customFields.some((cf) => cf.slug === key) ? `cf_${key}` : key) : DEFAULT_VISIBLE);
    setFilters(cfg.filters || []);
    setViewMode(view?.view_type || "TABLE");
    if (cfg.sorting?.length) {
      setSortBy(cfg.sorting[0].field || "deadline");
      setSortDir(cfg.sorting[0].direction || "asc");
    }
    setPage(1);
  };

  // Встроенные представления + сохранённые (§45: финансы только с finance.read)
  const builtinViews = useMemo(
    () =>
      [
        { key: "all", name: "Все проекты" },
        { key: "my", name: "Мои проекты" },
        { key: "production", name: "Производство" },
        ...(canFinance ? [{ key: "finance", name: "Финансы" }] : []),
        { key: "archive", name: "Архив" },
      ],
    [canFinance]
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
    if (view.key === "all") { setActiveView(null); setViewMode("TABLE"); setVisibleKeys(DEFAULT_VISIBLE); setFilters([]); setSortBy("deadline"); setSortDir("asc"); return; }
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
  const refreshViews = async () => {
    const latest = await api.listViews("projects");
    setViews(latest);
    return latest;
  };

  const toggleViewFavorite = async (view, event) => {
    event.stopPropagation();
    try { await api.favoriteView(view.id, !view.is_favorite); await refreshViews(); }
    catch (e) { toast(e.message, "error"); }
  };

  const duplicateSavedView = async (view, event) => {
    event.stopPropagation();
    try { const copy = await api.duplicateView(view.id); await refreshViews(); setActiveView(copy.id); applyViewConfig(copy); toast(`Создана копия «${copy.name}»`); }
    catch (e) { toast(e.message, "error"); }
  };

  const deleteSavedView = async (view, event) => {
    event.stopPropagation();
    if (!window.confirm(`Удалить представление «${view.name}»? Данные не будут удалены.`)) return;
    try { await api.deleteView(view.id); if (activeView === view.id) { setActiveView(null); setViewMode("TABLE"); } await refreshViews(); toast("Представление удалено"); }
    catch (e) { toast(e.message, "error"); }
  };

  const selectSavedView = async (view) => {
    setActiveView(view.id);
    setViewMode(view.view_type || "TABLE");
    setViewMenuOpen(false);
    setShowArchived(false);
    applyViewConfig(view);
    const params = new URLSearchParams(window.location.search);
    params.set("view", view.id);
    window.history.replaceState({}, "", `/projects?${params.toString()}`);
  };

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      {/* Заголовок */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Проекты</h1>
        <div className="flex items-center gap-2">
          {canImport && (
            <button className="btn btn-secondary" onClick={() => setImportOpen(true)}>
              ⬆ Импорт
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => setExportOpen(true)}>
            ⬇ Экспорт
          </button>
          <button className="btn btn-ghost" onClick={() => setImportHistoryOpen(true)} title="История импортов">
            🕘 История
          </button>
          {canCreate && (
            <button className="btn btn-primary" onClick={() => { setEditedProject(null); setFormOpen(true); }}>
              + Новый проект
            </button>
          )}
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

        {/* Тип представления */}
        <select className="input !w-auto" value={viewMode} onChange={(e) => setViewMode(e.target.value)} title="Тип отображения">
          <option value="TABLE">Таблица</option>
          <option value="KANBAN">Kanban</option>
          <option value="CALENDAR">Календарь</option>
        </select>

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
                <div key={v.id} className="flex items-center border-t border-slate-50">
                  <button
                    className={`flex-1 px-3 py-2 text-left text-sm hover:bg-slate-50 ${activeView === v.id ? "font-semibold text-indigo-600" : ""}`}
                    onClick={() => selectSavedView(v)}
                  >
                    {v.is_favorite ? "★ " : "☆ "}{v.name}
                  </button>
                  <div className="flex items-center">
                    <button className="px-1 text-xs text-amber-500" title="Закрепить" onClick={(e) => toggleViewFavorite(v, e)}>{v.is_favorite ? "★" : "☆"}</button>
                    <button className="px-1 text-xs text-slate-400 hover:text-indigo-600" title="Копировать" onClick={(e) => duplicateSavedView(v, e)}>⧉</button>
                    <button className="px-1 text-xs text-slate-400 hover:text-indigo-600" title="Настроить" onClick={(e) => { e.stopPropagation(); setViewMenuOpen(false); setEditingView(v); setViewBuilderOpen(true); }}>⋯</button>
                    {canViewDelete && v.created_by && <button className="px-1 text-xs text-red-400 hover:text-red-600" title="Удалить" onClick={(e) => deleteSavedView(v, e)}>×</button>}
                  </div>
                </div>
              ))}
              <div className="my-1 border-t border-slate-100" />
              {canViewCreate && (
                <button
                  className="block w-full px-3 py-2 text-left text-sm text-indigo-600 hover:bg-slate-50"
                  onClick={() => { setViewMenuOpen(false); setEditingView(null); setViewBuilderOpen(true); }}
                >
                  + Создать представление
                </button>
              )}
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
          {canBulk && (
            <button className="btn btn-danger !py-1" onClick={bulkArchive}>
              Архив
            </button>
          )}
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
            action={canCreate ? (
              <button className="btn btn-primary" onClick={() => { setEditedProject(null); setFormOpen(true); }}>
                + Новый проект
              </button>
            ) : null}
          />
        ) : viewMode === "KANBAN" ? (
            <ProjectKanban projects={projects} onProjectClick={openProject} />
          ) : viewMode === "CALENDAR" ? (
            <ProjectCalendar projects={projects} onProjectClick={openProject} />
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
      <ViewBuilder
        open={viewBuilderOpen}
        onClose={() => { setViewBuilderOpen(false); setEditingView(null); }}
        view={editingView}
        customFields={customFields}
        filterOptions={filterOptions}
        onSaved={(saved) => {
          setViews((all) => editingView ? all.map((v) => v.id === saved.id ? saved : v) : [...all, saved]);
          setActiveView(saved.id);
          applyViewConfig(saved);
          const params = new URLSearchParams(window.location.search);
          params.set("view", saved.id);
          window.history.replaceState({}, "", `/projects?${params.toString()}`);
        }}
      />
    </div>
  );

  function toggleSort(field) {
    if (sortBy === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(field); setSortDir("asc"); }
  }
}

function ProjectKanban({ projects, onProjectClick }) {
  const stages = ["Новые", "Макет", "Сигнал", "Производство", "Отгрузка", "Завершён"];
  const byStage = (stage) => projects.filter((p) => {
    const value = p.stage || "Новые";
    if (stage === "Новые") return !stages.slice(1).includes(value);
    return value === stage;
  });
  return (
    <div className="grid min-w-[900px] grid-cols-6 gap-3 p-3">
      {stages.map((stage) => (
        <div key={stage} className="min-h-40 rounded-lg bg-slate-50 p-2">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>{stage}</span><span className="rounded-full bg-white px-1.5">{byStage(stage).length}</span>
          </div>
          <div className="space-y-2">
            {byStage(stage).map((p) => (
              <button key={p.id} onClick={() => onProjectClick(p)} className="block w-full rounded-md border border-slate-200 bg-white p-2 text-left shadow-sm hover:border-indigo-300">
                <div className="font-mono text-[10px] text-slate-400">{p.display_id}</div>
                <div className="truncate text-xs font-semibold text-slate-700">{p.title}</div>
                <div className="mt-1 flex justify-between text-[10px] text-slate-500"><span>{p.manager_name || "—"}</span><span>{p.payment_percent || "—"}</span></div>
                {p.risk_level && p.risk_level !== "Нет" && <div className="mt-1 text-[10px] text-red-600">⚠ {p.risk_level}</div>}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ProjectCalendar({ projects, onProjectClick }) {
  const days = [...new Set(projects.filter((p) => p.deadline).map((p) => p.deadline.slice(0, 10)))].sort();
  return (
    <div className="p-4">
      <div className="mb-3 text-sm text-slate-500">Проекты сгруппированы по дедлайну</div>
      {days.length === 0 ? <div className="py-8 text-center text-sm text-slate-400">Нет проектов с дедлайном</div> : <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{days.map((day) => <div key={day} className="rounded-lg border border-slate-200 p-3"><div className="mb-2 text-xs font-semibold text-indigo-600">{day}</div>{projects.filter((p) => p.deadline?.slice(0, 10) === day).map((p) => <button key={p.id} onClick={() => onProjectClick(p)} className="mb-1 block w-full rounded bg-slate-50 px-2 py-1 text-left text-xs hover:bg-indigo-50"><b>{p.display_id}</b> — {p.title}</button>)}</div>)}</div>}
    </div>
  );
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
