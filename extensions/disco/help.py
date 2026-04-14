"""MIT License

Copyright (c) 2026 TwitchIO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Self

import discord
from discord import ui
from discord.ext import commands

import core


LOGGER: logging.Logger = logging.getLogger(__name__)
ROLES: list[int] = [core.CONST.admin_role, core.CONST.maint_role, core.CONST.contributor_role]
TAG_ID: int = 1493314108135706657

MSG = """### Welcome to the help forums!

To make helping easier for everyone please provide as much information about your problem as possible.
Including any relevant `code`, `tracebacks` and a `clear description` of what you expected and what happened.

You can post snippets of code with the following syntax:
\\`\\`\\`py
\\# CODE...
\\`\\`\\`

You can **close** this post at anytime by:

- clicking the **`Solved`** button below.
- Using the **`!solved`** command.
"""


class SolvedView(ui.View):
    def __init__(self, *, owner: int, thread: discord.Thread) -> None:
        self.owner = owner
        self.thread = thread
        super().__init__(timeout=None)

    async def do_solved(self, interaction: discord.Interaction[core.DiscordBot]) -> None:
        if self.thread.locked:
            self.stop()
            return

        self.solved.disabled = True
        await interaction.response.edit_message(view=self)

        await self.thread.add_tags(discord.Object(id=TAG_ID), reason="Help Post Solved.")
        await self.thread.edit(locked=True, reason="Help Post Solved")

        self.stop()

    @ui.button(label="Solved", disabled=True, style=discord.ButtonStyle.green)
    async def solved(self, interaction: discord.Interaction[core.DiscordBot], button: ui.Button[Self]) -> None:
        member = interaction.user
        assert isinstance(member, discord.Member)

        if any(r.id in ROLES for r in member.roles):
            return await self.do_solved(interaction)

        if member != self.owner:
            await interaction.response.send_message("Sorry you do not have permission to use this!", ephemeral=True)
            return

        await self.do_solved(interaction)


class HelpChannelCog(commands.Cog):
    def __init__(self, bot: core.DiscordBot) -> None:
        self.bot = bot
        self.waiters: set[asyncio.Task[None]] = set()

    async def disabled_waiter(self, message: discord.Message, view: SolvedView) -> None:
        await asyncio.sleep(8)

        if view.is_finished():
            return

        view.solved.disabled = False
        try:
            await message.edit(view=view)
        except Exception as e:
            LOGGER.debug("Failed to update disabled state on SolvedView: %s", e)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        parent = thread.parent
        if not isinstance(parent, discord.ForumChannel):
            return

        if parent.id != core.CONST.help_forums:
            return

        await asyncio.sleep(1)

        view = SolvedView(owner=thread.owner_id, thread=thread)
        try:
            message = await thread.send(content=MSG, view=view)
        except discord.HTTPException as e:
            LOGGER.warning("Unable to post solved view: %s", e)
            return

        task = asyncio.create_task(self.disabled_waiter(message, view))
        self.waiters.add(task)
        task.add_done_callback(self.waiters.discard)

    @commands.command(name="solved")
    async def solve_post(self, ctx: commands.Context[core.DiscordBot]) -> None:
        if not isinstance(ctx.channel, discord.Thread):
            return

        if ctx.channel.parent_id != core.CONST.help_forums:
            return

        assert isinstance(ctx.author, discord.Member)
        if ctx.author.id != ctx.channel.owner_id or not any(r.id in ROLES for r in ctx.author.roles):
            return

        await ctx.channel.add_tags(discord.Object(id=TAG_ID), reason="Help Post Solved.")
        await ctx.channel.edit(locked=True, reason="Help Post Solved")


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(HelpChannelCog(bot))
