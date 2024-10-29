from typing import List, Optional
from dataclasses import dataclass

from db.db import DB


@dataclass
class User:
    ADMIN = "admin"
    USER = "user"
    BLOCKED = "blocked"

    locations = {"1": "Москва", "2": "Долгопрудный"}

    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    location: str = "1"
    role: str = USER

    def __str__(self):
        return f"<a href='tg://user?id={self.id}'>{self.name}</a>\nPhone: {self.phone}\nEmergency Contact: {self.emergency_contact}"


class UsersStorage:
    __table = "users"

    def __init__(self, db: DB):
        self._db = db

    async def init(self):
        await self._db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.__table} (
                id BIGINT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                emergency_contact TEXT,
                location TEXT,
                role TEXT
            )
        """
        )

    async def get_by_id(self, user_id: int) -> User:
        data = await self._db.fetchrow(
            f"SELECT * FROM {self.__table} WHERE id = $1", user_id
        )
        if data is None:
            return None
        return User(data[0], data[1], data[2], data[3], data[4], data[5])

    async def promote_to_admin(self, user_id: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.ADMIN, user_id
        )

    async def demote_from_admin(self, user_id: int):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.USER, user_id
        )

    async def get_role_list(self, role: str) -> List[int]:
        roles = await self._db.fetch(
            f"SELECT * FROM {self.__table} WHERE role = $1", role
        )
        if roles is None:
            return None
        return [role[0] for role in roles]

    async def create(self, user: User):
        await self._db.execute(
            f"""
            INSERT INTO {self.__table} (id, name, phone, emergency_contact, location, role) VALUES ($1, $2, $3, $4, $5, $6)
        """,
            user.id,
            user.name,
            user.phone,
            user.emergency_contact,
            user.location,
            user.role,
        )

    async def update(self, user: User):
        await self._db.execute(
            f"""
            UPDATE {self.__table} SET name = $1, phone = $2, emergency_contact = $3, location = $4 WHERE id = $5
        """,
            user.name,
            user.phone,
            user.emergency_contact,
            user.location,
            user.id,
        )

    async def get_all_members(self) -> List[User]:
        data = await self._db.fetch(
            f"""
            SELECT * FROM {self.__table}
        """
        )
        if data is None:
            return None
        return [
            User(
                user_data[0],
                user_data[1],
                user_data[2],
                user_data[3],
                user_data[4],
                user_data[5],
            )
            for user_data in data
        ]

    async def get_user_amount(self) -> int:
        return await self._db.fetchval(f"SELECT COUNT(*) FROM {self.__table}")

    async def ban_user(self, user_id: User):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.BLOCKED, user_id
        )

    async def unban_user(self, user_id: User):
        await self._db.execute(
            f"UPDATE {self.__table} SET role = $1 WHERE id = $2", User.USER, user_id
        )

    async def delete(self, user_id: int):
        await self._db.execute(
            f"""
            DELETE FROM {self.__table} WHERE id = $1
        """,
            user_id,
        )
