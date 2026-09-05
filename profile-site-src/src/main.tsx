import { FormEvent, useEffect, useState } from "react";
import type { CSSProperties, FC, ReactElement } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Motif =
  | "blueprint"
  | "pipeline"
  | "ledger"
  | "terminal"
  | "timeledger"
  | "chat"
  | "board"
  | "cinema";

type Project = {
  id: string;
  num: string;
  title: string;
  kind: string;
  status: string;
  accent: string;
  dark?: boolean;
  summary: string;
  task: string;
  approach: string;
  result: string;
  stack: string[];
  role: string;
  motif: Motif;
};

const PROJECTS: Project[] = [
  {
    id: "freebuff",
    num: "01",
    title: "Freebuff / Workspace OS",
    kind: "Собственный продукт",
    status: "в активной разработке, 2025 — сейчас",
    accent: "#3E6B54",
    summary:
      "Платформа для долгоживущей AI-разработки: память, контекст, RAG, роутинг моделей и оркестрация агентов в одной среде.",
    task: "AI-инструменты по отдельности теряют контекст и работают несогласованно: у бота одна память, у скриптов другая, проверки ручные. Нужна среда, где агенты, знания и тестирование — единая система с контрактами.",
    approach:
      "Capability-based роутер выбирает модель под задачу. Пять уровней памяти хранят факты, решения и историю сессий. Knowledge Engine даёт RAG-поиск по документации, Event Bus связывает компоненты событиями, MCP открывает доступ внешним инструментам. Каждый модуль покрыт контрактными тестами.",
    result:
      "3350+ автоматических тестов. Система используется ежедневно как основная рабочая среда и развивается итеративно, без переписывания с нуля.",
    stack: ["Python", "SQLite / FTS5", "RAG", "MCP", "Telegram Bot API", "pytest"],
    role: "Архитектура, реализация, тестирование",
    motif: "blueprint",
  },
  {
    id: "production-stabilization",
    num: "02",
    title: "Стабилизация production-сервиса",
    kind: "Клиентский кейс · анонимно",
    status: "завершён, передан заказчику",
    accent: "#9A5B33",
    summary:
      "Аудит и восстановление пайплайна автодубляжа видео: загрузка, распознавание речи, перевод, синтез, монтаж.",
    task: "Сервис деградировал в production: падения по памяти, циклические рестарты, отваливающиеся cookies и застревающие задачи в очередях. Владелец терял готовые видео и не понимал причин.",
    approach:
      "Разобрал пайплайн по стадиям и устранил пять корневых причин: перенос склейки аудио из RAM в потоковый ffmpeg, Redis NX-локи против дублей, атомарная работа с cookies, очистка зависших задач, диагностика по логам systemd.",
    result:
      "0 ошибок на контрольном прогоне. Название сервиса и внутренние детали раскрываются только с разрешения клиента.",
    stack: ["FastAPI", "Celery", "PostgreSQL", "Redis", "FFmpeg", "TTS", "systemd"],
    role: "Аудит, стабилизация, передача",
    motif: "pipeline",
  },
  {
    id: "investment-analytics",
    num: "03",
    title: "Инвестиционная аналитика",
    kind: "Клиентский кейс · анонимно",
    status: "работает у заказчика",
    accent: "#33506B",
    summary:
      "Платформа с личным кабинетом и отчётностью: непредсказуемые выгрузки брокеров превращаются в понятную картину портфеля.",
    task: "Пользователи загружают CSV и XLSX-выгрузки самых разных форматов: разные колонки, локали, даты, скрытые строки. Их нужно превратить в корректную аналитику и отчёты.",
    approach:
      "Нормализация входа с сохранением происхождения данных, устойчивый парсинг форматов, аутентификация и личный кабинет, отчёты, понятные человеку без финансового образования.",
    result:
      "Хаотичные выгрузки превращены в структурированный портфель и отчёты, которыми пользуются реальные клиенты. Название платформы — с разрешения заказчика.",
    stack: ["FastAPI", "PostgreSQL", "CSV / XLSX", "Nginx"],
    role: "Backend, нормализация данных",
    motif: "ledger",
  },
  {
    id: "leviathan",
    num: "04",
    title: "Leviathan_Agent",
    kind: "Собственный проект",
    status: "периодическая разработка",
    accent: "#2F6B4F",
    summary:
      "Автономный DevOps-агент: диагностика и ремонт сервера по команде из Telegram, с пулом ключей и идемпотентными операциями.",
    task: "Рутинная диагностика сервера — вход по SSH, просмотр логов, рестарты — повторяется каждый день. Нужен агент, который делает это по команде и не ломает рабочие сервисы.",
    approach:
      "Gemini для разбора состояния, FastAPI и WebSocket для управления, пул из 14 API-ключей с ротацией, идемпотентность каждой операции, интеграция с systemd и MCP.",
    result:
      "Рутинные операции выполняются агентом, а повторный запуск операции не меняет результат и не ломает сервис.",
    stack: ["Python", "Gemini", "Docker", "systemd", "WebSocket", "MCP"],
    role: "Архитектура, реализация",
    motif: "terminal",
  },
  {
    id: "kwork-cli",
    num: "05",
    title: "kwork-cli",
    kind: "Собственный инструмент",
    status: "используется ежедневно",
    accent: "#7A3E2E",
    summary:
      "CLI-конвейер для фриланс-заказов: декомпозиция ТЗ, генерация решения, независимая проверка результата.",
    task: "Типовой заказ съедал 10–20 часов: чтение ТЗ, реализация, правки, проверка. Цикл нужно было превратить в управляемый процесс.",
    approach:
      "Декомпозиция ТЗ на проверяемые шаги, генерация каждой части отдельным запросом, независимая валидация результата и сборка итоговой поставки.",
    result:
      "10–20 часов превращены в 30–40 минут контроля на типовой заказ. Качество держится проверками, а не скоростью.",
    stack: ["Python", "LLM API", "pytest"],
    role: "Дизайн процесса, реализация",
    motif: "timeledger",
  },
  {
    id: "puhlyash",
    num: "06",
    title: "Бот «Пухляш»",
    kind: "Production-проект",
    status: "работает, активные пользователи",
    accent: "#8A6D3B",
    summary:
      "Telegram-бот по питанию: дневник, рецепты и дайджесты — доброжелательный ассистент вместо занудной таблицы калорий.",
    task: "Люди бросают трекеры питания из-за форм, граммов и чувства стыда. Нужен бот, с которым разговаривать проще, чем считать калории.",
    approach:
      "Диалоговый интерфейс на aiogram, трекинг в SQLite с WAL, ротация ключей Gemini для стабильности, еженедельные дайджесты привычек.",
    result: "Стабильный production с активными пользователями и ежедневными сессиями.",
    stack: ["Python", "aiogram", "SQLite / WAL", "Gemini API"],
    role: "Продукт, backend, развитие",
    motif: "chat",
  },
  {
    id: "hr-agent",
    num: "07",
    title: "HR-Agent",
    kind: "Собственный проект",
    status: "периодическая разработка",
    accent: "#2E5E52",
    summary:
      "Автоматизация поиска работы: анализ вакансий с HH.ru, оценка шансов и подготовка откликов в одном конвейере.",
    task: "Поиск вакансии — это сотни однообразных карточек и одинаковых откликов. Нужен конвейер, который сортирует, оценивает и готовит черновики.",
    approach:
      "Забор вакансий через HH.ru API, разбор требований, оценка соответствия профилю, подготовка черновиков откликов и уведомления в Telegram.",
    result: "От потока вакансий до подготовленных откликов — без ручной сортировки.",
    stack: ["FastAPI", "Telegram", "HH.ru API", "SQLite"],
    role: "Реализация, автоматизация",
    motif: "board",
  },
  {
    id: "kinovibe",
    num: "08",
    title: "KinoVibe",
    kind: "Собственный проект",
    status: "прототип",
    accent: "#B08A3E",
    dark: true,
    summary:
      "Кино-помощник: подбор фильма по настроению через голос или текст, с объяснением выбора.",
    task: "Подбор фильма по настроению плохо решается фильтрами по жанру: настроение — не жанр. Нужен интерфейс, который слушает и понимает запрос.",
    approach:
      "Голос и текст на входе, Gemini и Groq для разбора настроения, yt-dlp для данных о трейлерах, Flutter-клиент.",
    result: "Работающий прототип подбора «под настроение» вместо фильтров по жанру.",
    stack: ["FastAPI", "Gemini / Groq", "yt-dlp", "Flutter"],
    role: "Концепция, прототип",
    motif: "cinema",
  },
];

