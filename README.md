# Питер-Свет — сайт электромонтажа (питер-свет.рф)

Чистый HTML, CSS и JS, без конструкторов и фреймворков. Форма заявок на PHP отправляет заявки в Telegram.
Каждое изменение в ветке `main` само выгружается на хостинг Reg.ru через GitHub Actions.

## Структура

```
index.html                      главная
blog/index.html                 список статей (собирается автоматически)
blog/<адрес>/index.html         статьи
privacy/index.html              политика обработки персональных данных
404.html                        страница «не найдено»
api/lead.php                    приём заявок → Telegram (+ копия в api/data/leads.csv)
assets/css/style.css            все стили, шрифты Inter и Manrope лежат локально
assets/js/main.js               кабель между плитками, калькулятор, форма, Метрика
tools/build.py                  пересобирает список статей и sitemap.xml
.github/workflows/deploy.yml    автодеплой по FTP
.htaccess, robots.txt, sitemap.xml
```

## Настройка автодеплоя (один раз)

1. Создать репозиторий на GitHub и загрузить в него эти файлы (ветка `main`).
2. В репозитории открыть **Settings → Secrets and variables → Actions → New repository secret** и добавить:

| Секрет | Что вписать |
|---|---|
| `FTP_SERVER` | адрес FTP-сервера из письма Reg.ru о хостинге (например, `server123.hosting.reg.ru`) |
| `FTP_USERNAME` | логин FTP |
| `FTP_PASSWORD` | пароль FTP |
| `FTP_DIR` | папка сайта на хостинге с `/` в конце — смотрите в ispmanager → «Сайты» (обычно `www/питер-свет.рф/`) |
| `TG_BOT_TOKEN` | токен Telegram-бота от @BotFather |
| `TG_CHAT_ID` | ваш chat id (бот @userinfobot покажет его) |
| `MAIL_TO` | необязательно: почта для копии заявок |

3. Открыть вкладку **Actions** → «Deploy to Reg.ru» → **Run workflow**. Через минуту сайт на хостинге.

Секреты хранятся в GitHub в зашифрованном виде и не попадают в код.

## Как добавить статью

1. Скопировать папку `blog/zamena-provodki-v-kvartire/` под новым адресом латиницей.
2. Поменять в `<head>`: `<title>`, `description`, `article:published`, `article:excerpt`, `canonical`, `og:*`, JSON-LD.
3. Написать текст внутри `<article>`.
4. Сделать commit в `main` — список статей и sitemap пересоберутся и выгрузятся сами.

Проверить локально: `python3 tools/build.py`

## Что заполнить

- **Политика конфиденциальности**: в `privacy/index.html` заменить `{{ОПЕРАТОР}}` на ФИО или ИП.
- **Яндекс.Метрика**: в `assets/js/main.js` вписать номер счётчика в `metrikaId`. Цели: `lead` (заявка), `call` (клик по телефону), `calc_to_form` (переход из калькулятора).
- **Цены калькулятора**: `pricePerM2`, `typeK`, `scopeK` в начале `assets/js/main.js`.
- **Фото работ**: положить в `assets/img/works/` и раскомментировать блок «Портфолио» в `index.html`.
- **Старые адреса с Тильды**: если в поиске были другие страницы, добавить 301-редиректы в `.htaccess`.

## После запуска

- Яндекс.Вебмастер: добавить сайт, подтвердить права, указать `sitemap.xml`, регион — Санкт-Петербург.
- Яндекс.Бизнес: карточка организации со ссылкой на сайт.
