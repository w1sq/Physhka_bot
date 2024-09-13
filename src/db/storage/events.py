from typing import List
from dataclasses import dataclass, field

from db.db import DB
from db.storage.registrations import RegistrationsStorage


@dataclass
class Event:
    description: str
    date: str
    location: str
    tempo: str
    id: int = field(default=None)

    def __str__(self):
        return f"{self.description}\n\n{self.date}\n\n📍{self.location}\n{self.tempo}\n\nДо старта 🏃‍➡️"


class EventsStorage:
    __table = "events"

    def __init__(self, db: DB):
        self._db = db
        self._registrations = RegistrationsStorage(db)

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                id SERIAL PRIMARY KEY,
                description TEXT,
                date TEXT,
                location TEXT,
                tempo TEXT
            )
        """
        )
        await self._registrations.init()

    async def get_by_id(self, event_id: int) -> Event:
        data = await self._db.fetchrow(
            f"SELECT * FROM {self.__table} WHERE id = $1", event_id
        )
        if data is None:
            return None
        return Event(data[1], data[2], data[3], data[4], id=data[0])

    async def create(self, event: Event) -> int:
        return await self._db.fetchval(
            f"""
            INSERT INTO {self.__table} (description, date, location, tempo) 
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """,
            event.description,
            event.date,
            event.location,
            event.tempo,
        )

    async def get_all_events(self) -> List[Event]:
        data = await self._db.fetch(
            f"""
            SELECT * FROM {self.__table}
        """
        )
        if data is None:
            return []
        return [
            Event(
                event_data[1],
                event_data[2],
                event_data[3],
                event_data[4],
                id=event_data[0],
            )
            for event_data in data
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
        await self._registrations.register(user_id, event_id)

    async def unregister_user(self, user_id: int, event_id: int):
        await self._registrations.unregister(user_id, event_id)

    async def is_user_registered(self, user_id: int, event_id: int) -> bool:
        return await self._registrations.is_registered(user_id, event_id)

    async def get_event_participants(self, event_id: int) -> List[int]:
        return await self._registrations.get_event_registrations(event_id)

    async def get_user_events(self, user_id: int) -> List[Event]:
        event_ids = await self._registrations.get_user_registrations(user_id)
        events = []
        for event_id in event_ids:
            event = await self.get_by_id(event_id)
            if event:
                events.append(event)
        return events