function MotifBlueprint() {
  const layers: [string, string][] = [
    ["Telegram-интерфейс", "диалоги, команды, отчёты"],
    ["Оркестратор", "Event Bus, планирование шагов"],
    ["Роутер моделей", "capability-based выбор LLM"],
    ["Knowledge Engine", "RAG, чанкинг, FTS5-поиск"],
    ["Память · 5 уровней", "факты, решения, сессии"],
  ];
  return (
    <div className="motif motif-blueprint">
      {layers.map(([name, note], i) => (
        <div className="bp-item" key={name}>
          <div className="bp-block">
            <b>{name}</b>
            <span>{note}</span>
          </div>
          {i < layers.length - 1 && <div className="bp-link" aria-hidden="true" />}
        </div>
      ))}
      <div className="bp-note">Контракты и 3350+ тестов между всеми слоями</div>
    </div>
  );
}

function MotifPipeline() {
  const stages: [string, string][] = [
    ["Загрузка", "потоковый ffmpeg вместо RAM"],
    ["Распознавание", "очистка зависших задач"],
    ["Перевод", "устойчивый парсинг ответов"],
    ["Синтез речи", "атомарные cookies"],
    ["Монтаж", "Redis NX-локи от дублей"],
  ];
  return (
    <div className="motif motif-pipeline">
      <div className="pl-row">
        {stages.map(([stage, fix], i) => (
          <div className="pl-stage" key={stage}>
            <span className="pl-step">{String(i + 1).padStart(2, "0")}</span>
            <b>{stage}</b>
            <span className="pl-fix">{fix}</span>
          </div>
        ))}
      </div>
      <div className="pl-verdict">
        <span>было: 5 корневых причин сбоев</span>
        <span>стало: 0 ошибок на контрольном прогоне</span>
      </div>
    </div>
  );
}

