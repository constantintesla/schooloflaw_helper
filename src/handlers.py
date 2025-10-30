import json
from pathlib import Path
from typing import Dict, List, Tuple

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

from .config import DATA_DIR
from .keyboards import language_keyboard, main_menu_keyboard, nav_keyboard
from .i18n import UI


# Память на процесс: user_id -> (lang, section, index)
USER_STATE: Dict[int, Dict[str, object]] = {}


def read_json(path: Path):
	if not path.exists():
		return []
	with path.open("r", encoding="utf-8") as f:
		return json.load(f)


def load_datasets() -> Tuple[List[dict], List[dict], List[dict]]:
	terms = read_json(DATA_DIR / "terms.json")
	tips = read_json(DATA_DIR / "tips.json")
	docs = read_json(DATA_DIR / "documents.json")
	return terms, tips, docs


def load_mnemo() -> List[dict]:
	return read_json(DATA_DIR / "cards" / "index.json")


def format_term(item: dict, lang: str) -> str:
	return f"<b>{item.get(lang, '')}</b>"


def format_tip(item: dict, lang: str) -> str:
	return item.get(lang, "")


def format_doc(item: dict, lang: str) -> str:
	return f"<b>{item.get(lang, '')}</b>"


def build_router() -> Router:
	router = Router()

	@router.message(CommandStart())
	async def cmd_start(message: Message) -> None:
		USER_STATE[message.from_user.id] = {"lang": "ru", "section": None, "index": 0}
		await message.answer(UI["start"]["ru"], reply_markup=language_keyboard())

	@router.callback_query(F.data.startswith("lang:"))
	async def set_lang(callback: CallbackQuery) -> None:
		lang = callback.data.split(":", 1)[1]
		st = USER_STATE.setdefault(callback.from_user.id, {"lang": "ru", "section": None, "index": 0})
		st["lang"] = lang
		await callback.message.edit_text(
			UI["menu_prompt"].get(lang, UI["menu_prompt"]["ru"]),
			reply_markup=main_menu_keyboard(lang),
		)
		await callback.answer()

	@router.callback_query(F.data == "menu:lang")
	async def choose_lang(callback: CallbackQuery) -> None:
		await callback.message.edit_text(UI["start"]["ru"], reply_markup=language_keyboard())
		await callback.answer()

	@router.callback_query(F.data.startswith("menu:"))
	async def open_section(callback: CallbackQuery) -> None:
		section = callback.data.split(":", 1)[1]
		st = USER_STATE.setdefault(callback.from_user.id, {"lang": "ru", "section": None, "index": 0})
		st["section"] = section
		st["index"] = 0
		await show_current(callback)

	@router.callback_query(F.data == "nav:menu")
	async def go_menu(callback: CallbackQuery) -> None:
		st = USER_STATE.setdefault(callback.from_user.id, {"lang": "ru", "section": None, "index": 0})
		lang = st["lang"]
		if callback.message.text:
			await callback.message.edit_text(
				UI["menu_prompt"].get(lang, UI["menu_prompt"]["ru"]),
				reply_markup=main_menu_keyboard(lang),
			)
		else:
			await callback.message.answer(
				UI["menu_prompt"].get(lang, UI["menu_prompt"]["ru"]),
				reply_markup=main_menu_keyboard(lang),
			)
		await callback.answer()

	@router.callback_query(F.data == "nav:prev")
	async def go_prev(callback: CallbackQuery) -> None:
		st = USER_STATE.get(callback.from_user.id)
		if not st:
			await callback.answer()
			return
		st["index"] = max(0, int(st.get("index", 0)) - 1)
		await show_current(callback)

	@router.callback_query(F.data == "nav:next")
	async def go_next(callback: CallbackQuery) -> None:
		st = USER_STATE.get(callback.from_user.id)
		if not st:
			await callback.answer()
			return
		st["index"] = int(st.get("index", 0)) + 1
		await show_current(callback)

	async def show_current(callback: CallbackQuery) -> None:
		st = USER_STATE.get(callback.from_user.id)
		if not st:
			await callback.answer()
			return
		terms, tips, docs = load_datasets()
		mnemo = load_mnemo()
		section = st.get("section")
		idx = int(st.get("index", 0))
		lang = st.get("lang", "ru")

		if section == "terms":
			items = terms
			title = UI["dict_title"].get(lang, UI["dict_title"]["ru"])
			fmt = lambda it: format_term(it, lang)
			def responder(text, has_prev, has_next):
				return callback.message.edit_text(text, reply_markup=nav_keyboard(has_prev, has_next, lang))
		elif section == "tips":
			items = tips
			title = UI["tips_title"].get(lang, UI["tips_title"]["ru"])
			fmt = lambda it: format_tip(it, lang)
			def responder(text, has_prev, has_next):
				return callback.message.edit_text(text, reply_markup=nav_keyboard(has_prev, has_next, lang))
		elif section == "docs":
			items = docs
			title = UI["docs_title"].get(lang, UI["docs_title"]["ru"])
			fmt = lambda it: format_doc(it, lang)
			def responder(text, has_prev, has_next):
				return callback.message.edit_text(text, reply_markup=nav_keyboard(has_prev, has_next, lang))
		elif section == "mnemo":
			items = mnemo
			title = UI["mnemo_title"].get(lang, UI["mnemo_title"]["ru"]) 
			if not items:
				await callback.message.edit_text(title + "\n(данные отсутствуют)", reply_markup=nav_keyboard(False, False, lang))
				await callback.answer()
				return
			idx = max(0, min(idx, len(items) - 1))
			st["index"] = idx
			entry = items[idx]
			photo_path = DATA_DIR / "cards" / entry["file"]
			caption = entry.get(lang, "") or title
			has_prev = idx > 0
			has_next = idx < len(items) - 1
			await callback.message.answer_photo(
				photo=FSInputFile(str(photo_path)),
				caption=f"{caption}\n\n{idx + 1}/{len(items)}",
				reply_markup=nav_keyboard(has_prev, has_next, lang),
			)
			await callback.answer()
			return
		else:
			await callback.answer()
			return

		if not items:
			await callback.message.edit_text(title + "\n(данные отсутствуют)", reply_markup=nav_keyboard(False, False, lang))
			await callback.answer()
			return

		idx = max(0, min(idx, len(items) - 1))
		st["index"] = idx

		text = f"<b>{title}</b>\n\n{fmt(items[idx])}\n\n{idx + 1}/{len(items)}"
		has_prev = idx > 0
		has_next = idx < len(items) - 1
		await responder(text, has_prev, has_next)
		await callback.answer()

	return router
