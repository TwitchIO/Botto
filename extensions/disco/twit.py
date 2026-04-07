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

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands


if TYPE_CHECKING:
    import core


class TwitCog(commands.Cog):
    def __init__(self, bot: core.DiscordBot) -> None:
        self.bot = bot
        self.twit = bot.manager.twitch

    @app_commands.command(name="twitch_user")
    @app_commands.describe(username="The twitch username to fetch.")
    @app_commands.checks.cooldown(2, 10)
    async def fetch_twitch_user(self, interaction: discord.Interaction[core.DiscordBot], username: str) -> None:
        """Fetch basic data about a Twitch User by username."""
        await interaction.response.defer(thinking=True)

        name = username.lower()
        user = await self.twit.fetch_user(login=name)

        if not user:
            await interaction.followup.send(f"Unable to find the user: `{name}`.")
            return

        uid = user.id
        name = user.name
        display = user.display_name
        banner = user.offline_image.url if user.offline_image else None
        image = user.profile_image.url
        created = user.created_at

        embed = discord.Embed(title=display, color=0xF6BA08)
        embed.description = f"```\n{uid}```\n\nCreated-At: `{created}`\nChannel: [{name}](https://twitch.tv/{name})"
        embed.set_thumbnail(url=image)
        embed.set_image(url=banner)

        await interaction.followup.send(embed=embed)

    @fetch_twitch_user.error
    async def fetch_twitch_user_error(
        self,
        interaction: discord.Interaction[core.DiscordBot],
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown: Try again in {error.retry_after}s",
                ephemeral=True,
            )


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(TwitCog(bot))
