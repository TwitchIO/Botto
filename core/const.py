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

from typing import Any


class _CONSTANTS(type):
    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Constant value cannot be set.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Constant value cannot be deleted.")


class CONST(metaclass=_CONSTANTS):
    twitchio: int = 1478717647813214298
    tio_yellow: int = 0xF6BA08
    help_forums: int = 1478721197217812575

    # Roles
    admin_role: int = 1478717860506374207
    maint_role: int = 1478764617214984384
    contributor_role = 1479091582614503587
