# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Buffer, Iterable
import io
import os
import pathlib
import tempfile
import threading
import types
from typing import Any, final, Literal, NewType, override, Self


type StrPath = str | os.PathLike[str]


AbsPath = NewType("AbsPath", pathlib.Path)


def absolute(path: StrPath, /) -> AbsPath:
    return AbsPath(pathlib.Path(path).resolve())


@final
class AtomicReplace(io.RawIOBase):
    """Works like `io.FileIO` with `mode="wb+", opener=None`, except:
* **You must set `.replace = True` for the file to be opened and modified at
all, and only on close** (if `False`, the temporary file will be deleted)
* **Either the new contents of the file are fully written, or the file is
unchanged** (hence the name, implemented using a temporary file from
`tempfile.mkstemp` and `os.replace`)
* Only `str` or `__fspath__ -> str` filenames supported
* `prefix=` and `suffix=` (because `tempfile.mkstemp` is used)
* If an error occurs, there may or may not be a temporary file in the same
directory
* Empty directories can be replaced (because `os.replace` is used)
* `.name` is immutable (and refers to the target, not the temporary file, which
`.fileno()` refers to)

Example:
```
ar = AtomicReplace("output")
with io.BufferedWriter(ar) as fobj:
    # 256 MB cannot be written atomically
    fobj.write(bytes(range(256)) * 1_000_000)
    # This line not reached (and thus temporary file deleted) if write throws
    fobj.replace = True
    # replace exists because .close() cannot determine if it was thrown due to
    # an exception, and this class's .__enter__() and .__exit__() is not called
    # if the file object is wrapped, like in this example
```"""
    __slots__ = (
        "_lock",
        "_name",
        "_dest_abspath",
        "_tmp_abspath",
        "_fileio",
        "_replace",
    )

    _lock: threading.Lock
    _name: str
    _dest_abspath: str
    _tmp_abspath: str
    _fileio: io.FileIO
    _replace: bool

    def __init__(
            self,
            /,
            file: StrPath,
            *,
            prefix: str | None = None,
            suffix: str | None = None
    ) -> None:
        lock: threading.Lock = threading.Lock()
        file = os.fspath(file)
        dest_abspath: str = os.path.abspath(file)
        fd, tmp_abspath = tempfile.mkstemp(
            dir=os.path.dirname(dest_abspath),
            prefix=prefix,
            suffix=suffix,
        )
        self._lock = lock
        self._name = file  # type: ignore
        self._dest_abspath = dest_abspath
        self._tmp_abspath = tmp_abspath
        self._fileio = io.FileIO(fd, "wb+")
        self._replace = False

    @override
    def __enter__(self, /) -> Self:
        return self

    @override
    def __exit__(
            self,
            /,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: types.TracebackType | None
    ) -> None:
        self.close()

    @override
    def __iter__(self, /) -> Self:
        return self

    @override
    def __next__(self, /) -> bytes:
        with self._lock:
            return next(self._fileio)

    @override
    def close(self, /) -> None:
        with self._lock:
            if self._fileio.closed:
                return
            try:
                os.fsync(self._fileio.fileno())
            except OSError:
                self._fileio.close()
                os.remove(self._tmp_abspath)
                raise
            self._fileio.close()
            if self._replace:
                try:
                    os.replace(self._tmp_abspath, self._dest_abspath)
                except OSError:
                    os.remove(self._tmp_abspath)
                    raise
            else:
                os.remove(self._tmp_abspath)

    @property
    @override
    def closed(self, /) -> bool:
        with self._lock:
            return self._fileio.closed

    @property
    def closefd(self, /) -> Literal[True]:
        return True

    @override
    def fileno(self, /) -> int:
        with self._lock:
            return self._fileio.fileno()

    @override
    def flush(self, /) -> None:
        "No-op, to match `io.FileIO`."
        pass

    @override
    def isatty(self, /) -> Literal[False]:
        return False

    @property
    def mode(self, /) -> Literal["wb+"]:
        return "wb+"

    @property
    def name(self, /) -> str:
        return self._name

    @override
    def read(self, size: int | None = -1, /) -> bytes | Any:
        with self._lock:
            return self._fileio.read(size)

    @override
    def readable(self, /) -> Literal[True]:
        return True

    @override
    def readall(self, /) -> bytes:
        with self._lock:
            return self._fileio.readall()

    @override
    def readinto(self, buffer: Buffer, /) -> int | Any:
        with self._lock:
            return self._fileio.readinto(buffer)

    @override
    def readline(self, size: int | None = -1, /) -> bytes:
        with self._lock:
            return self._fileio.readline(size)

    @override
    def readlines(self, hint: int = -1, /) -> list[bytes]:
        with self._lock:
            return self._fileio.readlines(hint)

    @override
    def seek(self, pos: int, whence: int = 0, /) -> int:
        with self._lock:
            return self._fileio.seek(pos, whence)

    @override
    def seekable(self, /) -> Literal[True]:
        return True

    @override
    def tell(self, /) -> int:
        with self._lock:
            return self._fileio.tell()

    @override
    def truncate(self, size: int | None = None, /) -> int:
        with self._lock:
            return self._fileio.truncate(size)

    @override
    def writable(self, /) -> Literal[True]:
        return True

    @override
    def write(self, buffer: Buffer, /) -> int | Any:
        with self._lock:
            return self._fileio.write(buffer)

    @override
    def writelines(self, lines: Iterable[Buffer], /) -> None:
        with self._lock:
            return self._fileio.writelines(lines)

    @property
    def replace(self, /) -> bool:
        with self._lock:
            return self._replace

    @replace.setter
    def replace(self, to: bool, /) -> None:
        with self._lock:
            self._replace = to
