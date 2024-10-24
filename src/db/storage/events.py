from typing import List
from dataclasses import dataclass, field
from datetime import datetime
from db.db import DB
from db.storage.registrations import RegistrationsStorage


@dataclass
class Event:
    description: str
    date: datetime
    location: str
    tempo: str
    photo_id: str
    id: int = field(default=None)

    russian_days = {
        "Mon": "Понедельник",
        "Tue": "Вторник",
        "Wed": "Среда",
        "Thu": "Четверг",
        "Fri": "Пятница",
        "Sat": "Суббота",
        "Sun": "Воскресенье",
    }

    def __str__(self):
        return f"{self.description}\n\n{self.russian_days[self.date.strftime('%a')]} {self.date.strftime('%d.%m в %H:%M')}\n\n📍{self.location}\n{self.tempo}\n\nДо старта 🏃‍➡️"


class EventsStorage:
    __table = "events"

    def __init__(self, db: DB):
        self._db = db
        self.registrations = RegistrationsStorage(db)

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                id SERIAL PRIMARY KEY,
                description TEXT,
                date TEXT,
                location TEXT,
                tempo TEXT,
                photo_id TEXT
            )
            """
        )

    async def get_by_id(self, event_id: int) -> Event:
        data = await self._db.fetchrow(
            f"SELECT id, description, date, location, tempo, photo_id FROM {self.__table} WHERE id = $1",
            event_id,
        )
        if data is None:
            return None
        return Event(
            description=data[1],
            date=data[2],
            location=data[3],
            tempo=data[4],
            photo_id=data[5],
            id=data[0],
        )

    async def create(self, event: Event) -> int:
        return await self._db.fetchval(
            f"""
            INSERT INTO {self.__table} (description, date, location, tempo, photo_id) 
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """,
            event.description,
            event.date,
            event.location,
            event.tempo,
            event.photo_id,
        )

    async def update(self, event: Event):
        await self._db.execute(
            f"""
            UPDATE {self.__table} SET description = $1, date = $2, location = $3, tempo = $4, photo_id = $5 WHERE id = $6
        """,
            event.description,
            event.date,
            event.location,
            event.tempo,
            event.photo_id,
            event.id,
        )

    async def get_all_events(self, actual_only: bool = False) -> List[Event]:
        query = f"""
            SELECT id, description, date, location, tempo, photo_id 
            FROM {self.__table}
            {f"WHERE date > $1" if actual_only else ""}
            ORDER BY date ASC
        """
        params = [datetime.now()] if actual_only else []
        data = await self._db.fetch(query, *params)
        if not data:
            return []
        return [
            Event(
                description=row[1],
                date=row[2],
                location=row[3],
                tempo=row[4],
                photo_id=row[5],
                id=row[0],
            )
            for row in data
        ]

    async def get_event_amount(self) -> int:
        return await self._db.fetchval(f"SELECT COUNT(*) FROM {self.__table}")

    async def delete(self, event_id: int):
        await self._db.execute(
            f"""
            DELETE FROM {self.__table} WHERE id = $1
        """,
            event_id,
        )

    async def register_user(self, user_id: int, event_id: int):
        await self.registrations.register(user_id, event_id)

    async def unregister_user(self, user_id: int, event_id: int):
        await self.registrations.unregister(user_id, event_id)

    async def is_user_registered(self, user_id: int, event_id: int) -> bool:
        return await self.registrations.is_registered(user_id, event_id)

    async def get_event_participants(self, event_id: int) -> List[int]:
        return await self.registrations.get_event_registrations(event_id)

    async def get_user_events(
        self, user_id: int, actual_only: bool = False
    ) -> List[Event]:
        registrations_ids = await self.registrations.get_user_registrations(user_id)
        events = []
        for registration_id in registrations_ids:
            event = await self.get_by_id(registration_id)
            if event and (not actual_only or event.date > datetime.now()):
                events.append(event)
        return events
