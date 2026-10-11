# SPDX-License-Identifier: GPL-3.0-or-later

import copy
from collections.abc import ItemsView, Iterable, Iterator, \
    KeysView, Mapping, Set, ValuesView
from typing import Any, final, overload, override, Self, TypeVar


__all__ = (
    "FrozenDict",
)


_K = TypeVar("_K")
_V_co = TypeVar("_V_co", covariant=True)


@final
class FrozenDict(Mapping[_K, _V_co]):
    """Immutable version of `dict` that preserves insertion order (and thus
allows `reversed`)

`__hash__` computes the set hash of `items()`, the same as the `frozendict`
module on PyPI. (However, that module makes its `frozendict <: dict`, violating
the LSP.)

The current implementation strategy (subject to change) is to use an internal
`dict` to store key-value pairs and forward operations to it. Thus for now,
`keys()`, `values()`, and `items()` all also support `reversed`."""
    __slots__ = ("_dict",)

    _dict: dict[_K, _V_co]

    @classmethod
    def _from_internal_dict(cls, internal: dict[_K, _V_co], /) -> Self:
        self = super().__new__(cls)
        self._dict = internal
        return self

    @overload
    def __new__(cls, it: Iterable[tuple[_K, _V_co]] = (), /) -> Self:
        ...

    @overload
    def __new__(cls, map: Mapping[_K, _V_co], /) -> Self:
        ...

    @overload
    def __new__[K, V](
        cls: type[FrozenDict[K | str, V]],
        it: Iterable[tuple[K | str, V]] = (),
        /,
        **kwargs: V
    ) -> FrozenDict[K | str, V]:
        ...

    @overload
    def __new__[K, V](
        cls: type[FrozenDict[K | str, V]],
        map: Mapping[K | str, V],
        /,
        **kwargs: V
    ) -> FrozenDict[K | str, V]:
        ...

    def __new__(cls, /, *args: Any, **kwargs: Any) -> Self:  # type: ignore
        return cls._from_internal_dict(dict(*args, **kwargs))  # type: ignore

    @overload
    @classmethod
    def fromkeys[K, V](
        cls: type[FrozenDict[K, V]],
        it: Iterable[K],
        val: V,
        /
    ) -> FrozenDict[K, V]:
        ...

    @overload
    @classmethod
    def fromkeys[K, V](
        cls: type[FrozenDict[K, V | None]],
        it: Iterable[_K],
        /
    ) -> FrozenDict[K, V | None]:
        ...

    @classmethod
    def fromkeys(cls, it: Iterable[Any], val: Any = None, /) -> Any:
        return cls._from_internal_dict(dict.fromkeys(it, val))  # type: ignore

    def __repr__(self, /) -> str:
        return f"FrozenDict({self._dict!r})"

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, Mapping):
            return NotImplemented
        return self._dict == other

    @override
    def __ne__(self, other: object, /) -> bool:
        if not isinstance(other, Mapping):
            return NotImplemented
        return self._dict != other

    @override
    def __hash__(self, /) -> int:
        return Set._hash(self.items())  # type: ignore

    @override
    def __getitem__(self, key: _K, /) -> _V_co:
        return self._dict[key]

    @override
    def __iter__(self, /) -> Iterator[_K]:
        return iter(self._dict)

    def __reversed__(self, /) -> Iterator[_K]:
        return reversed(self._dict)

    @override
    def __len__(self, /) -> int:
        return len(self._dict)

    @override
    def __contains__(self, key: object, /) -> bool:
        return key in self._dict

    def __or__[K2, V2](
            self,
            other: FrozenDict[K2, V2],
            /
    ) -> FrozenDict[_K | K2, _V_co | V2]:
        return self._from_internal_dict(
            self._dict | other._dict  # type: ignore
        )

    @override
    def __reduce__(self, /) -> tuple[Any, Any]:
        return (type(self)._from_internal_dict, (self._dict,))

    def __copy__(self, /) -> Self:
        return self

    def __deepcopy__(self, memo: dict[Any, Any], /) -> Self:
        # Same strategy as copy.deepcopy(<tuple>)
        copied_internal_dict = dict[_K, _V_co]()
        use_copy: bool = False
        for k, v in self._dict.items():
            kc: _K = copy.deepcopy(k, memo)
            vc: _V_co = copy.deepcopy(v, memo)
            copied_internal_dict[kc] = vc
            use_copy |= k is not kc or v is not vc
        if use_copy:
            return self._from_internal_dict(copied_internal_dict)
        else:
            return self

    @overload
    def get(self, key: _K, /) -> _V_co | None:
        ...

    @overload
    def get[V2](self, key: _K, /, default: V2) -> _V_co | V2:
        ...

    @override
    def get(self, key: Any, /, default: Any = None) -> Any:  # type: ignore
        return self._dict.get(key, default)

    @override
    def keys(self, /) -> KeysView[_K]:
        return self._dict.keys()

    @override
    def values(self, /) -> ValuesView[_V_co]:
        return self._dict.values()

    @override
    def items(self, /) -> ItemsView[_K, _V_co]:
        return self._dict.items()

    def copy(self, /) -> Self:
        return self
