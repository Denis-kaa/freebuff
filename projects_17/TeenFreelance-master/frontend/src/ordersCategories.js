// Полная структура категорий для биржи заказов
export const ORDERS_CATEGORIES = [
  {
    id: 'seo-traffic',
    name: 'SEO и трафик',
    subcategories: [
      {
        id: 'seo-audits-consultations',
        name: 'SEO аудиты, консультации',
        subcategories: [
          { id: 'seo-audit', name: 'SEO аудит' },
          { id: 'consultation', name: 'Консультация' }
        ]
      },
      {
        id: 'site-promotion-top',
        name: 'Продвижение сайта в топ',
        subcategories: [
          { id: 'links-in-profiles', name: 'В профилях' },
          { id: 'links-in-social', name: 'В соцсетях' },
          { id: 'links-in-comments', name: 'В комментариях' },
          { id: 'catalogs', name: 'Каталоги сайтов' },
          { id: 'forum-links', name: 'Форумные' },
          { id: 'article-crowd', name: 'Статейные и крауд' }
        ]
      },
      {
        id: 'traffic',
        name: 'Трафик',
        subcategories: [
          { id: 'visitors-to-site', name: 'Посетители на сайт' },
          { id: 'behavioral-factors', name: 'Поведенческие факторы' }
        ]
      },
      {
        id: 'internal-optimization',
        name: 'Внутренняя оптимизация',
        subcategories: [
          { id: 'full-optimization', name: 'Полная оптимизация' },
          { id: 'page-optimization', name: 'Оптимизация страниц' },
          { id: 'robots-sitemap', name: 'Robots и sitemap' },
          { id: 'tags', name: 'Теги' },
          { id: 'interlinking', name: 'Перелинковка' },
          { id: 'microdata', name: 'Микроразметка' }
        ]
      },
      {
        id: 'semantic-core',
        name: 'Семантическое ядро',
        subcategories: [
          { id: 'semantic-from-scratch', name: 'С нуля' },
          { id: 'semantic-by-site', name: 'По сайту' },
          { id: 'semantic-ready', name: 'Готовое ядро' }
        ]
      },
      {
        id: 'statistics-analytics',
        name: 'Статистика и аналитика',
        subcategories: [
          { id: 'metrics-counters', name: 'Метрики и счетчики' },
          { id: 'site-market-analysis', name: 'Анализ сайтов, рынка' }
        ]
      }
    ]
  },
  {
    id: 'audio-video',
    name: 'Аудио, видео, съемка',
    subcategories: [
      {
        id: 'audio-recording-voiceover',
        name: 'Аудиозапись и озвучка',
        subcategories: [
          { id: 'voiceover-speakers', name: 'Озвучка и дикторы' },
          { id: 'audio-clip', name: 'Аудиоролик' }
        ]
      },
      {
        id: 'video-shooting-editing',
        name: 'Видеосъемка и монтаж',
        subcategories: [
          { id: 'video-shooting', name: 'Видеосъемка' },
          { id: 'video-editing', name: 'Монтаж и обработка видео' },
          { id: 'photo-shooting', name: 'Фотосъемка' }
        ]
      },
      {
        id: 'intro-logo-animation',
        name: 'Интро и анимация логотипа',
        subcategories: [
          { id: 'logo-animation', name: 'Анимация логотипа' },
          { id: 'intro-screens', name: 'Интро и заставки' },
          { id: 'gif-animation', name: 'GIF-анимация' }
        ]
      },
      {
        id: 'audio-editing',
        name: 'Редактирование аудио',
        subcategories: [
          { id: 'sound-processing', name: 'Обработка звука' },
          { id: 'sound-extraction', name: 'Выделение звука из видео' }
        ]
      },
      {
        id: 'video-clips',
        name: 'Видеоролики',
        subcategories: [
          { id: 'doodle-video', name: 'Дудл-видео' },
          { id: 'animated-clip', name: 'Анимационный ролик' },
          { id: 'promo-clip', name: 'Проморолик' },
          { id: 'screencasts-reviews', name: 'Скринкасты и видеообзоры' },
          { id: 'kinetic-typography', name: 'Кинетическая типографика' },
          { id: 'slideshow', name: 'Слайд-шоу' },
          { id: 'video-with-host', name: 'Видео с ведущим' },
          { id: 'video-presentation', name: 'Видеопрезентация' },
          { id: 'social-videos', name: 'Ролики для соцсетей' }
        ]
      },
      {
        id: 'ai-video-generation',
        name: 'ИИ-генерация видео',
        subcategories: []
      },
      {
        id: 'music-songs',
        name: 'Музыка и песни',
        subcategories: [
          { id: 'music-composition', name: 'Написание музыки' },
          { id: 'vocal-recording', name: 'Запись вокала' },
          { id: 'arrangement', name: 'Аранжировка' },
          { id: 'song-texts', name: 'Тексты песен' },
          { id: 'full-song', name: 'Песня (музыка + текст + вокал)' }
        ]
      }
    ]
  },
  {
    id: 'business-life',
    name: 'Бизнес и жизнь',
    subcategories: [
      {
        id: 'accounting-taxes',
        name: 'Бухгалтерия и налоги',
        subcategories: [
          { id: 'for-individuals', name: 'Для физлиц' },
          { id: 'for-entities-ip', name: 'Для юрлиц и ИП' }
        ]
      },
      {
        id: 'education-consulting',
        name: 'Обучение и консалтинг',
        subcategories: [
          { id: 'online-courses', name: 'Онлайн курсы' },
          { id: 'consulting', name: 'Консалтинг' },
          { id: 'gost-formatting', name: 'Оформление по ГОСТу' },
          { id: 'tutors', name: 'Репетиторы' }
        ]
      },
      {
        id: 'personnel-selection',
        name: 'Подбор персонала',
        subcategories: [
          { id: 'resume-selection', name: 'Подбор резюме' },
          { id: 'specialist-hiring', name: 'Найм специалиста' }
        ]
      },
      {
        id: 'construction-repair',
        name: 'Стройка и ремонт',
        subcategories: [
          { id: 'construction', name: 'Строительство' },
          { id: 'object-design', name: 'Проектирование объекта' },
          { id: 'mechanical-engineering', name: 'Машиностроение' },
          { id: 'items-accessories', name: 'Предметы и аксессуары' }
        ]
      },
      {
        id: 'calls-sales',
        name: 'Обзвоны и продажи',
        subcategories: [
          { id: 'phone-sales', name: 'Продажи по телефону' },
          { id: 'phone-survey', name: 'Телефонный опрос' },
          { id: 'call-reception', name: 'Прием звонков' }
        ]
      },
      {
        id: 'personal-assistant',
        name: 'Персональный помощник',
        subcategories: [
          { id: 'information-search', name: 'Поиск информации' },
          { id: 'ms-office-work', name: 'Работа в MS Office' },
          { id: 'information-analysis', name: 'Анализ информации' },
          { id: 'intellectual-work', name: 'Любая интеллектуальная работа' },
          { id: 'routine-work', name: 'Любая рутинная работа' },
          { id: 'project-management', name: 'Менеджмент проектов' }
        ]
      },
      {
        id: 'site-group-sales',
        name: 'Продажа сайтов и групп',
        subcategories: [
          { id: 'site-without-domain', name: 'Сайт без домена' },
          { id: 'site-with-domain', name: 'Сайт с доменом' },
          { id: 'applications', name: 'Приложения' },
          { id: 'audit-evaluation-help', name: 'Аудит, оценка, помощь' },
          { id: 'domains', name: 'Домены' },
          { id: 'social-groups-channels', name: 'Группы и каналы соцсетей' }
        ]
      },
      {
        id: 'legal-help',
        name: 'Юридическая помощь',
        subcategories: [
          { id: 'contract-power-of-attorney', name: 'Договор и доверенность' },
          { id: 'court-document', name: 'Судебный документ' },
          { id: 'legal-consultation', name: 'Юридическая консультация' },
          { id: 'oo-ip-management', name: 'Ведение ООО и ИП' },
          { id: 'internet-law', name: 'Интернет-право' },
          { id: 'visas', name: 'Визы' }
        ]
      }
    ]
  },
  {
    id: 'design',
    name: 'Дизайн',
    subcategories: [
      {
        id: 'art-illustrations',
        name: 'Арт и иллюстрации',
        subcategories: [
          { id: 'illustrations-drawings', name: 'Иллюстрации и рисунки' },
          { id: 'tattoo-prints', name: 'Тату, принты' },
          { id: 'game-design', name: 'Дизайн игр' },
          { id: 'templates-drawings', name: 'Готовые шаблоны и рисунки' },
          { id: 'portrait-caricature', name: 'Портрет, шарж, карикатура' },
          { id: 'stickers', name: 'Стикеры' },
          { id: 'nft-art', name: 'NFT арт' }
        ]
      },
      {
        id: 'ai-image-generation',
        name: 'ИИ-генерация изображений',
        subcategories: [
          { id: 'ai-photosession', name: 'Нейрофотосессия' },
          { id: 'ai-avatars-portraits', name: 'ИИ-аватары и портреты' },
          { id: 'ai-illustrations-concept', name: 'ИИ-иллюстрации и концепт-арт' },
          { id: 'ai-logos-infographics', name: 'ИИ-логотипы и инфографика' }
        ]
      },
      {
        id: 'logo-branding',
        name: 'Логотип и брендинг',
        subcategories: [
          { id: 'logos', name: 'Логотипы' },
          { id: 'corporate-identity', name: 'Фирменный стиль' },
          { id: 'branding-souvenirs', name: 'Брендирование и сувенирка' },
          { id: 'business-cards', name: 'Визитки' }
        ]
      },
      {
        id: 'outdoor-advertising',
        name: 'Наружная реклама',
        subcategories: [
          { id: 'billboards-stands', name: 'Билборды и стенды' },
          { id: 'windows-signs', name: 'Витрины и вывески' }
        ]
      },
      {
        id: 'print',
        name: 'Полиграфия',
        subcategories: [
          { id: 'brochure-booklet', name: 'Брошюра и буклет' },
          { id: 'leaflet-flyer', name: 'Листовка и флаер' },
          { id: 'poster-playbill', name: 'Плакат и афиша' },
          { id: 'calendar-postcard', name: 'Календарь и открытка' },
          { id: 'catalog-menu-book', name: 'Каталог, меню, книга' },
          { id: 'diploma-certificate', name: 'Грамота и сертификат' },
          { id: 'guide-checklist', name: 'Гайд и чек-лист' }
        ]
      },
      {
        id: 'industrial-design',
        name: 'Промышленный дизайн',
        subcategories: [
          { id: 'packaging-label', name: 'Упаковка и этикетка' },
          { id: 'electronics-devices', name: 'Электроника и устройства' },
          { id: 'items-accessories-design', name: 'Предметы и аксессуары' }
        ]
      },
      {
        id: 'web-mobile-design',
        name: 'Веб и мобильный дизайн',
        subcategories: [
          { id: 'mobile-design', name: 'Мобильный дизайн' },
          { id: 'email-design', name: 'Email-дизайн' },
          { id: 'web-design', name: 'Веб-дизайн' },
          { id: 'banners-icons', name: 'Баннеры и иконки' }
        ]
      },
      {
        id: 'interior-exterior',
        name: 'Интерьер и экстерьер',
        subcategories: [
          { id: 'interior', name: 'Интерьер' },
          { id: 'houses-structures-design', name: 'Дизайн домов и сооружений' },
          { id: 'landscape-design', name: 'Ландшафтный дизайн' },
          { id: 'furniture-design', name: 'Дизайн мебели' }
        ]
      },
      {
        id: 'marketplaces-social',
        name: 'Маркетплейсы и соцсети',
        subcategories: [
          { id: 'social-design', name: 'Дизайн в соцсетях' },
          { id: 'marketplace-design', name: 'Дизайн для маркетплейсов' }
        ]
      },
      {
        id: 'processing-editing',
        name: 'Обработка и редактирование',
        subcategories: [
          { id: 'vector-drawing', name: 'Отрисовка в векторе' },
          { id: '3d-graphics', name: '3D-графика' },
          { id: 'photo-montage', name: 'Фотомонтаж и обработка' }
        ]
      },
      {
        id: 'presentations-infographics',
        name: 'Презентации и инфографика',
        subcategories: [
          { id: 'presentations', name: 'Презентации' },
          { id: 'infographics', name: 'Инфографика' },
          { id: 'map-scheme', name: 'Карта и схема' }
        ]
      }
    ]
  },
  {
    id: 'development-it',
    name: 'Разработка и IT',
    subcategories: [
      {
        id: 'layout',
        name: 'Верстка',
        subcategories: [
          { id: 'layout-by-mockup', name: 'Верстка по макету' },
          { id: 'layout-refinement', name: 'Доработка и адаптация верстки' }
        ]
      },
      {
        id: 'site-refinement-setting',
        name: 'Доработка и настройка сайта',
        subcategories: [
          { id: 'site-refinement', name: 'Доработка сайта' },
          { id: 'error-fixing', name: 'Исправление ошибок' },
          { id: 'site-protection-treatment', name: 'Защита и лечение сайта' },
          { id: 'site-setting', name: 'Настройка сайта' },
          { id: 'plugins-themes', name: 'Плагины и темы' },
          { id: 'site-acceleration', name: 'Ускорение сайта' }
        ]
      },
      {
        id: 'mobile-apps',
        name: 'Мобильные приложения',
        subcategories: [
          { id: 'ios', name: 'iOS' },
          { id: 'android', name: 'Android' }
        ]
      },
      {
        id: 'scripts-bots-miniapps',
        name: 'Скрипты, боты и mini apps',
        subcategories: [
          { id: 'parsers', name: 'Парсеры' },
          { id: 'chat-bots', name: 'Чат-боты' },
          { id: 'scripts', name: 'Скрипты' },
          { id: 'telegram-miniapps', name: 'Telegram Mini Apps' },
          { id: 'ai-bots', name: 'ИИ-боты' },
          { id: 'machine-learning', name: 'Машинное обучение' }
        ]
      },
      {
        id: 'usability-tests-help',
        name: 'Юзабилити, тесты и помощь',
        subcategories: [
          { id: 'usability-audit', name: 'Юзабилити-аудит' },
          { id: 'error-testing', name: 'Тестирование на ошибки' },
          { id: 'computer-it-help', name: 'Компьютерная и IT помощь' }
        ]
      },
      {
        id: 'desktop-programming',
        name: 'Десктоп программирование',
        subcategories: [
          { id: 'custom-programs', name: 'Программы на заказ' },
          { id: 'office-macros', name: 'Макросы для Office' },
          { id: '1c', name: '1С' },
          { id: 'ready-programs', name: 'Готовые программы' }
        ]
      },
      {
        id: 'games',
        name: 'Игры',
        subcategories: [
          { id: 'game-development', name: 'Разработка игр' },
          { id: 'ready-games', name: 'Готовые игры' },
          { id: 'game-server', name: 'Игровой сервер' }
        ]
      },
      {
        id: 'servers-hosting',
        name: 'Сервера и хостинг',
        subcategories: [
          { id: 'server-administration', name: 'Администрирование сервера' },
          { id: 'domains-hosting', name: 'Домены' },
          { id: 'hosting', name: 'Хостинг' }
        ]
      },
      {
        id: 'site-creation',
        name: 'Создание сайта',
        subcategories: [
          { id: 'new-site', name: 'Новый сайт' },
          { id: 'site-copy', name: 'Копия сайта' }
        ]
      }
    ]
  },
  {
    id: 'social-marketing',
    name: 'Соцсети и маркетинг',
    subcategories: [
      {
        id: 'email-marketing',
        name: 'E-mail маркетинг и рассылки',
        subcategories: [
          { id: 'email-sending', name: 'Отправка рассылки' },
          { id: 'email-client-management', name: 'Ведение и настройка почтового клиента' }
        ]
      },
      {
        id: 'context-ads',
        name: 'Контекстная реклама',
        subcategories: [
          { id: 'yandex-direct', name: 'Яндекс Директ' },
          { id: 'google-ads', name: 'Google Ads' }
        ]
      },
      {
        id: 'marketplaces-boards',
        name: 'Маркетплейсы и доски объявлений',
        subcategories: [
          { id: 'directories-catalogs', name: 'Справочники и каталоги' },
          { id: 'marketplaces', name: 'Маркетплейсы' },
          { id: 'bulletin-boards', name: 'Доски объявлений' }
        ]
      },
      {
        id: 'databases-clients',
        name: 'Базы данных и клиентов',
        subcategories: [
          { id: 'data-collection', name: 'Сбор данных' },
          { id: 'ready-databases', name: 'Готовые базы' },
          { id: 'database-check-cleaning', name: 'Проверка, чистка базы' }
        ]
      },
      {
        id: 'marketing-pr',
        name: 'Маркетинг и PR',
        subcategories: [
          { id: 'content-marketing', name: 'Контент-маркетинг' },
          { id: 'music-promotion', name: 'Продвижение музыки' }
        ]
      },
      {
        id: 'social-smm',
        name: 'Соцсети и SMM',
        subcategories: [
          { id: 'vk', name: 'ВКонтакте' },
          { id: 'youtube', name: 'Youtube' },
          { id: 'ok', name: 'Одноклассники' },
          { id: 'telegram-social', name: 'Telegram' },
          { id: 'other-social', name: 'Другие' },
          { id: 'zen', name: 'Дзен' },
          { id: 'tiktok', name: 'TikTok' },
          { id: 'rutube', name: 'Rutube' }
        ]
      }
    ]
  },
  {
    id: 'texts-translations',
    name: 'Тексты и переводы',
    subcategories: [
      {
        id: 'ai-texts',
        name: 'ИИ-тексты',
        subcategories: [
          { id: 'ai-article-generation', name: 'ИИ-генерация статей' },
          { id: 'ai-text-processing', name: 'ИИ-обработка текстов' }
        ]
      },
      {
        id: 'translations',
        name: 'Переводы',
        subcategories: [
          { id: 'from-audio-video', name: 'С аудио/видео' },
          { id: 'from-text', name: 'С текста' },
          { id: 'from-images', name: 'С изображения' },
          { id: 'oral-translations', name: 'Переводы устные' }
        ]
      },
      {
        id: 'resume-vacancies',
        name: 'Резюме и вакансии',
        subcategories: [
          { id: 'vacancy-text', name: 'Текст вакансии' },
          { id: 'resume-creation', name: 'Составление резюме' },
          { id: 'cover-letters', name: 'Сопроводительные письма' }
        ]
      },
      {
        id: 'text-typing',
        name: 'Набор текста',
        subcategories: [
          { id: 'from-audio-video-typing', name: 'С аудио/видео' },
          { id: 'from-images-typing', name: 'С изображений' }
        ]
      },
      {
        id: 'sales-business-texts',
        name: 'Продающие и бизнес-тексты',
        subcategories: [
          { id: 'sales-texts', name: 'Продающие тексты' },
          { id: 'ad-email', name: 'Реклама и email' },
          { id: 'auto-moto', name: 'Авто и мото' },
          { id: 'work-career', name: 'Работа, карьера' },
          { id: 'legal', name: 'Юридическая' },
          { id: 'medicine-health', name: 'Медицина и здоровье' },
          { id: 'internet-tech', name: 'Интернет и технологии' },
          { id: 'cooking', name: 'Кулинария' },
          { id: 'electronics-gadgets', name: 'Электроника, гаджеты' },
          { id: 'beauty-fashion', name: 'Красота и мода' },
          { id: 'culture-art', name: 'Культура и искусство' },
          { id: 'real-estate', name: 'Недвижимость' },
          { id: 'education-science', name: 'Образование и наука' },
          { id: 'family-children', name: 'Семья, дети' },
          { id: 'rest-entertainment', name: 'Отдых и развлечения' },
          { id: 'sports', name: 'Спорт' },
          { id: 'construction-texts', name: 'Строительство' },
          { id: 'other-texts', name: 'Другое' },
          { id: 'tourism-travel', name: 'Туризм и путешествия' },
          { id: 'finance-banks', name: 'Финансы, банки' },
          { id: 'hobbies', name: 'Хобби и увлечения' },
          { id: 'commercial-proposals', name: 'Коммерческие предложения' },
          { id: 'sales-scripts', name: 'Скрипты продаж и выступлений' },
          { id: 'social-posts', name: 'Посты для соцсетей' }
        ]
      },
      {
        id: 'texts-site-content',
        name: 'Тексты и наполнение сайта',
        subcategories: [
          { id: 'literary-texts', name: 'Художественные тексты' },
          { id: 'scripts', name: 'Сценарии' },
          { id: 'comments', name: 'Комментарии' },
          { id: 'proofreading', name: 'Корректура' },
          { id: 'seo-texts-content', name: 'SEO-тексты' },
          { id: 'product-cards', name: 'Карточки товаров' },
          { id: 'articles', name: 'Статьи' }
        ]
      }
    ]
  }
];
