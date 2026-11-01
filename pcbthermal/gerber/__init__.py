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
         - what is it: `detect_function(name, head)` / `detect_file(path)` -> `LayerFunction`; `order_copper_layers`.
         - archives: `GerberArchive(path)` / `inspect_archive(path)` (zip-slip guard, 2 GB declared limit, headers only for the detection).
         A construct that would change the geometry if ignored raises `UnsupportedFeatureError` (file and feature named); see parser.py for the list.
         The reader is the port of the research prototype `research/gerber-import/lib/native_gerber.py`; the design is in `research/gerber-real-boards/INTEGRATION.md`.
"""

from pathlib import Path

from .archive import ArchiveMember, GerberArchive, inspect_archive
from .errors import GerberError, OutlineError, UnsafeArchiveError, UnsupportedFeatureError
from .excellon import DrillFile, Hole, drill_function, read_drill, read_drill_file
from .functions import LayerFunction, detect_file, detect_function, order_copper_layers
from .outline import Outline, OutlinePolygon, outline_from_layer, read_outline
from .parser import Flash, Layer, ObjectAttrs
from .raster import (DEFAULT_SUPERSAMPLE, RasterEstimate, Window, check_sample_spacing, coverage_area_mm2, estimate_raster_bytes,
                     pixel_counts, rasterize, suggest_pixel_mm, window_of)

__all__ = [
    "ArchiveMember", "DEFAULT_SUPERSAMPLE", "DrillFile", "Flash", "GerberArchive", "GerberError", "Hole", "Layer", "LayerFunction", "ObjectAttrs", "Outline",
    "OutlineError", "OutlinePolygon", "RasterEstimate", "UnsafeArchiveError", "UnsupportedFeatureError", "Window", "check_sample_spacing", "coverage_area_mm2",
    "detect_file", "detect_function", "drill_function", "estimate_raster_bytes", "inspect_archive", "order_copper_layers", "outline_from_layer", "parse_layer",
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


def read_layer(path):
    """!
    @brief Read and parse a Gerber file from disk.
    @param path File path.
    @return Layer.
    @throws UnsupportedFeatureError For a construct the reader refuses.
    @throws GerberError For a malformed file.
    """
    p = Path(path)
    return Layer(p.read_text(errors="replace"), p.name)
