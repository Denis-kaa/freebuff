/**
 * Deterministic PRNG + helpers for the mock ecosystem generator.
 * Seeded mulberry32 — same seed ⇒ same ecosystem (reproducible tests/demos).
 */

/** Mulberry32 — small, fast, seedable PRNG returning floats in [0, 1). */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Rng {
  /** float in [min, max) */
  next(min: number, max: number): number;
  /** integer in [min, max] inclusive */
  int(min: number, max: number): number;
  /** random element (throws on empty) */
  pick<T>(arr: readonly T[]): T;
  /** n distinct elements (or fewer if arr is smaller) */
  sample<T>(arr: readonly T[], n: number): T[];
  /** true with probability p (0..1) */
  chance(p: number): boolean;
  /** integer in [min, max] shaped by a bell curve (sum of 3 uniforms) */
  bell(min: number, max: number): number;
  /** lowercase hex string of the given length (deterministic, seeded) */
  hex(len: number): string;
}

export function createRng(seed: number): Rng {
  const rand = mulberry32(seed);
  const HEX = '0123456789abcdef';
  const rng: Rng = {
    next: (min, max) => min + rand() * (max - min),
    int: (min, max) => Math.floor(min + rand() * (max - min + 1)),
    hex: (len) => {
      let out = '';
      for (let i = 0; i < len; i++) out += HEX[Math.floor(rand() * 16)];
      return out;
    },
    pick<T>(arr: readonly T[]): T {
      if (arr.length === 0) throw new Error('rng.pick: empty array');
      return arr[Math.floor(rand() * arr.length)] as T;
    },
    sample<T>(arr: readonly T[], n: number): T[] {
      const pool = [...arr];
      const out: T[] = [];
      const take = Math.min(n, pool.length);
      for (let i = 0; i < take; i++) {
        out.push(pool.splice(Math.floor(rand() * pool.length), 1)[0] as T);
      }
      return out;
    },
    chance: (p) => rand() < p,
    bell: (min, max) => {
      const avg = (rand() + rand() + rand()) / 3;
      return Math.round(min + avg * (max - min));
    },
  };
  return rng;
}
