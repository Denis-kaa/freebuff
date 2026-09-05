# Денис Литвин — profile site

Standalone React/Vite сайт-визитка (AI Engineer × Visual Systems Creator).

## Публичный адрес

```text
http://185.233.184.192:4173/
```

Сервис: `profile-site.service` на сервере `whimco` (root@185.233.184.192).

Каталоги на сервере:

```text
/opt/freebuff/profile-site-src/   исходники и сборка
/opt/freebuff/profile-site/       production-файлы
```

Управление сервисом (на сервере):

```bash
systemctl status profile-site
systemctl restart profile-site
```

Обновление после правок кода: загрузить изменения в `profile-site-src`, выполнить `npm run build`, затем `cp -a dist/. /opt/freebuff/profile-site/`.

## Запуск локально

Из корня репозитория:

```bash
python3 -m http.server 8080 -d projects_17/profile_site
```

Откройте `http://localhost:8080`.

## Состав MVP

- адаптивная одностраничная визитка на русском;
- hero, позиционирование, три featured-кейса и каталог проектов;
- фильтры по направлениям и раскрытие деталей кейсов;
- детерминированное demo-интерактивное окно;
- creative-секция;
- Telegram deep-link форма без серверного хранения данных;
- SEO/Open Graph метаданные.

## Перед публикацией

1. Проверить актуальность публичных контактов и ссылок.
2. Подтвердить формулировки клиентских кейсов.
3. Добавить favicon/OG-image при готовности материалов.
4. Настроить HTTPS, CSP и security headers на VPS.
5. Если понадобится серверная форма, заменить deep-link на backend endpoint без публикации Telegram token.
