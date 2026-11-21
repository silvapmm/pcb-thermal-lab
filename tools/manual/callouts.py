#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file callouts.py
@brief Numbered red boxes on a screenshot of a window, found from the Qt geometry of the widgets, and the numbered list that explains them.

@details The user manual shows some windows with red boxes and numbers, and a numbered list under the picture says what each box is. The
         numbers in the picture and in the list must never drift apart, so both come from ONE list of `Callout` objects:

           - the rectangle of each box is the geometry of the widget itself (`QWidget.mapTo(root, (0, 0))` plus its size, in the logical pixels of
             the window that was grabbed), never a hand-measured pixel position; the pixmap of `QWidget.grab()` is `devicePixelRatio` times larger
             than the window and the boxes are scaled by that ratio, then by the factor that brings the picture to the width stored in the repository;
           - `annotate()` draws the boxes (outline of `BOX_WIDTH_PX` pixels in the final picture) and the numbered round badges with QPainter on a
             QImage, with no dependency beyond PySide 6, and returns the pixmap with the badge positions;
           - `callouts_markdown()` writes the list (`1. **Menu bar.** ...`) that is pasted in the manual;
           - the number of boxes is written into the PNG (text chunk `pcbt-callouts`), so `tests/test_user_manual.py` can check that the list
             under every annotated picture has exactly as many items as the picture has boxes.

         A badge sits OUTSIDE the corner of its box when the picture has room (top left, then the other corners, then along the top and the left
         edge), so it does not hide the element it numbers; two badges never overlap (the candidates are tried in order and a taken place is skipped);
         only when nothing outside is free (boxes that tile the window, as the docks do) the badge goes inside the box, at its top right corner,
         or at the top left one. Among the free places the badge also looks at the picture: a place that would hide text or lines (`busyness`) is
         passed over for the next one, so a badge does not land on a label or on the tab names beside a row of controls.

         The idea (numbered boxes drawn from the widget geometry, a list beside the picture) follows the manual of the maintainer's Water Pump
         Simulator; the code is ours. Used by `examples/make_manual_callouts.py`.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Union

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

BOX_COLOUR = "#e5251b"          # Red that reads on the white of the light theme and on the grey of the panels
BOX_WIDTH_PX = 2                # Outline of a box in the final picture
BADGE_RADIUS_PX = 11            # Radius of the numbered circle in the final picture
BUSY_LIMIT = 0.015              # A badge may hide at most this share of detail (pixels that differ from the background under it)
PNG_KEY = "pcbt-callouts"       # Text chunk of the PNG that holds the number of boxes

Target = Union[str, Callable, QRect, object]


@dataclass
class Callout:
    """!
    @brief One numbered box: what it marks and what the list says about it.
    @param target Where the box goes: a QWidget, a dotted attribute path from the root widget (`"results.tabs"`), a callable `f(root)` that returns a widget or a QRect, or a QRect already in the logical pixels of the root widget.
    @param text Markdown of the list item (the label in bold, then the explanation); the number is added by `callouts_markdown`.
    @param badge_left When the badge has to go inside the box, put it at the left end of the top edge instead of the right end (a status bar keeps its version number at the right).
    """

    target: Target
    text: str
    badge_left: bool = False


def widget_rect(widget, root) -> QRect:
    """!
    @brief Rectangle of a widget in the logical pixel coordinates of the root widget that is grabbed.
    @param widget The widget to mark (anything with `mapTo`, `width` and `height`, as QWidget).
    @param root The widget whose `grab()` is annotated (its top left is the origin).
    @return QRect with the position and size of the widget in the root, in logical pixels.
    """
    top_left = widget.mapTo(root, QPoint(0, 0))
    return QRect(top_left.x(), top_left.y(), widget.width(), widget.height())


def resolve(target: Target, root) -> QRect:
    """!
    @brief Turn the target of a callout into a rectangle in the root's logical pixels.
    @param target See `Callout.target`.
    @param root The grabbed widget.
    @return QRect in the logical pixels of the root.
    @throws AttributeError If a dotted path does not exist.
    @throws TypeError If a callable returns something that is neither a widget nor a QRect.
    """
    if isinstance(target, str):
        obj = root
        for part in target.split("."):
            obj = getattr(obj, part)
            obj = obj() if callable(obj) and not hasattr(obj, "mapTo") else obj       # an accessor such as `menuBar`
        target = obj
    elif callable(target) and not hasattr(target, "mapTo") and not isinstance(target, QRect):
        target = target(root)
    if isinstance(target, QRect):
        return QRect(target)
    if hasattr(target, "mapTo"):
        return widget_rect(target, root)
    raise TypeError(f"a callout target must be a widget, a QRect, a path or a callable, not {type(target).__name__}")


