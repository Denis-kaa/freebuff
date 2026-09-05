/**
 * App root — Stage 1 skeleton. Renders a single proof-of-wiring screen:
 * alias imports across all FSD layers compile, canonical types are in place.
 */
import type { ActivityEntry, Freelancer } from '@entities/user';
import { routes } from './routes';

const freelancer: Freelancer = {
  id: 'f-0001',
  name: 'Максим',
  role: 'freelancer',
  age: 17,
  reputation: 84,
  earnings: 47500,
  status: 'active',
  skills: { Figma: 82, Typography: 75, Copywriting: 60 },
  proofs: [
    { id: 'p-1', type: 'project', title: 'Ребрендинг «Зерно»', date: '2026-08-30' },
    { id: 'p-2', type: 'project', title: 'EcoFarm Landing', date: '2026-08-01' },
  ],
};

const feed: ActivityEntry[] = [
  { id: 'a-1', type: 'skill_up', text: 'Навык Figma обновлен (+2)', time: '2 часа назад' },
  { id: 'a-2', type: 'payment', text: 'Получена оплата за EcoFarm (₽15,000)', time: 'Вчера' },
];

export default function App() {
  return (
    <main style={{ fontFamily: 'monospace', padding: 32 }}>
      <p>TRAJECTORY · Stage 1 skeleton — FSD layers compile.</p>
      <p>
        {freelancer.name} · {freelancer.reputation}/100 · routes.intro = {routes.intro}
      </p>
      <ul>
        {feed.map((a) => (
          <li key={a.id}>{a.text}</li>
        ))}
      </ul>
    </main>
  );
}
