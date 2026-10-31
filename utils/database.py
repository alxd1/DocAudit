import asyncpg
import configuration.database_conf as db_conf


async def get_connection() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=db_conf.DB_HOST,
        port=db_conf.DB_PORT,
        database=db_conf.DB_NAME,
        user=db_conf.DB_USER,
        password=db_conf.DB_PASSWORD,
    )
