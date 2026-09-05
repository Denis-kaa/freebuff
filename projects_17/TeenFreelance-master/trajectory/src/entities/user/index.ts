/**
 * Entity: user — Freelancer / Mentor / Client / Parent + consent.
 * Canonical shapes live in src/types (single source of truth) —
 * this barrel is the FSD import surface for upper layers.
 */
export type {
  User,
  UserRole,
  Freelancer,
  Mentor,
  MentorLevel,
  Client,
  TalentPoolSnapshot,
  Parent,
  Proof,
  ProofType,
  ParentalConsent,
  ISODate,
  ActivityEntry,
} from '../../types';
