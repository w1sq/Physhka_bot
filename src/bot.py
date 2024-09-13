import typing

import aiogram
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from db.storage import UsersStorage, EventsStorage, User, Event


class GetUserData(StatesGroup):
    name = State()
    phone = State()
    emergency_contact = State()


class GetEventData(StatesGroup):
    photo = State()
    description = State()
    date = State()
    location = State()
    tempo = State()


class TG_Bot:
    def __init__(
        self,
        bot_token: str,
        users_storage: UsersStorage,
        events_storage: EventsStorage,
    ):
        self._users_storage: UsersStorage = users_storage
        self._events_storage: EventsStorage = events_storage
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

    async def _create_event(self, message: aiogram.types.Message, state: FSMContext):
        await message.answer("Отправьте фото для забега:")
        await state.set_state(GetEventData.description)

    async def _get_event_description(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        if not message.photo:
            await message.answer("Пожалуйста, отправьте фото для забега.")
            return

        photo = message.photo[-1]
        file_id = photo.file_id
        file = await self._bot.get_file(file_id)
        file_path = file.file_path

        # Create the directory if it doesn't exist
        os.makedirs("assets/events", exist_ok=True)

        # Download and save the photo
        await self._bot.download_file(file_path, f"assets/events/{event_id}.jpg")

        await message.answer("Фото сохранено. Теперь введите описание забега:")
        await state.set_state(GetEventData.description)
        await state.update_data(description=message.text)
        await message.answer("Введите дату забега:")
        await state.set_state(GetEventData.date)

    async def _get_event_description(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        await state.update_data(description=message.text)
        await message.answer("Введите дату забега:")
        await state.set_state(GetEventData.date)

    async def _get_event_date(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(date=message.text)
        await message.answer("Введите место проведения забега:")
        await state.set_state(GetEventData.location)

    async def _get_event_location(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        await state.update_data(location=message.text)
        await message.answer("Введите темп забега:")
        await state.set_state(GetEventData.tempo)

    async def _get_event_tempo(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(tempo=message.text)
        event_data = await state.get_data()
        event = Event(
            description=event_data["description"],
            date=event_data["date"],
            location=event_data["location"],
            tempo=event_data["tempo"],
        )
        await self._events_storage.create(event)
        await message.answer("Забег успешно создан")
        await state.clear()

    async def _show_menu(self, message: aiogram.types.Message, user: User):
        splitted_message_text = message.text.split()
        if len(splitted_message_text) == 2:
            event_id = splitted_message_text[1]
            event = await self._events_storage.get_by_id(event_id)
            if event is not None:
                registration_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Записаться",
                                callback_data=f"register_{event.id}_{user.id}",
                            )
                        ]
                    ]
                )
                await message.answer(
                    f"Запись на забег номер {event.id}",
                    reply_markup=registration_keyboard,
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

    async def _register_user(
        self, callback: aiogram.types.CallbackQuery, state: FSMContext
    ):
        event_id = callback.data.split("_")[1]
        user_id = callback.data.split("_")[2]
        user = await self._users_storage.get_by_id(user_id)
        event = await self._events_storage.get_by_id(event_id)
        if event is not None and user is not None:
            if user.name is not None:
                if await self._events_storage.is_user_registered(user_id, event_id):
                    await callback.answer(f"Вы уже записаны на забег номер {event.id}")
                else:
                    await self._events_storage.register_user(user_id, event_id)
                    await callback.answer(
                        f"Вы успешно записались на забег номер {event.id}"
                    )
            else:
                await self._bot.send_message(
                    user_id,
                    "Необходимо пройти регистрацию. Введите ваше имя:",
                )
                await state.set_state(GetUserData.name)
        else:
            await callback.answer("Забег не найден")

    async def _get_user_name(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer("Введите ваш номер телефона:")
        await state.set_state(GetUserData.phone)

    async def _get_user_phone(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(emergency_contact=message.text)
        await message.answer("Введите телефон экстренного контакта и его имя:")
        await state.set_state(GetUserData.emergency_contact)

    async def _get_user_emergency_contact(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        user_data = await state.get_data()
        user = User(
            id=message.chat.id,
            name=user_data["name"],
            phone=user_data["phone"],
            emergency_contact=user_data["emergency_contact"],
        )
        await self._users_storage.update(user)
        await state.clear()
        await message.answer(
            "Вы успешно зарегистрировались на забег",
            reply_markup=self._menu_keyboard_user,
        )

    async def _show_events(self, callback: aiogram.types.CallbackQuery):
        events = await self._events_storage.get_all()
        for event in events:
            await callback.answer(str(event))

    def _init_handler(self):
        self._dispatcher.message.register(
            self._user_middleware(self._show_menu), Command(commands=["start", "menu"])
        )
        self._dispatcher.message.register(
            self._user_middleware(self._show_menu), aiogram.F.text == "Menu"
        )
        self._dispatcher.callback_query.register(
            self._show_events,
            aiogram.F.data == "events",
        )
        self._dispatcher.callback_query.register(
            self._create_event,
            aiogram.F.data == "create_event",
        )
        self._dispatcher.callback_query.register(
            self._register_user,
            aiogram.F.data.startswith("register_"),
        )
        self._dispatcher.message.register(
            self._get_user_name,
            GetUserData.name,
        )
        self._dispatcher.message.register(
            self._get_user_phone,
            GetUserData.phone,
        )
        self._dispatcher.message.register(
            self._get_user_emergency_contact,
            GetUserData.emergency_contact,
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

        self._menu_keyboard_admin = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗓️ Создать забег", callback_data="create_event"
                    )
                ]
            ]
        )
