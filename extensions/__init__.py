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

import logging
import pathlib

import core


LOGGER: logging.Logger = logging.getLogger(__name__)


async def discord_setup(bot: core.DiscordBot) -> None:
    ext_path = pathlib.Path("extensions/disco")
    loaded: list[str] = []

    for ext in ext_path.glob("*.py"):
        try:
            await bot.load_extension(f"extensions.disco.{ext.stem}")
        except Exception as e:
            LOGGER.error("Failed to load discord extension %s: %s", ext.name, e)
        else:
            loaded.append(ext.name)

    LOGGER.info("Successfully loaded discord extensions: %r", loaded)


async def twitch_setup(bot: core.TwitchBot) -> None:
    ext_path = pathlib.Path("extensions/twit")
    loaded: list[str] = []

    for ext in ext_path.glob("*.py"):
        try:
            await bot.load_module(f"extensions.twit.{ext.stem}")
        except Exception as e:
            LOGGER.error("Failed to load twitch extension %s: %s", ext.name, e)
        else:
            loaded.append(ext.name)

    LOGGER.info("Successfully loaded twitch extensions: %r", loaded)


async def setup(bot: core.DiscordBot | core.TwitchBot) -> None:
    if isinstance(bot, core.DiscordBot):
        await discord_setup(bot)
    else:
        await twitch_setup(bot)