def union(*targets: Target) -> Callable:
    """!
    @brief A target that is the smallest rectangle holding several widgets (one box around a group of controls).
    @param targets Widgets, paths, callables or QRects, as `Callout.target`.
    @return A callable `f(root)` that returns the QRect of the union, for `Callout.target`.
    """
    def united(root) -> QRect:
        rects = [resolve(t, root) for t in targets]
        out = rects[0]
        for r in rects[1:]:
            out = out.united(r)
        return out
    return united


def grow(target: Target, margin: int) -> Callable:
    """!
    @brief A target that is another target enlarged on every side (a box with a little air around a small control).
    @param target Widget, path, callable or QRect, as `Callout.target`.
    @param margin Pixels added on each side, in the logical pixels of the root.
    @return A callable `f(root)` that returns the enlarged QRect.
    """
    return lambda root: resolve(target, root).adjusted(-margin, -margin, margin, margin)


def scale_rect(rect: QRect, factor: float) -> QRectF:
    """!
    @brief Scale a rectangle from logical pixels to the pixels of the final picture.
    @param rect Rectangle in logical pixels.
    @param factor Final pixels per logical pixel (device pixel ratio times the width reduction).
    @return QRectF in final pixels.
    """
    return QRectF(rect.x() * factor, rect.y() * factor, rect.width() * factor, rect.height() * factor)


