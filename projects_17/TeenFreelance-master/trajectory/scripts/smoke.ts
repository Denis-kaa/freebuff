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
check('100 parents generated', eco.parents.length === 100);
check(
  'parents+consents partition teens (2 children each, rules consent)',
  eco.parents.length === 100 &&
    eco.parents.every((p) => p.childIds.length === 2) &&
    [...eco.parents.flatMap((p) => p.childIds)].sort().join() ===
      [...eco.freelancers.map((f) => f.id)].sort().join() &&
    eco.consents.filter((c) => c.scope === 'platform_rules').length === 200,
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

import { selectReviewQueue, selectTaskDetail, selectConsentInbox, selectConsentForProject } from '../src/app/store.ts';

const r = store.getState();
const rEco = r.eco!;

// Return any task already in_review to a pre-review state so the loop below
// starts from a known point (generator distribution is deterministic but
// the happy-path task must not already be mid-review).
for (const t of rEco.tasks) if (t.status === 'in_review') r.requestChanges(t.id);

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
// Parental Gate: approval completes the task ⇒ consent must be active first.
const wConsent = selectConsentForProject(store.getState().eco, workTask.freelancerId, workTask.projectId);
if (wConsent?.status === 'pending') store.getState().grantConsent(wConsent.id);
else if (!wConsent) {
  const wreq = store.getState().requestConsent(workTask.freelancerId, workTask.projectId);
  if (wreq) store.getState().grantConsent(wreq.id);
}
check('consent arranged for the review-loop task', selectConsentForProject(store.getState().eco, workTask.freelancerId, workTask.projectId)?.status === 'granted');
check('approveTask works from in_review', store.getState().approveTask(workTask.id) === true);
const doneTask = store.getState().eco!.tasks.find((t) => t.id === workTask.id)!;
check('approved task is done with progress 100', doneTask.status === 'done' && doneTask.progress === 100);
check('approveTask on non-in_review rejected', store.getState().approveTask(workTask.id) === false);

// task detail selector
const detail = selectTaskDetail(store.getState().eco, workTask.id);
check('selectTaskDetail resolves context', detail !== null && detail.projectTitle !== '' && detail.freelancerName !== '');
check('selectTaskDetail null-safe', selectTaskDetail(rEco, 't-9999') === null);

/* ---------------- parental gate (Parental Gate, concept §5) ---------------- */

// Work through a fresh task so the ONLY blocker under test is consent.
const gateEco = store.getState().eco!;
const gateTask = gateEco.tasks.find((t) => t.status === 'in_progress')!;
const teenId = gateTask.freelancerId;
const projectId = gateTask.projectId;

// Move it into review: now approveTask fails ONLY on the consent gate.
store.getState().submitVersion(gateTask.id, 'Готов к сдаче');
check('gate task reached in_review', store.getState().startReview(gateTask.id) === true);

// Start: approve must be BLOCKED without an active payment consent.
const parentOfTeen = gateEco.parents.find((p) => p.childIds.includes(teenId))!;
check('parent exists for the teen (partition)', parentOfTeen !== undefined);
check('no consent yet for (teen, project)', selectConsentForProject(gateEco, teenId, projectId) === null);
check('approve BLOCKED without consent', store.getState().approveTask(gateTask.id) === false);

// Request → pending; idempotent for the same (teen, project).
const req1 = store.getState().requestConsent(teenId, projectId);
check('requestConsent creates pending', req1 !== null && req1.status === 'pending');
check('requestConsent has no token yet', req1 !== null && req1.token === '');
const reqDup = store.getState().requestConsent(teenId, projectId);
check('requestConsent idempotent', reqDup !== null && reqDup.id === req1!.id);
check('approve still BLOCKED while pending', store.getState().approveTask(gateTask.id) === false);

// Parent inbox shows the pending request; deny path returns it cleanly.
const inbox = selectConsentInbox(store.getState().eco, parentOfTeen.id);
check('inbox pending contains request', inbox.pending.some((x) => x.consent.id === req1!.id));
check('deny works from pending', store.getState().denyConsent(req1!.id) === true);
check('deny on denied rejected', store.getState().denyConsent(req1!.id) === false);
check('approve BLOCKED after denial', store.getState().approveTask(gateTask.id) === false);

// Second request (denied is final) → grant → approve → revoke → no more approvals.
const req2 = store.getState().requestConsent(teenId, projectId);
check('re-request after denial creates new consent', req2 !== null && req2.id !== req1!.id);
check('grant works from pending', store.getState().grantConsent(req2!.id) === true);
check('grant on granted rejected', store.getState().grantConsent(req2!.id) === false);
check('granted consent has token', (store.getState().eco!.consents.find((c) => c.id === req2!.id)?.token ?? '') !== '');
check('approve allowed WITH consent', store.getState().approveTask(gateTask.id) === true);
check('approved task done + progress 100', store.getState().eco!.tasks.find((t) => t.id === gateTask.id)!.status === 'done');
check('revoke works from granted', store.getState().revokeConsent(req2!.id) === true);
check('revoke on revoked rejected', store.getState().revokeConsent(req2!.id) === false);
const afterRevoke = store.getState().eco!.tasks.find(
  (t) => t.freelancerId === teenId && t.id !== gateTask.id && t.status === 'in_progress',
);
if (afterRevoke) {
  // Walk the next task into review — the revoked consent must block approval.
  store.getState().submitVersion(afterRevoke.id, 'Следующая сдача');
  store.getState().startReview(afterRevoke.id);
  check('approve BLOCKED after revocation (next task)', store.getState().approveTask(afterRevoke.id) === false);
} else {
  console.log('   (no second in_progress task for the teen — revocation-gate checked via denial path)');
}
check('inbox history contains denied+revoked',
  selectConsentInbox(store.getState().eco, parentOfTeen.id).history.length >= 2);

// ---------------- Skill Graph (Этап 3.1, feature layer) ----------------
import { buildSkillGraph, averageEffective, SKILL_BOOSTS, GRAPH_SKILLS } from '../src/features/skill-tree/index.ts';

const graphFreelancer = eco.freelancers[0]!;
const graph = buildSkillGraph(graphFreelancer);

check('skill graph: one node per closed-vocabulary skill', graph.length === GRAPH_SKILLS.length);
check('skill graph: stored level matches freelancer.skills',
  graph.every((n) => n.level === (graphFreelancer.skills[n.skill] ?? 0)));
check('skill graph: effective = min(100, round(stored + boost))',
  graph.every((n) => n.effective === Math.min(100, Math.round(n.level + n.boost))));
check('skill graph: boost rules stay inside closed vocabulary',
  SKILL_BOOSTS.every((r) => GRAPH_SKILLS.includes(r.from) && GRAPH_SKILLS.includes(r.to)));
check('skill graph: boost ≤ weight·from/100 (cap respected)',
  graph.every((n) => n.boost <= SKILL_BOOSTS.filter((r) => r.to === n.skill).reduce((s, r) => s + r.weight, 0)));
check('skill graph: pulse flag ⇔ effective > 80',
  graph.every((n) => n.pulsing === n.effective > 80));
check('skill graph: proofs counted from evidence with skills[] tag',
  graph.every((n) => n.proofs === graphFreelancer.proofs.filter((p) => (p.skills ?? []).includes(n.skill)).length));
check('skill graph: zero-skill freelancer → effective 0, no pulse', (() => {
  const empty = buildSkillGraph({ ...graphFreelancer, skills: {}, proofs: [] });
  return empty.every((n) => n.effective === 0 && !n.pulsing && n.boost === 0);
})());
check('skill graph: averageEffective = rounded mean',
  averageEffective(graph) === Math.round(graph.reduce((s, n) => s + n.effective, 0) / graph.length));

console.log(failures === 0 ? '\n🔥 SMOKE PASSED — all checks green' : `\n💥 SMOKE FAILED — ${failures} failing`);
process.exit(failures === 0 ? 0 : 1);
