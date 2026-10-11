# SPDX-License-Identifier: GPL-3.0-or-later

import abc
from collections.abc import Callable, Iterator
import dataclasses
import enum
from fractions import Fraction
from numbers import Rational
import random
from typing import ClassVar, final, Generic, override, Self, TypeVar


_T_co = TypeVar("_T_co", covariant=True)


type _Rational = int | Rational


@final
class InvalidAnswerReason(enum.Enum):
    MORE_CHARS_NEEDED = enum.auto()
    INVALID_CHAR = enum.auto()
    LEADING_ZEROS = enum.auto()
    REDUNDANT_SIGN = enum.auto()


@dataclasses.dataclass(frozen=True, slots=True)
class Answer[T](abc.ABC):
    value: str = ""
    MAX_LEN: ClassVar[int] = 30

    @final
    def __post_init__(self, /) -> None:
        if len(self.value) > Answer.MAX_LEN:
            raise ValueError("answer is too long")
        for char in self.value:
            if char not in self.allowed_chars():
                raise ValueError("answer contains invalid characters")

    @classmethod
    @abc.abstractmethod
    def allowed_chars(cls, /) -> str:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def enter_as_parens(cls, /) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def as_number(cls, /) -> T | InvalidAnswerReason:
        raise NotImplementedError

    @final
    def last_char_removed(self, /) -> Self:
        return type(self)(self.value[:-1])

    @final
    def str_added(self, added: str, /) -> Self:
        added = "".join(c for c in added if c in self.allowed_chars())
        added = added[:Answer.MAX_LEN - len(self.value)]
        return type(self)(self.value + added)


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Question(Generic[_T_co]):
    question: str
    answer_type: type[Answer[_T_co]]
    correct_answer: _T_co  # type: ignore


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class IntMatchData:
    end: int
    value: int


# The following are used instead of regex for absolute control over matching
# A string denoting an integer in "canonical form" shall fully match the regex
# 0|-?[1-9][0-9]*
def int_match(s: str, /, *, start: int = 0) -> \
        IntMatchData | InvalidAnswerReason:
    if not 0 <= start <= len(s):
        raise IndexError(start)
    s_end: int = len(s)
    current_idx: int = start
    negative: bool = False
    if current_idx != s_end and s[current_idx] == "-":
        negative = True
        current_idx += 1
    if current_idx == s_end:
        return InvalidAnswerReason.MORE_CHARS_NEEDED
    if s[current_idx] == "0":
        current_idx += 1
        if current_idx != s_end and "0" <= s[current_idx] <= "9":
            return InvalidAnswerReason.LEADING_ZEROS
        if negative:
            return InvalidAnswerReason.REDUNDANT_SIGN
        return IntMatchData(end=current_idx, value=int(s[start:current_idx]))
    if not "1" <= s[current_idx] <= "9":
        return InvalidAnswerReason.INVALID_CHAR
    current_idx += 1
    while current_idx != s_end and "0" <= s[current_idx] <= "9":
        current_idx += 1
    return IntMatchData(end=current_idx, value=int(s[start:current_idx]))


@final
class IntegerAnswer(Answer[int]):
    @override
    @classmethod
    def allowed_chars(cls, /) -> str:
        return "0123456789-"

    @override
    @classmethod
    def enter_as_parens(cls, /) -> str:
        return "(Enter as an integer)"

    @override
    def as_number(self, /) -> int | InvalidAnswerReason:
        match int_match(self.value):
            case IntMatchData(end=end, value=value) if end == len(self.value):
                return value
            case IntMatchData():
                return InvalidAnswerReason.INVALID_CHAR
            case reason:
                return reason


def random_int_with_digits(
        digits: int,
        /,
        *,
        allow_negative: bool = True
) -> int:
    if digits <= 0:
        raise ValueError("digits > 0 required")
    if digits == 0:
        if not allow_negative:
            return random.randint(0, 9)
        return random.randint(-9, 9)
    sign: int = 1
    if allow_negative:
        sign = random.choice((1, -1))
    return sign * random.randint(10 ** (digits - 1), 10 ** digits - 1)


def random_nonzero_int_with_digits(
        digits: int,
        /,
        *,
        allow_negative: bool = True
) -> int:
    if digits == 0:
        sign: int = 1
        if allow_negative:
            sign = random.choice((1, -1))
        return sign * random.randint(1, 9)
    return random_int_with_digits(digits, allow_negative=allow_negative)


def random_int_add_sub_question(digits: int, /) -> Question[int]:
    lhs: int = random_int_with_digits(digits)
    rhs: int = random_int_with_digits(digits)
    operation: str = random.choice(("+", "-"))
    return Question(
        question=f"{lhs} {operation} {rhs}",
        answer_type=IntegerAnswer,
        correct_answer=lhs + rhs if operation == "+" else lhs - rhs
    )


def random_int_mul_question(digits: int, /) -> Question[int]:
    lhs: int = random_int_with_digits(digits)
    rhs: int = random_int_with_digits(digits)
    return Question(
        question=f"{lhs} * {rhs}",
        answer_type=IntegerAnswer,
        correct_answer=lhs * rhs
    )


