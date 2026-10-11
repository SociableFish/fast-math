# SPDX-License-Identifier: GPL-3.0-or-later

import enum
import pathlib
import sys
from typing import final

import pygame.constants

from fast_math import gfx


@final
class Key(enum.Enum):
    """From https://pyga.me/docs/ref/key.html."""
    BACKSPACE = pygame.constants.K_BACKSPACE
    TAB = pygame.constants.K_TAB
    CLEAR = pygame.constants.K_CLEAR
    RETURN = pygame.constants.K_RETURN
    PAUSE = pygame.constants.K_PAUSE
    ESCAPE = pygame.constants.K_ESCAPE
    SPACE = pygame.constants.K_SPACE
    EXCLAIM = pygame.constants.K_EXCLAIM
    QUOTEDBL = pygame.constants.K_QUOTEDBL
    HASH = pygame.constants.K_HASH
    DOLLAR = pygame.constants.K_DOLLAR
    AMPERSAND = pygame.constants.K_AMPERSAND
    QUOTE = pygame.constants.K_QUOTE
    LEFTPAREN = pygame.constants.K_LEFTPAREN
    RIGHTPAREN = pygame.constants.K_RIGHTPAREN
    ASTERISK = pygame.constants.K_ASTERISK
    PLUS = pygame.constants.K_PLUS
    COMMA = pygame.constants.K_COMMA
    MINUS = pygame.constants.K_MINUS
    PERIOD = pygame.constants.K_PERIOD
    SLASH = pygame.constants.K_SLASH
    K_0 = pygame.constants.K_0
    K_1 = pygame.constants.K_1
    K_2 = pygame.constants.K_2
    K_3 = pygame.constants.K_3
    K_4 = pygame.constants.K_4
    K_5 = pygame.constants.K_5
    K_6 = pygame.constants.K_6
    K_7 = pygame.constants.K_7
    K_8 = pygame.constants.K_8
    K_9 = pygame.constants.K_9
    COLON = pygame.constants.K_COLON
    SEMICOLON = pygame.constants.K_SEMICOLON
    LESS = pygame.constants.K_LESS
    EQUALS = pygame.constants.K_EQUALS
    GREATER = pygame.constants.K_GREATER
    QUESTION = pygame.constants.K_QUESTION
    AT = pygame.constants.K_AT
    LEFTBRACKET = pygame.constants.K_LEFTBRACKET
    BACKSLASH = pygame.constants.K_BACKSLASH
    RIGHTBRACKET = pygame.constants.K_RIGHTBRACKET
    CARET = pygame.constants.K_CARET
    UNDERSCORE = pygame.constants.K_UNDERSCORE
    BACKQUOTE = pygame.constants.K_BACKQUOTE
    A = pygame.constants.K_a
    B = pygame.constants.K_b
    C = pygame.constants.K_c
    D = pygame.constants.K_d
    E = pygame.constants.K_e
    F = pygame.constants.K_f
    G = pygame.constants.K_g
    H = pygame.constants.K_h
    I = pygame.constants.K_i  # noqa: E741
    J = pygame.constants.K_j
    K = pygame.constants.K_k
    L = pygame.constants.K_l
    M = pygame.constants.K_m
    N = pygame.constants.K_n
    O = pygame.constants.K_o  # noqa: E741
    P = pygame.constants.K_p
    Q = pygame.constants.K_q
    R = pygame.constants.K_r
    S = pygame.constants.K_s
    T = pygame.constants.K_t
    U = pygame.constants.K_u
    V = pygame.constants.K_v
    W = pygame.constants.K_w
    X = pygame.constants.K_x
    Y = pygame.constants.K_y
    Z = pygame.constants.K_z
    DELETE = pygame.constants.K_DELETE
    KP0 = pygame.constants.K_KP0
    KP1 = pygame.constants.K_KP1
    KP2 = pygame.constants.K_KP2
    KP3 = pygame.constants.K_KP3
    KP4 = pygame.constants.K_KP4
    KP5 = pygame.constants.K_KP5
    KP6 = pygame.constants.K_KP6
    KP7 = pygame.constants.K_KP7
    KP8 = pygame.constants.K_KP8
    KP9 = pygame.constants.K_KP9
    KP_PERIOD = pygame.constants.K_KP_PERIOD
    KP_DIVIDE = pygame.constants.K_KP_DIVIDE
    KP_MULTIPLY = pygame.constants.K_KP_MULTIPLY
    KP_MINUS = pygame.constants.K_KP_MINUS
    KP_PLUS = pygame.constants.K_KP_PLUS
    KP_ENTER = pygame.constants.K_KP_ENTER
    KP_EQUALS = pygame.constants.K_KP_EQUALS
    UP = pygame.constants.K_UP
    DOWN = pygame.constants.K_DOWN
    RIGHT = pygame.constants.K_RIGHT
    LEFT = pygame.constants.K_LEFT
    INSERT = pygame.constants.K_INSERT
    HOME = pygame.constants.K_HOME
    END = pygame.constants.K_END
    PAGEUP = pygame.constants.K_PAGEUP
    PAGEDOWN = pygame.constants.K_PAGEDOWN
    F1 = pygame.constants.K_F1
    F2 = pygame.constants.K_F2
    F3 = pygame.constants.K_F3
    F4 = pygame.constants.K_F4
    F5 = pygame.constants.K_F5
    F6 = pygame.constants.K_F6
    F7 = pygame.constants.K_F7
    F8 = pygame.constants.K_F8
    F9 = pygame.constants.K_F9
    F10 = pygame.constants.K_F10
    F11 = pygame.constants.K_F11
    F12 = pygame.constants.K_F12
    F13 = pygame.constants.K_F13
    F14 = pygame.constants.K_F14
    F15 = pygame.constants.K_F15
    NUMLOCK = pygame.constants.K_NUMLOCK
    CAPSLOCK = pygame.constants.K_CAPSLOCK
    SCROLLOCK = pygame.constants.K_SCROLLOCK
    RSHIFT = pygame.constants.K_RSHIFT
    LSHIFT = pygame.constants.K_LSHIFT
    RCTRL = pygame.constants.K_RCTRL
    LCTRL = pygame.constants.K_LCTRL
    RALT = pygame.constants.K_RALT
    LALT = pygame.constants.K_LALT
    RMETA = pygame.constants.K_RMETA
    LMETA = pygame.constants.K_LMETA
    LSUPER = pygame.constants.K_LSUPER
    RSUPER = pygame.constants.K_RSUPER
    MODE = pygame.constants.K_MODE
    HELP = pygame.constants.K_HELP
    PRINT = pygame.constants.K_PRINT
    SYSREQ = pygame.constants.K_SYSREQ
    BREAK = pygame.constants.K_BREAK
    MENU = pygame.constants.K_MENU
    POWER = pygame.constants.K_POWER
    EURO = pygame.constants.K_EURO
    AC_BACK = pygame.constants.K_AC_BACK


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    MEIPASS = pathlib.Path(sys._MEIPASS).resolve()  # type: ignore
else:
    MEIPASS = pathlib.Path(__file__, "../../..").resolve()  # type: ignore
ASSETS = MEIPASS / "assets"


LOGO = gfx.get_image(ASSETS / "logo.png")


pygame.font.init()


INCONSOLATA_32 = pygame.Font(ASSETS / "inconsolata.ttf", 32)
INCONSOLATA_32_WIDTH = INCONSOLATA_32.size("-")[0]
