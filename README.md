## LawHelp International — Telegram бот + Админка

### Требования
- Python 3.10+
- Telegram Bot Token (BotFather)

### Установка
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
notepad .env  # добавьте переменные ниже
```
`.env`:
```
BOT_TOKEN=xxxxxxxx:yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
ADMIN_PASSWORD=admin
```

### Запуск
- Единый запуск (бот + админка):
```powershell
python -m src.run_all
```
- Админка доступна на: http://192.168.1.59:8001/ (локальная сеть)
- Бот запускается в том же процессе (aiogram polling)

Альтернативно по отдельности:
```powershell
python -m src.main
uvicorn src.admin.app:app --reload  # http://127.0.0.1:8000/
```

### Структура
- `src/main.py` — Telegram-бот (aiogram)
- `src/admin/app.py` — админка (FastAPI + Jinja2)
- `src/run_all.py` — общий запуск
- `templates/` — шаблоны админки (`base`, `login`, `admin_home`)
- `data/terms.json`, `data/tips.json`, `data/documents.json` — контент
- `data/cards/` — карточки для «Кодекса мнемоники» и `index.json`

### Админка
- Вход: `admin / ADMIN_PASSWORD`
- CRUD: Термины, Советы, Документы, Карточки (загрузка изображений и подписи)
- Логи действий: `data/admin/audit.jsonl`

### Git ignore (важно)
- `.env`, виртуальное окружение, `__pycache__`, логи
- `data/admin/*` (пользователи и журнал действий)
- одноразовые скрипты и временные файлы

### Примечания
- Если порт 8001 занят — измените `src/run_all.py` (host/port) или освободите порт в фаерволе.
- Для доступа из сети используется `192.168.1.59:8001` — при смене IP обновите `run_all.py`.
