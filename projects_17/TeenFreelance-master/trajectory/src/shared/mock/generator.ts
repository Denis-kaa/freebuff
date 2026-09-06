/**
 * Mock-data generator for the TRAJECTORY ecosystem — Phase 2 of the concept
 * (СИСТЕМНЫЙ ПРОМТ: 200 freelancers / 50 mentors / 100 clients / 200 projects,
 * ~5M ₽ turnover, mock-версия концепта «Траектория»).
 *
 * Deterministic: same seed ⇒ same ecosystem (see ./rng).
 * Entities conform to canonical types from src/types.
 */
import type {
  Client,
  Freelancer,
  Mentor,
  Parent,
  ParentalConsent,
  Project,
  ProjectStatus,
  SkillName,
  Task,
  TaskStatus,
} from '../../types';
import { createRng } from './rng.ts';

/* ------------------------- vocabularies ------------------------- */

export const SKILL_NAMES: readonly SkillName[] = [
  'Figma',
  'Blender',
  'Python',
  'Copywriting',
  'UX Research',
  'Typography',
  'Composition',
  'AI Tools',
];

const FIRST_NAMES = [
  'Максим', 'Анна', 'Даниил', 'Мария', 'Тимур', 'Софья', 'Артём', 'Алиса',
  'Никита', 'Вера', 'Егор', 'Полина', 'Лев', 'Дарья', 'Марк', 'Ева',
  'Кирилл', 'Юлия', 'Матвей', 'Алиса',
] as const;

const LAST_INITIALS = 'АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ'.split('');

const MENTOR_TITLES = [
  'Art Director', 'Senior Dev', 'Tech Lead', 'Product Designer', 'Copy Chief',
  'Data Scientist', 'Motion Designer', 'UX Lead', '3D Artist', 'CTO',
] as const;

const COMPANIES = [
  'Studio Arhi', 'FinTech Start', 'EcoFarm', 'Neon Media', 'DevHouse',
  'Zerno Coffee', 'PrintWorks', 'CloudKitchen', 'AgroTech', 'Bookfox',
  'Sportly', 'MebelCraft', 'AutoParts', 'TravelGo', 'EduLab',
] as const;

const PROJECT_TITLES: ReadonlyArray<[string, readonly SkillName[]]> = [
  ['Ребрендинг кофейни «Зерно»', ['Figma', 'Typography', 'Composition']],
  ['Лендинг EcoFarm', ['Copywriting', 'Figma']],
  ['30 карточек товаров для маркетплейса', ['Figma', 'AI Tools']],
  ['Мобильное приложение «Спортли» — UX-аудит', ['UX Research', 'Figma']],
  ['3D-визуализация мебельной фабрики', ['Blender', 'Composition']],
  ['Telegram-бот записи для автосервиса', ['Python']],
  ['Серия постеров для Neon Media', ['Composition', 'AI Tools', 'Typography']],
  ['Копирайтинг для Bookfox: 10 статей', ['Copywriting']],
  ['Аналитика для AgroTech: дашборд на Python', ['Python', 'UX Research']],
  ['AI-обложки для EduLab', ['AI Tools', 'Figma']],
];

const CLIENT_BUDGETS = [8000, 12000, 15000, 20000, 25000, 40000, 60000] as const;
const IMG_COVER_POOL = ['IMG-03', 'IMG-05', 'IMG-06', 'IMG-07'] as const;
const ECONOMY = { teen: 51, mentor: 20, platform: 20, reserve: 9 } as const;

/* ------------------------- id helpers ------------------------- */

const counters = new Map<string, number>();
const pad = (n: number, w = 4) => String(n).padStart(w, '0');
/** 2-digit month/day for mock ISO dates. */
const d2 = (n: number) => String(n).padStart(2, '0');
/** Per-prefix counter: f-0001 is always the first freelancer. */
const nextId = (prefix: string) => {
  const n = (counters.get(prefix) ?? 0) + 1;
  counters.set(prefix, n);
  return `${prefix}-${pad(n)}`;
};
const resetSeq = () => {
  counters.clear();
};

