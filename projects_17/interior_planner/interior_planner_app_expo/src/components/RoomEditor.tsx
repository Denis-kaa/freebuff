// src/components/RoomEditor.tsx — main screen orchestrator.
//
// Layers (top-down):
//   1. Header bar: project name + dimensions editor + save/export buttons
//   2. Canvas2D (gesture-enabled)
//   3. Bottom toolbar: category chips (Walls / Floor / Ceiling / Lighting / Furniture)
//   4. Properties sheet (modal, opens on object double-tap)

import React, { useState, useCallback ***REMOVED*** from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
***REMOVED*** from "react-native";
import * as Haptics from "expo-haptics";

import Canvas2D, { addObjectAtCenter ***REMOVED*** from "./Canvas2D";
import { useRoomStore, makeProject ***REMOVED*** from "../store/roomStore";
import knowledgeBaseJson from "../data/knowledge_base.json";
import type { KnowledgeBase, RoomType, FurnitureObject ***REMOVED*** from "../types/domain";

const KB: KnowledgeBase = knowledgeBaseJson as KnowledgeBase;
const ROOM_TYPES: RoomType[***REMOVED*** = [
  "kitchen",
  "living_room",
  "bedroom",
  "bathroom",
  "office",
  "dining",
***REMOVED***;
const FURNITURE_FILTER_TYPES = [
  "sofa",
  "table",
  "storage",
  "appliance",
***REMOVED*** as const;

type CategoryFilter = "Walls" | "Floor" | "Ceiling" | "Lighting" | "Furniture";

const CATEGORY_ORDER: CategoryFilter[***REMOVED*** = [
  "Walls",
  "Floor",
  "Ceiling",
  "Lighting",
  "Furniture",
***REMOVED***;

export default function RoomEditor(): React.ReactElement {
  const project = useRoomStore((s) => s.project);
  const setProject = useRoomStore((s) => s.setProject);
  const setRoom = useRoomStore((s) => s.setRoom);
  const setStyle = useRoomStore((s) => s.setStyle);
  const addObject = useRoomStore((s) => s.addObject);
  const deleteObject = useRoomStore((s) => s.deleteObject);
  const hasHydrated = useRoomStore((s) => s.hasHydrated);

  const [activeCategory, setActiveCategory***REMOVED*** =
    useState<CategoryFilter>("Furniture");
  const [activeFurnitureType, setActiveFurnitureType***REMOVED*** =
    useState<typeof FURNITURE_FILTER_TYPES[number***REMOVED*** | null>("table");

  // ─── Project bootstrap ───────────────────────────────────────────────

  const createNewProject = useCallback(() => {
    const room = {
      type: "living_room" as RoomType,
      dimensions_m: [5, 4***REMOVED*** as [number, number***REMOVED***,
      surfaces: {
        wall: "paint-white",
        floor: "laminate-oak",
        ceiling: "ceiling-white",
      ***REMOVED***,
    ***REMOVED***;
    setProject(makeProject("My Living Room", room, "scandi"));
  ***REMOVED***, [setProject***REMOVED***);

  // ─── Object add (from toolbar) ───────────────────────────────────────

  const handleAddItem = useCallback(
    (catalog_id: string) => {
      if (!project) {
        Alert.alert("No project", "Create a project first.");
        return;
      ***REMOVED***
      const [w, h***REMOVED*** = project.room.dimensions_m;
      const obj = addObjectAtCenter(catalog_id, w, h, project.objects.length);
      addObject(obj);
      void Haptics.selectionAsync().catch(() => { /* haptics optional */ ***REMOVED***);
    ***REMOVED***,
    [project, addObject***REMOVED***,
  );

  const handleDeleteObject = useCallback((id: string) => {
    Alert.alert("Delete?", "Remove this object from the room?", [
      { text: "Cancel", style: "cancel" ***REMOVED***,
      {
        text: "Delete",
        style: "destructive",
        onPress: () => {
          deleteObject(id);
          void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning)
            .catch(() => { ***REMOVED***);
        ***REMOVED***,
      ***REMOVED***,
    ***REMOVED***);
  ***REMOVED***, [deleteObject***REMOVED***);

  // ─── Render: hydration guard ─────────────────────────────────────────

  if (!hasHydrated) {
    return (
      <View style={styles.empty***REMOVED***>
        <Text style={styles.emptyTitle***REMOVED***>Loading project…</Text>
      </View>
    );
  ***REMOVED***

  if (!project) {
    return (
      <View style={styles.empty***REMOVED***>
        <Text style={styles.emptyTitle***REMOVED***>No project loaded.</Text>
        <TouchableOpacity style={styles.primaryButton***REMOVED*** onPress={createNewProject***REMOVED***>
          <Text style={styles.primaryButtonText***REMOVED***>+ New Project</Text>
        </TouchableOpacity>
      </View>
    );
  ***REMOVED***

  // ─── Render: category browser content ────────────────────────────────

  const renderCategoryItems = (): React.ReactElement => {
    switch (activeCategory) {
      case "Walls":
        return (
          <ScrollView horizontal style={styles.chipScroll***REMOVED*** showsHorizontalScrollIndicator={false***REMOVED***>
            {KB.materials.walls.map((m) => {
              const selected = project.room.surfaces.wall === m.id;
              return (
                <TouchableOpacity
                  key={m.id***REMOVED***
                  style={[styles.chip, selected && styles.chipSelected***REMOVED******REMOVED***
                  onPress={() =>
                    setRoom({ ...project.room, surfaces: { ...project.room.surfaces, wall: m.id ***REMOVED*** ***REMOVED***)
                  ***REMOVED***
                >
                  <Text style={[styles.chipText, selected && styles.chipTextSelected***REMOVED******REMOVED***>
                    {m.label***REMOVED***
                  </Text>
                </TouchableOpacity>
              );
            ***REMOVED***)***REMOVED***
          </ScrollView>
        );
      case "Floor":
        return (
          <ScrollView horizontal style={styles.chipScroll***REMOVED*** showsHorizontalScrollIndicator={false***REMOVED***>
            {KB.materials.floors.map((m) => {
              const selected = project.room.surfaces.floor === m.id;
              return (
                <TouchableOpacity
                  key={m.id***REMOVED***
                  style={[styles.chip, selected && styles.chipSelected***REMOVED******REMOVED***
                  onPress={() =>
                    setRoom({ ...project.room, surfaces: { ...project.room.surfaces, floor: m.id ***REMOVED*** ***REMOVED***)
                  ***REMOVED***
                >
                  <Text style={[styles.chipText, selected && styles.chipTextSelected***REMOVED******REMOVED***>
                    {m.label***REMOVED***
                  </Text>
                </TouchableOpacity>
              );
            ***REMOVED***)***REMOVED***
          </ScrollView>
        );
      case "Ceiling":
        return (
          <ScrollView horizontal style={styles.chipScroll***REMOVED*** showsHorizontalScrollIndicator={false***REMOVED***>
            {KB.materials.ceilings.map((m) => {
              const selected = project.room.surfaces.ceiling === m.id;
              return (
                <TouchableOpacity
                  key={m.id***REMOVED***
                  style={[styles.chip, selected && styles.chipSelected***REMOVED******REMOVED***
                  onPress={() =>
                    setRoom({ ...project.room, surfaces: { ...project.room.surfaces, ceiling: m.id ***REMOVED*** ***REMOVED***)
                  ***REMOVED***
                >
                  <Text style={[styles.chipText, selected && styles.chipTextSelected***REMOVED******REMOVED***>
                    {m.label***REMOVED***
                  </Text>
                </TouchableOpacity>
              );
            ***REMOVED***)***REMOVED***
          </ScrollView>
        );
      case "Lighting":
        return (
          <ScrollView horizontal style={styles.chipScroll***REMOVED*** showsHorizontalScrollIndicator={false***REMOVED***>
            {KB.lighting.map((l) => (
              <TouchableOpacity
                key={l.id***REMOVED***
                style={styles.chip***REMOVED***
                onPress={() => setStyle(l.id)***REMOVED***
              >
                <Text style={styles.chipText***REMOVED***>{l.label***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </ScrollView>
        );
      case "Furniture":
        return (
          <ScrollView style={styles.furnitureScroll***REMOVED*** showsVerticalScrollIndicator={false***REMOVED***>
            {FURNITURE_FILTER_TYPES.map((ftype) => (
              <View key={ftype***REMOVED*** style={styles.furnitureSection***REMOVED***>
                <Text style={styles.furnitureSectionLabel***REMOVED***>{ftype.toUpperCase()***REMOVED***</Text>
                <View style={styles.furnitureRow***REMOVED***>
                  {KB.furniture
                    .filter((f) => f.type === ftype)
                    .map((f) => (
                      <TouchableOpacity
                        key={f.id***REMOVED***
                        style={styles.furnitureCard***REMOVED***
                        onPress={() => handleAddItem(f.id)***REMOVED***
                      >
                        <Text style={styles.furnitureCardName***REMOVED***>{f.name***REMOVED***</Text>
                        <Text style={styles.furnitureCardDim***REMOVED***>
                          {f.size_m[0***REMOVED***.toFixed(2)***REMOVED***×{f.size_m[1***REMOVED***.toFixed(2)***REMOVED***m
                        </Text>
                      </TouchableOpacity>
                    ))***REMOVED***
                </View>
              </View>
            ))***REMOVED***
          </ScrollView>
        );
    ***REMOVED***
  ***REMOVED***;

  // ─── Render: main editor ─────────────────────────────────────────────

  return (
    <View style={styles.root***REMOVED***>
      {/* Header */***REMOVED***
      <View style={styles.header***REMOVED***>
        <Text style={styles.projectName***REMOVED***>{project.name***REMOVED***</Text>
        <Text style={styles.dimLabel***REMOVED***>
          {project.room.dimensions_m[0***REMOVED******REMOVED***×{project.room.dimensions_m[1***REMOVED******REMOVED***m ·{" "***REMOVED***
          {project.room.type***REMOVED***
        </Text>
      </View>

      {/* Canvas (gesture-enabled) */***REMOVED***
      <Canvas2D />

      {/* Category chips row */***REMOVED***
      <View style={styles.categoryRow***REMOVED***>
        {CATEGORY_ORDER.map((cat) => (
          <TouchableOpacity
            key={cat***REMOVED***
            style={[
              styles.categoryButton,
              activeCategory === cat && styles.categoryButtonActive,
            ***REMOVED******REMOVED***
            onPress={() => setActiveCategory(cat)***REMOVED***
          >
            <Text
              style={[
                styles.categoryText,
                activeCategory === cat && styles.categoryTextActive,
              ***REMOVED******REMOVED***
            >
              {cat***REMOVED***
            </Text>
          </TouchableOpacity>
        ))***REMOVED***
      </View>

      {/* Items panel for active category */***REMOVED***
      <View style={styles.itemsPanel***REMOVED***>{renderCategoryItems()***REMOVED***</View>

      {/* Objects list (delete shortcuts) */***REMOVED***
      <View style={styles.objectsFooter***REMOVED***>
        <Text style={styles.objectsFooterLabel***REMOVED***>
          {project.objects.length === 0
            ? "Tap a furniture card above to add"
            : `Objects: ${project.objects.length***REMOVED***`***REMOVED***
        </Text>
        {project.objects.length > 0 && (
          <ScrollView
            horizontal
            style={styles.objectsChipsRow***REMOVED***
            showsHorizontalScrollIndicator={false***REMOVED***
          >
            {project.objects.map((o) => (
              <TouchableOpacity
                key={o.id***REMOVED***
                style={styles.objectChip***REMOVED***
                onLongPress={() => handleDeleteObject(o.id)***REMOVED***
              >
                <Text style={styles.objectChipText***REMOVED***>{o.catalog_id***REMOVED***</Text>
              </TouchableOpacity>
            ))***REMOVED***
          </ScrollView>
        )***REMOVED***
      </View>
    </View>
  );
***REMOVED***

// ─── Styles ─────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#FFFFFF" ***REMOVED***,
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 ***REMOVED***,
  emptyTitle: { fontSize: 18, color: "#616161", marginBottom: 16 ***REMOVED***,
  primaryButton: {
    backgroundColor: "#1976D2",
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  ***REMOVED***,
  primaryButtonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "600" ***REMOVED***,
  header: { padding: 16, borderBottomWidth: 1, borderBottomColor: "#E0E0E0" ***REMOVED***,
  projectName: { fontSize: 18, fontWeight: "600", color: "#212121" ***REMOVED***,
  dimLabel: { fontSize: 13, color: "#757575", marginTop: 2 ***REMOVED***,
  categoryRow: {
    flexDirection: "row",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: "#E0E0E0",
    backgroundColor: "#FAFAFA",
  ***REMOVED***,
  categoryButton: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  ***REMOVED***,
  categoryButtonActive: { backgroundColor: "#1976D2" ***REMOVED***,
  categoryText: { fontSize: 13, color: "#424242" ***REMOVED***,
  categoryTextActive: { color: "#FFFFFF", fontWeight: "600" ***REMOVED***,
  itemsPanel: { height: 180, borderTopWidth: 1, borderTopColor: "#E0E0E0" ***REMOVED***,
  chipScroll: { padding: 8 ***REMOVED***,
  chip: {
    backgroundColor: "#F5F5F5",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    marginRight: 6,
    borderWidth: 1,
    borderColor: "#E0E0E0",
  ***REMOVED***,
  chipSelected: {
    backgroundColor: "#1976D2",
    borderColor: "#1565C0",
  ***REMOVED***,
  chipText: { fontSize: 12, color: "#424242" ***REMOVED***,
  chipTextSelected: { color: "#FFFFFF", fontWeight: "500" ***REMOVED***,
  furnitureScroll: { padding: 8 ***REMOVED***,
  furnitureSection: { marginBottom: 8 ***REMOVED***,
  furnitureSectionLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: "#9E9E9E",
    marginBottom: 4,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  ***REMOVED***,
  furnitureRow: { flexDirection: "row", flexWrap: "wrap" ***REMOVED***,
  furnitureCard: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 6,
    marginRight: 6,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: "#E0E0E0",
  ***REMOVED***,
  furnitureCardName: { fontSize: 12, color: "#212121" ***REMOVED***,
  furnitureCardDim: { fontSize: 10, color: "#9E9E9E", marginTop: 2 ***REMOVED***,
  objectsFooter: {
    padding: 8,
    borderTopWidth: 1,
    borderTopColor: "#E0E0E0",
    backgroundColor: "#FAFAFA",
  ***REMOVED***,
  objectsFooterLabel: { fontSize: 11, color: "#757575", marginBottom: 4 ***REMOVED***,
  objectsChipsRow: { paddingVertical: 4 ***REMOVED***,
  objectChip: {
    backgroundColor: "#FFEBEE",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
    marginRight: 4,
  ***REMOVED***,
  objectChipText: { fontSize: 11, color: "#C62828" ***REMOVED***,
***REMOVED***);
