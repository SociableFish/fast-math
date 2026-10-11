# SPDX-License-Identifier: GPL-3.0-or-later

import abc
from collections.abc import Iterable, Iterator
import contextlib
import dataclasses
import enum
import math
import re
from typing import final, Generator, Generic, Literal, NamedTuple, Protocol, \
    TypeVar

import numpy as np
import pygame

from fast_math import errors
from fast_math import files
from fast_math.files import AbsPath, StrPath
from fast_math import typed_cache


type SurfAndPos = tuple[pygame.Surface, tuple[int, int]]


type Surfarray = np.ndarray[tuple[int, int, Literal[4]], np.dtype[np.uint8]]


@final
class Align(enum.Enum):
    MIN = enum.auto()
    MID = enum.auto()
    MAX = enum.auto()


@final
@dataclasses.dataclass(frozen=True, slots=True)
class Rect:
    """Like `pygame.Rect`, but immutable, not a tuple, and must have
non-negative width and height. `__contains__` uses a closed set."""
    x: int
    y: int
    w: int
    h: int

    def __post_init__(self, /) -> None:
        if self.w < 0 or self.h < 0:
            raise ValueError("w and h must be positive")

    def __contains__(self, other: tuple[int, int] | Rect, /) -> bool:
        if isinstance(other, tuple):
            other = Rect(*other, 0, 0)
        return (
            self.xmin <= other.xmin
            and other.xmax <= self.xmax
            and self.ymin <= other.ymin
            and other.ymax <= self.ymax
        )

    @staticmethod
    def bounds_points(p1: tuple[int, int], /, *ps: tuple[int, int]) -> Rect:
        (xmin, ymin), (xmax, ymax) = p1, p1
        for px, py in ps:
            xmin = min(xmin, px)
            xmax = max(xmax, px)
            ymin = min(ymin, py)
            ymax = max(ymax, py)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)

    @property
    def rect(self, /) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    @property
    def xmin(self, /) -> int:
        return self.x

    @property
    def xmax(self, /) -> int:
        return self.x + self.w

    @property
    def ymin(self, /) -> int:
        return self.y

    @property
    def ymax(self, /) -> int:
        return self.y + self.h

    def pos(self, rx: int | Align, ry: int | Align, /) -> tuple[int, int]:
        x: int = self.x
        y: int = self.y
        match rx:
            case Align.MIN:
                pass
            case Align.MID:
                x += self.w // 2
            case Align.MAX:
                x += self.w
            case int():
                x += rx
        match ry:
            case Align.MIN:
                pass
            case Align.MID:
                y += self.h // 2
            case Align.MAX:
                y += self.h
            case int():
                y += ry
        return (x, y)

    def pos_and_args(
            self,
            rx: Align,
            ry: Align,
            /
    ) -> tuple[tuple[int, int], tuple[Align, Align]]:
        return self.pos(rx, ry), (rx, ry)

    def shift_edges(
            self,
            /,
            *,
            top: int = 0,
            bottom: int = 0,
            left: int = 0,
            right: int = 0
    ) -> Rect:
        return Rect.bounds_points(
            (self.xmin + left, self.ymin + top),
            (self.xmax + right, self.ymax + bottom)
        )

    def shift_in(self, by: int, /) -> Rect:
        return self.shift_edges(top=by, bottom=-by, left=by, right=-by)

    def only(
            self,
            /,
            *,
            top: int | None = None,
            bottom: int | None = None,
            left: int | None = None,
            right: int | None = None
    ) -> Rect:
        if top is None:
            top = self.h
        if bottom is None:
            bottom = self.h
        if left is None:
            left = self.w
        if right is None:
            right = self.w
        top = min(max(top, 0), self.h)
        bottom = min(max(bottom, self.h - top), self.h)
        left = min(max(left, 0), self.w)
        right = min(max(right, self.w - left), self.w)
        return self.shift_edges(
            top=self.h - bottom,
            bottom=top - self.h,
            left=self.w - right,
            right=left - self.w
        )


WIDTH = 640
HEIGHT = 480
DIMENSIONS = (WIDTH, HEIGHT)


UI_PAD = 10


SCREEN_RECT = Rect(0, 0, WIDTH, HEIGHT)


_Alpha = TypeVar("_Alpha", bound=int, covariant=True, default=int)


_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


@final
class Color(Generic[_Alpha], NamedTuple):
    """Like `pygame.Color`, but immutable."""
    r: int
    g: int
    b: int
    a: _Alpha

    @staticmethod
    def opaque(r: int, g: int, b: int, /) -> OpaqueColor:
        return Color[Literal[255]](r, g, b, 255)

    @staticmethod
    def from_hex(hex: str, /) -> OpaqueColor:
        if not _HEX_COLOR.fullmatch(hex):
            raise ValueError("hex is not a hex color")
        return Color.opaque(
            int(hex[1:3], base=16),
            int(hex[3:5], base=16),
            int(hex[5:7], base=16)
        )


BLACK = Color.from_hex("#000000")
WHITE = Color.from_hex("#FFFFFF")
RED = Color.from_hex("#FF0000")
ACCENT_COLOR = Color.from_hex("#004AAD")
LIGHT_BLUE = Color.from_hex("#80B6FD")
TRANSPARENT = Color[Literal[0]](0, 0, 0, 0)