function MotifLedger() {
  const messy = [
    "report_broker_FINAL_v2.csv",
    "движения (14 листов).xlsx",
    "сделки_экспорт 03.xlsx",
    "portfolio_old(1).xlsx",
  ];
  const clean = ["Портфель", "Отчёт по сделкам", "Динамика активов", "Личный кабинет"];
  return (
    <div className="motif motif-ledger">
      <div className="lg-col">
        <small>вход: как присылают пользователи</small>
        {messy.map((m) => (
          <div className="lg-row messy" key={m}>
            {m}
          </div>
        ))}
      </div>
      <div className="lg-arrow" aria-hidden="true">
        →
      </div>
      <div className="lg-col">
        <small>выход: что видит пользователь</small>
        {clean.map((m) => (
          <div className="lg-row" key={m}>
            {m}
          </div>
        ))}
      </div>
    </div>
  );
}

function MotifTerminal() {
  const lines: [string, string][] = [
    ["$", "leviathan diagnose --host prod"],
    ["ok", "пул ключей: 14, ротация активна"],
    ["ok", "systemd: 3 сервиса, 0 упавших"],
    ["fix", "nginx: рестарт применён (идемпотентно)"],
    ["ok", "повторный прогон: изменений нет"],
    ["$", "leviathan report --to telegram"],
  ];
  return (
    <div className="motif motif-terminal">
      <div className="term-bar">
        <i></i>
        <i></i>
        <i></i>
        <span>leviathan · prod</span>
      </div>
      <div className="term-body">
        {lines.map(([kind, text], i) => (
          <div className="term-line" key={i}>
            {kind === "$" ? <b>{kind}</b> : <em data-kind={kind}>{kind}</em>}
            <span>{text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MotifTimeledger() {
  return (
    <div className="motif motif-timeledger">
      <div className="tl-from">
        <b>10–20 ч</b>
        <span>типовой заказ: чтение ТЗ, реализация, правки</span>
      </div>
      <div className="tl-arrow" aria-hidden="true">
        →
      </div>
      <div className="tl-to">
        <b>30–40 мин</b>
        <span>контроль результата: проверка, сборка поставки</span>
      </div>
    </div>
  );
}

function MotifChat() {
  const rows: [boolean, string][] = [
    [true, "съел боул с курицей и рисом, грамм 450"],
    [false, "Записал: примерно 520 ккал, 38 г белка. К вечеру осталось около 600 ккал запаса."],
    [true, "а что приготовить на ужин?"],
    [false, "С учётом остатка — треска с овощами и гречкой. Рецепт на 25 минут, показать?"],
  ];
  return (
    <div className="motif motif-chat">
      {rows.map(([isUser, text], i) => (
        <div className={isUser ? "ch-row user" : "ch-row bot"} key={i}>
          <p>{text}</p>
        </div>
      ))}
    </div>
  );
}

function MotifBoard() {
  const cols: [string, string[]][] = [
    ["Найдено за сутки", ["Python-разработчик · 41", "AI-инженер · 12", "Data-аналитик · 27"]],
    ["Оценка шансов", ["AI-инженер · 78%", "Python · 54%", "Data · 31%"]],
    ["Черновики откликов", ["AI-инженер — готов", "Python — черновик", "Data — отклонено"]],
  ];
  return (
    <div className="motif motif-board">
      {cols.map(([title, items]) => (
        <div className="bd-col" key={title}>
          <small>{title}</small>
          {items.map((it) => (
            <div className="bd-card" key={it}>
              {it}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function MotifCinema() {
  const frames: [string, string][] = [
    ["настроение: дождливый вечер", "медленное кино, крупный город"],
    ["настроение: тревога перед утром", "нео-нуар, звук важнее картинки"],
    ["настроение: тёплая ностальгия", "плёночная фактура, лето, детство"],
  ];
  return (
    <div className="motif motif-cinema">
      {frames.map(([mood, pick]) => (
        <figure className="ci-frame" key={mood}>
          <figcaption>{mood}</figcaption>
          <div className="ci-screen">
            <span>{pick}</span>
          </div>
        </figure>
      ))}
    </div>
  );
}

const MOTIFS: Record<Motif, FC> = {
  blueprint: MotifBlueprint,
  pipeline: MotifPipeline,
  ledger: MotifLedger,
  terminal: MotifTerminal,
  timeledger: MotifTimeledger,
  chat: MotifChat,
  board: MotifBoard,
  cinema: MotifCinema,
};

function useHashRoute(): string {
  const [hash, setHash] = useState<string>(() => window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash || "#/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

function Nav({ route }: { route: string }) {
  const onHome = route === "#/" || !route.startsWith("#/project/");
  return (
    <nav className="nav">
      <a className="nav-brand" href="#/">
        Денис Литвинов
      </a>
      {onHome ? (
        <div className="nav-links">
          <a
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              scrollToId("projects");
            }}
          >
            Проекты
          </a>
          <a
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              scrollToId("approach");
            }}
          >
            Подход
          </a>
          <a
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              scrollToId("contact");
            }}
          >
            Контакты
          </a>
        </div>
      ) : (
        <div className="nav-links">
          <a href="#/">← Все проекты</a>
        </div>
      )}
      <a className="nav-github" href="https://github.com/lidenal85-blip" target="_blank" rel="noreferrer">
        GitHub
      </a>
    </nav>
  );
}

function Home() {
  return (
    <main>
      <section className="hero">
        <p className="hero-kicker">AI-инженер · интегратор LLM · визуальные системы</p>
        <h1>
          Из идеи —
          <br />
          в работающую систему.
        </h1>
        <p className="hero-lead">
          Проектирую AI-решения и интерфейсы к ним: постановка задачи, архитектура, проверка
          результата. Работаю с LLM, агентами, RAG, Telegram и backend-инфраструктурой.
        </p>
        <div className="hero-actions">
          <a
            className="cta"
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              scrollToId("projects");
            }}
          >
            Смотреть проекты
          </a>
          <a
            className="cta-quiet"
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              scrollToId("contact");
            }}
          >
            Обсудить задачу
          </a>
        </div>
        <p className="hero-context">
          Python · FastAPI · RAG · aiogram · Docker · systemd — от постановки задачи до проверенного
          результата.
        </p>
      </section>

      <section className="index" id="projects">
        <h2 className="sec-title">
          <span>01 — Проекты</span>Восемь историй о доведении до результата.
        </h2>
        <div className="index-list">
          {PROJECTS.map((p) => (
            <a
              className="index-row"
              key={p.id}
              href={`#/project/${p.id}`}
              style={{ "--acc": p.accent } as CSSProperties}
            >
              <span className="ir-num">{p.num}</span>
              <span className="ir-main">
                <b>{p.title}</b>
                <span>
                  {p.kind} · {p.status}
                </span>
              </span>
              <span className="ir-summary">{p.summary}</span>
              <span className="ir-arrow" aria-hidden="true">
                →
              </span>
            </a>
          ))}
        </div>
      </section>

      <section className="approach" id="approach">
        <h2 className="sec-title">
          <span>02 — Подход</span>Проверка важнее генерации.
        </h2>
        <div className="approach-cols">
          <div>
            <h3>Постановка</h3>
            <p>Сначала критерии приёмки и границы задачи, потом инструменты. Архитектура — до кода, а не после.</p>
          </div>
          <div>
            <h3>Проверка</h3>
            <p>Результат проверяется независимо от того, кто его создал — модель или я: тесты, контрольные прогоны, разбор отказов.</p>
          </div>
          <div>
            <h3>Доведение</h3>
            <p>Система готова, когда работает у пользователя, а не в демо. Документация и передача — часть результата.</p>
          </div>
        </div>
      </section>

      <Contact />
    </main>
  );
}

function Contact() {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = `Здравствуйте! Меня зовут ${String(data.get("name"))}. Тип задачи: ${String(
      data.get("type")
    )}. ${String(data.get("message"))}`;
    window.open(`https://t.me/vaalchik?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  }
  return (
    <section className="contact" id="contact">
      <h2 className="sec-title">
        <span>03 — Контакт</span>Опишите задачу — вернусь с планом.
      </h2>
      <div className="contact-grid">
        <div className="contact-info">
          <p>Работа, фриланс или нестандартный AI-прототип: расскажите, какой результат нужен на выходе.</p>
          <a href="https://t.me/vaalchik" target="_blank" rel="noreferrer">
            Telegram · @vaalchik
          </a>
          <a href="mailto:den4ikorm@yandex.ru">den4ikorm@yandex.ru</a>
          <a href="https://github.com/lidenal85-blip" target="_blank" rel="noreferrer">
            GitHub · lidenal85-blip
          </a>
        </div>
        <form onSubmit={submit}>
          <label>
            Имя
            <input name="name" required placeholder="Как к вам обращаться" />
          </label>
          <label>
            Тип задачи
            <select name="type">
              <option>Работа</option>
              <option>Фриланс / заказ</option>
              <option>AI-консультация</option>
            </select>
          </label>
          <label>
            Сообщение
            <textarea name="message" required placeholder="Что нужно получить на выходе" />
          </label>
          <button className="cta" type="submit">
            Отправить через Telegram
          </button>
          <small>Откроется Telegram с готовым текстом. Данные никуда не сохраняются.</small>
        </form>
      </div>
    </section>
  );
}

function ProjectPage({ project }: { project: Project }) {
  const Motif = MOTIFS[project.motif];
  const idx = PROJECTS.findIndex((p) => p.id === project.id);
  const prev = PROJECTS[(idx + PROJECTS.length - 1) % PROJECTS.length];
  const next = PROJECTS[(idx + 1) % PROJECTS.length];
  return (
    <main className={project.dark ? "page dark" : "page"}>
      <header className="page-hero" style={{ "--acc": project.accent } as CSSProperties}>
        <p className="page-kicker">
          {project.num} · {project.kind} · {project.status}
        </p>
        <h1>{project.title}</h1>
        <p className="page-summary">{project.summary}</p>
        <dl className="page-meta">
          <div>
            <dt>Стек</dt>
            <dd className="mono">{project.stack.join(" · ")}</dd>
          </div>
          <div>
            <dt>Роль</dt>
            <dd>{project.role}</dd>
          </div>
          <div>
            <dt>Статус</dt>
            <dd>{project.status}</dd>
          </div>
        </dl>
      </header>
      <section className="motif-section">
        <Motif />
      </section>
      <section className="page-body">
        <div className="pb-row">
          <h3>Задача</h3>
          <p>{project.task}</p>
        </div>
        <div className="pb-row">
          <h3>Подход</h3>
          <p>{project.approach}</p>
        </div>
        <div className="pb-row">
          <h3>Результат</h3>
          <p>{project.result}</p>
        </div>
      </section>
      <nav className="page-next">
        <a href={`#/project/${prev.id}`}>← {prev.title}</a>
        <a href={`#/project/${next.id}`}>{next.title} →</a>
      </nav>
    </main>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <span>Денис Литвинов, 2026</span>
      <a href="https://github.com/lidenal85-blip" target="_blank" rel="noreferrer">
        GitHub
      </a>
    </footer>
  );
}

function App() {
  const route = useHashRoute();
  let page: ReactElement;
  if (route.startsWith("#/project/")) {
    const id = decodeURIComponent(route.slice("#/project/".length));
    const project = PROJECTS.find((p) => p.id === id);
    page = project ? <ProjectPage project={project} /> : <Home />;
  } else {
    page = <Home />;
  }
  return (
    <>
      <Nav route={route} />
      {page}
      <Footer />
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
