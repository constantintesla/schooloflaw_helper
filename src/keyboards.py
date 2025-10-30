from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .i18n import UI


def language_keyboard() -> InlineKeyboardMarkup:
	return InlineKeyboardMarkup(inline_keyboard=[
		[
			InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
			InlineKeyboardButton(text="English", callback_data="lang:en"),
		],
		[
			InlineKeyboardButton(text="中文", callback_data="lang:zh"),
			InlineKeyboardButton(text="한국어", callback_data="lang:ko"),
		],
	])


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
	b = UI["btn"]
	return InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text=b["menu_terms"][lang], callback_data="menu:terms")],
		[InlineKeyboardButton(text=b["menu_tips"][lang], callback_data="menu:tips")],
		[InlineKeyboardButton(text=b["menu_docs"][lang], callback_data="menu:docs")],
		[InlineKeyboardButton(text=b["menu_mnemo"][lang], callback_data="menu:mnemo")],
		[InlineKeyboardButton(text=b["choose_lang"][lang], callback_data="menu:lang")],
	])


def nav_keyboard(has_prev: bool, has_next: bool, lang: str = "ru") -> InlineKeyboardMarkup:
	b = UI["btn"]
	row = []
	row.append(InlineKeyboardButton(text=b["menu"][lang], callback_data="nav:menu"))
	if has_prev:
		row.append(InlineKeyboardButton(text=b["prev"][lang], callback_data="nav:prev"))
	if has_next:
		row.append(InlineKeyboardButton(text=b["next"][lang], callback_data="nav:next"))
	return InlineKeyboardMarkup(inline_keyboard=[row])
