/**
 * Feature: review-system (async review loop, concept Часть 1 §2).
 *
 * Implemented in Phase 4b (2026-09-06):
 *   - versioned submissions + state machine live in `app/store.ts`
 *     (submitVersion / startReview / addReviewNote / requestChanges / approveTask);
 *   - UI lives in `widgets/review-loop` (queue, version history, pinned zones).
 *
 * This feature layer stays the contract surface for future domain logic
 * (mentor assignment checks, notification hooks) — no shape redefinitions here.
 */
export {};
