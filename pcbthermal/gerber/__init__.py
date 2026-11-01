#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file __init__.py
@brief Gerber import: our own reader of Gerber RS-274X (X2 attributes), Excellon drills, the board outline and ZIP sets, and the rasteriser to copper coverage. No GUI, no third-party dependency (NumPy and SciPy only).
@details Public API (everything in millimetres, the Gerber axes, rows of a raster running from the top edge downwards):
         - read: `read_layer(path)` / `parse_layer(text, name)` -> `Layer` (operations, X2 file attributes, object attributes net/ref/pin kept apart, `flashes()`, `bbox()`).
         - raster: `rasterize(layer, window, pixel_mm, supersample)` -> uint8 coverage (0..255), one layer at a time; `estimate_raster_bytes` for the memory guard;
           `Layer.thinnest_feature_mm`, `suggest_pixel_mm`, `check_sample_spacing` for the pixel; `coverage_area_mm2`, `window_of`, `Window`.
         - drills: `read_drill(text, name)` / `read_drill_file(path)` -> `DrillFile` of `Hole` (plated or not, slots).
         - outline: `read_outline(text, name)` / `outline_from_layer(layer)` -> `Outline` of polygons with holes, or `OutlineError`.
         - what is it: `detect_function(name, head)` / `detect_file(path)` -> `LayerFunction` (with a `confidence`: names alone are "low"), `detect_set(items)` (numbered copper layers resolved over the set); `order_copper_layers`.
         - parts: `components.py` (the X3 component layer, `parse_components`, `link_paste`, `link_copper`, `heat_polygon`) and `parts.py` (paste openings, placement files, the envelope
           matching rule, `build_parts` -> `PartsResult` of `ImportPart`); imported as submodules (`parts` needs the project model).
         - archives: `GerberArchive(path)` / `inspect_archive(path)` (zip-slip guard, 2 GB declared limit, 256 MB per member by default, headers only for the detection).
         A construct that would change the geometry if ignored raises `UnsupportedFeatureError` (file and feature named); see parser.py for the list.
         Hostile or broken input always ends in a `GerberError` (never a hang or a raw traceback): `parser.MAX_OPERATIONS` per layer, `excellon.MAX_HOLES`,
         bounded macro expressions, finite sizes, and `raster.MAX_RASTER_PIXELS` per rasterised window (the window is chosen from the outline, not from a stray object).
         The reader is the port of the research prototype `research/gerber-import/lib/native_gerber.py`; the design is in `research/gerber-real-boards/INTEGRATION.md`.
"""

from pathlib import Path

from . import limits
from .archive import ArchiveMember, GerberArchive, inspect_archive
from .errors import GerberError, OutlineError, UnsafeArchiveError, UnsupportedFeatureError
from .excellon import DrillFile, Hole, drill_function, read_drill, read_drill_file
from .functions import LayerFunction, detect_file, detect_function, detect_set, order_copper_layers
from .outline import Outline, OutlinePolygon, outline_from_layer, read_outline
from .parser import Flash, Layer, ObjectAttrs
from .raster import (DEFAULT_SUPERSAMPLE, RasterEstimate, Window, check_sample_spacing, coverage_area_mm2, estimate_raster_bytes,
                     pixel_counts, rasterize, suggest_pixel_mm, window_of)

__all__ = [
    "ArchiveMember", "DEFAULT_SUPERSAMPLE", "DrillFile", "Flash", "GerberArchive", "GerberError", "Hole", "Layer", "LayerFunction", "ObjectAttrs", "Outline",
    "OutlineError", "OutlinePolygon", "RasterEstimate", "UnsafeArchiveError", "UnsupportedFeatureError", "Window", "check_sample_spacing", "coverage_area_mm2",
    "detect_file", "detect_function", "detect_set", "drill_function", "estimate_raster_bytes", "inspect_archive", "order_copper_layers", "outline_from_layer", "parse_layer",
    "pixel_counts", "rasterize", "read_drill", "read_drill_file", "read_layer", "read_outline", "suggest_pixel_mm", "window_of",
]


def parse_layer(text, name=""):
    """!
    @brief Parse the text of a Gerber file.
    @param text File content.
    @param name File name, used in the messages of refusals and errors.
    @return Layer.
    @throws UnsupportedFeatureError For a construct the reader refuses.
    @throws GerberError For a malformed file.
    """
    return Layer(text, name)


def read_layer(path, max_bytes=None):
    """!
    @brief Read and parse a Gerber file from disk.
    @param path File path.
    @param max_bytes Largest file in bytes (None: the preference `gerber.max_file_mb`, 256 MB shipped); a larger file is refused from its size, before it is read.
    @return Layer.
    @throws UnsupportedFeatureError For a construct the reader refuses.
    @throws GerberError For a malformed file or one above the size limit.
    """
    p = Path(path)
    limits.check_path(p, max_bytes)
    return Layer(p.read_text(encoding="utf-8", errors="replace"), p.name)       # UTF-8 whatever the locale; a Latin-1 byte in a comment becomes U+FFFD
