import asyncpg
import yaml
import asyncio

with open("authentication.yaml", "r", encoding="utf8") as stream:
    yaml_data = yaml.safe_load(stream)


async def start_pool():
    pool = await asyncpg.create_pool(host=yaml_data['host'], database=yaml_data['database'],
                                     user=yaml_data['user'],
                                     password=yaml_data['password'])
    print("Pool successfully started.")
    return pool

async def table_create():
    conn = await asyncpg.connect(host=yaml_data['host'], database=yaml_data['database'], user=yaml_data['user'],
                                 password=yaml_data['password'])
    await conn.execute(
        'CREATE TABLE IF NOT EXISTS five_words ('
        'word TEXT PRIMARY KEY '
        ')')
    await conn.execute(
        'CREATE TABLE IF NOT EXISTS user_profile ('
        'user_id BIGINT PRIMARY KEY,'
        'five_word_solved INT DEFAULT 0,'
        'six_word_solved INT DEFAULT 0,'
        'seven_word_solved INT DEFAULT 0,'
        'currency INT DEFAULT 0'
        ')')
    await conn.execute(
        'CREATE TABLE IF NOT EXISTS daily_five_profile ('
        'id SERIAL PRIMARY KEY ,'
        'day_id INT,'
        'user_id BIGINT,'
        'attempt INT,'
        'completed INT,'
        'result1 INT,'
        'result2 INT,'
        'result3 INT,'
        'result4 INT,'
        'result5 INT,'
        'word_guessed TEXT, '
        'UNIQUE(day_id, user_id, attempt)'
        ')')
    await conn.execute(
        'CREATE TABLE IF NOT EXISTS five_word_history ('
        'day_id INT PRIMARY KEY,'
        'word TEXT'
        ')')
    await conn.execute(
        'CREATE TABLE IF NOT EXISTS daily_tracker ('
        'id INT PRIMARY KEY, '
        'date DATE,'
        'UNIQUE(date)'
        ')')
    await conn.close()

class Database:
    def __init__(self, pool):
        self.pool: asyncpg.Pool = pool

    async def execute(self, statement, *args):
        async with self.pool.acquire() as conn:
            if args:
                await conn.execute(statement, *args)
            else:
                await conn.execute(statement)

    async def fetchrow(self, statement, *args):
        async with self.pool.acquire() as conn:
            if args:
                return await conn.fetchrow(statement, *args)
            else:
                return await conn.fetchrow(statement)

    async def fetch(self, statement, *args):
        async with self.pool.acquire() as conn:
            if args:
                return await conn.fetch(statement, *args)
            else:
                return await conn.fetch(statement)


loop = asyncio.get_event_loop()
table = loop.run_until_complete(table_create())
pool = loop.run_until_complete(start_pool())
