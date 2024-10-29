import typing
from datetime import datetime
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
    city = State()
    photo = State()
    description = State()
    date = State()
    location = State()
    tempo = State()


class ConfirmDeletingEvent(StatesGroup):
    confirmation = State()


class EditEventData(StatesGroup):
    city = State()
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

    async def _create_event(self, callback: aiogram.types.CallbackQuery):
        city_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Москва", callback_data="set_event_city_1")],
                [
                    InlineKeyboardButton(
                        text="Долгопрудный", callback_data="set_event_city_2"
                    )
                ],
            ]
        )
        await callback.message.answer("Выберите город:", reply_markup=city_keyboard)

    async def _get_event_city(
        self, callback: aiogram.types.CallbackQuery, state: FSMContext
    ):
        await callback.message.edit_reply_markup()
        await state.update_data(city=callback.data.split("_")[-1])
        await callback.message.answer(
            "Отправьте фото для забега:", reply_markup=self._cancel_keyboard
        )
        await state.set_state(GetEventData.photo)

    async def _get_event_photo(self, message: aiogram.types.Message, state: FSMContext):
        if not message.photo:
            await message.answer(
                "Пожалуйста, отправьте фото для забега.",
                reply_markup=self._cancel_keyboard,
            )
            return

        photo = message.photo[-1]
        file_id = photo.file_id
        await state.update_data(event_photo_id=file_id)

        await message.answer(
            "Фото сохранено. Теперь введите описание забега:",
            reply_markup=self._cancel_keyboard,
        )
        await state.set_state(GetEventData.description)

    async def _get_event_description(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        await state.update_data(description=message.text.strip())
        await message.answer("Введите дату забега:", reply_markup=self._cancel_keyboard)
        await state.set_state(GetEventData.date)

    async def _get_event_date(self, message: aiogram.types.Message, state: FSMContext):
        try:
            datetime.strptime(message.text.strip(), "%d.%m в %H:%M")
        except ValueError:
            await message.answer(
                "Пожалуйста, введите дату в формате ДД.ММ в ЧЧ:ММ",
                reply_markup=self._cancel_keyboard,
            )
            return
        await state.update_data(date=message.text.strip())
        await message.answer(
            "Введите место проведения забега:", reply_markup=self._cancel_keyboard
        )
        await state.set_state(GetEventData.location)

    async def _get_event_location(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        await state.update_data(location=message.text.strip())
        await message.answer("Введите темп забега:", reply_markup=self._cancel_keyboard)
        await state.set_state(GetEventData.tempo)

    async def _get_event_tempo(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(tempo=message.text.strip())
        event_data = await state.get_data()
        date = datetime.strptime(event_data["date"], "%d.%m в %H:%M")
        date = date.replace(year=datetime.now().year)
        event = Event(
            city=event_data["city"],
            description=event_data["description"],
            date=date,
            location=event_data["location"],
            tempo=event_data["tempo"],
            photo_id=event_data["event_photo_id"],
        )

        event_id = await self._events_storage.create(event)

        await message.answer_photo(
            event.photo_id,
            caption=f"{event}\n\n<a href='https://t.me/physhkabot?start={event_id}'>Записаться</a>",
        )
        await message.answer(
            f"Забег успешно создан. Ссылка для регистрации:\n\n<code>https://t.me/physhkabot?start={event_id}</code>"
        )

        await state.clear()

    async def _show_menu(self, message: aiogram.types.Message, user: User):
        splitted_message_text = message.text.split()

        if len(splitted_message_text) == 2:
            event_id = int(splitted_message_text[1])
            event = await self._events_storage.get_by_id(event_id)
            if event is not None:
                if user.role == User.ADMIN:
                    registration_keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Посмотреть участников",
                                    callback_data=f"event_users_{event.id}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="Изменить забег",
                                    callback_data=f"edit_event_{event.id}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="Удалить забег",
                                    callback_data=f"delete_event_{event.id}",
                                )
                            ],
                        ]
                    )
                    await message.answer_photo(
                        event.photo_id,
                        caption=str(event),
                        reply_markup=registration_keyboard,
                    )
                else:
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
                    await message.answer_photo(
                        event.photo_id,
                        caption=f"Запись на забег:\n\n{event}",
                        reply_markup=registration_keyboard,
                    )
            else:
                await message.answer(
                    "Забег не найден", reply_markup=self._menu_keyboard_user
                )
        elif user.role == User.ADMIN:
            await message.answer(
                "Добро пожаловать в админ панель",
                reply_markup=self._menu_keyboard_admin,
            )
        else:
            await message.answer(
                "Добро пожаловать в телеграм бота бегового клуба Physhka",
                reply_markup=self._menu_keyboard_user,
            )

    async def _register_user(
        self, callback: aiogram.types.CallbackQuery, state: FSMContext
    ):
        event_id = int(callback.data.split("_")[1])
        user_id = int(callback.data.split("_")[2])
        user = await self._users_storage.get_by_id(user_id)
        event = await self._events_storage.get_by_id(event_id)
        if event is not None and user is not None:
            if user.name is not None:
                if await self._events_storage.is_user_registered(user_id, event_id):
                    await callback.message.edit_reply_markup()
                    await callback.answer("Вы уже записаны на этот забег")
                else:
                    await self._events_storage.register_user(user_id, event_id)
                    await callback.answer("Вы успешно записались на забег")
            else:
                await self._bot.send_message(
                    user_id,
                    "Необходимо пройти регистрацию. Введите ваше Имя и Фамилию:",
                )
                await state.set_state(GetUserData.name)
                await state.update_data(event_id=event_id)
        else:
            await callback.answer("Забег не найден")

    async def _get_user_name(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(name=message.text.strip())
        await message.answer("Введите ваш номер телефона:")
        await state.set_state(GetUserData.phone)

    async def _get_user_phone(self, message: aiogram.types.Message, state: FSMContext):
        await state.update_data(phone=message.text.strip())
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
            emergency_contact=message.text.strip(),
        )
        await self._users_storage.update(user)
        await self._events_storage.register_user(user.id, user_data["event_id"])
        await state.clear()
        await message.answer(
            "Вы успешно зарегистрировались на забег",
            reply_markup=self._menu_keyboard_user,
        )

    async def _show_my_events(self, callback: aiogram.types.CallbackQuery):
        user_id = callback.from_user.id
        events = await self._events_storage.get_user_events(user_id, actual_only=True)
        if len(events) == 0:
            await callback.message.answer("Вы не записаны ни на один забег")
        else:
            await callback.message.answer("Ваши регистрации:")
            for event in events:
                registration = (
                    await self._events_storage.registrations.get_registration(
                        user_id, event.id
                    )
                )
                await callback.message.answer_photo(
                    event.photo_id,
                    caption=str(event),
                    reply_markup=self._create_excuse_keyboard(
                        event.id, user_id, registration.late
                    ),
                )

    def _build_location_keyboard(self, user_location: str):
        print(user_location)
        moscow_text = "Москва"
        dolgoprudny_text = "Долгопрудный"
        all_text = "Все локации"
        if user_location == "12":
            all_text = "✅ Все локации"
        elif user_location == "1":
            moscow_text = "✅ Москва"
        elif user_location == "2":
            dolgoprudny_text = "✅ Долгопрудный"

        location_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=moscow_text, callback_data="change_location_1"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=dolgoprudny_text, callback_data="change_location_2"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=all_text, callback_data="change_location_12"
                    )
                ],
            ]
        )
        return location_keyboard

    async def _change_location(self, callback: aiogram.types.CallbackQuery):
        user = await self._users_storage.get_by_id(callback.from_user.id)
        await callback.message.answer(
            "Выберите город:", reply_markup=self._build_location_keyboard(user.location)
        )

    async def _change_location_choice(self, callback: aiogram.types.CallbackQuery):
        location = callback.data.split("_")[-1]
        user = await self._users_storage.get_by_id(callback.from_user.id)
        user.location = location
        await self._users_storage.update(user)
        await callback.message.edit_reply_markup(
            reply_markup=self._build_location_keyboard(location)
        )

    async def _show_events(self, callback: aiogram.types.CallbackQuery):
        user = await self._users_storage.get_by_id(callback.from_user.id)
        if user.role == User.USER:
            events = await self._events_storage.get_all_events(
                city=user.location, actual_only=True
            )
            if len(events) == 0:
                await callback.message.answer("На данный момент нет активных забегов")
            else:
                for event in events:
                    registration = (
                        await self._events_storage.registrations.is_registered(
                            callback.from_user.id, event.id
                        )
                    )
                    if not registration:
                        registration_keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="Записаться",
                                        callback_data=f"register_{event.id}_{callback.from_user.id}",
                                    )
                                ]
                            ]
                        )
                        await callback.message.answer_photo(
                            event.photo_id,
                            caption=str(event),
                            reply_markup=registration_keyboard,
                        )
                    else:
                        await callback.message.answer_photo(
                            event.photo_id,
                            caption=str(event),
                            reply_markup=self._create_excuse_keyboard(
                                event.id, callback.from_user.id, registration.late
                            ),
                        )
        else:
            events = await self._events_storage.get_all_events()
            for event in events:
                registration_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Посмотреть участников",
                                callback_data=f"event_users_{event.id}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Изменить забег",
                                callback_data=f"edit_event_{event.id}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="Удалить забег",
                                callback_data=f"delete_event_{event.id}",
                            )
                        ],
                    ]
                )
                await callback.message.answer_photo(
                    event.photo_id,
                    caption=str(event),
                    reply_markup=registration_keyboard,
                )

    async def _show_event_users(self, callback: aiogram.types.CallbackQuery):
        event_id = int(callback.data.split("_")[2])
        users_ids = await self._events_storage.get_event_participants(event_id)
        message = ""
        for user_id in users_ids:
            user = await self._users_storage.get_by_id(user_id)
            registration = await self._events_storage.registrations.get_registration(
                user_id, event_id
            )
            if registration.late == 0:
                message += str(user) + "\n\n"
            elif registration.late == -1:
                message += f"<s>{user}</s>\n\n"
            else:
                message += str(user) + f"\nОпоздание {registration.late} мин\n\n"
        await callback.message.answer(message)

    async def _ask_change_late(
        self, callback: aiogram.types.CallbackQuery, state: FSMContext
    ):
        event_id = int(callback.data.split("_")[-2])
        user_id = int(callback.data.split("_")[-1])
        late_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="5 минут", callback_data=f"late_{event_id}_{user_id}_5"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="10 минут", callback_data=f"late_{event_id}_{user_id}_10"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="15 минут", callback_data=f"late_{event_id}_{user_id}_15"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Отписаться",
                        callback_data=f"late_{event_id}_{user_id}_-1",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data=f"set_classic_late_keyboard_{event_id}_{user_id}",
                    )
                ],
            ]
        )
        await self._bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=late_keyboard,
        )

    def _create_excuse_keyboard(self, event_id: int, user_id: int, late: int):
        if late == -1:
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Я всё-таки приду",
                            callback_data=f"late_{event_id}_{user_id}_0",
                        )
                    ]
                ]
            )
        elif late == 0:
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Я не приду/опоздаю",
                            callback_data=f"change_late_{event_id}_{user_id}",
                        )
                    ]
                ]
            )
        else:
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Я буду вовремя",
                            callback_data=f"late_{event_id}_{user_id}_0",
                        )
                    ]
                ]
            )

    async def _set_late(self, callback: aiogram.types.CallbackQuery):
        event_id = int(callback.data.split("_")[1])
        user_id = int(callback.data.split("_")[2])
        late_minutes = int(callback.data.split("_")[3])
        await self._events_storage.registrations.set_late(
            user_id, event_id, late_minutes
        )
        await self._bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=self._create_excuse_keyboard(event_id, user_id, late_minutes),
        )

    async def _set_classic_late_keyboard(self, callback: aiogram.types.CallbackQuery):
        event_id = int(callback.data.split("_")[-2])
        user_id = int(callback.data.split("_")[-1])
        late_cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Я не приду/опоздаю",
                        callback_data=f"change_late_{event_id}_{user_id}",
                    )
                ]
            ]
        )
        await self._bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=late_cancel_keyboard,
        )

    async def _confirm_deleting_event(
        self, callback: aiogram.types.CallbackQuery, state: FSMContext
    ):
        event_id = int(callback.data.split("_")[2])
        await state.set_state(ConfirmDeletingEvent.confirmation)
        await state.update_data(event_id=event_id)
        await callback.message.answer(
            f"Вы уверены, что хотите удалить забег {event_id}?",
            reply_markup=self._cancel_keyboard,
        )

    async def _edit_event(
        self, callback: aiogram.types.CallbackQuery, state: FSMContext
    ):
        event_id = int(callback.data.split("_")[2])
        await state.set_state(EditEventData.description)
        await state.update_data(event_id=event_id)
        await callback.message.answer(
            "Введите новое описание забега:", reply_markup=self._cancel_keyboard
        )

    async def _edit_event_description(
        self, message: aiogram.types.Message, state: FSMContext
    ):
        event_id = (await state.get_data())["event_id"]
        event = await self._events_storage.get_by_id(event_id)
        if event is not None:
            event.description = message.text.strip()
            await self._events_storage.update(event)
            await message.answer(
                "Описание успешно изменено", reply_markup=self._menu_keyboard_admin
            )
        else:
            await message.answer("Забег не найден")
        await state.clear()

    async def _delete_event(self, message: aiogram.types.Message, state: FSMContext):
        if message.text.lower() == "да":
            event_id = (await state.get_data())["event_id"]
            await self._events_storage.delete(event_id)
            await message.answer("Забег удален")
        else:
            await message.answer("Действие отменено")
        await state.clear()

    async def _cancel(self, callback: aiogram.types.CallbackQuery, state: FSMContext):
        await state.clear()
        user = await self._users_storage.get_by_id(callback.from_user.id)
        if user.role == User.ADMIN:
            await callback.message.answer(
                "Действие отменено", reply_markup=self._menu_keyboard_admin
            )
        else:
            await callback.message.answer(
                "Действие отменено", reply_markup=self._menu_keyboard_user
            )

    def _init_handler(self):
        self._dispatcher.message.register(
            self._user_middleware(self._show_menu), Command(commands=["start", "menu"])
        )
        self._dispatcher.message.register(
            self._user_middleware(self._show_menu), aiogram.F.text == "Menu"
        )
        self._dispatcher.callback_query.register(
            self._change_location,
            aiogram.F.data == "change_location",
        )
        self._dispatcher.callback_query.register(
            self._change_location_choice,
            aiogram.F.data.startswith("change_location_"),
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
            self._get_event_city,
            aiogram.F.data.startswith("set_event_city_"),
        )
        self._dispatcher.callback_query.register(
            self._confirm_deleting_event,
            aiogram.F.data.startswith("delete_event_"),
        )
        self._dispatcher.message.register(
            self._delete_event,
            ConfirmDeletingEvent.confirmation,
        )
        self._dispatcher.callback_query.register(
            self._register_user,
            aiogram.F.data.startswith("register_"),
        )
        self._dispatcher.callback_query.register(
            self._show_my_events,
            aiogram.F.data.startswith("my_registrations"),
        )
        self._dispatcher.callback_query.register(
            self._show_event_users,
            aiogram.F.data.startswith("event_users_"),
        )
        self._dispatcher.callback_query.register(
            self._edit_event,
            aiogram.F.data.startswith("edit_event_"),
        )
        self._dispatcher.callback_query.register(
            self._ask_change_late,
            aiogram.F.data.startswith("change_late_"),
        )
        self._dispatcher.callback_query.register(
            self._set_classic_late_keyboard,
            aiogram.F.data.startswith("set_classic_late_keyboard_"),
        )
        self._dispatcher.callback_query.register(
            self._set_late,
            aiogram.F.data.startswith("late_"),
        )
        self._dispatcher.message.register(
            self._edit_event_description,
            EditEventData.description,
        )
        self._dispatcher.callback_query.register(
            self._cancel,
            aiogram.F.data == "cancel",
        )
        self._dispatcher.message.register(
            self._get_event_photo,
            GetEventData.photo,
        )
        self._dispatcher.message.register(
            self._get_event_description,
            GetEventData.description,
        )
        self._dispatcher.message.register(
            self._get_event_date,
            GetEventData.date,
        )
        self._dispatcher.message.register(
            self._get_event_location,
            GetEventData.location,
        )
        self._dispatcher.message.register(
            self._get_event_tempo,
            GetEventData.tempo,
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
                if message.chat.id in [483131594, 631874013]:
                    user = User(id=message.chat.id, role=User.ADMIN)
                else:
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
                [
                    InlineKeyboardButton(
                        text="🏃‍♂️ Мои регистрации", callback_data="my_registrations"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Выбрать город", callback_data="change_location"
                    )
                ],
                # [InlineKeyboardButton(text="🏃‍♂️ Наши бегуны", callback_data="runners")],
            ],
            resize_keyboard=True,
        )

        self._menu_keyboard_admin = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Забеги", callback_data="events")],
                [InlineKeyboardButton(text="Пользователи", callback_data="users")],
                [
                    InlineKeyboardButton(
                        text="🗓️ Создать забег", callback_data="create_event"
                    )
                ],
            ]
        )

        self._cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
            ]
        )
