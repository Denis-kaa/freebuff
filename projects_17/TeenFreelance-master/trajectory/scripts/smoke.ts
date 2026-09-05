/**
 * Smoke test for Phase 2 data layer (runs under plain node --experimental-strip-types).
 * Validates generator invariants + selector logic without a browser.
 *
 * Usage: node --experimental-strip-types scripts/smoke.ts
 */
import { generateEcosystem, totalTurnover, computeEcosystemStats } from '../src/shared/mock/index.ts';
import {
  useTrajectoryStore,
  selectStats,
  selectCurrentUser,
  selectCandidates,
  selectTasksOfUser,
} from '../src/app/store.ts';

let failures = 0;
function check(name: string, cond: boolean): void {
  console.log(`${cond ? '✅' : '❌'} ${name}`);
  if (!cond) failures++;
}

/* ---------------- generator invariants ---------------- */

const eco = generateEcosystem(); // default seed — deterministic

check('200 freelancers generated', eco.freelancers.length === 200);
check('50 mentors generated', eco.mentors.length === 50);
check('100 clients generated', eco.clients.length === 100);
check('200 projects generated', eco.projects.length === 200);
check('tasks generated for team members', eco.tasks.length >= 200 && eco.tasks.length <= 600);

// ids unique *per prefix* (seq counter is shared, so 't-0001'/'f-0001' may coexist)
for (const [label, list] of [
  ['freelancers', eco.freelancers],
  ['mentors', eco.mentors],
  ['clients', eco.clients],
  ['projects', eco.projects],
  ['tasks', eco.tasks],
] as const) {
  const ids = new Set(list.map((x) => x.id));
  check(`${label}: ids unique within collection`, ids.size === list.length);
}

check(
  'freelancer ages in 14..18',
  eco.freelancers.every((f) => f.age >= 14 && f.age <= 18),
);
check(
  'every non-draft project has a mentor',
  eco.projects.every((p) => (p.status === 'draft' ? true : p.mentorId !== null)),
);
check(
  'project budgets positive',
  eco.projects.every((p) => p.budget > 0),
);

const t = totalTurnover(eco);
console.log(`   turnover: ₽${t.toLocaleString('ru-RU')}`);
check('turnover in plausible mock range (3–8M ₽)', t >= 3_000_000 && t <= 8_000_000);

const stats = computeEcosystemStats(eco);
check('stats: teens 51% share consistent', stats.teensEarnedRub === Math.round(t * 0.51));
check('stats: topMentors max 5', stats.topMentors.length <= 5);
check('stats: skillCounts sorted desc', stats.skillCounts.every((s, i, a) => i === 0 || (a[i - 1]?.count ?? 0) >= s.count));

/* ---------------- determinism ---------------- */

const eco2 = generateEcosystem();
check(
  'deterministic: same seed ⇒ identical first freelancer',
  JSON.stringify(eco.freelancers[0]) === JSON.stringify(eco2.freelancers[0]),
);

/* ---------------- store selectors ---------------- */

const store = useTrajectoryStore;
store.getState().init();
const state = store.getState();
check('store status ready after init', state.status === 'ready');
check('store eco generated', state.eco !== null && state.eco.freelancers.length === 200);
check('default user is f-0001', state.currentUserId === 'f-0001');

const user = selectCurrentUser(state.eco, state.currentUserId);
check('current user resolves', user !== null);
console.log(`   current user: ${user?.name} (${user?.role})`);

const statsSel = selectStats(state.eco);
check('selectStats returns counts 200/50/100/200', statsSel?.counts.freelancers === 200 && statsSel?.counts.mentors === 50);

const candidates = selectCandidates(state.eco, ['Figma', 'Copywriting'], 50);
console.log(`   candidates Figma+Copywriting >=50: ${candidates.length}`);
check('selectCandidates returns ranked list', candidates.length > 0);
check(
  'candidates all have both skills >= threshold',
  candidates.every((f) => (f.skills['Figma'] ?? 0) >= 50 && (f.skills['Copywriting'] ?? 0) >= 50),
);

// pick the first freelancer who actually has tasks in the generated graph
const busy = eco.freelancers.find((f) => eco.tasks.some((t) => t.freelancerId === f.id));
check('at least one freelancer has tasks', busy !== undefined);
if (busy) {
  const tasks = selectTasksOfUser(state.eco, busy.id);
  check('selectTasksOfUser attaches project titles', tasks.length > 0 && tasks[0]?.projectTitle !== '');
  console.log(`   ${busy.name}: ${tasks.length} tasks, first → «${tasks[0]?.projectTitle}»`);
}

console.log(failures === 0 ? '\n🔥 SMOKE PASSED — all checks green' : `\n💥 SMOKE FAILED — ${failures} failing`);
process.exit(failures === 0 ? 0 : 1);
