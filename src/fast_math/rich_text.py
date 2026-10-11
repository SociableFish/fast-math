# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Iterable, Iterator
import dataclasses
from typing import final

import pygame

from fast_math import gfx


pygame.font.init()


def join[T](
        between: Iterable[T],
        to_join: Iterable[Iterable[T]],
        /
) -> Iterator[T]:
    """Like `str.join` and `bytes.join`, but for any iterables, and returning
an iterator. Generalization of `itertools.chain.from_iterable`."""
    between_list = list[T]()
    for idx, it in enumerate(to_join):
        if idx == 1:
            for i in between:
                yield i
                between_list.append(i)
        elif idx > 1:
            yield from between_list
        yield from it


@final
@dataclasses.dataclass(frozen=True, slots=True)
class RichTextChar:
    char: str
    color: gfx.OpaqueColor = gfx.ACCENT_COLOR

    def __post_init__(self, /) -> None:
        if len(self.char) != 1:
            raise ValueError("RichTextChar must be a single character")


type RichText = Iterable[RichTextChar]


type RichTextTup = tuple[RichTextChar, ...]


def rich_text(
        text: str,
        color: gfx.OpaqueColor = gfx.ACCENT_COLOR,
) -> RichTextTup:
    return tuple(RichTextChar(char=char, color=color) for char in text)


def _render_one_line_multicolor(
        font: pygame.Font,
        chars: RichText,
        line_y: int,
        /
) -> tuple[int, list[gfx.SurfAndPos]]:
    """Gets the X size (from unperturbed characters) and a list of tuples of
surfaces and positions and how to shake them."""
    combined: str = "".join(char.char for char in chars)
    if not combined:
        return (0, [])
    xsize: int = font.size(combined)[0]
    second = list[gfx.SurfAndPos]()
    curr_x: int = 0
    for char, (_, _, _, _, advance) in zip(
        chars,
        font.metrics(combined),
        strict=True
    ):
        second.append((
            font.render(char.char, True, char.color),
            (curr_x, line_y)
        ))
        curr_x += advance
    return xsize, second


def render_as_chars(
        font: pygame.Font,
        text: RichText,
        align: gfx.Align = gfx.Align.MIN,
) -> tuple[tuple[int, int], list[gfx.SurfAndPos]]:
    """Gets the size (from unperturbed characters) and a list of surfaces
and positions."""
    height: int = font.get_height()
    char_line_list = list[list[RichTextChar]]([[]])
    for char in text:
        if char.char == "\n":
            char_line_list.append([])
        else:
            char_line_list[-1].append(char)
    total_lines: int = len(char_line_list)
    line_x_sizes_and_surf_and_pos = list(
        _render_one_line_multicolor(font, chars, height * lineno)
        for lineno, chars in enumerate(char_line_list)
    )
    max_x_size: int = max(x for x, _ in line_x_sizes_and_surf_and_pos)
    result = list[gfx.SurfAndPos]()
    for x_size, surf_and_pos_line in line_x_sizes_and_surf_and_pos:
        x_off: int
        match align:
            case gfx.Align.MIN:
                x_off = 0
            case gfx.Align.MID:
                x_off = (max_x_size - x_size) // 2
            case gfx.Align.MAX:
                x_off = max_x_size - x_size
        for surf, (x_pos, y_pos) in surf_and_pos_line:
            x_pos += x_off
            result.append((surf, (x_pos, y_pos)))
    return ((max_x_size, height * total_lines), result)


def render(
        font: pygame.Font,
        text: RichText,
        align: gfx.Align = gfx.Align.MIN,
        /
) -> pygame.Surface:
    size, surfaces = render_as_chars(font, text, align)
    return gfx.single_surface_from(surfaces, size)


def strip_formatting(text: RichText, /) -> str:
    return "".join(char.char for char in text)


def rich_split(text: RichText, on: str, /) -> tuple[RichTextTup, ...]:
    text = tuple(text)
    raw: list[str] = strip_formatting(text).split(on)
    begin_indices: list[int] = [0]
    for segment in raw[:-1]:
        begin_indices.append(begin_indices[-1] + len(on) + len(segment))
    return tuple(
        text[begin:begin + len(raw[idx])]
        for idx, begin in enumerate(begin_indices)
    )
