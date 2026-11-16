#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file dots.py
@brief The round verdict dot, drawn once for every place that shows one (the warning rows and the memory lines of the Simulation panel): the same tokens as the memory verdicts.
@details Colours are the theme tokens `bad` (a warning, the colour of 'refuse') and `warn` (a note, the colour of 'slow'); the dot is never the only carrier of
         the severity (the rows also say 'Warning:' or 'Note:' in their accessible name and tooltip).
"""

import base64
import math

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap

_HTML_CACHE = {}      # (logical size, colour) -> the <img> tag of the dot for rich text
_ICON_CACHE = {}      # (logical size, device pixel ratio, colour) -> QPixmap of the dot, drawn once


def severity_token(severe):
    """!
    @brief The theme token of a severity.
    @param severe True for a warning (alert), False for a note.
    @return str "bad" or "warn".
    """
    return "bad" if severe else "warn"


def dot_pixmap(size, dpr, colour):
    """!
    @brief The severity dot of a warning: a solid round dot centred in a square of `size` px, drawn with QPainter (ours, no glyph set).
    @details The severity is also in the accessible name and the tooltip of the row, so the colour is never the only carrier. Cached per (size, ratio, colour).
    @param size Logical edge of the square in px.
    @param dpr Device pixel ratio of the screen.
    @param colour Fill colour as '#rrggbb' (the `bad` token for a warning, the `warn` token for a note: the colours of the memory verdicts).
    @return QPixmap.
    """
    key = (size, round(dpr, 3), colour)
    pm = _ICON_CACHE.get(key)
    if pm is not None:
        return pm
    pm = QPixmap(math.ceil(size * dpr), math.ceil(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(colour))
    r = max(3.0, size * 0.30)                          # A dot of about 60 % of the square: the same weight as the memory-verdict dots
    p.drawEllipse(QPointF(size / 2.0, size / 2.0), r, r)
    p.end()
    _ICON_CACHE[key] = pm
    return pm


def dot_html(colour, size=12):
    """!
    @brief The same dot as rich text, for a QLabel that shows lines of HTML (the memory lines of the Simulation panel): an <img> of the pixmap of dot_pixmap.
    @details One painter for every dot of the window (review of the window: the memory lines drew a text glyph, the warning rows a pixmap). The picture is drawn at
             twice the size and shown at `size` px, so it stays round on a screen with a device pixel ratio of 2; Qt's rich text reads the data URL.
    @param colour Fill colour as '#rrggbb' (a theme token value).
    @param size Logical edge in px of the square of the dot (the height of a line of small text).
    @return str HTML <img> tag.
    """
    key = (size, colour)
    tag = _HTML_CACHE.get(key)
    if tag is None:
        pm = dot_pixmap(size, 2.0, colour)
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.WriteOnly)
        pm.save(buf, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(bytes(data)).decode("ascii")
        tag = f'<img src="{uri}" alt="{colour}" width="{size}" height="{size}" style="vertical-align: middle">'   # alt: the colour, readable in the text
        _HTML_CACHE[key] = tag
    return tag
