from typing import List
from dataclasses import dataclass
from datetime import datetime

from db.db import DB


@dataclass
class Event:
    id: int
    description: str
    date: datetime
    location: str
    tempo: str


class EventsStorage:
    __table = "events"

    def __init__(self, db: DB):
        self._db = db

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                id BIGINT PRIMARY KEY,
                description TEXT,
                date TIMESTAMP,
                location TEXT,
                tempo TEXT
            )
        """
        )

    async def get_by_id(self, event_id: int) -> Event:
        data = await self._db.fetchrow(
            f"SELECT * FROM {self.__table} WHERE id = $1", event_id
        )
        if data is None:
            return None
        return Event(data[0], data[1], data[2], data[3], data[4])

    async def create(self, event: Event):
        await self._db.execute(
            f"""
            INSERT INTO {self.__table} (id, description, date, location, tempo) VALUES ($1, $2, $3, $4, $5)
        """,
            event.id,
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
            return None
        return [
            Event(
                event_data[0],
                event_data[1],
                event_data[2],
                event_data[3],
                event_data[4],
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
