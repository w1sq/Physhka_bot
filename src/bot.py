import typing

import aiogram
from aiogram.filters.command import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from db.storage import UsersStorage, User


class TG_Bot:
    def __init__(self, bot_token: str, users_storage: UsersStorage):
        self._users_storage: UsersStorage = users_storage
        self._bot: aiogram.Bot = aiogram.Bot(
            token=bot_token, default=DefaultBotProperties(parse_mode="HTML")
        )
        self._storage: MemoryStorage = MemoryStorage()
        self._dispatcher: aiogram.Dispatcher = aiogram.Dispatcher(storage=self._storage)
        self._create_keyboards()

    async def init(self):
        self._init_handler()

    async def start(self):
        print("Bot has started")
        await self._dispatcher.start_polling(self._bot)

    async def _show_menu(self, message: aiogram.types.Message, user: User):
        splitted_message_text = message.text.split()
        if len(splitted_message_text) == 2:
            event_id = splitted_message_text[1]
            event = await self._events_storage.get_by_id(event_id)
            if event is not None:
                await message.answer(
                    f"Запись на забег номер {event.id}",
                    # reply_markup=self._menu_keyboard_admin,
                )
            else:
                await message.answer(
                    "Забег не найден", reply_markup=self._menu_keyboard_user
                )
        else:
            await message.answer(
                "Добро пожаловать в телеграм бота бегового клуба Physhka",
                reply_markup=self._menu_keyboard_user,
            )

    def _init_handler(self):
        self._dispatcher.message.register(
            self._user_middleware(self._show_menu), Command(commands=["start", "menu"])
        )
        self._dispatcher.message.register(
            self._user_middleware(self._show_menu), aiogram.F.text == "Menu"
        )

    def _user_middleware(self, func: typing.Callable) -> typing.Callable:
        async def wrapper(message: aiogram.types.Message, *args, **kwargs):
            user = await self._users_storage.get_by_id(message.chat.id)
            if user is None:
                user = User(id=message.chat.id, role=User.USER)
                await self._users_storage.create(user)

            if user.role != User.BLOCKED:
                await func(message, user)

        return wrapper

    def _admin_required(self, func: typing.Callable) -> typing.Callable:
        async def wrapper(message: aiogram.types.Message, user: User, *args, **kwargs):
            if user.role == User.ADMIN:
                await func(message, user)

        return wrapper

    def _create_keyboards(self):
        self._menu_keyboard_user = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📅 Ближайшие забеги", callback_data="events"
                    )
                ],
                # [InlineKeyboardButton(text="🏃‍♂️ Наши бегуны", callback_data="runners")],
            ],
            resize_keyboard=True,
        )
