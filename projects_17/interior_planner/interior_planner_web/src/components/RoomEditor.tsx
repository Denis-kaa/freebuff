// RoomEditor.tsx — главный экран дизайнера интерьеров (русская версия).
// Трёхколоночная структура: сайдбар | холст | панель инструментов.

import React, { useState, useCallback, useRef, useEffect ***REMOVED*** from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  TextInput,
  Image,
  useWindowDimensions,
***REMOVED*** from "react-native";

import Canvas2D, { addObjectAtCenter ***REMOVED*** from "./Canvas2D";
import { useRoomStore, makeProject ***REMOVED*** from "../store/roomStore";
import knowledgeBaseJson from "../data/knowledge_base_ru.json";
import type { KnowledgeBase, RoomType, FurnitureObject ***REMOVED*** from "../types/domain";

const KB: KnowledgeBase = knowledgeBaseJson as KnowledgeBase;

// ─── Картинки материалов через Picsum Photos (seed API, бесплатно) ──────
const materialImageUrl = (id: string): string =>
  `https://picsum.photos/seed/interior-${encodeURIComponent(id)***REMOVED***/300/300`;

// Fallback-цвета для свотчей (показываются пока картинка грузится) — белые не видны
const SWATCH_FALLBACK: Record<string, string> = {***REMOVED***;
KB.materials.walls.forEach((m) => { SWATCH_FALLBACK[m.id***REMOVED*** = m.color; ***REMOVED***);
KB.materials.floors.forEach((m) => { SWATCH_FALLBACK[m.id***REMOVED*** = m.color; ***REMOVED***);
KB.materials.ceilings.forEach((m) => { SWATCH_FALLBACK[m.id***REMOVED*** = m.color; ***REMOVED***);
KB.furniture.forEach((f) => { SWATCH_FALLBACK[f.id***REMOVED*** = f.color; ***REMOVED***);

// Лёгкий React-компонент: картинка-свотч с fallback на цвет
const SwatchImage: React.FC<{ materialId: string; variant?: "lg" | "sm" ***REMOVED***> = ({ materialId, variant = "lg" ***REMOVED***) => {
  const [loaded, setLoaded***REMOVED*** = useState(false);
  const [error, setError***REMOVED*** = useState(false);
  const bg = SWATCH_FALLBACK[materialId***REMOVED*** || "#444";
  const size = variant === "sm" ? { height: 30, borderRadius: 3, marginBottom: 3 ***REMOVED*** : { height: 40, borderRadius: 4, marginBottom: 4 ***REMOVED***;
  return (
    <View style={{ width: "100%", overflow: "hidden", backgroundColor: bg, borderWidth: 1, borderColor: "rgba(255,255,255,0.15)", ...size ***REMOVED******REMOVED***>
      {!error && (
        <Image
          source={{ uri: materialImageUrl(materialId) ***REMOVED******REMOVED***
          resizeMode="cover"
          onLoad={() => setLoaded(true)***REMOVED***
          onError={() => setError(true)***REMOVED***
          style={{ width: "100%", height: "100%", opacity: loaded ? 1 : 0 ***REMOVED******REMOVED***
        />
      )***REMOVED***
    </View>
  );
***REMOVED***;

const ROOM_TYPES: { id: RoomType; label: string ***REMOVED***[***REMOVED*** = [
  { id: "kitchen", label: "Кухня" ***REMOVED***,
  { id: "living_room", label: "Гостиная" ***REMOVED***,
  { id: "bedroom", label: "Спальня" ***REMOVED***,
  { id: "bathroom", label: "Ванная" ***REMOVED***,
  { id: "office", label: "Кабинет" ***REMOVED***,
  { id: "dining", label: "Столовая" ***REMOVED***,
***REMOVED***;

type Tab = "room" | "walls" | "floor" | "ceiling" | "light" | "furniture";

const TABS: { id: Tab; label: string ***REMOVED***[***REMOVED*** = [
  { id: "room", label: "🏠 Комната" ***REMOVED***,
  { id: "walls", label: "🖼 Стены" ***REMOVED***,
  { id: "floor", label: "🪵 Пол" ***REMOVED***,
  { id: "ceiling", label: "⬜ Потолок" ***REMOVED***,
  { id: "light", label: "💡 Свет" ***REMOVED***,
  { id: "furniture", label: "🪑 Мебель" ***REMOVED***,
***REMOVED***;

const FURNITURE_TYPES: { id: string; label: string ***REMOVED***[***REMOVED*** = [
  { id: "sofa", label: "Диваны" ***REMOVED***,
  { id: "bed", label: "Кровати" ***REMOVED***,
  { id: "table", label: "Столы" ***REMOVED***,
  { id: "chair", label: "Стулья" ***REMOVED***,
  { id: "storage", label: "Хранение" ***REMOVED***,
  { id: "fixture", label: "Сантехника" ***REMOVED***,
  { id: "appliance", label: "Техника" ***REMOVED***,
  { id: "decor", label: "Декор" ***REMOVED***,
***REMOVED***;

// ─── Валидация размеров комнаты (Задача 2.4) ───────────────────────────
const MIN_ROOM_M = 2;
const MAX_ROOM_M = 20;

const parseDim = (v: string): number => parseFloat(v.replace(",", "."));

const validateDims = (wStr: string, hStr: string): { valid: boolean; message: string ***REMOVED*** => {
  const w = parseDim(wStr);
  const h = parseDim(hStr);
  if (isNaN(w) || isNaN(h)) return { valid: false, message: "Укажите ширину и высоту комнаты (числа в метрах)." ***REMOVED***;
  if (w < MIN_ROOM_M || h < MIN_ROOM_M) return { valid: false, message: `Минимальный размер комнаты — ${MIN_ROOM_M***REMOVED***×${MIN_ROOM_M***REMOVED*** м.` ***REMOVED***;
  if (w > MAX_ROOM_M || h > MAX_ROOM_M) return { valid: false, message: `Максимальный размер комнаты — ${MAX_ROOM_M***REMOVED***×${MAX_ROOM_M***REMOVED*** м.` ***REMOVED***;
  return { valid: true, message: "" ***REMOVED***;
***REMOVED***;

export default function RoomEditor(): React.ReactElement {
  const project = useRoomStore((s) => s.project);
  const setProject = useRoomStore((s) => s.setProject);
  const setRoom = useRoomStore((s) => s.setRoom);
  const setStyle = useRoomStore((s) => s.setStyle);
  const addObject = useRoomStore((s) => s.addObject);
  const deleteObject = useRoomStore((s) => s.deleteObject);
  const undo = useRoomStore((s) => s.undo);
  const redo = useRoomStore((s) => s.redo);
  const canUndo = useRoomStore((s) => s.canUndo());
  const canRedo = useRoomStore((s) => s.canRedo());
  const hasHydrated = useRoomStore((s) => s.hasHydrated);

  const [activeTab, setActiveTab***REMOVED*** = useState<Tab>("room");
  const [sidebarOpen, setSidebarOpen***REMOVED*** = useState(false);
  const [dragItem, setDragItem***REMOVED*** = useState<string | null>(null);
  const [selectedObj, setSelectedObj***REMOVED*** = useState<string | null>(null);
  const { width: screenW ***REMOVED*** = useWindowDimensions();
  const isMobile = screenW < 768;

  // Открываем сайдбар при переходе на десктоп (после SSR/hydration)
  useEffect(() => {
    if (!isMobile) setSidebarOpen(true);
  ***REMOVED***, [isMobile***REMOVED***);

  // ─── Room config state ─────────────────────────────────────────────
  const [cfgName, setCfgName***REMOVED*** = useState("Моя комната");
  const [cfgType, setCfgType***REMOVED*** = useState<RoomType>("living_room");
  const [cfgW, setCfgW***REMOVED*** = useState("5");
  const [cfgH, setCfgH***REMOVED*** = useState("4");
  const [cfgStyle, setCfgStyle***REMOVED*** = useState("scandi");
  const cfgDims = validateDims(cfgW, cfgH);
  const roomDims = project
    ? validateDims(String(project.room.dimensions_m[0***REMOVED***), String(project.room.dimensions_m[1***REMOVED***))
    : { valid: true, message: "" ***REMOVED***;

  // ─── Project bootstrap ─────────────────────────────────────────────
  const createNewProject = useCallback(() => {
    const res = validateDims(cfgW, cfgH);
    if (!res.valid) {
      Alert.alert("Размеры комнаты", res.message);
      return;
    ***REMOVED***
    const w = parseDim(cfgW);
    const h = parseDim(cfgH);
    const room = {
      type: cfgType,
      dimensions_m: [w, h***REMOVED*** as [number, number***REMOVED***,
      surfaces: { wall: "paint-white", floor: "laminate-oak", ceiling: "ceiling-white" ***REMOVED***,
    ***REMOVED***;
    setProject(makeProject(cfgName, room, cfgStyle));
    setSidebarOpen(false);
    if (isMobile) setSidebarOpen(false);
  ***REMOVED***, [cfgName, cfgType, cfgW, cfgH, cfgStyle, setProject, isMobile***REMOVED***);

  // ─── Drag & drop (через dataTransfer, не React state — избегаем гонки) ──
  const handleDragStart = useCallback((e: React.DragEvent, catalogId: string) => {
    (e as any).dataTransfer.setData('text/plain', catalogId);
    (e as any).dataTransfer.effectAllowed = 'copy';
    setDragItem(catalogId);
  ***REMOVED***, [***REMOVED***);

  const handleDragEnd = useCallback(() => {
    setDragItem(null);
  ***REMOVED***, [***REMOVED***);

  const handleCanvasDrop = useCallback((catalogId: string, x_m: number, y_m: number) => {
    if (!project) return;
    const f = KB.furniture.find((e) => e.id === catalogId);
    if (!f) return;
    const z = project.objects.length;
    const obj: FurnitureObject = {
      id: `${Date.now().toString(36)***REMOVED***-${Math.random().toString(36).slice(2, 8)***REMOVED***`,
      catalog_id: catalogId,
      position_m: [Math.max(0, x_m), Math.max(0, y_m)***REMOVED***,
      size_m: f.size_m,
      rotation_deg: 0,
      z_index: z,
    ***REMOVED***;
    addObject(obj);
    setDragItem(null);
  ***REMOVED***, [project, addObject***REMOVED***);

  const handleCanvasObjectSelect = useCallback((objId: string | null) => {
    setSelectedObj(objId);
  ***REMOVED***, [***REMOVED***);

  const handleDeleteSelected = useCallback(() => {
    if (!selectedObj) return;
    Alert.alert("Удалить?", "Убрать этот предмет из комнаты?", [
      { text: "Отмена", style: "cancel" ***REMOVED***,
      { text: "Удалить", style: "destructive", onPress: () => { deleteObject(selectedObj); setSelectedObj(null); ***REMOVED*** ***REMOVED***,
    ***REMOVED***);
  ***REMOVED***, [selectedObj, deleteObject***REMOVED***);

  // ─── Prompt generation ─────────────────────────────────────────────
  const generatePrompt = useCallback((): string => {
    if (!project) return "Создайте проект, чтобы сгенерировать промт.";
    const r = project.room;
    const wall = KB.materials.walls.find((m) => m.id === r.surfaces.wall);
    const floor = KB.materials.floors.find((m) => m.id === r.surfaces.floor);
    const ceil = KB.materials.ceilings.find((m) => m.id === r.surfaces.ceiling);
    const style = KB.styles.find((s) => s.id === project.style_id);
    const lightId = (project as any)._light_id || "lighting-warm";
    const light = KB.lighting.find((l) => l.id === lightId) || KB.lighting[0***REMOVED***;
    const furn = project.objects.map((o) => {
      const f = KB.furniture.find((fe) => fe.id === o.catalog_id);
      return f ? `— ${f.name***REMOVED*** (${f.size_m[0***REMOVED***.toFixed(1)***REMOVED***×${f.size_m[1***REMOVED***.toFixed(1)***REMOVED***м)` : o.catalog_id;
    ***REMOVED***).join("\n");

    return [
      `Создай фотореалистичный рендер интерьера:`,
      `— Комната: ${r.type === "living_room" ? "гостиная" : r.type***REMOVED***, ${r.dimensions_m[0***REMOVED******REMOVED***×${r.dimensions_m[1***REMOVED******REMOVED***м`,
      `— Стиль: ${style?.prefix || style?.label || "современный"***REMOVED***`,
      `— Стены: ${wall?.label || r.surfaces.wall***REMOVED***, Пол: ${floor?.label || r.surfaces.floor***REMOVED***, Потолок: ${ceil?.label || r.surfaces.ceiling***REMOVED***`,
      `— Освещение: ${light?.modifier || "естественное"***REMOVED***`,
      `— Мебель:`,
      furn || "— (не выбрана)",
      "",
      `Камера: вид сверху-сбоку (3/4), focal length 24mm, фотореализм, интерьерная съёмка.`,
    ***REMOVED***.join("\n");
  ***REMOVED***, [project***REMOVED***);

  // ─── Hydration guard ───────────────────────────────────────────────
  if (!hasHydrated) {
    return <View style={ss.empty***REMOVED***><Text style={ss.emptyTitle***REMOVED***>Загрузка проекта…</Text></View>;
  ***REMOVED***

  // ─── Sidebar content ───────────────────────────────────────────────
  const renderSidebar = (): React.ReactElement => {
    if (!project) {
      // Конфигуратор новой комнаты
      return (
        <ScrollView style={ss.sidebarInner***REMOVED***>
          <Text style={ss.sidebarTitle***REMOVED***>Новый проект</Text>

          <Text style={ss.label***REMOVED***>Название</Text>
          <TextInput style={ss.input***REMOVED*** value={cfgName***REMOVED*** onChangeText={setCfgName***REMOVED*** placeholder="Моя комната" />

          <Text style={ss.label***REMOVED***>Тип комнаты</Text>
          <View style={ss.chipRow***REMOVED***>
            {ROOM_TYPES.map((rt) => (
              <TouchableOpacity key={rt.id***REMOVED*** style={[ss.chip, cfgType === rt.id && ss.chipActive***REMOVED******REMOVED***
                onPress={() => setCfgType(rt.id)***REMOVED***>
                <Text style={[ss.chipText, cfgType === rt.id && ss.chipTextActive***REMOVED******REMOVED***>{rt.label***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </View>

          <Text style={ss.label***REMOVED***>Размеры (м)</Text>
          <View style={ss.row***REMOVED***>
            <TextInput style={[ss.input, ss.halfInput, !cfgDims.valid && ss.inputInvalid***REMOVED******REMOVED*** value={cfgW***REMOVED*** onChangeText={setCfgW***REMOVED*** keyboardType="numeric" placeholder="Ширина" />
            <Text style={ss.dimSep***REMOVED***>×</Text>
            <TextInput style={[ss.input, ss.halfInput, !cfgDims.valid && ss.inputInvalid***REMOVED******REMOVED*** value={cfgH***REMOVED*** onChangeText={setCfgH***REMOVED*** keyboardType="numeric" placeholder="Высота" />
          </View>
          {!cfgDims.valid && <Text style={ss.invalidHint***REMOVED***>⚠ {cfgDims.message***REMOVED***</Text>***REMOVED***
          <Text style={ss.rangeHint***REMOVED***>Допустимо: {MIN_ROOM_M***REMOVED***–{MAX_ROOM_M***REMOVED*** м по каждой стороне</Text>

          <Text style={ss.label***REMOVED***>Стиль</Text>
          <View style={ss.chipRow***REMOVED***>
            {KB.styles.map((st) => (
              <TouchableOpacity key={st.id***REMOVED*** style={[ss.chip, cfgStyle === st.id && ss.chipActive***REMOVED******REMOVED***
                onPress={() => setCfgStyle(st.id)***REMOVED***>
                <Text style={[ss.chipText, cfgStyle === st.id && ss.chipTextActive***REMOVED******REMOVED***>{st.label***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </View>

          <TouchableOpacity
            style={[ss.primaryButton, !cfgDims.valid && ss.primaryButtonDisabled***REMOVED******REMOVED***
            onPress={() => {
              if (!cfgDims.valid) {
                Alert.alert("Размеры комнаты", cfgDims.message);
                return;
              ***REMOVED***
              createNewProject();
            ***REMOVED******REMOVED***
          >
            <Text style={ss.primaryButtonText***REMOVED***>✨ Создать проект</Text>
          </TouchableOpacity>
        </ScrollView>
      );
    ***REMOVED***

    // Редактирование существующего проекта
    return (
      <ScrollView style={ss.sidebarInner***REMOVED***>
        <Text style={ss.sidebarTitle***REMOVED***>{project.name***REMOVED***</Text>
        <Text style={ss.dimLabel***REMOVED***>{project.room.dimensions_m[0***REMOVED******REMOVED***×{project.room.dimensions_m[1***REMOVED******REMOVED***м · {ROOM_TYPES.find((r) => r.id === project.room.type)?.label || project.room.type***REMOVED***</Text>

        {/* Экспорт / Импорт */***REMOVED***
        <View style={ss.row***REMOVED***>
          <TouchableOpacity style={ss.ioBtn***REMOVED*** onPress={handleExport***REMOVED***>
            <Text style={ss.ioBtnText***REMOVED***>📥 JSON</Text>
          </TouchableOpacity>
          <TouchableOpacity style={ss.ioBtn***REMOVED*** onPress={handleImport***REMOVED***>
            <Text style={ss.ioBtnText***REMOVED***>📤 JSON</Text>
          </TouchableOpacity>
        </View>

        {/* Табы */***REMOVED***
        <View style={ss.tabRow***REMOVED***>
          {TABS.map((t) => (
            <TouchableOpacity key={t.id***REMOVED*** style={[ss.tab, activeTab === t.id && ss.tabActive***REMOVED******REMOVED***
              onPress={() => setActiveTab(t.id)***REMOVED***>
              <Text style={[ss.tabText, activeTab === t.id && ss.tabTextActive***REMOVED******REMOVED***>{t.label***REMOVED***</Text>
            </TouchableOpacity>
          ))***REMOVED***
        </View>

        {/* Содержимое таба */***REMOVED***
        {activeTab === "room" && (
          <View>
            <Text style={ss.label***REMOVED***>Тип комнаты</Text>
            <View style={ss.chipRow***REMOVED***>
              {ROOM_TYPES.map((rt) => (
                <TouchableOpacity key={rt.id***REMOVED*** style={[ss.chip, project.room.type === rt.id && ss.chipActive***REMOVED******REMOVED***
                  onPress={() => setRoom({ ...project.room, type: rt.id ***REMOVED***)***REMOVED***>
                  <Text style={[ss.chipText, project.room.type === rt.id && ss.chipTextActive***REMOVED******REMOVED***>{rt.label***REMOVED***</Text>
                </TouchableOpacity>
              ))***REMOVED***
            </View>
            <Text style={ss.label***REMOVED***>Размеры (м)</Text>
            <View style={ss.row***REMOVED***>
              <TextInput style={[ss.input, ss.halfInput, !roomDims.valid && ss.inputInvalid***REMOVED******REMOVED*** value={String(project.room.dimensions_m[0***REMOVED***)***REMOVED***
                onChangeText={(v) => {
                  const n = parseDim(v);
                  setRoom({ ...project.room, dimensions_m: [isNaN(n) ? project.room.dimensions_m[0***REMOVED*** : n, project.room.dimensions_m[1***REMOVED******REMOVED*** ***REMOVED***);
                ***REMOVED******REMOVED*** keyboardType="numeric" />
              <Text style={ss.dimSep***REMOVED***>×</Text>
              <TextInput style={[ss.input, ss.halfInput, !roomDims.valid && ss.inputInvalid***REMOVED******REMOVED*** value={String(project.room.dimensions_m[1***REMOVED***)***REMOVED***
                onChangeText={(v) => {
                  const n = parseDim(v);
                  setRoom({ ...project.room, dimensions_m: [project.room.dimensions_m[0***REMOVED***, isNaN(n) ? project.room.dimensions_m[1***REMOVED*** : n***REMOVED*** ***REMOVED***);
                ***REMOVED******REMOVED*** keyboardType="numeric" />
            </View>
            {!roomDims.valid && <Text style={ss.invalidHint***REMOVED***>⚠ {roomDims.message***REMOVED***</Text>***REMOVED***
            <Text style={ss.label***REMOVED***>Стиль</Text>
            <View style={ss.chipRow***REMOVED***>
              {KB.styles.map((st) => (
                <TouchableOpacity key={st.id***REMOVED*** style={[ss.chip, project.style_id === st.id && ss.chipActive***REMOVED******REMOVED***
                  onPress={() => setStyle(st.id)***REMOVED***>
                  <Text style={[ss.chipText, project.style_id === st.id && ss.chipTextActive***REMOVED******REMOVED***>{st.label***REMOVED***</Text>
                </TouchableOpacity>
              ))***REMOVED***
            </View>
          </View>
        )***REMOVED***

        {activeTab === "walls" && (
          <View style={ss.chipRow***REMOVED***>
            {KB.materials.walls.map((m) => (
              <TouchableOpacity key={m.id***REMOVED*** style={[ss.materialCard, project.room.surfaces.wall === m.id && ss.materialCardActive***REMOVED******REMOVED***
                onPress={() => setRoom({ ...project.room, surfaces: { ...project.room.surfaces, wall: m.id ***REMOVED*** ***REMOVED***)***REMOVED***>
                <SwatchImage materialId={m.id***REMOVED*** />
                <Text style={ss.materialLabel***REMOVED***>{m.label***REMOVED***</Text>
                <Text style={ss.materialMood***REMOVED***>{m.mood***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </View>
        )***REMOVED***

        {activeTab === "floor" && (
          <View style={ss.chipRow***REMOVED***>
            {KB.materials.floors.map((m) => (
              <TouchableOpacity key={m.id***REMOVED*** style={[ss.materialCard, project.room.surfaces.floor === m.id && ss.materialCardActive***REMOVED******REMOVED***
                onPress={() => setRoom({ ...project.room, surfaces: { ...project.room.surfaces, floor: m.id ***REMOVED*** ***REMOVED***)***REMOVED***>
                <SwatchImage materialId={m.id***REMOVED*** />
                <Text style={ss.materialLabel***REMOVED***>{m.label***REMOVED***</Text>
                <Text style={ss.materialMood***REMOVED***>{m.mood***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </View>
        )***REMOVED***

        {activeTab === "ceiling" && (
          <View style={ss.chipRow***REMOVED***>
            {KB.materials.ceilings.map((m) => (
              <TouchableOpacity key={m.id***REMOVED*** style={[ss.materialCard, project.room.surfaces.ceiling === m.id && ss.materialCardActive***REMOVED******REMOVED***
                onPress={() => setRoom({ ...project.room, surfaces: { ...project.room.surfaces, ceiling: m.id ***REMOVED*** ***REMOVED***)***REMOVED***>
                <SwatchImage materialId={m.id***REMOVED*** />
                <Text style={ss.materialLabel***REMOVED***>{m.label***REMOVED***</Text>
                <Text style={ss.materialMood***REMOVED***>{m.mood***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </View>
        )***REMOVED***

        {activeTab === "light" && (
          <View style={ss.chipRow***REMOVED***>
            {KB.lighting.map((l) => (
              <TouchableOpacity key={l.id***REMOVED*** style={[ss.materialCard, (project as any)._light_id === l.id && ss.materialCardActive***REMOVED******REMOVED***
                onPress={() => {
                  // Сохраняем lighting_id отдельно от style_id
                  (project as any)._light_id = l.id;
                  // Форсируем ререндер через setRoom
                  setRoom({ ...project.room ***REMOVED***);
                ***REMOVED******REMOVED***>
                <Text style={ss.materialLabel***REMOVED***>{l.label***REMOVED***</Text>
                <Text style={ss.materialMood***REMOVED***>{l.modifier***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </View>
        )***REMOVED***

        {activeTab === "furniture" && (
          <View>
            {FURNITURE_TYPES.map((ft) => {
              const items = KB.furniture.filter((f) => f.type === ft.id);
              if (items.length === 0) return null;
              return (
                <View key={ft.id***REMOVED*** style={ss.furnSection***REMOVED***>
                  <Text style={ss.furnSectionTitle***REMOVED***>{ft.label***REMOVED***</Text>
                  <View style={ss.furnGrid***REMOVED***>
                    {items.map((f) => (
                      <View
                        key={f.id***REMOVED***
                        style={[ss.furnCard, dragItem === f.id && ss.furnCardDragging***REMOVED*** as any***REMOVED***
                        draggable={true***REMOVED***
                        onDragStart={(e: any) => handleDragStart(e, f.id)***REMOVED***
                        onDragEnd={handleDragEnd***REMOVED***
                        onClick={() => {
                          if (!project) return;
                          const [w, h***REMOVED*** = project.room.dimensions_m;
                          addObject(addObjectAtCenter(f.id, w, h, project.objects.length));
                        ***REMOVED******REMOVED***
                      >
                        <SwatchImage materialId={f.id***REMOVED*** variant="sm" />
                        <Text style={ss.furnName***REMOVED***>{f.name***REMOVED***</Text>
                        <Text style={ss.furnDim***REMOVED***>{f.size_m[0***REMOVED***.toFixed(1)***REMOVED***×{f.size_m[1***REMOVED***.toFixed(1)***REMOVED***м</Text>
                      </View>
                    ))***REMOVED***
                  </View>
                </View>
              );
            ***REMOVED***)***REMOVED***
          </View>
        )***REMOVED***
      </ScrollView>
    );
  ***REMOVED***;

  // ─── Prompt panel ──────────────────────────────────────────────────
  const [showPrompt, setShowPrompt***REMOVED*** = useState(false);
  const promptText = generatePrompt();

  // ─── Export / Import ──────────────────────────────────────────────
  const handleExport = useCallback(() => {
    if (!project) return;
    const data = JSON.stringify(project, null, 2);
    const blob = new Blob([data***REMOVED***, { type: "application/json" ***REMOVED***);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${project.name.replace(/\s+/g, "_")***REMOVED***.json`;
    a.click();
    URL.revokeObjectURL(url);
  ***REMOVED***, [project***REMOVED***);

  const handleImport = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".json";
    input.onchange = (e: any) => {
      const file = e.target?.files?.[0***REMOVED***;
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const imported = JSON.parse(reader.result as string);
          if (!imported.id || !imported.room || !imported.objects) {
            Alert.alert("Ошибка", "Неверный формат файла проекта.");
            return;
          ***REMOVED***
          (imported as any)._light_id = (project as any)?._light_id || "lighting-warm";
          setProject(imported);
          setSidebarOpen(false);
        ***REMOVED*** catch { Alert.alert("Ошибка", "Не удалось прочитать файл."); ***REMOVED***
      ***REMOVED***;
      reader.readAsText(file);
    ***REMOVED***;
    input.click();
  ***REMOVED***, [project, setProject***REMOVED***);

  // ─── Main render ───────────────────────────────────────────────────
  return (
    <View style={ss.root***REMOVED***>
      {/* Верхняя панель */***REMOVED***
      <View style={ss.topBar***REMOVED***>
        <TouchableOpacity style={ss.hamburger***REMOVED*** onPress={() => setSidebarOpen(!sidebarOpen)***REMOVED***>
          <Text style={ss.hamburgerText***REMOVED***>{sidebarOpen ? "✕" : "☰"***REMOVED***</Text>
        </TouchableOpacity>
        <Text style={ss.appTitle***REMOVED***>🏗 Дизайнер интерьеров</Text>
        <View style={ss.row***REMOVED***>
          <TouchableOpacity style={[ss.undoBtn, !canUndo && ss.undoBtnDisabled***REMOVED******REMOVED*** onPress={undo***REMOVED*** disabled={!canUndo***REMOVED***>
            <Text style={ss.undoBtnText***REMOVED***>↩</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[ss.undoBtn, !canRedo && ss.undoBtnDisabled***REMOVED******REMOVED*** onPress={redo***REMOVED*** disabled={!canRedo***REMOVED***>
            <Text style={ss.undoBtnText***REMOVED***>↪</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity style={ss.promptBtn***REMOVED*** onPress={() => setShowPrompt(!showPrompt)***REMOVED***>
          <Text style={ss.promptBtnText***REMOVED***>📋 Промт</Text>
        </TouchableOpacity>
      </View>

      <View style={ss.body***REMOVED***>
        {/* Сайдбар (overlay на мобильных) */***REMOVED***
        {sidebarOpen && (
          <View style={[ss.sidebar, isMobile && ss.sidebarMobile***REMOVED******REMOVED***>{renderSidebar()***REMOVED***</View>
        )***REMOVED***
        {isMobile && sidebarOpen && (
          <TouchableOpacity style={ss.backdrop***REMOVED*** onPress={() => setSidebarOpen(false)***REMOVED*** activeOpacity={1***REMOVED*** />
        )***REMOVED***

        {/* Центр — холст */***REMOVED***
        <View style={ss.canvasArea***REMOVED***>
          {project ? (
            <Canvas2D
              dropItem={dragItem***REMOVED***
              onDrop={handleCanvasDrop***REMOVED***
              selectedObj={selectedObj***REMOVED***
              onSelect={handleCanvasObjectSelect***REMOVED***
              isMobile={isMobile***REMOVED***
            />
          ) : (
            <View style={ss.emptyCanvas***REMOVED***>
              <Text style={ss.emptyCanvasTitle***REMOVED***>Создайте проект в сайдбаре</Text>
              <Text style={ss.emptyCanvasSub***REMOVED***>Настройте комнату и добавляйте мебель</Text>
            </View>
          )***REMOVED***
        </View>

        {/* Панель выделенного объекта (overlay на мобильных) */***REMOVED***
        {selectedObj && project && (
          <View style={[ss.rightPanel, isMobile && ss.rightPanelMobile***REMOVED******REMOVED***>
            <View style={ss.rightPanelHead***REMOVED***>
              <Text style={ss.rightPanelTitle***REMOVED***>Предмет</Text>
              {isMobile && (
                <TouchableOpacity onPress={() => setSelectedObj(null)***REMOVED***>
                  <Text style={{ color: "#E0E0E0", fontSize: 16 ***REMOVED******REMOVED***>✕</Text>
                </TouchableOpacity>
              )***REMOVED***
            </View>
            <Text style={ss.rightPanelText***REMOVED***>
              {(() => {
                const o = project.objects.find((x) => x.id === selectedObj);
                if (!o) return "—";
                const f = KB.furniture.find((fe) => fe.id === o.catalog_id);
                return f ? f.name : o.catalog_id;
              ***REMOVED***)()***REMOVED***
            </Text>
            <TouchableOpacity style={ss.deleteBtn***REMOVED*** onPress={handleDeleteSelected***REMOVED***>
              <Text style={ss.deleteBtnText***REMOVED***>🗑 Удалить</Text>
            </TouchableOpacity>
            <Text style={ss.hint***REMOVED***>Совет: перетащите мебель на холст мышью</Text>
          </View>
        )***REMOVED***
      </View>

      {/* Промт-панель (снизу) */***REMOVED***
      {showPrompt && (
        <View style={ss.promptPanel***REMOVED***>
          <View style={ss.promptHead***REMOVED***>
            <Text style={ss.promptTitle***REMOVED***>📋 Сгенерированный промт</Text>
            <TouchableOpacity onPress={() => setShowPrompt(false)***REMOVED***>
              <Text style={ss.promptClose***REMOVED***>✕</Text>
            </TouchableOpacity>
          </View>
          <ScrollView style={ss.promptScroll***REMOVED***>
            <Text style={ss.promptText***REMOVED***>{promptText***REMOVED***</Text>
          </ScrollView>
          <TouchableOpacity style={ss.copyBtn***REMOVED*** onPress={() => {
            if (typeof navigator !== "undefined" && navigator.clipboard) {
              navigator.clipboard.writeText(promptText).catch(() => {***REMOVED***);
              Alert.alert("Скопировано", "Промт скопирован в буфер обмена.");
            ***REMOVED***
          ***REMOVED******REMOVED***>
            <Text style={ss.copyBtnText***REMOVED***>📋 Скопировать промт</Text>
          </TouchableOpacity>
        </View>
      )***REMOVED***
    </View>
  );
***REMOVED***

// ─── Styles ─────────────────────────────────────────────────────────────
const ss = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1A1A2E" ***REMOVED***,
  topBar: { flexDirection: "row", alignItems: "center", padding: 8, backgroundColor: "#16213E", borderBottomWidth: 1, borderBottomColor: "#0F3460" ***REMOVED***,
  hamburger: { padding: 8 ***REMOVED***,
  hamburgerText: { color: "#E0E0E0", fontSize: 18 ***REMOVED***,
  appTitle: { flex: 1, color: "#FFFFFF", fontSize: 16, fontWeight: "700", textAlign: "center" ***REMOVED***,
  promptBtn: { paddingHorizontal: 12, paddingVertical: 6, backgroundColor: "#0F3460", borderRadius: 8 ***REMOVED***,
  undoBtn: { marginRight: 6, paddingHorizontal: 10, paddingVertical: 4, backgroundColor: "#0F3460", borderRadius: 6, borderWidth: 1, borderColor: "#1A5276" ***REMOVED***,
  undoBtnDisabled: { opacity: 0.35 ***REMOVED***,
  undoBtnText: { color: "#E0E0E0", fontSize: 14, fontWeight: "700" ***REMOVED***,
  promptBtnText: { color: "#E0E0E0", fontSize: 13 ***REMOVED***,
  body: { flex: 1, flexDirection: "row" ***REMOVED***,
  sidebar: { width: 280, backgroundColor: "#16213E", borderRightWidth: 1, borderRightColor: "#0F3460", overflow: "hidden" ***REMOVED***,
  sidebarMobile: { position: "absolute" as any, top: 0, left: 0, bottom: 0, zIndex: 100, width: 280 ***REMOVED***,
  backdrop: { position: "absolute" as any, top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)" as any, zIndex: 99 ***REMOVED***,
  sidebarInner: { padding: 12 ***REMOVED***,
  sidebarTitle: { color: "#FFFFFF", fontSize: 16, fontWeight: "700", marginBottom: 4 ***REMOVED***,
  dimLabel: { color: "#9E9E9E", fontSize: 12, marginBottom: 12 ***REMOVED***,
  label: { color: "#B0B0B0", fontSize: 12, fontWeight: "600", marginTop: 10, marginBottom: 4 ***REMOVED***,
  input: { backgroundColor: "#0F3460", color: "#FFFFFF", padding: 8, borderRadius: 6, fontSize: 13, borderWidth: 1, borderColor: "#1A5276" ***REMOVED***,
  halfInput: { flex: 1 ***REMOVED***,
  dimSep: { color: "#FFFFFF", fontSize: 16, marginHorizontal: 8, alignSelf: "center" ***REMOVED***,
  row: { flexDirection: "row", alignItems: "center" ***REMOVED***,
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 4 ***REMOVED***,
  chip: { backgroundColor: "#0F3460", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, marginRight: 4, marginBottom: 4, borderWidth: 1, borderColor: "#1A5276" ***REMOVED***,
  chipActive: { backgroundColor: "#1976D2", borderColor: "#42A5F5" ***REMOVED***,
  chipText: { color: "#B0B0B0", fontSize: 11 ***REMOVED***,
  chipTextActive: { color: "#FFFFFF", fontWeight: "600" ***REMOVED***,
  materialCard: { backgroundColor: "#0F3460", padding: 8, borderRadius: 8, marginRight: 6, marginBottom: 6, width: 120, borderWidth: 1, borderColor: "#1A5276" ***REMOVED***,
  materialCardActive: { borderColor: "#42A5F5", borderWidth: 2 ***REMOVED***,
  swatch: { width: "100%", height: 40, borderRadius: 4, marginBottom: 4, borderWidth: 1, borderColor: "rgba(255,255,255,0.15)" ***REMOVED***,
  materialLabel: { color: "#FFFFFF", fontSize: 11, fontWeight: "600" ***REMOVED***,
  materialMood: { color: "#9E9E9E", fontSize: 10 ***REMOVED***,
  tabRow: { flexDirection: "row", flexWrap: "wrap", gap: 4, marginBottom: 10 ***REMOVED***,
  tab: { backgroundColor: "#0F3460", paddingHorizontal: 8, paddingVertical: 5, borderRadius: 6, borderWidth: 1, borderColor: "#1A5276" ***REMOVED***,
  tabActive: { backgroundColor: "#1976D2", borderColor: "#42A5F5" ***REMOVED***,
  tabText: { color: "#B0B0B0", fontSize: 11 ***REMOVED***,
  tabTextActive: { color: "#FFFFFF", fontWeight: "600" ***REMOVED***,
  furnSection: { marginBottom: 10 ***REMOVED***,
  furnSectionTitle: { color: "#42A5F5", fontSize: 12, fontWeight: "700", marginBottom: 4 ***REMOVED***,
  furnGrid: { flexDirection: "row", flexWrap: "wrap", gap: 4 ***REMOVED***,
  furnCard: { backgroundColor: "#0F3460", padding: 6, borderRadius: 6, width: 115, borderWidth: 1, borderColor: "#1A5276", cursor: "grab" as any ***REMOVED***,
  furnCardDragging: { opacity: 0.4, borderColor: "#42A5F5" ***REMOVED***,
  furnSwatch: { width: "100%", height: 30, borderRadius: 3, marginBottom: 3 ***REMOVED***,
  furnName: { color: "#FFFFFF", fontSize: 10, fontWeight: "600" ***REMOVED***,
  furnDim: { color: "#9E9E9E", fontSize: 9 ***REMOVED***,
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, backgroundColor: "#1A1A2E" ***REMOVED***,
  emptyTitle: { fontSize: 18, color: "#B0B0B0" ***REMOVED***,
  primaryButton: { backgroundColor: "#1976D2", padding: 12, borderRadius: 8, marginTop: 16, alignItems: "center" ***REMOVED***,
  primaryButtonDisabled: { opacity: 0.5 ***REMOVED***,
  primaryButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" ***REMOVED***,
  inputInvalid: { borderColor: "#EF5350", borderWidth: 1.5 ***REMOVED***,
  invalidHint: { color: "#EF5350", fontSize: 11, marginTop: 4 ***REMOVED***,
  rangeHint: { color: "#757575", fontSize: 10, marginTop: 4 ***REMOVED***,
  canvasArea: { flex: 1, alignItems: "center", justifyContent: "center", overflow: "scroll" as any ***REMOVED***,
  emptyCanvas: { alignItems: "center", justifyContent: "center", padding: 40 ***REMOVED***,
  emptyCanvasTitle: { color: "#FFFFFF", fontSize: 18, fontWeight: "600" ***REMOVED***,
  emptyCanvasSub: { color: "#9E9E9E", fontSize: 13, marginTop: 4 ***REMOVED***,
  rightPanel: { width: 200, backgroundColor: "#16213E", borderLeftWidth: 1, borderLeftColor: "#0F3460", padding: 12 ***REMOVED***,
  rightPanelMobile: { position: "absolute" as any, top: 0, right: 0, bottom: 0, zIndex: 100, width: 200 ***REMOVED***,
  rightPanelHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 ***REMOVED***,
  rightPanelTitle: { color: "#FFFFFF", fontSize: 14, fontWeight: "700", marginBottom: 8 ***REMOVED***,
  rightPanelText: { color: "#E0E0E0", fontSize: 12, marginBottom: 12 ***REMOVED***,
  deleteBtn: { backgroundColor: "#C62828", padding: 8, borderRadius: 6, alignItems: "center", marginBottom: 12 ***REMOVED***,
  deleteBtnText: { color: "#FFFFFF", fontSize: 12, fontWeight: "600" ***REMOVED***,
  hint: { color: "#757575", fontSize: 10, fontStyle: "italic" ***REMOVED***,
  promptPanel: { backgroundColor: "#16213E", borderTopWidth: 2, borderTopColor: "#0F3460", padding: 12, maxHeight: 200 ***REMOVED***,
  promptHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 ***REMOVED***,
  promptTitle: { color: "#FFFFFF", fontSize: 13, fontWeight: "700" ***REMOVED***,
  promptClose: { color: "#E0E0E0", fontSize: 16, padding: 4 ***REMOVED***,
  promptScroll: { maxHeight: 100 ***REMOVED***,
  promptText: { color: "#B0B0B0", fontSize: 11, fontFamily: "monospace", lineHeight: 16 ***REMOVED***,
  copyBtn: { backgroundColor: "#0F3460", padding: 8, borderRadius: 6, alignItems: "center", marginTop: 8 ***REMOVED***,
  copyBtnText: { color: "#E0E0E0", fontSize: 12, fontWeight: "600" ***REMOVED***,
  ioBtn: { backgroundColor: "#0F3460", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 6, marginRight: 6, borderWidth: 1, borderColor: "#1A5276" ***REMOVED***,
  ioBtnText: { color: "#B0B0B0", fontSize: 11 ***REMOVED***,
***REMOVED***);
