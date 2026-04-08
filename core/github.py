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

import datetime
import logging
import pathlib
import time
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Self

import aiohttp
import jwt

from .config import CONFIG


if TYPE_CHECKING:
    from ..types_.github import GHExampleRespT, GHJWTPayloadT, GHTokenRespT


LOGGER: logging.Logger = logging.getLogger("GitHubClient")

GH_BASE: str = "https://api.github.com"
API_VER: str = "2026-03-10"


class GitHubClient:
    session: aiohttp.ClientSession
    JWT_ALG: ClassVar[str] = "RS256"
    __SIGNING_KEY: bytes

    def __init__(self) -> None:
        self._token_data: GHTokenRespT | None = None
        self._example_cache: dict[str, str] = {}

    @property
    def examples(self) -> MappingProxyType[str, str]:
        """A mapping of example name to url."""
        return MappingProxyType(self._example_cache)

    async def __aenter__(self) -> Self:
        await self.setup()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.cleanup()

    async def setup(self) -> None:
        path = pathlib.Path(CONFIG["github"]["private_key"])
        if not path.exists():
            raise RuntimeError("Unable to start GitHubClient: Private Key cannot be found.")

        with path.open("rb") as fp:
            key = fp.read()
            setattr(self, "_GitHubClient__SIGNING_KEY", key)

        self.session = aiohttp.ClientSession()
        await self.refresh_caches()

        LOGGER.info("Successfully setup %s.", repr(self.__class__.__name__))

    async def refresh_caches(self) -> None:
        LOGGER.debug("Attempting to refresh %s caches.", repr(self.__class__.__name__))

        examples = await self.fetch_examples()
        self._example_cache = {e["name"].lower(): e["html_url"] for e in examples}

        LOGGER.info("Refreshed caches on %s.", repr(self.__class__.__name__))

    async def cleanup(self) -> None:
        LOGGER.debug("Attempting to cleanup %s.", repr(self.__class__.__name__))

        setattr(self, "_GitHubClient__SIGNING_KEY", None)
        await self.session.close()

        LOGGER.info("Successfully cleaned up %s.", repr(self.__class__.__name__))

    def headers(self, *, github_json: bool = True, bearer: str | None = None) -> dict[str, str]:
        payload: dict[str, str] = {}
        accept = "application/vnd.github+json" if github_json else "application/json"

        payload["Accept"] = accept
        if bearer:
            payload["Authorization"] = f"Bearer {bearer}"

        payload["X-GitHub-Api-Version"] = API_VER
        return payload

    def generate_jwt(self) -> str:
        payload: GHJWTPayloadT = {
            "iat": int(time.time()) - 10,
            "exp": int(time.time()) + 300,  # 5 minutes expiry
            "iss": CONFIG["github"]["app_id"],
        }

        encoded = jwt.encode(payload, self.__SIGNING_KEY, algorithm=self.JWT_ALG)  # type: ignore
        return encoded

    async def request_token(self) -> None:
        LOGGER.debug("Attempting to generate a new access token for %s.", repr(self.__class__.__name__))

        install_id = CONFIG["github"]["install_id"]
        url = f"{GH_BASE}/app/installations/{install_id}/access_tokens"

        jwt_ = self.generate_jwt()
        headers = self.headers(bearer=jwt_)

        async with self.session.post(url, headers=headers) as resp:
            resp.raise_for_status()

            data: GHTokenRespT = await resp.json()
            self._token_data = data

        LOGGER.debug("Successfully generated a new token for %s.", repr(self.__class__.__name__))

    async def request(self, endpoint: str, *, method: str, headers: dict[str, str] | None = None) -> Any:
        url = f"{GH_BASE}{endpoint}"

        LOGGER.debug("Attempting to make a request on %s: %s-%s", repr(self.__class__.__name__), method, url)

        if headers is None or not headers.get("Authorization"):
            original = headers or {}
            tdata = self._token_data or {}

            expires = tdata.get("expires_at")
            slack = datetime.timedelta(seconds=30)

            if not expires or datetime.datetime.fromisoformat(expires) - slack <= datetime.datetime.now(tz=datetime.UTC):
                await self.request_token()

            tdata = self._token_data
            if not tdata:
                raise RuntimeError("Unable to make request: Invalid token data.")

            headers = self.headers(bearer=tdata["token"])
            headers["Accept"] = original.get("Accept", headers["Accept"])

        async with self.session.request(method, url, headers=headers) as resp:
            resp.raise_for_status()

            LOGGER.debug("Successfully finished request on %s: %s-%s", repr(self.__class__.__name__), method, url)
            return await resp.json()

    async def fetch_examples(self) -> list[GHExampleRespT]:
        endpoint = "/repos/TwitchIO/TwitchIO/contents/examples"
        data: list[GHExampleRespT] = await self.request(endpoint, method="GET")

        return data
