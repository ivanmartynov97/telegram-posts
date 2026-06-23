# 📱 Telegram Channel Mini App

Менеджер контента для Telegram-канала — работает прямо внутри Telegram как Mini App. Хранит очередь постов в GitHub, генерирует тексты через Groq AI, ищет исторические фото через Wikimedia Commons.

Изначально создан для канала [@history_plus_facts](https://t.me/history_plus_facts) — но легко адаптируется под любой канал.

---

## ✨ Возможности

**Управление очередью**
- Список всех постов с превью, тегами и кнопками быстрого действия
- Календарный вид — посты по дням и часам публикации
- Добавление поста вручную с текстом, картинкой, кнопками и расписанием
- Удаление поста — автозамена из резерва

**AI-генерация контента**
- Вкладка «Идеи» — вводишь тему, AI пишет 1–3 поста на основе Wikipedia
- Специальный режим «фото модели 80-х» — ищет фото из Wikimedia Commons по десятилетию
- Обновление поста кнопкой 🔄 — меняет и текст, и картинку
- Генерация 5 постов сразу в свободные слоты

**Форматы контента (автоматический микс)**
- 60% — исторические факты (Wikipedia → Groq)
- 20% — фото + короткая подпись
- 10% — ретро-красавицы (19 век — 1990-е)
- 10% — старинные объекты/изобретения с фото

**Аналитика**
- Просмотры, реакции, комментарии по каждому посту
- Ранняя вовлечённость: views за первые 15 минут / 1000 подписчиков
- История подписчиков по дням
- Лучшие темы по early engagement rate

**Автоматизация (Python + launchd)**
- Автопостинг через Bot API по расписанию
- Сбор просмотров через Telethon (MTProto)
- Сбор реакций и комментариев
- Мониторинг очереди — уведомление если мало постов

---

## 🛠 Стек технологий

| Компонент | Технология |
|---|---|
| Frontend | Vanilla JS, HTML/CSS — один файл `index.html` |
| Хостинг | GitHub Pages (бесплатно) |
| Хранилище данных | GitHub Contents API — JSON файлы в репозитории |
| AI текст | [Groq API](https://console.groq.com) — llama-3.3-70b-versatile |
| Фото | Wikimedia Commons API, Wikipedia API |
| Telegram | Bot API + Telethon (MTProto) |
| Автоматизация | Python 3 + macOS launchd |

---

## ⚙️ Установка с нуля

### 1. Создай свой GitHub репозиторий

```bash
git clone https://github.com/ТВОЙ_ЛОГИН/ТВОЙ_РЕПО.git
cd ТВОЙ_РЕПО
```

Создай папки:
```bash
mkdir queue analytics reserve
echo '[]' > analytics/.gitkeep
```

### 2. Включи GitHub Pages

Настройки репозитория → Pages → Source: **Deploy from branch `main`**, папка **`/ (root)`**.

Через 1–2 минуты твой мини апп будет доступен по адресу:
`https://ТВОЙ_ЛОГИН.github.io/ТВОЙ_РЕПО/`

### 3. Получи Groq API ключ

Зайди на [console.groq.com](https://console.groq.com) → Create API Key. Бесплатный тариф даёт ~14k запросов в день.

### 4. Создай Telegram бота

1. Напиши [@BotFather](https://t.me/BotFather) → `/newbot`
2. Получи токен вида `1234567890:AAAA...`
3. Добавь бота администратором в свой канал

Чтобы использовать Mini App:
1. BotFather → `/newapp` → укажи URL своего GitHub Pages
2. Или просто открывай `index.html` как обычный веб-сайт — без Telegram тоже работает

### 5. Получи Telegram API credentials

1. Зайди на [my.telegram.org](https://my.telegram.org)
2. Войди своим номером телефона
3. API Development Tools → Create new application
4. Получишь `api_id` (число) и `api_hash` (строка)

Нужно для Telethon — сбор просмотров, реакций, ранняя аналитика.

### 6. Создай config.json

```json
{
  "bot_token": "123456789:AAAA...",
  "channel_id": "@твой_канал",
  "github_token": "github_pat_...",
  "admin_chat_id": "ВАШ_TELEGRAM_ID",
  "api_id": 1234567,
  "api_hash": "abcdef1234567890abcdef1234567890"
}
```

> ⚠️ **Важно**: добавь `config.json` в `.gitignore` — никогда не коммить токены в публичный репозиторий.

Твой Telegram ID: напиши [@userinfobot](https://t.me/userinfobot).

GitHub токен: Settings → Developer settings → Personal access tokens → Classic → scope `repo`.

### 7. Настрой index.html

Открой `index.html` и замени две строки в начале JS-кода:

```javascript
const REPO = "ТВОЙ_ЛОГИН/ТВОЙ_РЕПО";  // GitHub репозиторий
```

И в настройках мини апп укажи Groq ключ (вкладка ⚙️ AI).

### 8. Авторизуй Telethon (один раз)

```bash
pip3 install telethon
python3 setup_telethon.py
```

Введи номер телефона и код из Telegram. Создастся файл `tg_user_session.session` — не удалять.

### 9. Установи автоматизацию (macOS launchd)

Скопируй `.plist` файлы в LaunchAgents и загрузи:

```bash
cp com.ivan.*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ivan.fetch-views.plist
launchctl load ~/Library/LaunchAgents/com.ivan.early-performance.plist
launchctl load ~/Library/LaunchAgents/com.ivan.fetch-reactions.plist
launchctl load ~/Library/LaunchAgents/com.ivan.check-queue.plist
```

---

## 📁 Структура файлов

```
├── index.html              # Весь мини апп — один файл
├── config.json             # Токены и ключи (в .gitignore!)
├── queue/                  # Очередь постов
│   ├── 001.json            # Посты без расписания
│   └── slot-2026-07-02T18.json  # Посты с расписанием
├── analytics/              # Статистика постов
│   ├── {message_id}.json   # Данные по каждому посту
│   ├── topic_performance.json   # Агрегат по темам
│   └── subscriber_history.json  # История подписчиков
├── queue/reserve/          # Резервные посты (используются при удалении)
│
├── auto_publish.py         # Постинг по расписанию через Bot API
├── fetch_views.py          # Сбор просмотров через Telethon
├── fetch_reactions.py      # Сбор реакций через Bot API
├── early_performance.py    # Анализ охватов за первые 15 минут ⭐
├── check_queue.py          # Уведомление если очередь пустеет
├── setup_telethon.py       # Авторизация Telethon (один раз)
│
└── com.ivan.*.plist        # launchd конфиги для автозапуска
```

---

## 📦 Формат поста в очереди

```json
{
  "text": "Текст поста с эмодзи...",
  "image_url": "https://upload.wikimedia.org/...",
  "scheduled_at": "2026-07-04T18:00:00+03:00",
  "ai_generated": true,
  "ai_topic": "Первый самолёт",
  "ai_keywords": ["Братья Райт", "1903", "Китти-Хок"],
  "wiki_title": "Wright Flyer",
  "created_at": "2026-07-02T14:30:00+03:00"
}
```

---

## 🔄 Расписание публикаций

По умолчанию 6 постов в день (московское время +3):

```javascript
const HOURS = [7, 11, 13, 16, 18, 22];
```

Измени в `index.html` под свой часовой пояс и частоту.

---

## 🤖 AI настройка

**Groq модель**: `llama-3.3-70b-versatile` (бесплатно, быстро)

**Форматы контента** — соотношение меняется в `getPostFormat()`:
- `regular` (60%) — исторические факты
- `photo_caption` (20%) — фото + подпись
- `retro_beauty` (10%) — ретро фото красавиц
- `vintage_object` (10%) — старинные объекты

**Источники фото** (цепочка поиска):
1. Wikipedia thumbnail (ru → en)
2. Wikimedia Commons текстовый поиск
3. Wikimedia Commons категория

---

## 📊 Early Performance — как работает

Скрипт `early_performance.py` запускается каждые 5 минут. Когда находит пост опубликованный 10–25 минут назад:

1. Считывает текущие просмотры и реакции
2. Рассчитывает `early_rate = views / subscribers × 1000`
3. Сохраняет в `analytics/{id}.json`
4. Обновляет `analytics/topic_performance.json` — агрегат лучших тем

В мини аппе вкладка Аналитика показывает темы отсортированные по early_rate — сразу видно какой контент заходит аудитории в первые минуты.

---

## 🔒 Безопасность

- `config.json` → в `.gitignore` (токены никогда не в репо)
- `*.session` → в `.gitignore` (файл сессии Telethon)
- GitHub token → минимальный scope `repo`
- Groq ключ хранится в `localStorage` браузера, не в коде

---

## 🙋 Адаптация под свой канал

Минимальные изменения в `index.html`:

| Что менять | Где |
|---|---|
| `const REPO` | ~строка 5 в JS |
| `const HOURS` | расписание публикаций |
| `RETRO_BEAUTY_NAMES` | список имён для ретро-постов |
| `VINTAGE_FIRSTS` | список изобретений/объектов |
| Системный промпт AI | функция `groqGenerate()` |

---

## 📄 Лицензия

MIT — используй, форкай, адаптируй.
