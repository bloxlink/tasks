import aredis
import asyncio
import re
import discord
import logging
from aiotrello import Trello
from os import environ as env

MASTER_GUILD = 372036754078826496
PARTNER_ROLE = 465022011727675393
TRELLO_BOARD = "https://trello.com/b/o9PkeQYF/partners-and-notable-groups"


trello_name_regex = re.compile("(.+):(.+)")
loop = asyncio.get_event_loop()
logging.basicConfig(level=logging.ERROR)


try:
    from config import REDIS
except ImportError:
    REDIS = {
        "HOST": env.get("REDIS_HOST"),
        "PORT": int(env.get("REDIS_PORT")),
        "PASSWORD": env.get("REDIS_PASSWORD")
    }

try:
    from config import TRELLO
except ImportError:
    TRELLO = {
        "KEY": env.get("TRELLO_KEY"),
        "TOKEN": env.get("TRELLO_TOKEN")
    }

try:
    from config import TOKEN as BOT_TOKEN
except ImportError:
    BOT_TOKEN = env.get("TOKEN")

trello = Trello(
    key=TRELLO["KEY"],
    token=TRELLO["TOKEN"],
    cache_mode="none"
)
redis = aredis.StrictRedis(host=REDIS["HOST"], port=REDIS["PORT"], password=REDIS["PASSWORD"])

async def parse_trello_data(trello_list, directory):
    data = {}

    for card in await trello_list.get_cards():
        match = trello_name_regex.search(card.name)

        if match:
            group_name = match.group(1)
            group_id = match.group(2)
            guilds = [(lambda x: x.isdigit() and int(x))(y.strip()) for y in card.desc.split(",")]

            for server_id in guilds:
                await redis.hmset(f"partners:guilds:{server_id}", {
                   "group_name": group_name,
                   "group_id": group_id
                })
                await redis.expire(f"partners:guilds:{server_id}", 120 * 60)

            data[group_id] = group_name

    await redis.hmset(f"partners:{directory}", data)

    print(f"PARTNERS | Successfully saved the {directory}.", flush=True)

async def record_partners():
    intents = discord.Intents.default()
    intents.members = True

    client = discord.AutoShardedClient(intents=intents, loop=loop)

    @client.event
    async def on_ready():
        print(f"DISCORD | Logged in as {client.user.name}", flush=True)

        guild = client.get_guild(MASTER_GUILD)

        await guild.chunk()

        role = discord.utils.find(lambda r: r.name == "Partners", guild.roles)

        if role:
            for member in role.members:
                await redis.set(f"partners:users:{member.id}", "1", ex=120*60)

        print("PARTNERS | Successfully saved the partnered users.", flush=True)

        await client.close()


    @client.event
    async def on_error(event, *args, **kwargs):
        print(event, args, kwargs, flush=True)
        await client.close()



    await client.start(BOT_TOKEN)


async def main():
    trello_board = await trello.get_board(TRELLO_BOARD)

    partners_list = await trello_board.get_list(lambda l: l.name == "Partners")
    notable_groups_list = await trello_board.get_list(lambda l: l.name == "Notable Groups")

    await parse_trello_data(partners_list, "partners")
    await parse_trello_data(notable_groups_list, "notable_groups")

    await record_partners()


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
