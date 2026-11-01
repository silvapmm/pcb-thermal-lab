#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file limits.py
@brief The size limit of one Gerber or drill file (or one member of a ZIP): a machine preference, 256 MB by default, checked before the file is read.
@details A real Gerber file is 0.01 to 2 MB; a file of hundreds of MB is a mistake or a hostile file. The decoded text takes about twice the file in memory (UTF-8 bytes,
         then the text, then the blocks), so the limit is read before anything is loaded: from the size on disk, or from the size a ZIP member declares. The value is the
         Preferences entry `gerber.max_file_mb` (shipped 256, range MIN_FILE_MB to MAX_FILE_MB), like `solver.memory_fraction` it belongs to the machine and is not
         saved in a project. A function that reads a file takes an optional `max_bytes` that overrides it (tests and studies).
"""

import os
from typing import Optional

from .errors import GerberError

MB = 1024 * 1024
DEFAULT_FILE_MB = 256
MIN_FILE_MB = 16
MAX_FILE_MB = 4096


def max_file_bytes() -> int:
    """!
    @brief The limit in force for one file, in bytes.
    @details The Preferences value `gerber.max_file_mb` (shipped defaults plus the user's file); a value that is missing, not a number or outside MIN_FILE_MB to MAX_FILE_MB
             is ignored and DEFAULT_FILE_MB is used.
    @return int Bytes.
    """
    mb = DEFAULT_FILE_MB
    try:
        from .. import defaults                                                # Lazy: the reader has no other need of the defaults
        value = float(defaults.load()["gerber"].get("max_file_mb", DEFAULT_FILE_MB))
        if MIN_FILE_MB <= value <= MAX_FILE_MB:
            mb = value
    except (KeyError, TypeError, ValueError, OSError):
        pass
    return int(mb * MB)


def check_size(size: int, name: str, max_bytes: Optional[int] = None) -> None:
    """!
    @brief Refuse a file larger than the limit.
    @param size Size of the file in bytes.
    @param name File name, for the message.
    @param max_bytes Limit in bytes (None: the preference, see max_file_bytes).
    @return None.
    @throws GerberError If the size is above the limit.
    """
    limit = max_file_bytes() if max_bytes is None else max_bytes
    if size > limit:
        raise GerberError(f"{name}: the file has {size / MB:.1f} MB, above the limit of {limit / MB:.0f} MB "
                          "(Preferences, Gerber import, 'Largest file'; a real Gerber file is under 2 MB)")


def check_path(path, max_bytes: Optional[int] = None) -> None:
    """!
    @brief Refuse a file on disk that is larger than the limit, from its size (nothing is read).
    @param path File path.
    @param max_bytes Limit in bytes (None: the preference).
    @return None.
    @throws GerberError If the file is above the limit.
    """
    check_size(os.path.getsize(path), os.path.basename(str(path)), max_bytes)
