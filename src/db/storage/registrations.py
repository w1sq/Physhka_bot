from dataclasses import dataclass
from typing import List

from db.db import DB


@dataclass
class Registration:
    user_id: int
    event_id: int


class RegistrationsStorage:
    __table = "registrations"

    def __init__(self, db: DB):
        self._db = db

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                user_id BIGINT,
                event_id BIGINT,
                PRIMARY KEY (user_id, event_id),
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
            """
        )

    async def register(self, user_id: int, event_id: int):
        await self._db.execute(
            f"""
            INSERT INTO {self.__table} (user_id, event_id) 
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            user_id,
            event_id,
        )

    async def unregister(self, user_id: int, event_id: int):
        await self._db.execute(
            f"""
            DELETE FROM {self.__table}
            WHERE user_id = $1 AND event_id = $2
            """,
            user_id,
            event_id,
        )

    async def is_registered(self, user_id: int, event_id: int) -> bool:
        result = await self._db.fetchval(
            f"""
            SELECT EXISTS(
                SELECT 1 FROM {self.__table}
                WHERE user_id = $1 AND event_id = $2
            )
            """,
            user_id,
            event_id,
        )
        return result

    async def get_event_registrations(self, event_id: int) -> List[int]:
        data = await self._db.fetch(
            f"""
            SELECT user_id FROM {self.__table}
            WHERE event_id = $1
            """,
            event_id,
        )
        return [row[0] for row in data]

    async def get_user_registrations(self, user_id: int) -> List[int]:
        data = await self._db.fetch(
            f"""
            SELECT event_id FROM {self.__table}
            WHERE user_id = $1
            """,
            user_id,
        )
        return [row[0] for row in data]
