# SPDX-License-Identifier: GPL-3.0-or-later

import os
import traceback
from typing import Any, NoReturn

import pygame

from fast_math import errors
from fast_math.errors import CustomErrorMessageBox
from fast_math import gfx
from fast_math import screens


def main() -> NoReturn:
    try:
        pygame.display.init()
        window: pygame.Surface = \
            pygame.display.set_mode(gfx.DIMENSIONS, vsync=True)
        # pygame.display.set_icon(LOGO)
        pygame.display.set_caption("FAST MATH")
        screens.State(window).event_loop()
    except FileNotFoundError as exc:
        filename: Any = exc.filename
        if not isinstance(filename, str | bytes):
            errors.showerror_exit(
                title="FileNotFoundError from library has invalid filename",
                message=traceback.format_exc()
            )
        if isinstance(filename, bytes):
            filename = os.fsdecode(filename)
        errors.showerror_exit(
            title="File or directory not found",
            message=f"Expected file or directory at {filename!r}"
        )
    except Exception as exc:
        if isinstance(exc, CustomErrorMessageBox):
            errors.showerror_exit(title=exc.title, message=exc.message)
        errors.showerror_exit(
            title="Unhandled exception!",
            message=traceback.format_exc()
        )
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
