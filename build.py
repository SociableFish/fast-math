"""
To prepare the repository for building:

1. Navigate to the repository root.
1. Create a `venv` virtual environment under EXACTLY Python 3.14.6.
1. With the virtual environment activated, run `python -m pip install .`.

To build, run `python build.py` in the repository root with the virtual
environment activated, creating the `dist` folder, which is renamed and
distributed to users as the binary download.

To run from source without building, navigate to `src` and run
`python -m fast_math` with the virtual environment activated.
"""

import pathlib
import shutil
import subprocess
import sys
from typing import NoReturn


BUILD = pathlib.Path("build").resolve()
OUTPUT = pathlib.Path("dist").resolve()
NOT_IN_INTERNAL = ("COPYRIGHT", "CREDITS", "LICENSES")


def main() -> NoReturn:
    try:
        shutil.rmtree(BUILD)
    except FileNotFoundError:
        pass
    try:
        shutil.rmtree(OUTPUT)
    except FileNotFoundError:
        pass
    success: bool = not subprocess.run(["pyinstaller", ".spec"]).returncode
    try:
        shutil.rmtree(BUILD)
    except FileNotFoundError:
        pass
    if not success:
        try:
            shutil.rmtree(OUTPUT)
        except FileNotFoundError:
            pass
        sys.exit(1)
    # We handle these explicitly because pyinstaller would put them in
    # _internal, harming UX upon a user checking for these
    for file_or_folder in NOT_IN_INTERNAL:
        pathlib.Path(file_or_folder).copy(OUTPUT / file_or_folder)
    sys.exit(0)


if __name__ == "__main__":
    main()
