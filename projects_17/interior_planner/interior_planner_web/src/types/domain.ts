// src/types/domain.ts — Project-local type definitions for interior_planner_app.
// NOT shared with Freebuff core (would belong to scenarios/blueprint_v3).
// Project-scoped types only — keep them narrow.

export type RoomType =
  | "kitchen"
  | "living_room"
  | "bedroom"
  | "bathroom"
  | "office"
  | "dining";

export interface RoomSurface {
  wall: string;       // FK to materials.walls[****REMOVED***.id
  floor: string;      // FK to materials.floors[****REMOVED***.id
  ceiling: string;    // FK to materials.ceilings[****REMOVED***.id
***REMOVED***

export interface Room {
  type: RoomType;
  dimensions_m: [number, number***REMOVED***;   // [width, height***REMOVED*** in metres, top-down origin = (0,0)
  surfaces: RoomSurface;
***REMOVED***

export interface FurnitureObject {
  id: string;                        // UUID generated client-side
  catalog_id: string;                // FK to knowledge_base.json:furniture[****REMOVED***.id
  position_m: [number, number***REMOVED***;      // [x, y***REMOVED*** from top-left of room, in metres
  size_m: [number, number***REMOVED***;          // real dimensions from knowledge_base (mirrored)
  rotation_deg: number;              // 0..359
  z_index: number;                  // render order
***REMOVED***

export interface FurnitureCatalogEntry {
  id: string;
  name: string;
  size_m: [number, number***REMOVED***;
  type: "sofa" | "table" | "storage" | "appliance";
***REMOVED***

export interface MaterialEntry {
  id: string;
  label: string;
  mood: string;
***REMOVED***

export interface StyleEntry {
  id: string;
  label: string;
  prefix: string;
***REMOVED***

export interface LightingEntry {
  id: string;
  label: string;
  modifier: string;
***REMOVED***

export interface KnowledgeBase {
  furniture: FurnitureCatalogEntry[***REMOVED***;
  materials: {
    walls: MaterialEntry[***REMOVED***;
    floors: MaterialEntry[***REMOVED***;
    ceilings: MaterialEntry[***REMOVED***;
  ***REMOVED***;
  lighting: LightingEntry[***REMOVED***;
  styles: StyleEntry[***REMOVED***;
***REMOVED***

export interface Project {
  id: string;
  name: string;
  created_at: string;                // ISO 8601
  updated_at: string;                // ISO 8601
  room: Room;
  objects: FurnitureObject[***REMOVED***;
  style_id: string;                  // FK to styles[****REMOVED***.id — last chosen for export
***REMOVED***
