# Деплой на VPS

## Локальная проверка

```bash
cd projects_17/profile_site
npm install
npm run build
npm run preview
```

Production-файлы будут в `dist/`.

## Nginx пример

```nginx
server {
    listen 80;
    server_name _;
    root /var/www/profile-site/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    ***REMOVED***

    location ~* \.(js|css|png|jpg|jpeg|webp|svg|woff2)$ {
        add_header Cache-Control "public, max-age=604800, immutable";
    ***REMOVED***

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header Referrer-Policy strict-origin-when-cross-origin;
***REMOVED***
```

## Текущий отдельный порт

Сайт развернут без изменения default Nginx-сайта и доступен по адресу:

```text
http://185.233.184.192:4173/
```

Сервис `profile-site.service` слушает `0.0.0.0:4173`.

## Sync do design_manifest.yaml (anti-slop)

O arquivo `design_manifest.yaml` é a fonte da verdade do anti-slop e deve
ir JUNTO ao deploy — sem ele, um `anti-slop audit` no servidor cai para
o modo "sem manifest" e perde os overrides documentados.

```bash
# Enviar o manifest junto com o dist
scp projects_17/profile_site/design_manifest.yaml \
    whimco:/opt/freebuff/profile-site/design_manifest.yaml

# Conferir no servidor (o audit lê o manifest do mesmo diretório do site)
ssh whimco "anti-slop audit /opt/freebuff/profile-site"
```

Regra: se o `design_manifest.yaml` mudar no repositório, atualizar a cópia
no servidor no MESMO deploy. Manifest e dist/ andam sempre juntos.

## Безопасный порядок

1. Подтвердить IP/hostname и каталог именно этого сайта.
2. Сделать backup текущего каталога.
3. Собрать `dist` локально.
4. Передать только содержимое `dist/` + `design_manifest.yaml` (anti-slop) в отдельный каталог сайта.
5. Проверить HTTP-ответ и основные маршруты.
6. Только после проверки переключить Nginx.

Не выполнять `rm`, замену production-каталога или reload Nginx автоматически. SSH-ключи, Telegram token и другие секреты не должны попадать в репозиторий.
