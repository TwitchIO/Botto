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


class InfoCog(commands.Cog):
    def __init__(self, bot: core.DiscordBot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(example="The specific example to fetch")
    async def examples(self, interaction: discord.Interaction[core.DiscordBot], example: str | None = None) -> None:
        """Fetch an example from the TwitchIO Github."""
        if not example:
            msg = "**TwitchIO Examples**:\n<https://github.com/TwitchIO/TwitchIO/tree/main/examples>"
            await interaction.response.send_message(msg)
            return

        await interaction.response.send_message(f"<{example}>")

    @examples.autocomplete("example")
    async def example_autocomplete(
        self, interaction: discord.Interaction[core.DiscordBot], value: str
    ) -> list[app_commands.Choice[str]]:
        examples = self.bot.ghc.examples

        if not examples:
            await self.bot.ghc.refresh_caches()

        choices = [app_commands.Choice(name=e.name, value=e.url) for e in examples if value.lower() in e.name.lower()]
        return choices


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(InfoCog(bot))
