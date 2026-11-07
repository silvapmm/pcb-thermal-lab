#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file archive.py
@brief Safe reading of a ZIP file of Gerber and drill files: member names checked, sizes limited, nothing written to disk.
@details A fabrication set usually travels as one ZIP file that comes from someone else, so the reader treats it as hostile. The members are never extracted to disk (a name
         such as `../../x` or `/etc/passwd` could not escape anything, and is still refused as a zip-slip attempt); they are read into memory one at a time, with a limit on the
         bytes actually read (the sizes declared in the headers can lie). Refused with an `UnsafeArchiveError`: an absolute or drive-lettered name, a `..` component, a NUL character, more than
         MAX_MEMBERS members, a declared total of uncompressed bytes above MAX_UNCOMPRESSED_BYTES (2 GB), a member above the file limit (`limits.max_file_bytes()`, Preferences `gerber.max_file_mb`, 256 MB shipped; MAX_MEMBER_BYTES is that default), an encrypted member, a
         compression ratio above MAX_RATIO (a zip bomb) and two members with the same name. Names that differ only in case, symbolic-link members (read as their
         stored text) and nested archives (listed as unknown files, never opened) are harmless because nothing is written to disk. Detection reads only the first HEAD_BYTES of each member.
"""

import io
import struct
import zipfile
import zlib
from pathlib import PurePosixPath
from typing import NamedTuple, Optional

from . import limits
from .errors import UnsafeArchiveError
from .functions import HEAD_BYTES, LayerFunction, detect_set

MAX_UNCOMPRESSED_BYTES = 2 * 1024 ** 3        # declared total, the limit stated for the import
MAX_MEMBER_BYTES = limits.DEFAULT_FILE_MB * limits.MB     # the shipped default of one member; the limit in force is the preference (limits.max_file_bytes)
MAX_MEMBERS = 5000
MAX_RATIO = 1000.0                            # uncompressed over compressed bytes of one member
# What the zipfile module raises on a damaged or hostile file besides BadZipFile (a negative seek from a lying header, an undecodable name, an unknown version)
_ZIP_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, ValueError, UnicodeDecodeError, struct.error, OverflowError, OSError)


class ArchiveMember(NamedTuple):
    """!@brief A usable member of an archive: its (normalised) name, declared uncompressed size, and detected function."""
    name: str
    size: int
    function: LayerFunction


def check_member_name(name):
    """!
    @brief Check one member name against zip-slip.
    @param name Name as stored in the archive.
    @return str The normalised name (forward slashes).
    @throws UnsafeArchiveError For an absolute name, a drive letter, a `..` component or a NUL character.
    """
    norm = name.replace("\\", "/")
    parts = PurePosixPath(norm).parts
    if "\x00" in norm or norm.startswith("/") or (len(norm) > 1 and norm[1] == ":") or ".." in parts:
        raise UnsafeArchiveError(f"unsafe name in the archive: {name!r}")
    return norm


class GerberArchive:
    """!@brief A ZIP file opened for reading with the limits above; use it as a context manager or call close()."""

    def __init__(self, source, max_member_bytes=None):
        """!
        @brief Open an archive and validate every member before anything is read.
        @param source Path of the ZIP file, or its bytes.
        @param max_member_bytes Largest member in bytes (None: the preference `gerber.max_file_mb`).
        @throws UnsafeArchiveError For an unsafe or oversized archive, or a file that is not a ZIP.
        """
        try:
            self._zf = zipfile.ZipFile(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
        except (FileNotFoundError, PermissionError, IsADirectoryError):
            raise                                               # the path itself is wrong: the usual error of the operating system
        except _ZIP_ERRORS as exc:
            raise UnsafeArchiveError(f"not a valid ZIP file: {type(exc).__name__}: {exc}") from exc
        self._max_member = limits.max_file_bytes() if max_member_bytes is None else max_member_bytes
        try:
            self._validate()
        except BaseException:
            self._zf.close()                                    # a refused archive does not keep its file open
            raise

    def _validate(self):
        """!
        @brief Check every member name and size against the limits.
        @throws UnsafeArchiveError For an unsafe or oversized archive.
        """
        for i in self._zf.infolist():
            check_member_name(i.filename)                       # also the directory entries: a name that tries to leave the folder is refused whatever it is
        infos = [i for i in self._zf.infolist() if not i.is_dir()]
        if len(infos) > MAX_MEMBERS:
            raise UnsafeArchiveError(f"the archive has {len(infos)} members (limit {MAX_MEMBERS})")
        total = 0
        self._infos = {}
        for info in infos:
            norm = check_member_name(info.filename)
            if norm in self._infos:                             # two members of one name: which one is "the" file is ambiguous (and one would be hidden)
                raise UnsafeArchiveError(f"the archive holds two members named {norm!r}")
            if info.flag_bits & 0x1:
                raise UnsafeArchiveError(f"encrypted member {norm!r}")
            if info.file_size > self._max_member:
                raise UnsafeArchiveError(f"member {norm!r} declares {info.file_size} bytes (limit {self._max_member}; Preferences, Gerber import, 'Largest file')")
            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_RATIO:
                raise UnsafeArchiveError(f"member {norm!r} has a compression ratio above {MAX_RATIO:.0f} (zip bomb?)")
            total += info.file_size
            self._infos[norm] = info
        if total > MAX_UNCOMPRESSED_BYTES:
            raise UnsafeArchiveError(f"the archive declares {total} uncompressed bytes (limit {MAX_UNCOMPRESSED_BYTES})")

    def __enter__(self):
        """!
        @brief Context manager entry.
        @return GerberArchive self.
        """
        return self

    def __exit__(self, *exc):
        """!
        @brief Context manager exit: close the archive.
        @param exc Exception information (ignored).
        @return bool False (exceptions propagate).
        """
        self.close()
        return False

    def close(self):
        """!@brief Close the archive."""
        self._zf.close()

    def names(self):
        """!
        @brief The names of the files in the archive, without the junk of a file manager (`__MACOSX/`, `.DS_Store`, `Thumbs.db`).
        @return list of str.
        """
        return [n for n in self._infos if not (n.startswith("__MACOSX/") or n.rsplit("/", 1)[-1] in (".DS_Store", "Thumbs.db"))]

    def read_head_bytes(self, name, n=HEAD_BYTES):
        """!
        @brief Read only the first bytes of a member, undecoded.
        @param name Member name.
        @param n    Number of bytes.
        @return bytes
        @throws UnsafeArchiveError If the member cannot be read.
        """
        try:
            with self._zf.open(self._infos[name]) as fh:
                return fh.read(n)
        except _ZIP_ERRORS as exc:
            raise UnsafeArchiveError(f"member {name!r} cannot be read: {exc}") from exc

    def read_head(self, name, n=HEAD_BYTES):
        """!
        @brief Read only the first bytes of a member (enough for the file attributes and the Excellon header).
        @param name Member name.
        @param n    Number of bytes.
        @return str The text, decoded leniently.
        """
        return self.read_head_bytes(name, n).decode("utf-8", "replace")

    def read_text(self, name):
        """!
        @brief Read a whole member into memory, never more than the declared size (a header that lies cannot make the reader take more).
        @param name Member name.
        @return str The text, decoded leniently.
        @throws UnsafeArchiveError If the member holds more bytes than it declares or cannot be decompressed.
        """
        return self.read_bytes(name).decode("utf-8", "replace")

    def read_bytes(self, name):
        """!
        @brief Read a whole member into memory as its original bytes (no decoding), never more than the declared size; used to store the file unchanged in a project package.
        @param name Member name.
        @return bytes The content (CRC checked by the library).
        @throws UnsafeArchiveError If the member holds more bytes than it declares or cannot be decompressed.
        """
        info = self._infos[name]
        try:
            with self._zf.open(info) as fh:
                data = fh.read(info.file_size + 1)
        except _ZIP_ERRORS as exc:
            # The library checks the CRC and the sizes itself: a header that lies about the size ends here
            raise UnsafeArchiveError(f"member {name!r} cannot be read (it holds more or other bytes than it declares?): {exc}") from exc
        if len(data) > info.file_size:
            raise UnsafeArchiveError(f"member {name!r} holds more bytes than it declares")
        return data

    def members(self):
        """!
        @brief The usable members with their declared size and detected function (only the headers are read).
        @return list of ArchiveMember.
        """
        names = self.names()
        found = detect_set([(n, self.read_head(n)) for n in names])            # at set level: numbered copper layers are ordered from the top
        return [ArchiveMember(n, self._infos[n].file_size, found[n]) for n in names]


def inspect_archive(source, max_member_bytes=None) -> Optional[list]:
    """!
    @brief List the members of a ZIP file with their detected functions.
    @param source Path of the ZIP file, or its bytes.
    @param max_member_bytes Largest member in bytes (None: the preference).
    @return list of ArchiveMember.
    @throws UnsafeArchiveError For an unsafe archive.
    """
    with GerberArchive(source, max_member_bytes) as zf:
        return zf.members()
