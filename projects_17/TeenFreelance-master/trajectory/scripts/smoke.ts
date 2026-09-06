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

/* ---------------- draft (TeamBuilder, Этап 3.2) ---------------- */

import { MENTOR_TEAM_LIMIT, selectMentorCapacity } from '../src/app/store.ts';

const d = store.getState();
check('draft starts empty', d.draft.requiredSkills.length === 0 && d.draft.invitedIds.length === 0);

// 1) skill filter + scoring
const draftEco = d.eco!;
d.toggleSkill('Figma');
d.toggleSkill('Copywriting');
d.toggleSkill('Figma'); // toggle off → back to 1 skill
const afterToggle = store.getState().draft;
check('toggleSkill adds and removes', afterToggle.requiredSkills.length === 1 && afterToggle.requiredSkills[0] === 'Copywriting');
check('results recomputed on filter change', afterToggle.results.length > 0);
check(
  'results: every candidate holds all required skills >= minLevel',
  afterToggle.results.every((r) =>
    afterToggle.requiredSkills.every((s) => (r.freelancer.skills[s] ?? 0) >= afterToggle.minLevel),
  ),
);
check(
  'results sorted by avg desc',
  afterToggle.results.every((r, i, a) => i === 0 || (a[i - 1]?.avg ?? 0) >= r.avg),
);

// 2) mentor gate
const seniorMentor = draftEco.mentors.find((m) => m.level === 'Senior') ?? draftEco.mentors[0]!;
store.getState().pickMentor(seniorMentor.id);
const capped = store.getState().draft;
const capSenior = MENTOR_TEAM_LIMIT[seniorMentor.level];
check('pickMentor sets mentorId', capped.mentorId === seniorMentor.id);
check('invites clipped to mentor cap', capped.invitedIds.length <= capSenior);

// invite up to cap + 5 attempts beyond → must stay capped
for (const c of capped.results.slice(0, capSenior + 5)) store.getState().toggleInvite(c.freelancer.id);
const full = store.getState().draft;
check(`toggleInvite enforces cap (Senior → ${capSenior})`, full.invitedIds.length === Math.min(capSenior, full.results.length));
check('toggleInvite dedupes', new Set(full.invitedIds).size === full.invitedIds.length);

// 3) project creation
store.getState().setDraftTitle('Смоук-проект драфта');
const created = store.getState().createProjectFromTeam();
check('createProjectFromTeam returns project', created !== null);
check('created project id unique', created !== null && draftEco.projects.every((p) => p.id !== created!.id));
check('created project carries team + skills', created !== null && created!.teamIds.length > 0 && created!.requiredSkills.length > 0);
check(
  'created project status follows mentor+team rule',
  created !== null && created!.status === (created!.mentorId !== null && created!.teamIds.length > 0 ? 'in_progress' : 'draft'),
);
check('draft reset after creation', store.getState().draft.requiredSkills.length === 0 && store.getState().draft.invitedIds.length === 0);
check('created project persisted in eco', created !== null && store.getState().eco!.projects.some((p) => p.id === created!.id));

// solo mode: no mentor → status draft even with a team
store.getState().toggleSkill('Blender');
const soloEco = store.getState().eco!;
const soloFirst = soloEco.freelancers[0]!;
store.getState().toggleInvite(soloFirst.id);
const solo = store.getState().createProjectFromTeam();
check('solo (no mentor) project stays draft', solo !== null && solo!.status === 'draft');

// capacity selector
const capSel = selectMentorCapacity(store.getState().eco, seniorMentor.id);
check('selectMentorCapacity reports level limit', capSel.limit === capSenior && capSel.mentor !== null);

/* ---------------- review loop (Review Loop, concept §2) ---------------- */

import { selectReviewQueue, selectTaskDetail } from '../src/app/store.ts';

const r = store.getState();
const rEco = r.eco!;

// queue selector: only cycle tasks
const queueIds = new Set(selectReviewQueue(rEco).map((q) => q.task.id));
const cycleStatuses = new Set(['submitted', 'in_review', 'changes_requested']);
check(
  'selectReviewQueue = exactly the cycle tasks',
  rEco.tasks.every((t) => queueIds.has(t.id) === cycleStatuses.has(t.status)),
);

// rejection first: a task outside the submittable states (done/todo)
const blockedTask = rEco.tasks.find((t) => t.status === 'done') ?? rEco.tasks.find((t) => t.status === 'todo')!;
check('submitVersion on non-submittable task rejected', blockedTask !== undefined && r.submitVersion(blockedTask.id, 'x') === null);

// happy path on an in_progress task (deterministic seed ⇒ exists)
const workTask = rEco.tasks.find((t) => t.status === 'in_progress') ?? rEco.tasks[0]!;
const beforeCount = workTask.versions.length;
const v1 = store.getState().submitVersion(workTask.id, 'Первая версия макета');
check('submitVersion returns version', v1 !== null);
check('submitVersion increments + numbers', v1 !== null && v1.version === beforeCount + 1);
check('submitVersion → status submitted', store.getState().eco!.tasks.find((t) => t.id === workTask.id)!.status === 'submitted');
check('submitVersion on submitted rejected (double-send)', store.getState().submitVersion(workTask.id, 'dup') === null);

// mentor review
check('addReviewNote before review rejected', store.getState().addReviewNote(workTask.id, 'A', 'ранний пин', 'm-0001') === false);
check('startReview works from submitted', store.getState().startReview(workTask.id) === true);
check('startReview on non-submitted rejected', store.getState().startReview(workTask.id) === false);
check('empty note rejected', store.getState().addReviewNote(workTask.id, 'A', '   ', 'm-0001') === false);
check('pin lands on latest version', store.getState().addReviewNote(workTask.id, 'B', 'логотип больше', 'm-0001') === true);
const pinned = store.getState().eco!.tasks.find((t) => t.id === workTask.id)!.versions.at(-1)!;
check('pinned note stored with area+author', (pinned.reviewNotes?.length ?? 0) === 1 && pinned.reviewNotes?.[0]?.area === 'B');

// changes_requested → resubmit → approve
check('requestChanges works from in_review', store.getState().requestChanges(workTask.id) === true);
check('requestChanges on done rejected', store.getState().requestChanges(workTask.id) === false);
const v2 = store.getState().submitVersion(workTask.id, 'Правки по пину B');
check('resubmit after changes works', v2 !== null && v2.version === beforeCount + 2);
store.getState().startReview(workTask.id);
check('approveTask works from in_review', store.getState().approveTask(workTask.id) === true);
const doneTask = store.getState().eco!.tasks.find((t) => t.id === workTask.id)!;
check('approved task is done with progress 100', doneTask.status === 'done' && doneTask.progress === 100);
check('approveTask on non-in_review rejected', store.getState().approveTask(workTask.id) === false);

// task detail selector
const detail = selectTaskDetail(store.getState().eco, workTask.id);
check('selectTaskDetail resolves context', detail !== null && detail.projectTitle !== '' && detail.freelancerName !== '');
check('selectTaskDetail null-safe', selectTaskDetail(rEco, 't-9999') === null);

console.log(failures === 0 ? '\n🔥 SMOKE PASSED — all checks green' : `\n💥 SMOKE FAILED — ${failures} failing`);
process.exit(failures === 0 ? 0 : 1);
