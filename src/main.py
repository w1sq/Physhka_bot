import asyncio

import aioschedule

from db.db import DB
from bot import TG_Bot
from config_reader import config
from db.storage import UsersStorage


async def init_db():
    db = DB(
        host=config.host.get_secret_value(),
        port=config.port.get_secret_value(),
        login=config.login.get_secret_value(),
        password=config.password.get_secret_value(),
        database=config.database.get_secret_value(),
    )
    await db.init()
    users_storage = UsersStorage(db)
    await users_storage.init()
    return users_storage


async def check_schedule():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    users_storage = await init_db()
    tg_bot = TG_Bot(
        bot_token=config.tgbot_api_key.get_secret_value(), users_storage=users_storage
    )
    await tg_bot.init()

    asyncio.create_task(check_schedule())

    await tg_bot.start()


if __name__ == "__main__":
    asyncio.run(main())
