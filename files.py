"""
Taking a copy of a file before changing it.

Every file the installer edits is one the user cannot afford to lose: a project
file that no longer opens, or a source with their own code in it. So a copy is
taken first, beside the file, under a name that never replaces an older copy.
"""

import shutil
from datetime import datetime
from pathlib import Path


def backup(path):
    """
    Copy a file aside before editing it.

    Named with a timestamp rather than a plain .bak, so a second install does
    not overwrite the copy taken before the first one.
    """
    path = Path(path)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_suffix(path.suffix + f".{stamp}.bak")
    count = 1

    # A library and the one it needs are installed in one run, often inside
    # the same second. The second copy must not replace the first, which is
    # the only one holding the file as it was before either of them.
    while target.exists():
        count += 1
        target = path.with_suffix(path.suffix + f".{stamp}-{count}.bak")

    shutil.copyfile(path, target)

    return target
