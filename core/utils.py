import aiohttp
import git
from datetime import datetime
from typing import List, Union

import discord
from discord.ext import commands

from core.config import config
from core.text import text


def git_get_hash():
    repo = git.Repo(search_parent_directories=True)
    return repo.head.object.hexsha


def git_get_branch():
    repo = git.Repo(search_parent_directories=True)
    return repo.active_branch.name


def git_commit_msg():
    repo = git.Repo(search_parent_directories=True)
    return repo.head.commit.message


def git_pull():
    repo = git.Repo(search_parent_directories=True)
    cmd = repo.git
    return cmd.pull()


async def set_presence(bot):
    activity = discord.Game(start=datetime.utcnow(), name=config.prefix + "help")
    await bot.change_presence(activity=activity)


def id_to_datetime(snowflake_id: int):
    return datetime.fromtimestamp(((snowflake_id >> 22) + 1420070400000) / 1000)


def str_emoji_id(emoji):
    if isinstance(emoji, int):
        return str(emoji)

    return emoji if isinstance(emoji, str) else str(emoji.id)


def has_role(user, role):
    if type(user) != discord.Member:
        return None

    try:
        int(role)
        return role in [u.id for u in user.roles]
    except ValueError:
        return role.lower() in [u.name.lower() for u in user.roles]
    return


def seconds2str(time):
    time = int(time)
    D = 3600 * 24
    H = 3600
    M = 60

    d = int((time - (time % D)) / D)
    h = int((time - (time % H)) / H) % 24
    m = int((time - (time % M)) / M) % 60
    s = time % 60

    if d > 0:
        return f"{d} d, {h:02}:{m:02}:{s:02}"
    if h > 0:
        return f"{h}:{m:02}:{s:02}"
    if m > 0:
        return f"{m}:{s:02}"
    if s > 4:
        return f"{s} vteřin"
    if s > 1:
        return f"{s} vteřiny"
    return "vteřinu"


async def room_check(ctx: commands.Context):
    if not isinstance(ctx.channel, discord.TextChannel):
        return

    # Do not send message if the message has been sent to other guild
    if ctx.guild.id != config.guild_id:
        return

    if ctx.channel.id not in config.get("channels", "bot allowed"):
        # we do not have `bot` variable, so we have to construct the botroom mention directly
        await ctx.send(
            text.fill(
                "server",
                "botroom redirect",
                mention=ctx.author.mention,
                channel=f"<#{config.get('channels', 'botspam')}>",
            )
        )


async def send(
    target: discord.abc.Messageable,
    text: str = None,
    *,
    embed: discord.Embed = None,
    delete_after: float = None,
    nonce: int = None,
    file: discord.File = None,
    files: List[discord.File] = None,
):
    # fmt: off
    if not isinstance(target, discord.TextChannel) \
    or (
        isinstance(target, discord.TextChannel) and
        target.id in config.get("channels", "bot allowed")
    ):
        delete_after = None

    await target.send(
        content=text,
        embed=embed,
        delete_after=delete_after,
        nonce=nonce,
        file=file,
        files=files,
    )
    # fmt: on


async def delete(thing):
    if hasattr(thing, "message"):
        thing = thing.message
    if isinstance(thing, discord.Message):
        try:
            await thing.delete()
        except discord.Forbidden:
            pass


async def remove_reaction(reaction, user):
    try:
        await reaction.remove(user)
    except Exception:
        pass


async def send_help(ctx: commands.Context):
    if not hasattr(ctx, "command") or not hasattr(ctx.command, "qualified_name"):
        return
    if ctx.invoked_subcommand is not None:
        return
    await ctx.send_help(ctx.command.qualified_name)


def paginate(text: Union[List[str], str]) -> List[str]:
    """Convert to messages that will fit into the 2000 character limit"""
    if type(text) == str:
        return list(text[0 + i : 1980 + i] for i in range(0, len(text), 1980))

    result = []
    output = ""
    for line in text:
        if len(output) + len(line) > 1980:
            result.append(output)
            output = ""
        output += "\n" + line
    result.append(output)
    return result


def get_digit_emoji(number: int) -> str:
    """Convert digit to emoji"""
    numbers = ("0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣")
    if number > len(numbers) or number < 0:
        raise ValueError("Number must be between 0 and 9.")
    return numbers[number]


async def fetch_json(url: str) -> dict:
    """Fetch data from a URL and return a dict"""

    async with aiohttp.ClientSession() as cs:
        async with cs.get(url) as r:
            return await r.json()
