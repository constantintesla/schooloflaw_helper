from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import os
import time
from passlib.context import CryptContext
from ..config import DATA_DIR

app = FastAPI(title="LawHelp Admin")

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ADMIN_DIR = DATA_DIR / "admin"
ADMIN_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = ADMIN_DIR / "users.json"
AUDIT_FILE = ADMIN_DIR / "audit.jsonl"

# Используем pbkdf2_sha256 для совместимости на Windows
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin")


def read_json(path: Path):
	if not path.exists():
		return [] if path.suffix == ".json" else {}
	return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
	path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# Простой middleware-pass-through (без сессий)
@app.middleware("http")
async def passthrough(request: Request, call_next):
	response = await call_next(request)
	return response


def ensure_admin_user():
	users = read_json(USERS_FILE)
	if not users:
		users = []
		users.append({
			"username": "admin",
			"password_hash": pwd_ctx.hash(DEFAULT_ADMIN_PASS),
			"role": "admin"
		})
		write_json(USERS_FILE, users)
	return users


def get_users():
	return ensure_admin_user()


def find_user(username: str):
	for u in get_users():
		if u["username"] == username:
			return u
	return None


def save_users(users):
	write_json(USERS_FILE, users)


def append_audit(actor: str, action: str, details: dict):
	entry = {"ts": int(time.time()), "actor": actor, "action": action, "details": details}
	with AUDIT_FILE.open("a", encoding="utf-8") as f:
		f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def current_user(request: Request) -> dict | None:
	username = request.cookies.get("lh_admin_user")
	if not username:
		return None
	u = find_user(username)
	return u


def require_auth(request: Request):
	u = current_user(request)
	if not u:
		raise HTTPException(status_code=401)
	return u


def require_admin(user: dict):
	if user.get("role") != "admin":
		raise HTTPException(status_code=403, detail="Admin only")


# Логин теперь на корневом URL
@app.get("/", response_class=HTMLResponse)
async def login_form(request: Request):
	return templates.TemplateResponse("login.html", {"request": request})


@app.post("/")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
	users = get_users()
	u = find_user(username)
	if not u or not pwd_ctx.verify(password, u["password_hash"]):
		return templates.TemplateResponse("login.html", {"request": request, "error": "Неверные логин или пароль"}, status_code=401)
	resp = RedirectResponse(url="/admin", status_code=303)
	resp.set_cookie("lh_admin_user", u["username"], httponly=True, samesite="lax")
	append_audit(u["username"], "login", {})
	return resp


# Совместимость со старым путём
@app.get("/admin/login")
async def old_login_redirect():
	return RedirectResponse(url="/", status_code=307)


@app.post("/admin/login")
async def old_login_post_redirect():
	return RedirectResponse(url="/", status_code=307)


@app.get("/admin/logout")
async def logout(request: Request):
	resp = RedirectResponse(url="/", status_code=303)
	resp.delete_cookie("lh_admin_user")
	return resp


@app.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request, user: dict = Depends(require_auth)):
	terms = read_json(DATA_DIR / "terms.json")
	tips = read_json(DATA_DIR / "tips.json")
	docs = read_json(DATA_DIR / "documents.json")
	cards = read_json(DATA_DIR / "cards" / "index.json")
	logs = []
	if AUDIT_FILE.exists():
		with AUDIT_FILE.open("r", encoding="utf-8") as f:
			for line in f.readlines()[-100:]:
				try:
					logs.append(json.loads(line))
				except Exception:
					pass
	return templates.TemplateResponse("admin_home.html", {"request": request, "user": user, "terms": terms, "tips": tips, "docs": docs, "cards": cards, "logs": logs})


@app.post("/admin/users/create")
async def users_create(user: dict = Depends(require_auth), username: str = Form(...), password: str = Form(...), role: str = Form("editor")):
	require_admin(user)
	users = get_users()
	if find_user(username):
		raise HTTPException(400, detail="User exists")
	users.append({"username": username, "password_hash": pwd_ctx.hash(password), "role": role})
	save_users(users)
	append_audit(user["username"], "user_create", {"username": username, "role": role})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/users/delete/{username}")
async def users_delete(username: str, user: dict = Depends(require_auth)):
	require_admin(user)
	users = get_users()
	users = [u for u in users if u["username"] != username]
	save_users(users)
	append_audit(user["username"], "user_delete", {"username": username})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/users/password/{username}")
async def users_password(username: str, user: dict = Depends(require_auth), password: str = Form(...)):
	require_admin(user)
	users = get_users()
	for u in users:
		if u["username"] == username:
			u["password_hash"] = pwd_ctx.hash(password)
			save_users(users)
			append_audit(user["username"], "user_password", {"username": username})
			break
	return RedirectResponse(url="/admin", status_code=303)


