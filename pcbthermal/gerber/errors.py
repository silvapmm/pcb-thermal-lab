#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file errors.py
@brief The exceptions of the Gerber reader: a file that cannot be read, a feature the reader refuses, an open outline, an unsafe archive.
@details A refusal always names the file and the feature, so that the import can tell the user what to change (or which tool to export with)
         instead of drawing a wrong board. A refused feature never produces a wrong area: the reader stops.
"""


class GerberError(ValueError):
    """!@brief A file (Gerber, Excellon, archive) that cannot be read or is malformed."""


class UnsupportedFeatureError(GerberError, NotImplementedError):
    """!@brief A valid construct that the reader deliberately does not implement (ignoring it would change the geometry)."""

    def __init__(self, file, feature):
        """!
        @brief Build the refusal.
        @param file    Name of the file (empty when unknown).
        @param feature Description of the unsupported construct.
        """
        self.file = file or ""
        self.feature = feature
        where = f"{self.file}: " if self.file else ""
        super().__init__(f"{where}{feature} is not supported")


class OutlineError(GerberError):
    """!@brief The profile layer does not describe a closed board contour."""


class UnsafeArchiveError(GerberError):
    """!@brief A ZIP file that is refused: unsafe member name (zip-slip), too large, too many members or an implausible compression ratio."""