type OpaqueColor = Color[Literal[255]]


class _HasLockUnlock(Protocol):
    @abc.abstractmethod
    def lock(self, /) -> object:
        raise NotImplementedError

    @abc.abstractmethod
    def unlock(self, /) -> object:
        raise NotImplementedError


@contextlib.contextmanager
def lock_unlock(obj: _HasLockUnlock, /) -> Generator[None]:
    obj.lock()
    try:
        yield
    finally:
        obj.unlock()


def unicolor_surface(
        xsize: int,
        ysize: int,
        color: Color[int],
        /
) -> pygame.Surface:
    result = pygame.Surface((xsize, ysize), pygame.SRCALPHA, 32)
    result.fill(color)
    return result


@typed_cache.cache
def _cached_image_load(filename: AbsPath, /) -> pygame.Surface:
    try:
        # To force a FileNotFoundError to include the filename
        with open(filename, "rb") as file:
            return pygame.image.load(file, namehint=str(filename))
    except pygame.error as exc:
        errors.raise_with_title_and_message(
            exc,
            title="Invalid image",
            message=f"{filename!r} is not an image of a recognized format"
        )


def get_image(filename: StrPath, /) -> pygame.Surface:
    shared: pygame.Surface = \
        _cached_image_load(files.absolute(filename))
    result: pygame.Surface = unicolor_surface(*shared.size, TRANSPARENT)
    result.blit(shared)
    return result


def blit(
        dst: pygame.Surface,
        src: pygame.Surface,
        pos: tuple[float, float],
        align: tuple[Align, Align],
        /
) -> None:
    blit_x: float = pos[0]
    blit_y: float = pos[1]
    src_xsize, src_ysize = src.size
    match align[0]:
        case Align.MIN:
            pass
        case Align.MID:
            blit_x -= src_xsize / 2
        case Align.MAX:
            blit_x -= src_xsize
    match align[1]:
        case Align.MIN:
            pass
        case Align.MID:
            blit_y -= src_ysize / 2
        case Align.MAX:
            blit_y -= src_ysize
    dst.blit(src, (blit_x, blit_y))


def offset(
        surfs: Iterable[SurfAndPos],
        /,
        x: int = 0,
        y: int = 0
) -> Iterator[SurfAndPos]:
    return ((surf, (px + x, py + y)) for surf, (px, py) in surfs)


def single_surface_from(
        surf_and_pos: Iterable[SurfAndPos],
        size: tuple[int, int],
        /
) -> pygame.Surface:
    result: pygame.Surface = unicolor_surface(*size, TRANSPARENT)
    result.blits(surf_and_pos)
    return result


def to_surfarray(surf: pygame.Surface, /) -> Surfarray:
    """Mutable array of dtype `uint8` and shape `surf.size + (4,)` returned."""
    result = np.zeros(surf.size + (4,), dtype=np.uint8)
    with lock_unlock(surf):
        result[:, :, :3] = pygame.surfarray.array3d(surf)
        result[:, :, 3] = pygame.surfarray.array_alpha(surf)
    return result


def from_surfarray(arr: Surfarray, /) -> pygame.Surface:
    """Array of dtype `uint8` and shape `<result>.size + (4,)` expected."""
    result = unicolor_surface(*arr.shape[:2], TRANSPARENT)
    rshift, gshift, bshift, ashift = result.get_shifts()
    pygame.surfarray.blit_array(
        result,
        (arr[:, :, 0].astype(np.uint32) << np.uint32(rshift))
        | (arr[:, :, 1].astype(np.uint32) << np.uint32(gshift))
        | (arr[:, :, 2].astype(np.uint32) << np.uint32(bshift))
        | (arr[:, :, 3].astype(np.uint32) << np.uint32(ashift))
    )
    return result


def line_as_thin_rect(
        surf: pygame.Surface,
        color: OpaqueColor,
        p1: tuple[float, float],
        p2: tuple[float, float],
        thickness: int,
        /
) -> None:
    if thickness <= 0:
        return
    # pygame-ce does not use order-independent algorithms
    # Canonicalization step
    if p1 > p2:
        p1, p2 = p2, p1
    if thickness == 1:
        pygame.draw.line(surf, color, p1, p2)
        return
    p1x, p1y = p1
    p2x, p2y = p2
    perpx: float = p2y - p1y
    perpy: float = p1x - p2x
    if (linelen := math.hypot(perpx, perpy)) < 0.5:
        return
    perpx = perpx / linelen * thickness / 2
    perpy = perpy / linelen * thickness / 2
    # Canonicalization step
    verts: tuple[tuple[float, float], ...] = (
        (p1x + perpx, p1y + perpy),
        (p2x + perpx, p2y + perpy),
        (p2x - perpx, p2y - perpy),
        (p1x - perpx, p1y - perpy)
    )
    # Booth's algorithm not used because O(N^2) is for N=4
    verts = min(
        min(verts[i:] + verts[:i], verts[::-1][i:] + verts[::-1][:i])
        for i in range(len(verts))
    )
    pygame.draw.polygon(surf, color, verts)
