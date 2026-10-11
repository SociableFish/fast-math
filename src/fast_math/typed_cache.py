# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
import functools


def cache[**P, R](f: Callable[P, R], /) -> Callable[P, R]:
    return functools.cache(f)  # type: ignore