def random_int_div_question(digits: int, /) -> Question[int]:
    lhs: int = random_nonzero_int_with_digits(digits)
    rhs: int = random_nonzero_int_with_digits((digits + 1) // 2)
    operation: str = random.choice(("quotient", "remainder"))
    return Question(
        question=f"{lhs} / {rhs} ({operation})",
        answer_type=IntegerAnswer,
        correct_answer=lhs // rhs if operation == "quotient" else lhs % rhs
    )


# A string denoting a fraction in "canonical form" shall be a canonical
# integer, then a "/", then a canonical nonnegative integer
@final
@dataclasses.dataclass(frozen=True, slots=True)
class GeneralFraction:
    """A class to preserve exact numerators and denominators, to allow answers
to be marked wrong if fractions are not simplified, unlike `fractions.Fraction`
which simplifies the fraction inside its constructor. `denominator == 0` is
also allowed, to always mark it wrong. `denominator < 0` is still not allowed,
because the answer field only allows writing `<integer>/<nonnegative integer>`.
"""
    numerator: int
    denominator: int

    def __post_init__(self, /) -> None:
        if self.denominator < 0:
            raise ValueError("denominator >= 0 required")

    @override
    def __str__(self, /) -> str:
        return f"{self.numerator}/{self.denominator}"

    @staticmethod
    def from_rational(x: _Rational, /) -> GeneralFraction:
        x = Fraction(x)
        return GeneralFraction(x.numerator, x.denominator)

    def as_fraction(self, /) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    @staticmethod
    def random_with_digits(digits: int, /) -> GeneralFraction:
        return GeneralFraction(
            random_int_with_digits(digits),
            random_nonzero_int_with_digits(digits, allow_negative=False)
        )

    @staticmethod
    def random_nonzero_with_digits(digits: int, /) -> GeneralFraction:
        return GeneralFraction(
            random_nonzero_int_with_digits(digits),
            random_nonzero_int_with_digits(digits, allow_negative=False)
        )


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FractionMatchData:
    end: int
    value: GeneralFraction


def fraction_match(s: str, /, *, start: int = 0) -> \
        FractionMatchData | InvalidAnswerReason:
    s_end: int = len(s)
    numerator = int_match(s, start=start)
    if not isinstance(numerator, IntMatchData):
        return numerator
    curr: int = numerator.end
    if curr == s_end:
        return InvalidAnswerReason.MORE_CHARS_NEEDED
    if s[curr] != "/":
        return InvalidAnswerReason.INVALID_CHAR
    curr += 1
    denominator = int_match(s, start=curr)
    if not isinstance(denominator, IntMatchData):
        return denominator
    if denominator.value < 0:
        return InvalidAnswerReason.INVALID_CHAR
    return FractionMatchData(
        end=denominator.end,
        value=GeneralFraction(numerator.value, denominator.value)
    )


@final
class FractionAnswer(Answer[GeneralFraction]):
    @override
    @classmethod
    def allowed_chars(cls, /) -> str:
        return "0123456789-/"

    @override
    @classmethod
    def enter_as_parens(cls, /) -> str:
        return "(Enter as a proper or improper fraction)"

    @override
    def as_number(self, /) -> GeneralFraction | InvalidAnswerReason:
        match fraction_match(self.value):
            case FractionMatchData(end=end, value=value) if \
                    end == len(self.value):
                return value
            case FractionMatchData():
                return InvalidAnswerReason.INVALID_CHAR
            case reason:
                return reason


def random_fraction_add_sub_question(digits: int, /) -> \
        Question[GeneralFraction]:
    lhs = GeneralFraction.random_with_digits(digits)
    rhs = GeneralFraction.random_with_digits(digits)
    lhs_f: Fraction = lhs.as_fraction()
    rhs_f: Fraction = rhs.as_fraction()
    operation: str = random.choice(("+", "-"))
    result: Fraction = lhs_f + rhs_f if operation == "+" else lhs_f - rhs_f
    return Question(
        question=f"{lhs!s} {operation} {rhs!s}",
        answer_type=FractionAnswer,
        correct_answer=GeneralFraction.from_rational(result)
    )


def random_fraction_mul_div_question(digits: int, /) -> \
        Question[GeneralFraction]:
    operation: str = random.choice(("*", "/"))
    lhs = GeneralFraction.random_with_digits(digits)
    rhs: GeneralFraction
    if operation == "*":
        rhs = GeneralFraction.random_with_digits(digits)
    else:
        rhs = GeneralFraction.random_nonzero_with_digits(digits)
    lhs_f: Fraction = lhs.as_fraction()
    rhs_f: Fraction = rhs.as_fraction()
    result: Fraction = lhs_f * rhs_f if operation == "*" else lhs_f / rhs_f
    return Question(
        question=f"{lhs!s} {operation} {rhs!s}",
        answer_type=FractionAnswer,
        correct_answer=GeneralFraction.from_rational(result)
    )


def repeat_calls[**P, R](
        times: int,
        fn: Callable[P, R],
        /,
        *args: P.args,
        **kwargs: P.kwargs
) -> Iterator[R]:
    if times < 0:
        raise ValueError("times >= 0 required")
    return (fn(*args, **kwargs) for _ in range(times))
