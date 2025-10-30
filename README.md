## LawHelp International — Telegram бот + Админка

### Требования
- Python 3.10+ или Docker / Docker Compose
- Telegram Bot Token (BotFather)

### Установка (без Docker)
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

### Запуск (без Docker)
Единый запуск (бот + админка):
```powershell
python -m src.run_all
```
- Админка слушает на 0.0.0.0:8001 → http://<ВАШ_IP>:8001/

### Запуск в Docker
Собрать и запустить:
```bash
docker compose up --build -d
```
- Контейнер: `schooloflaw_helper`
- Порт: 8001 (проброшен на хост)
- Окружение: из `.env` (BOT_TOKEN, ADMIN_PASSWORD)
- Данные: `./data` монтируются внутрь контейнера `/app/data`

Остановить:
```bash
docker compose down
```

### Структура
- `src/main.py` — Telegram-бот (aiogram)
- `src/admin/app.py` — админка (FastAPI + Jinja2)
- `src/run_all.py` — общий запуск (бот + админка на 0.0.0.0:8001)
- `templates/` — шаблоны админки (`base`, `login`, `admin_home`)
- `data/*.json` — контент (термины, советы, документы)
- `data/cards/` — карточки и `index.json`

### Примечания
- Если 8001 занят — измените порт в `docker-compose.yml` и/или `src/run_all.py`.
- Для внешнего доступа используйте адрес хоста: `http://<IP_ХОСТА>:8001/`.
