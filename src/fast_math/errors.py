# SPDX-License-Identifier: GPL-3.0-or-later

import abc
import sys
from tkinter import messagebox
from typing import NoReturn, Protocol, runtime_checkable

import pygame

from fast_math import files
from fast_math.files import StrPath


@runtime_checkable
class CustomErrorMessageBox(Protocol):
    """Deriving from this protocol is useless if one does not also derive from
`Exception`."""
    __slots__ = ()

    @property
    @abc.abstractmethod
    def title(self, /) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def message(self, /) -> str:
        raise NotImplementedError


def showerror_exit(*, title: str, message: str) -> NoReturn:
    """Closes the display and shows an error message box before calling
`sys.exit(1)`."""
    pygame.display.quit()
    messagebox.showerror(title=title, message=message)
    sys.exit(1)


def raise_with_title_and_message(
        exc: BaseException,
        /,
        *,
        title: str,
        message: str
) -> NoReturn:
    exc.title = title  # type: ignore
    exc.message = message  # type: ignore
    raise exc


def invalid_internal_path(path: StrPath, /) -> NoReturn:
    raise_with_title_and_message(
        ValueError(),
        title="Invalid internal file or folder!",
        message=str(files.absolute(path))
    )
