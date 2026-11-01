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

import logging
import os
from typing import Optional

from .errors import GerberError

MB = 1024 * 1024
DEFAULT_FILE_MB = 256
MIN_FILE_MB = 16
MAX_FILE_MB = 4096
_LOG = logging.getLogger(__name__)


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
        else:                                                                 # NaN, infinite, negative, zero or absurd: the shipped value, and say so in the log
            _LOG.warning("gerber.max_file_mb = %r is outside %d to %d MB: %d MB is used", value, MIN_FILE_MB, MAX_FILE_MB, DEFAULT_FILE_MB)
    except (KeyError, TypeError, ValueError, OSError, AttributeError):
        _LOG.warning("gerber.max_file_mb cannot be read from the defaults: %d MB is used", DEFAULT_FILE_MB)
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


def read_text(path, max_bytes: Optional[int] = None) -> str:
    """!
    @brief Read a whole file as UTF-8 text (an undecodable byte becomes U+FFFD, newlines as in text mode), never more than the limit.
    @details The size on disk is checked first (nothing is read for a file above the limit); then at most limit + 1 bytes are read, so that a file whose size the
             system does not report (a pipe, a device, a file that grows while it is read) cannot make the reader take more than the limit either.
    @param path File path.
    @param max_bytes Limit in bytes (None: the preference).
    @return str The text.
    @throws GerberError If the file is above the limit.
    @throws OSError If the file cannot be opened.
    """
    limit = max_file_bytes() if max_bytes is None else max_bytes
    name = os.path.basename(str(path))
    check_path(path, limit)
    with open(path, "rb") as fh:
        data = fh.read(limit + 1)
    check_size(len(data), name, limit)
    # The same text as Path.read_text: universal newlines (CR LF and a lone CR become LF), so the readers see what they saw before the limit was added
    text = data.decode("utf-8", errors="replace")
    del data                                                                  # the bytes and the text are not held together longer than the decoding
    return text.replace("\r\n", "\n").replace("\r", "\n") if "\r" in text else text
