# buffy-playground — Frontend Development Sandbox

> **Назначение:** изолированная среда для разработки и тестирования frontend-компонентов Buffy.
> **Технологии:** Vite + React + TypeScript
> **Не является частью:** production-сборки. Исключительно для разработки.

---

## Структура

```
buffy-playground/
├── src/
│   ├── App.tsx          # Главный компонент
│   ├── App.css          # Стили
│   ├── main.tsx         # Точка входа
│   ├── index.css        # Глобальные стили
│   └── assets/          # Изображения, иконки
├── public/
│   └── favicon.svg
├── index.html           # HTML-шаблон
├── vite.config.ts       # Конфигурация Vite
├── tsconfig.json        # TypeScript конфигурация
├── package.json         # Зависимости
└── README.md
```

## Использование

```bash
cd buffy-playground
npm install
npm run dev     # Запуск dev-сервера
npm run build   # Production сборка
```

## Назначение

- Прототипирование UI-компонентов перед интеграцией в основную систему
- Тестирование React-компонентов в изоляции
- Эксперименты с новыми frontend-фичами
- Песочница для визуальных концепций

## Статус

🏗️ В разработке. Используется по мере необходимости.