def place_badges(boxes: Sequence[QRectF], width: float, height: float, radius: float = BADGE_RADIUS_PX, left_first: Sequence[int] = (), busy: Optional[Callable[[QPointF], float]] = None) -> list:
    """!
    @brief Choose the centre of every numbered badge: outside the corner of its box when there is room, never over another badge, never inside another box.
    @details Candidates in order: outside the top left corner, the other three corners, along the top and down the left edge; then, for a box that is hemmed
             in (a dock beside a dock, a picture edge), INSIDE its own top right corner (then further left along the top edge) and, last, its top left corner. A candidate whose centre lies deeper than half a badge inside another
             callout's box is skipped (touching boxes share an edge), because the number would read as that box's number.
    @param boxes Rectangles in the pixels of the final picture, in the order of the numbers.
    @param width Width of the picture in pixels.
    @param height Height of the picture in pixels.
    @param radius Radius of a badge in pixels.
    @param left_first Indices of the boxes whose badge goes at the left end of the top edge when it has to go inside.
    @param busy Function that tells how much of the picture a badge at a centre would hide (0 = plain background, 1 = all detail), or None to ignore the content. The first free candidate that hides at most `BUSY_LIMIT` is taken; when every free candidate hides more, the least busy one.
    @return List of QPointF, the centre of the badge of each box.
    """
    placed: list = []
    step = 2 * radius + 3                                    # centre distance that keeps two badges apart with a small gap

    def gap(c: QPointF, b: QRectF) -> float:
        # Distance from a point to a rectangle (0 inside it)
        dx = max(b.left() - c.x(), 0.0, c.x() - b.right())
        dy = max(b.top() - c.y(), 0.0, c.y() - b.bottom())
        return math.hypot(dx, dy)

    def free(c: QPointF, own: QRectF, inside_own: bool) -> bool:
        # Inside the picture and clear of every badge already placed
        if c.x() < radius + 1 or c.y() < radius + 1 or c.x() > width - radius - 1 or c.y() > height - radius - 1:
            return False
        if any(math.hypot(c.x() - p.x(), c.y() - p.y()) < step for p in placed):
            return False
        inner = QRectF(own).adjusted(1, 1, -1, -1)
        if inside_own:
            return inner.contains(c)
        if inner.contains(c):
            return False
        # An outside badge must not read as the number of a neighbour. A small control may sit close to its neighbours (a row of check boxes
        # has gaps of a few pixels), so its badge may overlap a neighbour's edge by a sliver; a large box (a dock, a table, a picture) may not touch
        # another box at all, and goes inside its own corner instead, where it is unambiguous.
        large = min(own.width(), own.height()) > 6 * radius
        for b in boxes:
            if b is own:
                continue
            if large and gap(c, b) < 1.5 * radius:
                return False
            if not large and QRectF(b).adjusted(radius * 0.5, radius * 0.5, -radius * 0.5, -radius * 0.5).contains(c):
                return False
        return True

    for index, box in enumerate(boxes):
        x0, y0, x1, y1 = box.left(), box.top(), box.right(), box.bottom()
        r = radius
        outside = [QPointF(x0 - r * 0.9, y0 - r * 0.9)]      # at the corner, the disc just clear of the box: it hides nothing of the element
        outside += [QPointF(x0 - r, y0 - r), QPointF(x1 + r, y0 - r), QPointF(x0 - r, y1 + r), QPointF(x1 + r, y1 + r)]
        cy = (y0 + y1) / 2.0
        outside += [QPointF(x1 + r, cy), QPointF(x0 - r, cy)]  # level with the middle of the box, to its right (a tab bar) and to its left
        for k in range(1, 6):                               # along the top edge, to the right, and down the left edge
            outside.append(QPointF(x0 + k * step - r, y0 - r))
            outside.append(QPointF(x0 - r, y0 + k * step - r))
        inside = [QPointF(x1 - r - 3 - k * step, y0 + r + 3) for k in range(4)] + [QPointF(x0 + r + 3, y0 + r + 3)]
        if index in left_first:
            inside = [QPointF(x0 + r + 3 + k * step, y0 + r + 3) for k in range(4)] + [QPointF(x1 - r - 3, y0 + r + 3)]
        # Free places, outside ones first; the content under the badge decides among them
        candidates = [c for c in outside if free(c, box, False)] + [c for c in inside if free(c, box, True)]
        chosen = None
        if candidates:
            if busy is None:
                chosen = candidates[0]
            else:
                scores = [busy(c) for c in candidates]
                chosen = next((c for c, v in zip(candidates, scores) if v <= BUSY_LIMIT), candidates[scores.index(min(scores))])
        if chosen is None:                                  # nothing is free (a thin box on the picture edge): scan along its top edge, then down, from the preferred end
            rows = max(1, int((height - 2 * r) // step))
            cols = max(1, int((width - 2 * r) // step))
            sign, start = (1, x0 + r + 3) if index in left_first else (-1, x1 - r - 3)
            scan = [QPointF(min(max(start + sign * i * step, r + 1), width - r - 1), min(y0 + r + 3 + j * step, height - r - 1)) for j in range(rows) for i in range(cols)]
            clear = [c for c in scan if all(math.hypot(c.x() - p.x(), c.y() - p.y()) >= step for p in placed)] or scan[:1]
            scores = [busy(c) if busy else 0.0 for c in clear]
            chosen = next((c for c, v in zip(clear, scores) if v <= BUSY_LIMIT), clear[scores.index(min(scores))])
        placed.append(chosen)
    return placed


def busyness(image: QImage, centre: QPointF, radius: float) -> float:
    """!
    @brief How much detail a badge at `centre` would hide: the share of the pixels of the disc that differ much from the typical (median) brightness there.
    @param image The picture (RGB), outlines of the boxes already drawn.
    @param centre Centre of the badge, pixels of `image`.
    @param radius Radius of the badge in pixels.
    @return A number between 0 (a plain background) and 1 (all of the disc is text, lines or an image).
    """
    values = []
    cx, cy, r = int(round(centre.x())), int(round(centre.y())), int(radius)
    for y in range(max(0, cy - r), min(image.height(), cy + r + 1)):
        for x in range(max(0, cx - r), min(image.width(), cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                c = QColor(image.pixel(x, y))
                values.append((c.red() + c.green() + c.blue()) / 3.0)
    if not values:
        return 1.0
    typical = sorted(values)[len(values) // 2]
    return sum(1 for v in values if abs(v - typical) > 40) / len(values)


def annotate(image: QImage, boxes: Sequence[QRectF], colour: str = BOX_COLOUR, left_first: Sequence[int] = ()) -> list:
    """!
    @brief Draw the numbered boxes on a picture, in place.
    @param image QImage (the final picture, already at its stored width); drawn on directly.
    @param boxes Rectangles in the pixels of `image`, in the order of the numbers (the first box is number 1).
    @param colour Colour of the outlines and the badges, `#rrggbb`.
    @param left_first Indices of the boxes whose badge goes at the left end of the top edge when it has to go inside (see `place_badges`).
    @return List of QPointF with the centre of each badge, in pixels of `image`.
    """
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    red = QColor(colour)
    # Outline of the box: a rectangle whose line lies inside the box edge, so that two neighbouring boxes stay apart
    half = BOX_WIDTH_PX / 2.0
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(red, BOX_WIDTH_PX, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin))
    for box in boxes:
        painter.drawRect(box.adjusted(half, half, -half, -half))
    painter.end()
    # The badges are placed on the picture with the outlines already drawn, so that a badge also keeps off the line of a neighbour
    centres = place_badges(boxes, image.width(), image.height(), left_first=left_first, busy=lambda c: busyness(image, c, BADGE_RADIUS_PX))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    # Badge: red disc with a white ring (it reads on a dark or a light part of the window) and the number in white
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(BADGE_RADIUS_PX * 1.25))
    painter.setFont(font)
    for number, centre in enumerate(centres, start=1):
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(red)
        painter.drawEllipse(centre, BADGE_RADIUS_PX, BADGE_RADIUS_PX)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(centre.x() - BADGE_RADIUS_PX, centre.y() - BADGE_RADIUS_PX, 2 * BADGE_RADIUS_PX, 2 * BADGE_RADIUS_PX), Qt.AlignCenter, str(number))
    painter.end()
    return centres


def callouts_markdown(callouts: Sequence[Callout]) -> str:
    """!
    @brief The numbered list that goes under the picture, one item per box, numbered as the badges.
    @param callouts The callouts in the order of the numbers.
    @return Markdown text with `1. ...`, `2. ...`, one item per callout.
    """
    return "".join(f"{n}. {c.text.strip()}\n" for n, c in enumerate(callouts, start=1))


def render(widget, callouts: Sequence[Callout], path: str, max_width: int = 1400, region: Optional[QRect] = None, zoom: float = 1.0) -> list:
    """!
    @brief Grab a widget, draw the numbered boxes of its callouts, save the PNG and write the list beside it.
    @param widget The window or dialog to grab (it must be shown and laid out).
    @param callouts The callouts in the order of the numbers.
    @param path The PNG to write; the list goes to the same name with the suffix `.md`, in the same folder.
    @param max_width Widest picture stored, in pixels (the grab is scaled down to it, then the boxes are drawn so that the outline stays BOX_WIDTH_PX wide).
    @param region Part of the widget to keep, a QRect in the logical pixels of the widget (None: the whole widget); the boxes follow the crop.
    @param zoom Enlargement of a small crop (a tool bar strip) before the boxes are drawn; the width still stops at `max_width`.
    @return List of QPointF, the centres of the badges in the saved picture.
    """
    pix = widget.grab(region) if region is not None else widget.grab()
    ratio = pix.devicePixelRatio()
    image = pix.toImage().convertToFormat(QImage.Format_RGB32)
    image.setDevicePixelRatio(1.0)
    factor = ratio * zoom                                   # final pixels per logical pixel
    target_width = min(max_width, round(image.width() * zoom))
    factor *= target_width / (image.width() * zoom)
    if target_width != image.width():
        image = image.scaledToWidth(target_width, Qt.SmoothTransformation)
    origin = region.topLeft() if region is not None else QPoint(0, 0)
    boxes = [scale_rect(resolve(c.target, widget).translated(-origin), factor) for c in callouts]
    centres = annotate(image, boxes, left_first=[i for i, c in enumerate(callouts) if c.badge_left])
    # The count of boxes travels in the file: the manual test compares it with the items of the list
    image.setText(PNG_KEY, str(len(callouts)))
    image.save(path)
    with open(os.path.splitext(path)[0] + ".md", "w", encoding="utf-8") as handle:
        handle.write(callouts_markdown(callouts))
    return centres


def count_in_png(path: str) -> Optional[int]:
    """!
    @brief Number of boxes stored in a picture made by `render`.
    @param path PNG file.
    @return The number of boxes, or None if the file carries no such text chunk (a plain screenshot).
    """
    image = QImage(path)
    text = image.text(PNG_KEY)
    return int(text) if text else None
