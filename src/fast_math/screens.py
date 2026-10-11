# SPDX-License-Identifier: GPL-3.0-or-later

import abc
from collections.abc import Callable
import copy
import dataclasses
import datetime as dt
import enum
import sys
from typing import ClassVar, final, Generic, override, NoReturn, Protocol, \
    TypeVar

import numpy as np
import pygame

from fast_math.constants import Key, LOGO, INCONSOLATA_32, INCONSOLATA_32_WIDTH
from fast_math.frozendict import FrozenDict
from fast_math import gfx
from fast_math import rich_text
from fast_math.quizzes import InvalidAnswerReason, Answer, Question, \
    random_int_add_sub_question, random_int_mul_question, \
    random_int_div_question, random_fraction_add_sub_question, \
    random_fraction_mul_div_question, repeat_calls
from fast_math.time_utils import TimePoint, Stopwatch, ImmutableStopwatch, \
    Timer, seconds_string


_T_co = TypeVar("_T_co", covariant=True)


@final
class KeySet(frozenset[Key], enum.Enum):
    """`frozenset`s of `Key`s with special meaning for the UI."""
    # To quickly advance in a quiz by not pressing a mouse button
    ENTER = frozenset((Key.RETURN, Key.KP_ENTER))
    # "0123456789-/. " is all you need for any integer, decimal, proper
    # fraction, improper fraction, or mixed number
    # Delete and OVR not implemented due to the cursor being fixed to the end
    K_0 = frozenset((Key.K_0, Key.KP0))
    K_1 = frozenset((Key.K_1, Key.KP1))
    K_2 = frozenset((Key.K_2, Key.KP2))
    K_3 = frozenset((Key.K_3, Key.KP3))
    K_4 = frozenset((Key.K_4, Key.KP4))
    K_5 = frozenset((Key.K_5, Key.KP5))
    K_6 = frozenset((Key.K_6, Key.KP6))
    K_7 = frozenset((Key.K_7, Key.KP7))
    K_8 = frozenset((Key.K_8, Key.KP8))
    K_9 = frozenset((Key.K_9, Key.KP9))
    MINUS = frozenset((Key.MINUS, Key.KP_MINUS))
    SLASH = frozenset((Key.SLASH, Key.KP_DIVIDE))
    PERIOD = frozenset((Key.PERIOD,))
    SPACE = frozenset((Key.SPACE,))
    BACKSPACE = frozenset((Key.BACKSPACE,))


_KEYS_TO_CHARS = FrozenDict({
    KeySet.K_0: "0",
    KeySet.K_1: "1",
    KeySet.K_2: "2",
    KeySet.K_3: "3",
    KeySet.K_4: "4",
    KeySet.K_5: "5",
    KeySet.K_6: "6",
    KeySet.K_7: "7",
    KeySet.K_8: "8",
    KeySet.K_9: "9",
    KeySet.MINUS: "-",
    KeySet.SLASH: "/",
    KeySet.PERIOD: ".",
    KeySet.SPACE: ".",
})