# ----- TERMS CRUD -----
@app.post("/admin/terms/create")
async def terms_create(user: dict = Depends(require_auth), ru: str = Form(...), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	terms = read_json(DATA_DIR / "terms.json")
	terms.append({"ru": ru, "en": en, "zh": zh, "ko": ko})
	write_json(DATA_DIR / "terms.json", terms)
	append_audit(user["username"], "terms_create", {"ru": ru})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/terms/update/{idx}")
async def terms_update(idx: int, user: dict = Depends(require_auth), ru: str = Form(...), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	terms = read_json(DATA_DIR / "terms.json")
	if idx < 0 or idx >= len(terms):
		raise HTTPException(404)
	terms[idx] = {"ru": ru, "en": en, "zh": zh, "ko": ko}
	write_json(DATA_DIR / "terms.json", terms)
	append_audit(user["username"], "terms_update", {"idx": idx, "ru": ru})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/terms/delete/{idx}")
async def terms_delete(idx: int, user: dict = Depends(require_auth)):
	terms = read_json(DATA_DIR / "terms.json")
	if idx < 0 or idx >= len(terms):
		raise HTTPException(404)
	deleted = terms[idx]
	del terms[idx]
	write_json(DATA_DIR / "terms.json", terms)
	append_audit(user["username"], "terms_delete", {"idx": idx, "ru": deleted.get("ru")})
	return RedirectResponse(url="/admin", status_code=303)


# ----- TIPS CRUD -----
@app.post("/admin/tips/create")
async def tips_create(user: dict = Depends(require_auth), ru: str = Form(...), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	tips = read_json(DATA_DIR / "tips.json")
	tips.append({"ru": ru, "en": en, "zh": zh, "ko": ko})
	write_json(DATA_DIR / "tips.json", tips)
	append_audit(user["username"], "tips_create", {"ru": ru})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/tips/update/{idx}")
async def tips_update(idx: int, user: dict = Depends(require_auth), ru: str = Form(...), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	tips = read_json(DATA_DIR / "tips.json")
	if idx < 0 or idx >= len(tips):
		raise HTTPException(404)
	tips[idx] = {"ru": ru, "en": en, "zh": zh, "ko": ko}
	write_json(DATA_DIR / "tips.json", tips)
	append_audit(user["username"], "tips_update", {"idx": idx, "ru": ru})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/tips/delete/{idx}")
async def tips_delete(idx: int, user: dict = Depends(require_auth)):
	tips = read_json(DATA_DIR / "tips.json")
	if idx < 0 or idx >= len(tips):
		raise HTTPException(404)
	deleted = tips[idx]
	del tips[idx]
	write_json(DATA_DIR / "tips.json", tips)
	append_audit(user["username"], "tips_delete", {"idx": idx, "ru": deleted.get("ru")})
	return RedirectResponse(url="/admin", status_code=303)


# ----- DOCS CRUD -----
@app.post("/admin/docs/create")
async def docs_create(user: dict = Depends(require_auth), ru: str = Form(...), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	docs = read_json(DATA_DIR / "documents.json")
	docs.append({"ru": ru, "en": en, "zh": zh, "ko": ko})
	write_json(DATA_DIR / "documents.json", docs)
	append_audit(user["username"], "docs_create", {"ru": ru})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/docs/update/{idx}")
async def docs_update(idx: int, user: dict = Depends(require_auth), ru: str = Form(...), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	docs = read_json(DATA_DIR / "documents.json")
	if idx < 0 or idx >= len(docs):
		raise HTTPException(404)
	docs[idx] = {"ru": ru, "en": en, "zh": zh, "ko": ko}
	write_json(DATA_DIR / "documents.json", docs)
	append_audit(user["username"], "docs_update", {"idx": idx, "ru": ru})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/docs/delete/{idx}")
async def docs_delete(idx: int, user: dict = Depends(require_auth)):
	docs = read_json(DATA_DIR / "documents.json")
	if idx < 0 or idx >= len(docs):
		raise HTTPException(404)
	deleted = docs[idx]
	del docs[idx]
	write_json(DATA_DIR / "documents.json", docs)
	append_audit(user["username"], "docs_delete", {"idx": idx, "ru": deleted.get("ru")})
	return RedirectResponse(url="/admin", status_code=303)


# ----- CARDS CRUD -----
CARDS_DIR = DATA_DIR / "cards"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/admin/cards/upload")
async def cards_upload(user: dict = Depends(require_auth), file: UploadFile = File(...)):
	content = await file.read()
	dest = CARDS_DIR / file.filename
	dest.write_bytes(content)
	index = read_json(CARDS_DIR / "index.json")
	index.append({"file": file.filename, "ru": "", "en": "", "zh": "", "ko": ""})
	write_json(CARDS_DIR / "index.json", index)
	append_audit(user["username"], "cards_upload", {"file": file.filename})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/cards/update/{idx}")
async def cards_update(idx: int, user: dict = Depends(require_auth), ru: str = Form(""), en: str = Form(""), zh: str = Form(""), ko: str = Form("")):
	index = read_json(CARDS_DIR / "index.json")
	if idx < 0 or idx >= len(index):
		raise HTTPException(404)
	item = index[idx]
	item.update({"ru": ru, "en": en, "zh": zh, "ko": ko})
	write_json(CARDS_DIR / "index.json", index)
	append_audit(user["username"], "cards_update", {"idx": idx, "file": item.get("file")})
	return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/cards/delete/{idx}")
async def cards_delete(idx: int, user: dict = Depends(require_auth)):
	index = read_json(CARDS_DIR / "index.json")
	if idx < 0 or idx >= len(index):
		raise HTTPException(404)
	fname = index[idx]["file"]
	p = CARDS_DIR / fname
	if p.exists():
		p.unlink()
	deleted = index[idx]
	del index[idx]
	write_json(CARDS_DIR / "index.json", index)
	append_audit(user["username"], "cards_delete", {"idx": idx, "file": deleted.get("file")})
	return RedirectResponse(url="/admin", status_code=303)