/* ------------------------- generator ------------------------- */

export interface Ecosystem {
  freelancers: Freelancer[];
  mentors: Mentor[];
  clients: Client[];
  parents: Parent[];
  consents: ParentalConsent[];
  projects: Project[];
  tasks: Task[];
}

export function generateEcosystem(seed = 20260905): Ecosystem {
  const rng = createRng(seed);
  resetSeq();

  const freelancers: Freelancer[] = [];
  const mentors: Mentor[] = [];
  const clients: Client[] = [];
  const parents: Parent[] = [];
  const consents: ParentalConsent[] = [];
  const projects: Project[] = [];
  const tasks: Task[] = [];

  /* --- 200 freelancers: 14–18 y.o., Skill Score + proofs --- */
  for (let i = 0; i < 200; i++) {
    const name = `${rng.pick(FIRST_NAMES)} ${rng.pick(LAST_INITIALS)}.`;
    const skillCount = rng.int(2, 5);
    const chosenSkills = rng.sample(SKILL_NAMES, skillCount);
    const skills: Partial<Record<SkillName, number>> = {};
    for (const s of chosenSkills) {
      // bell-shaped distribution: most skills 30..80, outliers reach 95
      skills[s] = rng.bell(25, 95);
      if (skills[s] === 95 && !rng.chance(0.3)) skills[s] = rng.int(70, 88);
    }

    const proofs = chosenSkills.slice(0, rng.int(1, 3)).map((s) => ({
      id: nextId('prf'),
      type: (rng.chance(0.75) ? 'project' : 'review') as 'project' | 'review',
      title: `Практика: ${s}`,
      date: `2026-${d2(rng.int(1, 9))}-${d2(rng.int(1, 28))}`,
    }));

    const earnings = rng.chance(0.55)
      ? rng.int(0, 8) * 5000 // has already earned something
      : rng.int(0, 3) * 1000; // newcomer

    const f: Freelancer = {
      id: nextId('f'),
      name,
      role: 'freelancer',
      age: rng.int(14, 18),
      reputation: rng.bell(40, 95),
      skills,
      proofs,
      earnings,
      status: rng.chance(0.5) ? 'looking' : rng.chance(0.6) ? 'active' : 'busy',
    };
    freelancers.push(f);

    /* --- 100 parents: 2 children each = perfect partition of 200 teens (concept §1) --- */
    if (i % 2 === 0) {
      parents.push({
        id: nextId('par'),
        name: `Родитель ${name}`,
        role: 'parent',
        reputation: 0,
        childIds: [],
      });
    }
    const parent = parents[parents.length - 1] as Parent | undefined;
    if (parent) {
      parent.childIds.push(f.id);
      // Platform rules consent exists from the start; payment consents are requested later.
      consents.push({
        id: nextId('cons'),
        parentId: parent.id,
        freelancerId: f.id,
        scope: 'platform_rules',
        grantedAt: `2026-${d2(rng.int(1, 9))}-${d2(rng.int(1, 28))}`,
        token: `tok-${rng.hex(12)}`, // mock token; real impl: opaque + hashed at rest
        status: 'granted',
      });
    }
  }

  /* --- 50 mentors: level gates complexity (concept §8) --- */
  for (let i = 0; i < 50; i++) {
    const level: Mentor['level'] = (() => {
      const r = rng.next(0, 1);
      if (r < 0.4) return 'Junior';
      if (r < 0.7) return 'Pro';
      if (r < 0.9) return 'Senior';
      return 'Expert';
    })();
    mentors.push({
      id: nextId('m'),
      name: `${rng.pick(FIRST_NAMES)} ${rng.pick(MENTOR_TITLES)}`,
      role: 'mentor',
      specialization: rng.pick(SKILL_NAMES),
      level,
      studentsCount: rng.int(2, 32),
      successRate: rng.bell(55, 98),
      reputation: rng.bell(60, 99),
    });
  }

  /* --- 100 clients: companies with budgets (concept §12 Talent Pool) --- */
  for (let i = 0; i < 100; i++) {
    clients.push({
      id: nextId('c'),
      name: `${rng.pick(FIRST_NAMES)} ${rng.pick(LAST_INITIALS)}.`,
      role: 'client',
      companyName: rng.pick(COMPANIES),
      budget: rng.pick(CLIENT_BUDGETS) * rng.int(1, 4),
      reputation: rng.bell(50, 95),
    });
  }

  /* --- 200 projects: mentor-led teams (concept §2) --- */
  const projectStatuses: readonly ProjectStatus[] = ['draft', 'in_progress', 'review', 'completed', 'cancelled'];
  for (let i = 0; i < 200; i++) {
    const [title, reqSkills] = rng.pick(PROJECT_TITLES);
    const mentor = rng.pick(mentors);
    // Mentor level gates team size and budget (concept §8)
    const teamSize =
      mentor.level === 'Expert' ? rng.int(3, 5)
      : mentor.level === 'Senior' ? rng.int(2, 4)
      : mentor.level === 'Pro' ? rng.int(1, 3)
      : 1;
    const teamIds = rng.sample(freelancers, teamSize).map((f) => f.id);

    const status: ProjectStatus = rng.chance(0.06)
      ? 'draft'
      : rng.pick(projectStatuses.filter((s) => s !== 'draft'));
    const clientId = rng.pick(clients).id;

    projects.push({
      id: nextId('PRJ'),
      title,
      description: `Проект для ${clientId}: ${reqSkills.join(' + ')}. Команда под руководством ${mentor.name}.`,
      budget: rng.pick(CLIENT_BUDGETS),
      clientId,
      mentorId: mentor.id,
      teamIds,
      status,
      requiredSkills: [...reqSkills],
      coverImgId: rng.pick(IMG_COVER_POOL),
      createdAt: `2026-${d2(rng.int(1, 9))}-${d2(rng.int(1, 28))}`,
      deadline: rng.chance(0.7) ? `2026-${d2(rng.int(10, 12))}-${d2(rng.int(1, 28))}` : undefined,
    });

    /* --- 1..3 tasks per project for team members --- */
    const created = projects[projects.length - 1] as Project;
    for (const fid of rng.sample(created.teamIds, Math.min(created.teamIds.length, rng.int(1, 3)))) {
      const taskStatus: TaskStatus = rng.pick([
        'todo', 'in_progress', 'submitted', 'in_review', 'changes_requested', 'done',
      ] as const);
      tasks.push({
        id: nextId('t'),
        projectId: created.id,
        freelancerId: fid,
        title: `${created.title} — роль: ${reqSkills[rng.int(0, reqSkills.length - 1)]}`,
        description: `Часть команды проекта «${created.title}».`,
        status: taskStatus,
        progress:
          taskStatus === 'done' ? 100
          : taskStatus === 'todo' ? 0
          : taskStatus === 'submitted' || taskStatus === 'in_review' ? rng.int(70, 95)
          : rng.int(10, 70),
        deadline: created.deadline,
        versions: [],
        reward: Math.round((created.budget * ECONOMY.teen) / 100 / Math.max(1, created.teamIds.length)),
      });
    }
  }

  return { freelancers, mentors, clients, parents, consents, projects, tasks };
}

/** Economy split reference (concept §11) — used by store selectors. */
export const ECONOMY_SPLIT = ECONOMY;

/** Total turnover of all non-draft projects (mock «оборот 5 млн ₽» metric). */
export function totalTurnover(eco: Ecosystem): number {
  return eco.projects
    .filter((p) => p.status !== 'draft' && p.status !== 'cancelled')
    .reduce((sum, p) => sum + p.budget, 0);
}
