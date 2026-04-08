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

import os
import re
import zlib
from io import BytesIO
from typing import TYPE_CHECKING, NamedTuple

import discord
import rapidfuzz as fuzzy
from discord import app_commands
from discord.ext import commands
from yarl import URL

from core import CONST


if TYPE_CHECKING:
    from collections.abc import Generator

    import core


class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer: bytes) -> None:
        self.stream = BytesIO(buffer)

    def readline(self) -> str:
        return self.stream.readline().decode("utf-8")

    def skipline(self) -> None:
        self.stream.readline()

    def read_compressed_chunks(self) -> Generator[bytes]:
        decompressor = zlib.decompressobj()

        while True:
            chunk = self.stream.read(self.BUFSIZE)

            if len(chunk) == 0:
                break

            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self) -> Generator[str]:
        buf = b""

        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b"\n")

            while pos != -1:
                yield buf[:pos].decode("utf-8")

                buf = buf[pos + 1 :]
                pos = buf.find(b"\n")


class RTFXDetails(NamedTuple):
    raw_url: str | None
    token: str | None

    @property
    def url(self) -> URL | None:
        if self.raw_url:
            return URL(self.raw_url)

        return None


class InfoCog(commands.Cog):
    _rtfm_cache: dict[str, dict[str, str]]

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

        value = self.bot.ghc.examples.get(example)
        if not value:
            matches = fuzzy.process.extract(
                example,
                self.bot.ghc.examples,
                scorer=fuzzy.fuzz.WRatio,
                limit=3,
                processor=fuzzy.utils.default_process,
                score_cutoff=50,
            )

            if not matches:
                await interaction.response.send_message(f"No examples found for query: `{example}`")
                return

            value = "\n".join(f"<{m[0]}>" for m in matches[:3])
        else:
            value = f"<{value}>"

        await interaction.response.send_message(value)

    @examples.autocomplete("example")
    async def example_autocomplete(
        self,
        interaction: discord.Interaction[core.DiscordBot],
        value: str,
    ) -> list[app_commands.Choice[str]]:
        if not self.bot.ghc.examples:
            await self.bot.ghc.refresh_caches()

        choices = [app_commands.Choice(name=e, value=e) for e in self.bot.ghc.examples if value.lower() in e]
        return choices

    def parse_object_inv(self, stream: SphinxObjectFileReader, url: str) -> dict[str, str]:
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result: dict[str, str] = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        _ = stream.readline().rstrip()[11:]
        stream.readline().rstrip()[11:]  # move the buffer along

        # next line says if it's a zlib header
        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, _, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            key = key.replace("twitchio.ext.commands.", "").replace("twitchio.", "")
            result[f"{prefix}{key}"] = os.path.join(url, location)  # noqa: PTH118

        return result

    async def build_rtfm_lookup_table(self) -> None:
        cache: dict[str, dict[str, str]] = {}
        key = "twitchio"
        page = "https://twitchio.dev/en/latest"
        cache[key] = {}

        async with self.bot.session.get(page + "/objects.inv") as resp:
            if resp.status != 200:
                msg_ = f"Cannot build rtfm lookup table for {page}, try again later."
                raise RuntimeError(msg_)

            stream = SphinxObjectFileReader(await resp.read())
            cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: commands.Context[core.DiscordBot], key: str, obj: str | None) -> None:
        if obj is None:
            await ctx.send("<https://twitchio.dev/en/latest>")
            return None

        if not hasattr(self, "_rtfm_cache"):
            await ctx.typing()
            await self.build_rtfm_lookup_table()

        obj = re.sub(r"^(?:twitchio\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)
        matches = fuzzy.process.extract(
            obj,
            self._rtfm_cache[key],
            scorer=fuzzy.fuzz.WRatio,
            limit=8,
            score_cutoff=30,
        )

        if not matches:
            await ctx.send("Could not find any documentaiton with that query.")

        embed = discord.Embed(colour=CONST.tio_yellow)
        embed.description = "\n".join(f"[`{m[2]}`]({m[0]})" for m in matches)

        await ctx.reply(embed=embed)  # type: ignore

    async def rtfm_slash_autocomplete(
        self,
        interaction: discord.Interaction[core.DiscordBot],
        value: str,
    ) -> list[app_commands.Choice[str]]:
        if not hasattr(self, "_rtfm_cache"):
            await interaction.response.autocomplete([])
            await self.build_rtfm_lookup_table()
            return []

        if not value:
            return []

        if len(value) < 3:
            return [app_commands.Choice(name=value, value=value)]

        assert interaction.command is not None

        matches = fuzzy.process.extract(
            value,
            self._rtfm_cache["twitchio"],
            scorer=fuzzy.fuzz.WRatio,
            limit=8,
            score_cutoff=30,
        )
        return [app_commands.Choice(name=m[2], value=m[2]) for m in matches]

    @commands.hybrid_command(aliases=["rtfd", "rtfm"])
    @app_commands.describe(entry="The documentation entry to search for.")
    @app_commands.autocomplete(entry=rtfm_slash_autocomplete)
    async def rtd(self, ctx: commands.Context[core.DiscordBot], *, entry: str | None = None) -> None:
        """Gives you a documentation link for twitchio based on your search. Uses fuzzy matching."""
        await self.do_rtfm(ctx, "twitchio", entry)


async def setup(bot: core.DiscordBot) -> None:
    await bot.add_cog(InfoCog(bot))
