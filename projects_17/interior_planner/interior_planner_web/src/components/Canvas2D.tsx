// Canvas2D.tsx — HTML5 Canvas рендерер с drag & drop поддержкой.
// Текстуры материалов (кирпич, дерево, плитка) через Canvas patterns.

import React, { useRef, useEffect, useCallback, useState ***REMOVED*** from "react";
import { View, StyleSheet ***REMOVED*** from "react-native";
import { useRoomStore ***REMOVED*** from "../store/roomStore";
import type { FurnitureObject, KnowledgeBase ***REMOVED*** from "../types/domain";
import knowledgeBaseJson from "../data/knowledge_base_ru.json";

const KB: KnowledgeBase = knowledgeBaseJson as KnowledgeBase;
const PAD = 16;
const FURNITURE_STROKE = "#5D4037";
const ROOM_BORDER = "#37474F";
const GRID_LINE = "rgba(255,255,255,0.08)";
const HIT_RADIUS = 28;

const m2px = (m: number, rm: number, cp: number): number => ((m / rm) * (cp - PAD * 2)) + PAD;
const px2m = (px: number, rm: number, cp: number): number => ((px - PAD) / (cp - PAD * 2)) * rm;

// ─── Загрузка текстур из Picsum Photos ──────────────────────────────
const materialImageUrl = (id: string): string =>
  `https://picsum.photos/seed/interior-${encodeURIComponent(id)***REMOVED***/300/300`;

const loadedImageCache = new Map<string, HTMLImageElement>();
const imagePatternCache = new Map<string, CanvasPattern>();

function loadImageTexture(materialId: string): Promise<HTMLImageElement> {
  if (loadedImageCache.has(materialId)) return Promise.resolve(loadedImageCache.get(materialId)!);
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => { loadedImageCache.set(materialId, img); resolve(img); ***REMOVED***;
    img.onerror = () => reject(new Error(`Failed to load: ${materialId***REMOVED***`));
    img.src = materialImageUrl(materialId);
  ***REMOVED***);
***REMOVED***

function getImagePattern(materialId: string): CanvasPattern | null {
  const img = loadedImageCache.get(materialId);
  if (!img) return null;
  const cacheKey = `pat-${materialId***REMOVED***`;
  if (imagePatternCache.has(cacheKey)) return imagePatternCache.get(cacheKey)!;
  const c = document.createElement("canvas");
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  const ctx = c.getContext("2d")!;
  ctx.drawImage(img, 0, 0);
  const pat = ctx.createPattern(c, "repeat")!;
  imagePatternCache.set(cacheKey, pat);
  return pat;
***REMOVED***

// ─── Текстуры материалов (генерируются на лету) ──────────────────────

const textureCache = new Map<string, CanvasPattern>();

function makeBrickPattern(size: number, color: string, mortar: string): CanvasPattern {
  const key = `brick-${color***REMOVED***-${mortar***REMOVED***`;
  if (textureCache.has(key)) return textureCache.get(key)!;
  const c = document.createElement("canvas");
  c.width = size * 3; c.height = size * 2;
  const ctx = c.getContext("2d")!;
  // Фон раствора
  ctx.fillStyle = mortar; ctx.fillRect(0, 0, c.width, c.height);
  // Кирпичи
  ctx.fillStyle = color;
  ctx.fillRect(1, 1, size - 2, size / 3 - 2);
  ctx.fillRect(size + 1 + size / 2, 1, size - 2, size / 3 - 2);
  ctx.fillRect(size / 4, size / 2 + 1, size - 2, size / 3 - 2);
  ctx.fillRect(size + 1, size / 2 + 1, size - 2, size / 3 - 2);
  ctx.fillRect(size / 4 + size + size / 4, size / 2 + 1, size - 2, size / 3 - 2);
  ctx.fillRect(1, size + 1, size - 2, size / 3 - 2);
  ctx.fillRect(size + 1 + size / 2, size + 1, size - 2, size / 3 - 2);
  ctx.fillRect(size / 4, size + size / 2 + 1, size - 2, size / 3 - 2);
  ctx.fillRect(size + 1, size + size / 2 + 1, size - 2, size / 3 - 2);
  const pat = ctx.createPattern(c, "repeat")!;
  textureCache.set(key, pat);
  return pat;
***REMOVED***

function makeWoodPattern(color: string): CanvasPattern {
  const key = `wood-${color***REMOVED***`;
  if (textureCache.has(key)) return textureCache.get(key)!;
  const c = document.createElement("canvas");
  c.width = 120; c.height = 120;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = color; ctx.fillRect(0, 0, 120, 120);
  // Линии дерева
  ctx.strokeStyle = "rgba(0,0,0,0.08)";
  for (let i = 0; i < 12; i++) {
    ctx.lineWidth = 1 + Math.random();
    ctx.beginPath();
    const y = i * 10 + Math.random() * 3;
    ctx.moveTo(0, y);
    ctx.lineTo(120, y + Math.random() * 6 - 3);
    ctx.stroke();
  ***REMOVED***
  // Сучки
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = "rgba(0,0,0,0.06)";
    ctx.beginPath();
    ctx.ellipse(10 + i * 50 + Math.random() * 20, 40 + Math.random() * 40, 4, 8, Math.random() * 2, 0, Math.PI * 2);
    ctx.fill();
  ***REMOVED***
  const pat = ctx.createPattern(c, "repeat")!;
  textureCache.set(key, pat);
  return pat;
***REMOVED***

function makeTilePattern(size: number, color: string): CanvasPattern {
  const key = `tile-${color***REMOVED***-${size***REMOVED***`;
  if (textureCache.has(key)) return textureCache.get(key)!;
  const c = document.createElement("canvas");
  c.width = size; c.height = size;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = color; ctx.fillRect(0, 0, size, size);
  ctx.strokeStyle = "rgba(255,255,255,0.3)";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, size - 1, size - 1);
  const pat = ctx.createPattern(c, "repeat")!;
  textureCache.set(key, pat);
  return pat;
***REMOVED***

const TEXTURE_MAP: Record<string, (color: string) => CanvasPattern> = {
  "wallpaper-brick": (c) => makeBrickPattern(40, c, "#D7CCC8"),
  "wood-panel-oak": (c) => makeWoodPattern(c),
  "laminate-oak": (c) => makeWoodPattern(c),
  "parquet-herringbone": (c) => makeWoodPattern(c),
  "tile-white": (c) => makeTilePattern(30, c),
***REMOVED***;

interface Props {
  dropItem?: string | null;
  onDrop?: (catalogId: string, x_m: number, y_m: number) => void;
  selectedObj?: string | null;
  onSelect?: (id: string | null) => void;
  isMobile?: boolean;
***REMOVED***

export default function Canvas2D({ dropItem, onDrop, selectedObj, onSelect, isMobile ***REMOVED***: Props): React.ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const project = useRoomStore((s) => s.project);
  const rotateObject = useRoomStore((s) => s.rotateObject);
  const moveObject = useRoomStore((s) => s.moveObject);
  const [cp, setCp***REMOVED*** = useState(400); // fallback until measured
  const zoomRef = useRef(1);
  const [texLoaded, setTexLoaded***REMOVED*** = useState(0);

  // Измеряем реальную ширину контейнера (mobile-first: без хардкода 340px)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      setCp(Math.max(280, Math.min(w - 24, 700)));
    ***REMOVED***;
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  ***REMOVED***, [***REMOVED***);

  // Предзагрузка текстур материалов + мебели при смене проекта
  useEffect(() => {
    if (!project) return;
    const ids = [
      project.room.surfaces.wall, project.room.surfaces.floor, project.room.surfaces.ceiling,
      ...project.objects.map((o) => o.catalog_id),
    ***REMOVED***;
    ids.forEach((id) => {
      if (loadedImageCache.has(id)) return;
      loadImageTexture(id).then(() => setTexLoaded((n) => n + 1)).catch(() => {***REMOVED***);
    ***REMOVED***);
  ***REMOVED***, [
    project?.room.surfaces.wall, project?.room.surfaces.floor, project?.room.surfaces.ceiling,
    project?.objects.map((o) => o.catalog_id).join(","),
  ***REMOVED***);

  // Вспомогательная: стиль заливки (текстура или цвет)
  const getFill = useCallback((materialId: string, fallbackColor: string): string | CanvasPattern => {
    const pat = getImagePattern(materialId);
    if (pat) return pat;
    const texFn = TEXTURE_MAP[materialId***REMOVED***;
    if (texFn) return texFn(fallbackColor);
    return fallbackColor;
  ***REMOVED***, [***REMOVED***);

  const render = useCallback(() => {
    const c = canvasRef.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const zoom = zoomRef.current;
    c.width = cp * dpr; c.height = cp * dpr;
    c.style.width = `${cp***REMOVED***px`; c.style.height = `${cp***REMOVED***px`;
    ctx.setTransform(dpr * zoom, 0, 0, dpr * zoom, (cp - cp * zoom) / 2 * dpr, (cp - cp * zoom) / 2 * dpr);

    if (!project) {
      ctx.fillStyle = "#1A1A2E"; ctx.fillRect(0, 0, cp, cp);
      ctx.fillStyle = "#B0B0B0"; ctx.font = "14px sans-serif"; ctx.textAlign = "center";
      ctx.fillText("Создайте проект в сайдбаре", cp / 2, cp / 2);
      return;
    ***REMOVED***

    const rx = PAD, ry = PAD, rw = cp - PAD * 2, rh = cp - PAD * 2;
    const wallId = project.room.surfaces.wall;
    const floorId = project.room.surfaces.floor;
    const wallColor = KB.materials.walls.find((m) => m.id === wallId)?.color || "#FEFEFE";
    const floorColor = KB.materials.floors.find((m) => m.id === floorId)?.color || "#D4A574";

    // Пол — текстура (Picsum > procedural > цвет)
    ctx.fillStyle = getFill(floorId, floorColor);
    ctx.fillRect(rx, ry + rh * 0.55, rw, rh * 0.45);

    // Стены — текстура (Picsum > procedural > цвет)
    ctx.fillStyle = getFill(wallId, wallColor);
    ctx.fillRect(rx, ry, rw, rh * 0.55);

    // Сетка
    ctx.strokeStyle = GRID_LINE; ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const px = rx + (rw / 10) * i; ctx.beginPath(); ctx.moveTo(px, ry); ctx.lineTo(px, ry + rh); ctx.stroke();
      const py = ry + (rh / 10) * i; ctx.beginPath(); ctx.moveTo(rx, py); ctx.lineTo(rx + rw, py); ctx.stroke();
    ***REMOVED***

    ctx.strokeStyle = ROOM_BORDER; ctx.lineWidth = 2; ctx.strokeRect(rx, ry, rw, rh);

    const [wm, hm***REMOVED*** = project.room.dimensions_m;
    ctx.fillStyle = "#B0B0B0"; ctx.font = "bold 11px sans-serif"; ctx.textAlign = "center";
    ctx.fillText(`${wm***REMOVED***×${hm***REMOVED***м`, rx + rw / 2, ry - 6);

    // Мебель
    const sorted = [...project.objects***REMOVED***.sort((a, b) => a.z_index - b.z_index);
    for (const o of sorted) {
      const f = KB.furniture.find((e) => e.id === o.catalog_id);
      const [sx, sy***REMOVED*** = f?.size_m ?? o.size_m;
      const fx = m2px(o.position_m[0***REMOVED***, wm, cp), fy = m2px(o.position_m[1***REMOVED***, hm, cp);
      const fw = m2px(sx, wm, cp), fh = m2px(sy, hm, cp);
      const color = f?.color || "#A1887F";

      // Поворот мебели
      const cx = fx + fw / 2, cy = fy + fh / 2;
      ctx.save();
      if (o.rotation_deg) {
        ctx.translate(cx, cy);
        ctx.rotate((o.rotation_deg * Math.PI) / 180);
        ctx.translate(-cx, -cy);
      ***REMOVED***
      // Тень
      ctx.fillStyle = "rgba(0,0,0,0.15)";
      ctx.fillRect(fx + 2, fy + 2, fw, fh);
      // Тело — текстура из Picsum (если загружена), иначе цвет
      const furnPat = getImagePattern(o.catalog_id);
      ctx.fillStyle = furnPat || color;
      ctx.fillRect(fx, fy, fw, fh);
      ctx.strokeStyle = o.id === selectedObj ? "#42A5F5" : FURNITURE_STROKE;
      ctx.lineWidth = o.id === selectedObj ? 2.5 : 1.5;
      ctx.strokeRect(fx, fy, fw, fh);

      // Подпись
      if (fw > 40 && fh > 20) {
        const label = f?.name || o.catalog_id;
        const short = label.length > 14 ? label.slice(0, 12) + "…" : label;
        ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.font = "bold 9px sans-serif"; ctx.textAlign = "center";
        ctx.fillText(short, fx + fw / 2 + 1, fy + fh / 2 + 4);
        ctx.fillStyle = "#FFFFFF";
        ctx.fillText(short, fx + fw / 2, fy + fh / 2 + 3);
      ***REMOVED***
      ctx.restore();
    ***REMOVED***

    // Drop-индикатор
    if (dropItem && project) {
      const f = KB.furniture.find((e) => e.id === dropItem);
      if (f) {
        const [sx***REMOVED*** = f.size_m;
        const dfw = m2px(sx, wm, cp), dfh = m2px(f.size_m[1***REMOVED***, hm, cp);
        ctx.fillStyle = "rgba(66,165,245,0.25)"; ctx.strokeStyle = "#42A5F5"; ctx.lineWidth = 2;
        ctx.setLineDash([4, 4***REMOVED***);
        ctx.fillRect(cp / 2 - dfw / 2, cp / 2 - dfh / 2, dfw, dfh);
        ctx.strokeRect(cp / 2 - dfw / 2, cp / 2 - dfh / 2, dfw, dfh);
        ctx.setLineDash([***REMOVED***);
        ctx.fillStyle = "#42A5F5"; ctx.font = "bold 11px sans-serif"; ctx.textAlign = "center";
        ctx.fillText("Отпустите для размещения", cp / 2, cp / 2 - dfh / 2 - 12);
      ***REMOVED***
    ***REMOVED***
  ***REMOVED***, [project, cp, selectedObj, dropItem, getFill, texLoaded***REMOVED***);

  useEffect(() => { render(); ***REMOVED***, [render***REMOVED***);

  const dragging = useRef(false);
  const getXY = useCallback((e: React.MouseEvent) => {
    const c = canvasRef.current; if (!c) return { x: 0, y: 0 ***REMOVED***;
    const r = c.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top ***REMOVED***;
  ***REMOVED***, [***REMOVED***);

  // ─── Touch-жесты (mobile-first) ────────────────────────────────────
  const touchPoints = useRef<Map<number, { x: number; y: number ***REMOVED***>>(new Map());
  const pinchDistRef = useRef(0);
  const touchStartTimeRef = useRef(0);
  const lastTapTimeRef = useRef(0);
  const touchMovedRef = useRef(false); // true если палец двигался (drag/pinch) — не тап

  const hitTest = useCallback((x: number, y: number): FurnitureObject | null => {
    if (!project) return null;
    const [wm, hm***REMOVED*** = project.room.dimensions_m;
    let hit: FurnitureObject | null = null; let best = Infinity;
    for (const o of project.objects) {
      const cx = m2px(o.position_m[0***REMOVED*** + o.size_m[0***REMOVED*** / 2, wm, cp), cy = m2px(o.position_m[1***REMOVED*** + o.size_m[1***REMOVED*** / 2, hm, cp);
      const d = Math.hypot(cx - x, cy - y);
      if (d < HIT_RADIUS && d < best) { best = d; hit = o; ***REMOVED***
    ***REMOVED***
    return hit;
  ***REMOVED***, [project, cp***REMOVED***);

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    if (!project) return;
    touchPoints.current.clear();
    pinchDistRef.current = 0;
    touchMovedRef.current = false;
    touchStartTimeRef.current = Date.now();
    for (let i = 0; i < e.touches.length; i++) {
      const t = e.touches[i***REMOVED***;
      touchPoints.current.set(t.identifier, { x: t.clientX, y: t.clientY ***REMOVED***);
    ***REMOVED***
    if (e.touches.length === 2) {
      const [a, b***REMOVED*** = [...touchPoints.current.values()***REMOVED***;
      pinchDistRef.current = Math.hypot(a.x - b.x, a.y - b.y);
    ***REMOVED*** else if (e.touches.length === 1) {
      // Один палец: hit-test → select + drag
      const c = canvasRef.current; if (!c) return;
      const r = c.getBoundingClientRect();
      const t = e.touches[0***REMOVED***;
      const hit = hitTest(t.clientX - r.left, t.clientY - r.top);
      if (hit) { dragging.current = true; onSelect?.(hit.id); ***REMOVED***
    ***REMOVED***
  ***REMOVED***, [project, cp, onSelect, hitTest***REMOVED***);

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    if (!project) return;
    for (let i = 0; i < e.touches.length; i++) {
      const t = e.touches[i***REMOVED***;
      touchPoints.current.set(t.identifier, { x: t.clientX, y: t.clientY ***REMOVED***);
    ***REMOVED***
    const pts = [...touchPoints.current.values()***REMOVED***;
    if (pts.length >= 2) {
      touchMovedRef.current = true;
      // Pinch-to-zoom
      const dist = Math.hypot(pts[0***REMOVED***.x - pts[1***REMOVED***.x, pts[0***REMOVED***.y - pts[1***REMOVED***.y);
      if (pinchDistRef.current > 0) {
        const ratio = dist / pinchDistRef.current;
        zoomRef.current = Math.max(0.3, Math.min(3, zoomRef.current * ratio));
        render();
      ***REMOVED***
      pinchDistRef.current = dist;
    ***REMOVED*** else if (pts.length === 1 && dragging.current) {
      // Pan выделенного объекта
      touchMovedRef.current = true;
      const c = canvasRef.current; if (!c) return;
      const r = c.getBoundingClientRect();
      const x = pts[0***REMOVED***.x - r.left, y = pts[0***REMOVED***.y - r.top;
      const [wm, hm***REMOVED*** = project.room.dimensions_m;
      const sel = project.objects.find((o) => o.id === selectedObj);
      if (!sel) return;
      moveObject(sel.id, Math.max(0, px2m(x - (m2px(sel.size_m[0***REMOVED***, wm, cp)) / 2, wm, cp)), Math.max(0, px2m(y - (m2px(sel.size_m[1***REMOVED***, hm, cp)) / 2, hm, cp)));
    ***REMOVED***
  ***REMOVED***, [project, cp, selectedObj, moveObject, render***REMOVED***);

  const onTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault();
    dragging.current = false;
    pinchDistRef.current = 0;
    for (let i = 0; i < e.changedTouches.length; i++) {
      touchPoints.current.delete(e.changedTouches[i***REMOVED***.identifier);
    ***REMOVED***
    if (touchPoints.current.size > 0) return;
    // Было движение (drag/pinch) — это не тап
    if (touchMovedRef.current) { touchMovedRef.current = false; return; ***REMOVED***
    // Тап (короткий, без движения) → select; двойной тап → поворот
    const now = Date.now();
    if (now - touchStartTimeRef.current > 400) return;
    const c = canvasRef.current; if (!c) return;
    const r = c.getBoundingClientRect();
    const t = e.changedTouches[0***REMOVED***;
    if (!t) return;
    const hit = hitTest(t.clientX - r.left, t.clientY - r.top);
    if (hit) {
      if (now - lastTapTimeRef.current < 500) {
        // Двойной тап = поворот на 45°
        const newRot = ((hit.rotation_deg || 0) + 45) % 360;
        rotateObject(hit.id, newRot);
        lastTapTimeRef.current = 0;
      ***REMOVED*** else {
        lastTapTimeRef.current = now;
        onSelect?.(hit.id);
      ***REMOVED***
    ***REMOVED*** else {
      onSelect?.(null);
    ***REMOVED***
  ***REMOVED***, [project, cp, onSelect, hitTest, rotateObject***REMOVED***);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (!project) return;
    const { x, y ***REMOVED*** = getXY(e);
    const hit = hitTest(x, y);
    // Shift+клик = поворот на 45°
    if (hit && (e as any).shiftKey) {
      const newRot = ((hit.rotation_deg || 0) + 45) % 360;
      rotateObject(hit.id, newRot);
      onSelect?.(hit.id);
      return;
    ***REMOVED***
    if (hit) { dragging.current = true; onSelect?.(hit.id); ***REMOVED*** else { onSelect?.(null); ***REMOVED***
  ***REMOVED***, [project, cp, getXY, onSelect, rotateObject, hitTest***REMOVED***);

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current || !project) return;
    const { x, y ***REMOVED*** = getXY(e);
    const [wm, hm***REMOVED*** = project.room.dimensions_m;
    const sel = project.objects.find((o) => o.id === selectedObj);
    if (!sel) return;
    moveObject(sel.id, Math.max(0, px2m(x - (m2px(sel.size_m[0***REMOVED***, wm, cp)) / 2, wm, cp)), Math.max(0, px2m(y - (m2px(sel.size_m[1***REMOVED***, hm, cp)) / 2, hm, cp)));
  ***REMOVED***, [project, cp, selectedObj, moveObject, getXY***REMOVED***);

  const onMouseUp = useCallback(() => { dragging.current = false; ***REMOVED***, [***REMOVED***);

  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); ***REMOVED***, [***REMOVED***);
  const onCanvasDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!dropItem || !project || !onDrop) return;
    const c = canvasRef.current; if (!c) return;
    const r = c.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    const [wm, hm***REMOVED*** = project.room.dimensions_m;
    const f = KB.furniture.find((fe) => fe.id === dropItem);
    const [sx***REMOVED*** = f?.size_m || [0.6***REMOVED***;
    onDrop(dropItem, Math.max(0, px2m(x - (m2px(sx, wm, cp)) / 2, wm, cp)), Math.max(0, px2m(y - 1, hm, cp)));
  ***REMOVED***, [dropItem, project, onDrop, cp***REMOVED***);

  // ─── Zoom (колесо мыши) ──────────────────────────────────────────
  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    zoomRef.current = Math.max(0.3, Math.min(3, zoomRef.current + delta));
    render();
  ***REMOVED***, [render***REMOVED***);

  return (
    <View ref={containerRef as any***REMOVED*** style={ss.container***REMOVED***>
      <canvas
        ref={canvasRef***REMOVED***
        style={{ ...ss.canvas, cursor: dragging.current ? "grabbing" : (dropItem ? "copy" : "grab"), touchAction: "none" ***REMOVED*** as any***REMOVED***
        onMouseDown={onMouseDown***REMOVED***
        onMouseMove={onMouseMove***REMOVED***
        onMouseUp={onMouseUp***REMOVED***
        onMouseLeave={onMouseUp***REMOVED***
        onWheel={onWheel as any***REMOVED***
        onTouchStart={onTouchStart***REMOVED***
        onTouchMove={onTouchMove***REMOVED***
        onTouchEnd={onTouchEnd***REMOVED***
        onTouchCancel={onTouchEnd***REMOVED***
        onDragOver={onDragOver***REMOVED***
        onDrop={onCanvasDrop***REMOVED***
      />
    </View>
  );
***REMOVED***

export { m2px as m_to_px, px2m as px_to_m ***REMOVED***;

export const addObjectAtCenter = (catalog_id: string, rw: number, rh: number, cnt: number): FurnitureObject => {
  const f = KB.furniture.find((e) => e.id === catalog_id);
  if (!f) throw new Error(`Unknown: ${catalog_id***REMOVED***`);
  return {
    id: `${Date.now().toString(36)***REMOVED***-${Math.random().toString(36).slice(2, 8)***REMOVED***`,
    catalog_id, position_m: [Math.max(0, (rw - f.size_m[0***REMOVED***) / 2), Math.max(0, (rh - f.size_m[1***REMOVED***) / 2)***REMOVED***,
    size_m: f.size_m, rotation_deg: 0, z_index: cnt,
  ***REMOVED***;
***REMOVED***;

const ss = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: 8 ***REMOVED***,
  canvas: { borderRadius: 6, boxShadow: "0 0 20px rgba(0,0,0,0.4)" ***REMOVED*** as any,
***REMOVED***);
