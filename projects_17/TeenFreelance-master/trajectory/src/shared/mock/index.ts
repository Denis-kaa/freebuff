/**
 * Shared: mock — deterministic mock-data layer (Phase 2).
 * Exposes generator + stats + imagePrompts registry.
 */
export { generateEcosystem, totalTurnover, ECONOMY_SPLIT, type Ecosystem } from './generator.ts';
export { computeEcosystemStats, type EcosystemStats } from './ecoStats.ts';
export { createRng, type Rng } from './rng.ts';
export { imagePrompts, getImagePrompt } from './imagePrompts.ts';
