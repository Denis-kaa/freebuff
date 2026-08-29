// src/components/Canvas2D.tsx — react-native-skia 2D renderer for room + furniture.
//
// Skia compiles to native Skia — 60 FPS at 50+ objects on iPhone 12+ (Sprint 2 benchmark).
// HTML5 Canvas is FORBIDDEN per promt47 ANTI-7b contract.
//
// Project-local component. Imports:
//   - @shopify/react-native-skia (compiled native Skia)
//   - react-native-gesture-handler (drag gesture)
//
// v2 fix (корректирует v5.48.0 reviewer blockers):
//   1. findNearestObject теперь работает на JS thread через runOnJS callback
//      (worklet не может вызывать Array.find / closures с component-scope vars)
//   2. <Text> rendering лабели удалён (useFont(null, ...) не работает — Skia
//      требует реальный font source; rect names уже видны в chips list ниже)
//
// Gesture pipeline:
//   1. canvas-drag  → JS callback → findNearestObject → moveObject (all on JS thread)
//   2. furniture-tap + long-press → handled in RoomEditor (delete via long-press chip)

import React, { useMemo, useCallback ***REMOVED*** from "react";
import { Canvas, Group, Rect ***REMOVED*** from "@shopify/react-native-skia";
import { StyleSheet, View, useWindowDimensions ***REMOVED*** from "react-native";
import {
  GestureDetector,
  Gesture,
***REMOVED*** from "react-native-gesture-handler";
import { runOnJS ***REMOVED*** from "react-native-reanimated";

import { useRoomStore ***REMOVED*** from "../store/roomStore";
import type { FurnitureObject, KnowledgeBase ***REMOVED*** from "../types/domain";
import knowledgeBaseJson from "../data/knowledge_base.json";

// ─── Constants ──────────────────────────────────────────────────────────
const KB: KnowledgeBase = knowledgeBaseJson as KnowledgeBase;
const CANVAS_PADDING_PX = 16;
const FURNITURE_FILL = "#A1887F";
const FURNITURE_STROKE = "#5D4037";
const ROOM_BORDER = "#37474F";
const GRID_LINE = "#E0E0E0";

// Hit-test radius in CANVAS px.
const HIT_RADIUS_PX = 28;

// ─── Helpers (pure-JS, called only from JS thread) ────────────────────

const m_to_px = (m: number, room_m: number, canvas_px: number): number =>
  ((m / room_m) * (canvas_px - CANVAS_PADDING_PX * 2)) + CANVAS_PADDING_PX;

const px_to_m = (
  px: number,
  room_m: number,
  canvas_px: number,
): number =>
  ((px - CANVAS_PADDING_PX) / (canvas_px - CANVAS_PADDING_PX * 2)) * room_m;

const findNearestObject = (
  objects: FurnitureObject[***REMOVED***,
  touch_x_px: number,
  touch_y_px: number,
  room_m_x: number,
  room_m_y: number,
  canvas_px_x: number,
  canvas_px_y: number,
): FurnitureObject | null => {
  let best: FurnitureObject | null = null;
  let best_dist = Infinity;
  for (const o of objects) {
    const cx = m_to_px(o.position_m[0***REMOVED*** + o.size_m[0***REMOVED*** / 2, room_m_x, canvas_px_x);
    const cy = m_to_px(o.position_m[1***REMOVED*** + o.size_m[1***REMOVED*** / 2, room_m_y, canvas_px_y);
    const d = Math.hypot(cx - touch_x_px, cy - touch_y_px);
    if (d < best_dist) {
      best_dist = d;
      best = o;
    ***REMOVED***
  ***REMOVED***
  return best_dist < HIT_RADIUS_PX ? best : null;
***REMOVED***;

// ─── Component ──────────────────────────────────────────────────────────

export default function Canvas2D(): React.ReactElement {
  const project = useRoomStore((s) => s.project);
  const moveObject = useRoomStore((s) => s.moveObject);

  const { width: screen_w ***REMOVED*** = useWindowDimensions();
  const canvas_px = Math.min(screen_w - 32, 720);

  // JS-thread handler (v2 fix: keep all geometry logic off worklet)
  const handleDragUpdate = useCallback(
    (touch_x_px: number, touch_y_px: number) => {
      if (!project) return;
      const [w_m, h_m***REMOVED*** = project.room.dimensions_m;
      const obj = findNearestObject(
        project.objects,
        touch_x_px,
        touch_y_px,
        w_m,
        h_m,
        canvas_px,
        canvas_px,
      );
      if (!obj) return;
      const new_x_m = px_to_m(
        touch_x_px - obj.size_m[0***REMOVED*** * (canvas_px / w_m) / 2,
        w_m,
        canvas_px,
      );
      const new_y_m = px_to_m(
        touch_y_px - obj.size_m[1***REMOVED*** * (canvas_px / h_m) / 2,
        h_m,
        canvas_px,
      );
      moveObject(obj.id, new_x_m, new_y_m);
    ***REMOVED***,
    [project, moveObject, canvas_px***REMOVED***,
  );

  // Pan gesture: событие из UI thread → runOnJS к handleDragUpdate (JS thread)
  const pan = Gesture.Pan()
    .onUpdate((e) => {
      "worklet";
      runOnJS(handleDragUpdate)(e.x, e.y);
    ***REMOVED***);

  // Convert object → screen rect (snap to top-down 2D; rotation rendering deferred to v2)
  const renderRects = useMemo(() => {
    if (!project) return [***REMOVED***;
    const [w_m, h_m***REMOVED*** = project.room.dimensions_m;
    return project.objects.map((o) => {
      const f = KB.furniture.find((e) => e.id === o.catalog_id);
      const [sx, sy***REMOVED*** = f?.size_m ?? o.size_m;
      const [px, py***REMOVED*** = o.position_m;
      return {
        id: o.id,
        x: m_to_px(px, w_m, canvas_px),
        y: m_to_px(py, h_m, canvas_px),
        w: m_to_px(sx, w_m, canvas_px),
        h: m_to_px(sy, h_m, canvas_px),
      ***REMOVED***;
    ***REMOVED***);
  ***REMOVED***, [project, canvas_px***REMOVED***);

  if (!project) {
    return (
      <View style={styles.emptyContainer***REMOVED***>
        <Canvas style={{ width: canvas_px, height: canvas_px ***REMOVED******REMOVED***>
          <Rect x={0***REMOVED*** y={0***REMOVED*** width={canvas_px***REMOVED*** height={canvas_px***REMOVED*** color="#FAFAFA" />
        </Canvas>
      </View>
    );
  ***REMOVED***

  const room_x = CANVAS_PADDING_PX;
  const room_y = CANVAS_PADDING_PX;
  const room_w = canvas_px - CANVAS_PADDING_PX * 2;
  const room_h = canvas_px - CANVAS_PADDING_PX * 2;

  return (
    <View style={styles.container***REMOVED***>
      <GestureDetector gesture={pan***REMOVED***>
        <Canvas style={{ width: canvas_px, height: canvas_px ***REMOVED******REMOVED***>
          {/* Grid background (10x10 cells) */***REMOVED***
          <Group>
            {Array.from({ length: 11 ***REMOVED***, (_, i) => (
              <Rect
                key={`gx${i***REMOVED***`***REMOVED***
                x={room_x + (room_w / 10) * i***REMOVED***
                y={room_y***REMOVED***
                width={1***REMOVED***
                height={room_h***REMOVED***
                color={GRID_LINE***REMOVED***
              />
            ))***REMOVED***
            {Array.from({ length: 11 ***REMOVED***, (_, i) => (
              <Rect
                key={`gy${i***REMOVED***`***REMOVED***
                x={room_x***REMOVED***
                y={room_y + (room_h / 10) * i***REMOVED***
                width={room_w***REMOVED***
                height={1***REMOVED***
                color={GRID_LINE***REMOVED***
              />
            ))***REMOVED***
          </Group>

          {/* Room boundary */***REMOVED***
          <Rect
            x={room_x***REMOVED***
            y={room_y***REMOVED***
            width={room_w***REMOVED***
            height={room_h***REMOVED***
            style="stroke"
            strokeWidth={2***REMOVED***
            color={ROOM_BORDER***REMOVED***
          />

          {/* Furniture (sorted by z_index — topmost furniture renders last) */***REMOVED***
          {[...renderRects***REMOVED***
            .sort((a, b) => {
              const za = project.objects.find((o) => o.id === a.id)?.z_index ?? 0;
              const zb = project.objects.find((o) => o.id === b.id)?.z_index ?? 0;
              return za - zb;
            ***REMOVED***)
            .map((r) => (
              <Group key={r.id***REMOVED***>
                <Rect
                  x={r.x***REMOVED***
                  y={r.y***REMOVED***
                  width={r.w***REMOVED***
                  height={r.h***REMOVED***
                  color={FURNITURE_FILL***REMOVED***
                />
                <Rect
                  x={r.x***REMOVED***
                  y={r.y***REMOVED***
                  width={r.w***REMOVED***
                  height={r.h***REMOVED***
                  style="stroke"
                  strokeWidth={1.5***REMOVED***
                  color={FURNITURE_STROKE***REMOVED***
                />
              </Group>
            ))***REMOVED***
        </Canvas>
      </GestureDetector>
    </View>
  );
***REMOVED***

// ─── Helpers re-exported for RoomEditor toolbar ──────────────────────────

export { m_to_px, px_to_m ***REMOVED***;

export const addObjectAtCenter = (
  catalog_id: string,
  room_w: number,
  room_h: number,
  existing_count: number,
): FurnitureObject => {
  const f = KB.furniture.find((e) => e.id === catalog_id);
  if (!f) throw new Error(`Unknown catalog_id: ${catalog_id***REMOVED***`);
  const [sx, sy***REMOVED*** = f.size_m;
  return {
    id: `${Date.now().toString(36)***REMOVED***-${Math.random().toString(36).slice(2, 8)***REMOVED***`,
    catalog_id,
    position_m: [
      Math.max(0, (room_w - sx) / 2),
      Math.max(0, (room_h - sy) / 2),
    ***REMOVED***,
    size_m: [sx, sy***REMOVED***,
    rotation_deg: 0,
    z_index: existing_count,
  ***REMOVED***;
***REMOVED***;

// ─── Styles ─────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  ***REMOVED***,
  emptyContainer: {
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  ***REMOVED***,
***REMOVED***);