class MouseButton(enum.IntEnum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Input:
    held_for: FrozenDict[Key | MouseButton, ImmutableStopwatch] = FrozenDict()
    one_of_held_for: FrozenDict[KeySet, ImmutableStopwatch] = FrozenDict()
    mouse_pos: tuple[int, int] = (0, 0)

    def input_held_for(self, input: Key | MouseButton, /) -> dt.timedelta:
        """Outputs `datetime.timedelta()` if it is not held."""
        if (held_for := self.held_for.get(input)) is not None:
            return held_for.elapsed
        return dt.timedelta()

    def key_set_held_for(self, key_set: KeySet, /) -> dt.timedelta:
        """Outputs `datetime.timedelta()` if it is not held."""
        if (held_for := self.one_of_held_for.get(key_set)) is not None:
            return held_for.elapsed
        return dt.timedelta()

    def as_key_set(self, /) -> KeySet | None:
        if not (
            just_pressed :=
            [k for k, v in self.one_of_held_for.items() if not v.elapsed]
        ):
            return None
        return just_pressed[0]

    def mouse_just_pressed(self, input: MouseButton, /) -> bool:
        match self.held_for.get(input):
            case ImmutableStopwatch(elapsed=elapsed) if not elapsed:
                return True
            case _:
                return False


class Screen(Protocol):
    """Callable with a state."""
    __slots__ = ()

    @abc.abstractmethod
    def __call__(self, state: State, /) -> None:
        raise NotImplementedError


@final
@dataclasses.dataclass(frozen=True, slots=True)
class TitleScreen(Screen):
    from_entry: Stopwatch

    @override
    def __call__(self, state: State, /) -> None:
        self.from_entry.running = True
        seconds: float = self.from_entry.elapsed.total_seconds()
        logo_brightness: float = max(0, 1 - (1 - min(max(seconds, 0), 1)) ** 2)
        credits_brightness: float = \
            max(0, 1 - (1 - min(max(seconds - 1, 0), 1)) ** 2)
        faded_logo = gfx.to_surfarray(LOGO).astype(np.uint32)
        faded_logo[:, :, 3] *= round(logo_brightness * (1 << 24))
        faded_logo[:, :, 3] >>= 24
        faded_credits = gfx.to_surfarray(rich_text.render(
            INCONSOLATA_32,
            rich_text.rich_text("Made by SociableFish")
        )).astype(np.uint32)
        faded_credits[:, :, 3] *= round(credits_brightness * (1 << 24))
        faded_credits[:, :, 3] >>= 24
        gfx.blit(
            state.window,
            gfx.from_surfarray(faded_logo.astype(np.uint8)),
            (gfx.WIDTH // 2, gfx.HEIGHT // 2),
            (gfx.Align.MID, gfx.Align.MID)
        )
        gfx.blit(
            state.window,
            gfx.from_surfarray(faded_credits.astype(np.uint8)),
            (gfx.WIDTH // 2, gfx.HEIGHT // 2 + faded_logo.shape[1] // 2),
            (gfx.Align.MID, gfx.Align.MIN)
        )
        if seconds >= 3:
            state.screen = MAIN_MENU


def draw_top_get_back_clicked_rect(
        state: State,
        top_text: str,
        /,
        *,
        show_back: bool = True
) -> tuple[bool, gfx.Rect]:
    result = gfx.Rect(0, 0, *gfx.DIMENSIONS).shift_in(gfx.UI_PAD)
    gfx.blit(
        state.window,
        rich_text.render(
            INCONSOLATA_32,
            rich_text.rich_text(top_text), gfx.Align.MID
        ),
        *result.pos_and_args(gfx.Align.MID, gfx.Align.MIN)
    )
    bottom_rect: gfx.Rect = result.shift_edges(top=32 + gfx.UI_PAD)
    if not show_back:
        return False, bottom_rect
    blue_back = rich_text.rich_text("< Back")
    black_back = rich_text.rich_text("< Back", gfx.BLACK)
    back_text = rich_text.render(INCONSOLATA_32, blue_back)
    back_hover: bool = state.input.mouse_pos in \
        gfx.Rect(gfx.UI_PAD, gfx.UI_PAD, *back_text.size)
    if back_hover:
        back_text = rich_text.render(INCONSOLATA_32, black_back)
    gfx.blit(
        state.window,
        back_text,
        *result.pos_and_args(gfx.Align.MIN, gfx.Align.MIN)
    )
    return (
        (
            back_hover
            and state.input.mouse_just_pressed(MouseButton.LEFT)
        ),
        result.shift_edges(top=32 + gfx.UI_PAD)
    )


@final
@dataclasses.dataclass(frozen=True, slots=True)
class SelectScreen(Screen):
    """Paginated selection screen. Requires at least one option to select.
Supports "options" that do nothing to simulate a more complex screen with
buttons."""
    MAX_OPTIONS: ClassVar[int] = 10
    title: str
    options: tuple[tuple[str, Callable[[State], Screen] | None], ...]
    page: int = 0
    show_back: bool = dataclasses.field(default=True, kw_only=True)

    def __post_init__(self, /) -> None:
        pages: int = (len(self.options) - 1) // SelectScreen.MAX_OPTIONS + 1
        if self.page not in range(pages):
            raise IndexError

    @property
    def pages(self, /) -> int:
        return (len(self.options) - 1) // SelectScreen.MAX_OPTIONS + 1

    def moved_up(self, /) -> SelectScreen:
        return copy.replace(self, page=max(self.page - 1, 0))

    def moved_down(self, /) -> SelectScreen:
        return copy.replace(self, page=min(self.page + 1, self.pages - 1))

    @override
    def __call__(
            self: SelectScreen,
            state: State,
            /
    ) -> None:
        title: str
        names: list[str]
        option_offset: int
        prev_page_idx: int | None
        next_page_idx: int | None
        if self.pages == 1:
            title = self.title
            names = [name for name, _ in self.options]
            option_offset = 0
            prev_page_idx = None
            next_page_idx = None
        else:
            start_idx: int = self.page * SelectScreen.MAX_OPTIONS
            end_idx: int = start_idx + SelectScreen.MAX_OPTIONS
            title = f"{self.title} (Page {self.page + 1}/{self.pages})"
            names = (
                [
                    f"Page {self.page}/{self.pages}" if self.page else ""
                ]
                + [
                    self.options[idx][0]
                    for idx in range(len(self.options))[start_idx:end_idx]
                ]
                + [
                    f"Page {self.page + 2}/{self.pages}"
                    if self.page != self.pages - 1
                    else ""
                ]
            )
            option_offset = start_idx - 1
            prev_page_idx = 0
            next_page_idx = len(names) - 1
        back, draw_in = draw_top_get_back_clicked_rect(
            state,
            title,
            show_back=self.show_back
        )
        buttons = [
            rich_text.render(INCONSOLATA_32, rich_text.rich_text(name))
            for name in names
        ]
        to_blits = [
            (
                surface,
                (
                    draw_in.x + (draw_in.w - surface.width) // 2,
                    draw_in.y
                    + draw_in.h // 2
                    - 16 * len(buttons)
                    + 32 * btn_idx
                )
            )
            for btn_idx, surface in enumerate(buttons)
        ]
        mouse_pos: tuple[int, int] = state.input.mouse_pos
        hover_idx: int | None = None
        for btn_idx, (surface, pos) in enumerate(to_blits):
            if (
                btn_idx != prev_page_idx
                and btn_idx != next_page_idx
                and self.options[btn_idx + option_offset][1] is None
            ):
                continue
            if mouse_pos not in gfx.Rect(*pos, *surface.size):
                continue
            new_surf = rich_text.render(
                INCONSOLATA_32,
                rich_text.rich_text(names[btn_idx], gfx.BLACK)
            )
            to_blits[btn_idx] = (new_surf, to_blits[btn_idx][1])
            hover_idx = btn_idx
            break
        state.window.blits(to_blits)
        if back:
            state.move_to_parent_screen()
        elif (
            hover_idx is not None
            and state.input.mouse_just_pressed(MouseButton.LEFT)
        ):
            if hover_idx == prev_page_idx:
                state.screen = self.moved_up()
            elif hover_idx == next_page_idx:
                state.screen = self.moved_down()
            elif (transition := self.options[hover_idx + option_offset][1]) \
                    is not None:
                state.move_to_child_screen(transition(state))


_REASON_TO_STR = FrozenDict({
    InvalidAnswerReason.MORE_CHARS_NEEDED: "More characters needed",
    InvalidAnswerReason.INVALID_CHAR: "Invalid characters present",
    InvalidAnswerReason.LEADING_ZEROS: "Leading zeros not allowed",
    InvalidAnswerReason.REDUNDANT_SIGN: "Redundant signs not allowed",
})


def show_quiz_question_and_went_back(
        *,
        state: State,
        curr_question: Question[object],
        curr_answer: Answer[object],
        curr_question_idx: int,
        questions: int,
        time: dt.timedelta | None,
        red_text_below: str,
) -> bool:
    back, draw_in = draw_top_get_back_clicked_rect(
        state,
        f"{curr_question_idx + 1}/{questions}"
    )
    if time is not None:
        gfx.blit(
            state.window,
            rich_text.render(
                INCONSOLATA_32,
                rich_text.rich_text(seconds_string(time))
            ),
            *draw_in.pos_and_args(gfx.Align.MID, gfx.Align.MIN)
        )
        draw_in = draw_in.shift_edges(top=32)
    answer_width: int = Answer.MAX_LEN * INCONSOLATA_32_WIDTH
    answer_rect = gfx.Rect(
        x=draw_in.x + (draw_in.w - answer_width) // 2,
        y=draw_in.y + draw_in.h // 2 - 16,
        w=answer_width,
        h=32
    )
    above_answer: gfx.Rect = draw_in.only(top=draw_in.h // 2 - 16)
    below_answer: gfx.Rect = draw_in.only(bottom=draw_in.h // 2 - 16)
    gfx.blit(
        state.window,
        rich_text.render(
            INCONSOLATA_32,
            rich_text.rich_text(
                f"{curr_question.question}\n"
                f"{curr_answer.enter_as_parens()}"
            ),
            gfx.Align.MID
        ),
        *above_answer.pos_and_args(gfx.Align.MID, gfx.Align.MID)
    )
    state.window.fill(gfx.LIGHT_BLUE, answer_rect)
    gfx.blit(
        state.window,
        rich_text.render(
            INCONSOLATA_32,
            rich_text.rich_text(curr_answer.value, color=gfx.BLACK)
        ),
        *answer_rect.pos_and_args(gfx.Align.MID, gfx.Align.MID)
    )
    gfx.blit(
        state.window,
        rich_text.render(
            INCONSOLATA_32,
            rich_text.rich_text(red_text_below, color=gfx.RED)
        ),
        *below_answer.pos_and_args(gfx.Align.MID, gfx.Align.MID)
    )
    return back


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ReviewIncorrectAnswer(Screen):
    question: Question[object]
    answer: Answer[object]
    index: int
    questions: int

    @override
    def __call__(self, state: State, /) -> None:
        if show_quiz_question_and_went_back(
            state=state,
            curr_question=self.question,
            curr_answer=self.answer,
            curr_question_idx=self.index,
            questions=self.questions,
            time=None,
            red_text_below=f"Correct answer: {self.question.correct_answer!s}",
        ):
            state.move_to_parent_screen()
            return


@final
@dataclasses.dataclass(frozen=True, slots=True)
class QuizResults:
    questions: int
    correct: int
    incorrect: tuple[tuple[int, Question[object], Answer[object]], ...]
    time: dt.timedelta


@final
class QuizScreen(Screen):
    """The main screen of the app."""
    __slots__ = (
        "_from_entry",
        "_questions",
        "_answers",
        "_invalid_answer_reason",
        "_clear_reason",
    )
    _from_entry: ImmutableStopwatch
    _questions: tuple[Question[object], ...]
    _answers: list[Answer[object]]
    _invalid_answer_reason: str
    _clear_reason: Timer

    def __init__(
            self,
            /,
            *,
            state: State,
            questions: tuple[Question[object], ...],
    ) -> None:
        if not questions:
            raise ValueError("At least 1 question required")
        self._from_entry = state.stopwatch_started_now()
        self._questions = questions
        self._answers = [questions[0].answer_type()]
        self._invalid_answer_reason = ""
        self._clear_reason = Timer(GetCurrFrame(state))
        self._clear_reason.running = True

    @staticmethod
    def maker[**P](
            questions: int,
            question_maker: Callable[P, Question[object]],
            /,
            *args: P.args,
            **kwargs: P.kwargs
    ) -> Callable[[State], QuizScreen]:
        if questions <= 0:
            raise ValueError("questions > 0 required")
        return lambda state: QuizScreen(
            state=state,
            questions=tuple(
                repeat_calls(questions, question_maker, *args, **kwargs)
            )
        )

    @property
    def curr_question_idx(self, /) -> int:
        return len(self._answers) - 1

    @property
    def curr_question(self, /) -> Question[object]:
        return self._questions[self.curr_question_idx]

    @property
    def curr_answer(self, /) -> Answer[object]:
        return self._answers[-1]

    @curr_answer.setter
    def curr_answer(self, to: Answer[object], /) -> None:
        self._answers[-1] = to

    def advance(self, /) -> None | QuizResults | InvalidAnswerReason:
        if isinstance(
            reason := self.curr_answer.as_number(),
            InvalidAnswerReason
        ):
            return reason
        if self.curr_question_idx != len(self._questions) - 1:
            self._answers.append(
                self._questions[self.curr_question_idx + 1].answer_type()
            )
            return None
        correct: int = 0
        incorrect = list[tuple[int, Question[object], Answer[object]]]()
        for i, (q, a) in enumerate(zip(self._questions, self._answers)):
            if q.correct_answer == a.as_number():
                correct += 1
            else:
                incorrect.append((i, q, a))
        return QuizResults(
            questions=len(self._questions),
            correct=correct,
            incorrect=tuple(incorrect),
            time=self._from_entry.elapsed,
        )

    @override
    def __call__(self, state: State, /) -> None:
        if self._clear_reason.remaining <= dt.timedelta():
            self._invalid_answer_reason = ""
        if show_quiz_question_and_went_back(
            state=state,
            curr_question=self.curr_question,
            curr_answer=self.curr_answer,
            curr_question_idx=self.curr_question_idx,
            questions=len(self._questions),
            time=self._from_entry.elapsed,
            red_text_below=self._invalid_answer_reason,
        ):
            state.move_to_parent_screen()
            return
        match state.input.as_key_set():
            case None:
                return
            case KeySet.BACKSPACE:
                self.curr_answer = self.curr_answer.last_char_removed()
                return
            case KeySet.ENTER:
                pass
            case key:
                self.curr_answer = \
                    self.curr_answer.str_added(_KEYS_TO_CHARS[key])
                return
        match self.advance():
            case None:
                self._invalid_answer_reason = ""
                return
            case InvalidAnswerReason() as reason:
                self._invalid_answer_reason = _REASON_TO_STR[reason]
                self._clear_reason.remaining = dt.timedelta(seconds=3)
                return
            case results:
                pass
        per_question_seconds: float = \
            self._from_entry.elapsed.total_seconds() / len(self._questions)
        basic_report = (
            (
                (
                    f"Accuracy: {results.correct}/{results.questions} ("
                    f"{results.correct/results.questions:.0%})"
                ),
                None
            ),
            (
                (
                    f"Time: {seconds_string(self._from_entry.elapsed)} ("
                    f"{per_question_seconds:.3f} s/question)",
                    None
                )
            )
        )
        if not results.incorrect:
            state.screen = SelectScreen(
                title="Quiz Results",
                options=basic_report
            )
            return
        incorrect_answers = SelectScreen(
            title="Review",
            options=tuple(
                (f"Question {index + 1}", ReturnArg(ReviewIncorrectAnswer(
                    question=question,
                    answer=answer,
                    index=index,
                    questions=len(self._questions)
                )))
                for index, question, answer in results.incorrect
            )
        )
        state.screen = SelectScreen(
            title="Quiz Results",
            options=(
                *basic_report,
                ("Review incorrect answers", ReturnArg(incorrect_answers))
            )
        )


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ShowTopTextBarCenterText(Screen):
    top_text: str
    center_text: rich_text.RichText

    @override
    def __call__(self, state: State, /) -> None:
        back, draw_in = draw_top_get_back_clicked_rect(state, self.top_text)
        gfx.blit(
            state.window,
            rich_text.render(INCONSOLATA_32, self.center_text, gfx.Align.MID),
            *draw_in.pos_and_args(gfx.Align.MID, gfx.Align.MID)
        )
        if back:
            state.move_to_parent_screen()


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ReturnArg(Generic[_T_co]):
    arg: _T_co  # type: ignore

    def __call__(self, /, *_: object, **__: object) -> _T_co:
        return self.arg


@final
@dataclasses.dataclass(frozen=True, slots=True)
class GetCurrFrame:
    """Compares equal if states are identical, making it a good instance or
nested member for various purposes."""
    state: State

    def __call__(self, /) -> TimePoint:
        return self.state.curr_frame


@final
class State:
    __slots__ = (
        "_window",
        "_screens",
        "_input",
        "_events",
        "_curr_frame",
        "_prev_frame",
    )
    _window: pygame.Surface
    _screens: list[Screen]
    _input: Input
    _events: tuple[pygame.Event, ...]
    _curr_frame: TimePoint
    _prev_frame: TimePoint

    def __init__(self, window: pygame.Surface, /) -> None:
        if window.size != gfx.DIMENSIONS:
            raise ValueError("Invalid window")
        now: TimePoint = TimePoint.now()
        self._window = window
        self._screens = [TitleScreen(Stopwatch(GetCurrFrame(self)))]
        self._input = Input()
        self._events = ()
        self._curr_frame = now
        self._prev_frame = now

    @property
    def window(self, /) -> pygame.Surface:
        return self._window

    @property
    def screen(self, /) -> Screen:
        return self._screens[-1]

    @screen.setter
    def screen(self, set_to: Screen, /) -> None:
        self._screens[-1] = set_to

    @property
    def input(self, /) -> Input:
        return self._input

    @property
    def events(self, /) -> tuple[pygame.Event, ...]:
        return self._events

    @property
    def curr_frame(self, /) -> TimePoint:
        return self._curr_frame

    @property
    def prev_frame(self, /) -> TimePoint:
        return self._prev_frame

    def switch_and_run_screen(self, screen: Screen, /) -> None:
        self.screen = screen
        self.screen(self)

    def stopwatch_started_now(self, /) -> ImmutableStopwatch:
        return ImmutableStopwatch.started_now(GetCurrFrame(self))

    def move_to_child_screen(self, to_add: Screen, /) -> None:
        self._screens.append(to_add)

    def move_to_parent_screen(self, /) -> None:
        if len(self._screens) > 1:
            self._screens.pop()

    def event_loop(self, /) -> NoReturn:
        self._prev_frame = TimePoint.now()
        self._curr_frame = TimePoint.now()
        while True:
            started_now = \
                    ImmutableStopwatch.started_now(GetCurrFrame(self))
            self._events = tuple(pygame.event.get())
            held_for = dict(self.input.held_for)
            one_of_held_for = dict(self.input.one_of_held_for)
            for event in self.events:
                if event.type == pygame.QUIT:
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key not in Key:
                        continue
                    key = Key(event.key)
                    held_for[key] = started_now
                elif event.type == pygame.KEYUP:
                    if event.key not in Key:
                        continue
                    key = Key(event.key)
                    del held_for[key]
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button not in MouseButton:
                        continue
                    button = MouseButton(event.button)
                    held_for[button] = started_now
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button not in MouseButton:
                        continue
                    button = MouseButton(event.button)
                    del held_for[button]
            for key_set in KeySet:
                if key_set & held_for.keys():
                    if key_set not in one_of_held_for:
                        one_of_held_for[key_set] = started_now
                else:
                    one_of_held_for.pop(key_set, None)
            self._input = Input(
                held_for=FrozenDict(held_for),
                one_of_held_for=FrozenDict(one_of_held_for),
                mouse_pos=pygame.mouse.get_pos()
            )
            self.window.fill(gfx.WHITE)
            self.screen(self)
            pygame.display.update()
            self._prev_frame = self.curr_frame
            self._curr_frame = TimePoint.now()


INTEGER_QUIZZES = SelectScreen(
    "Integer Quizzes",
    (
        (
            "1-Digit Addition/Subtraction",
            QuizScreen.maker(20, random_int_add_sub_question, 1)
        ),
        (
            "2-Digit Addition/Subtraction",
            QuizScreen.maker(20, random_int_add_sub_question, 2)
        ),
        (
            "3-Digit Addition/Subtraction",
            QuizScreen.maker(20, random_int_add_sub_question, 3)
        ),
        (
            "4-Digit Addition/Subtraction",
            QuizScreen.maker(20, random_int_add_sub_question, 4)
        ),
        (
            "1-Digit Multiplication",
            QuizScreen.maker(20, random_int_mul_question, 1)
        ),
        (
            "2-Digit Multiplication",
            QuizScreen.maker(20, random_int_mul_question, 2)
        ),
        (
            "3-Digit Multiplication",
            QuizScreen.maker(20, random_int_mul_question, 3)
        ),
        (
            "2-Digit Division",
            QuizScreen.maker(20, random_int_div_question, 2)
        ),
        (
            "3-Digit Division",
            QuizScreen.maker(20, random_int_div_question, 3)
        ),
        (
            "4-Digit Division",
            QuizScreen.maker(20, random_int_div_question, 4)
        )
    )
)


FRACTION_QUIZZES = SelectScreen(
    "Fraction Quizzes",
    (
        (
            "1-Digit Addition/Subtraction",
            QuizScreen.maker(20, random_fraction_add_sub_question, 1)
        ),
        (
            "2-Digit Addition/Subtraction",
            QuizScreen.maker(20, random_fraction_add_sub_question, 2)
        ),
        (
            "1-Digit Multiplication/Division",
            QuizScreen.maker(20, random_fraction_mul_div_question, 1)
        ),
        (
            "2-Digit Multiplication/Division",
            QuizScreen.maker(20, random_fraction_mul_div_question, 2)
        ),
    )
)


CREDITS_SCREEN = ShowTopTextBarCenterText(
    "Credits",
    rich_text.rich_text(
        "FAST MATH by SociableFish.\n"
        "\n"
        "See COPYRIGHT and CREDITS files and the\n"
        "LICENSES folder for more information.",
    )
)


MAIN_MENU = SelectScreen(
    "Main Menu",
    (
        ("Integer Quizzes", ReturnArg(INTEGER_QUIZZES)),
        ("Fraction Quizzes", ReturnArg(FRACTION_QUIZZES)),
        ("Credits", ReturnArg(CREDITS_SCREEN))
    ),
    show_back=False
)
