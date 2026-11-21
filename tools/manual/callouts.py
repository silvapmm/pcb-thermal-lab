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

         A badge must read as the number of its own box: it never reaches into another box and is never nearer another box than its own
         (`place_badges`). A small box (a button, a combo box) gets its badge outside a corner or beside it; a large box (a table, a chart, a
         dock) inside its own top right corner, where a table or a chart is usually empty. Two badges never overlap, and among the places that
         pass, one that would hide text or lines (`busyness`, judged on the picture without the outlines) is passed over for the next one.

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
    @param badge_left When the badge has to go inside the box, start from its left end instead of the right end (a status bar keeps its version number at the right).
    @param badge_inside Treat the box as a large one: its badge goes inside its top right corner first (a wide button or a line of text with empty room at its
                        right end, whose outside is crowded with text).
    """

    target: Target
    text: str
    badge_left: bool = False
    badge_inside: bool = False


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


def place_badges(boxes: Sequence[QRectF], width: float, height: float, radius: float = BADGE_RADIUS_PX, left_first: Sequence[int] = (), busy: Optional[Callable[[QPointF], float]] = None, inside_first: Sequence[int] = ()) -> list:
    """!
    @brief Choose the centre of every numbered badge so that it reads as the number of its own box: never nearer another box than its own, never over another badge.
    @details A badge is useful only if the eye gives it to the right box. In a dense window (a row of controls under a tab bar, two rows of controls one
             above the other) a badge just outside a corner is often as near the next control as its own, and reads as the next one's number (the first
             version of this rule put the badge of the Scheme row of the Animation page beside the Model row). So every candidate must pass the
             OWNERSHIP test: the disc does not reach into another box (its centre is at least one radius from it) and its centre is not nearer another
             box than its own box. A box that holds the badge's box (a group box around a control) counts by its outline, so a badge inside it, far from
             its edges, is fine.

             Candidates in order. A large box (a table, a chart, a dock: both sides above 4 radii) first tries INSIDE its own top right corner, then further
             left along the top edge, then its top left corner (the inside corner of a table or a chart is usually empty and the badge is unambiguous
             there); then the outside places. A small box (a button, a combo box, a line) first tries the outside places: the top left corner (the disc
             just clear of the box), level with its middle on the left (a bullet), the top right corner, level with its middle on the right, the
             bottom corners, along the top edge and down the left edge; then the inside corners. Among the candidates that pass, the first that hides at most `BUSY_LIMIT` of detail is taken,
             otherwise the least busy of the preferred side (inside for a large box, outside for a small one). When nothing passes (a thin bar at the picture edge: the menu bar, the status bar), the badge goes inside the box,
             on its middle line, at the first quiet place from the preferred end (left with `left_first`, else right).
    @param boxes Rectangles in the pixels of the final picture, in the order of the numbers.
    @param width Width of the picture in pixels.
    @param height Height of the picture in pixels.
    @param radius Radius of a badge in pixels.
    @param left_first Indices of the boxes whose badge, when it has to go inside, starts from the left end (a status bar keeps the version at the right).
    @param inside_first Indices of the boxes treated as large whatever their size (`Callout.badge_inside`).
    @param busy Function `busy(centre, clip=None)` that tells how much of the picture a badge at a centre would hide (0 = plain background, 1 = all detail),
                counting only the pixels inside the QRectF `clip` when one is given (the last resort inside a thin bar), or None to ignore the content.
    @return List of QPointF, the centre of the badge of each box.
    """
    placed: list = []
    step = 2 * radius + 3                                    # centre distance that keeps two badges apart with a small gap

    def gap(c: QPointF, b: QRectF) -> float:
        # Distance from a point to a rectangle (0 inside it)
        dx = max(b.left() - c.x(), 0.0, c.x() - b.right())
        dy = max(b.top() - c.y(), 0.0, c.y() - b.bottom())
        return math.hypot(dx, dy)

    def edge_gap(c: QPointF, b: QRectF) -> float:
        # Distance from a point to the OUTLINE of a rectangle (inside it: to the nearest edge)
        if b.contains(c):
            return min(c.x() - b.left(), b.right() - c.x(), c.y() - b.top(), b.bottom() - c.y())
        return gap(c, b)

    def holds(outer: QRectF, inner: QRectF) -> bool:
        # The outer box contains the inner one (a group box around a control), with a pixel of tolerance
        return QRectF(outer).adjusted(-1, -1, 1, 1).contains(inner)

    def owned(c: QPointF, own: QRectF, inside_own: bool) -> bool:
        # Inside the picture, clear of every badge already placed, and unambiguously the number of its own box
        if c.x() < radius + 1 or c.y() < radius + 1 or c.x() > width - radius - 1 or c.y() > height - radius - 1:
            return False
        if any(math.hypot(c.x() - p.x(), c.y() - p.y()) < step for p in placed):
            return False
        inner = QRectF(own).adjusted(1, 1, -1, -1)
        if inside_own != inner.contains(c):
            return False
        own_gap = 0.0 if inside_own else gap(c, own)
        for b in boxes:
            if b is own:
                continue
            other = edge_gap(c, b) if holds(b, own) else gap(c, b)
            if other < radius - 1 or other < own_gap - 1:           # one pixel of tolerance: the disc may graze a neighbour's line
                return False
        return True

    for index, box in enumerate(boxes):
        x0, y0, x1, y1 = box.left(), box.top(), box.right(), box.bottom()
        r = radius
        cy = (y0 + y1) / 2.0
        outside = [QPointF(x0 - r * 0.9, y0 - r * 0.9)]      # at the corner, the disc just clear of the box: it hides nothing of the element
        outside += [QPointF(x0 - r, cy)]                    # level with the middle of the box, to its left, as a list bullet (a row between two rows)
        outside += [QPointF(x0 - r, y0 - r), QPointF(x1 + r, y0 - r), QPointF(x1 + r, cy), QPointF(x0 - r, y1 + r), QPointF(x1 + r, y1 + r)]
        for k in range(1, 6):                               # along the top edge, to the right, and down the left edge
            outside.append(QPointF(x0 + k * step - r, y0 - r))
            outside.append(QPointF(x0 - r, y0 + k * step - r))
        yi = min(y0 + r + 3, cy)                            # inside: just under the top edge, or on the middle line of a box thinner than a badge
        inside = [QPointF(x1 - r - 3 - k * step, yi) for k in range(4)] + [QPointF(x0 + r + 3, yi)]
        if index in left_first:
            inside = [QPointF(x0 + r + 3 + k * step, yi) for k in range(4)] + [QPointF(x1 - r - 3, yi)]
        large = min(box.width(), box.height()) > 4 * r or index in inside_first
        first_group = [c for c in (inside if large else outside) if owned(c, box, large)]
        second_group = [c for c in (outside if large else inside) if owned(c, box, not large)]
        # A small control's badge goes inside it only when no outside place passes: inside, even a quiet place (the gap between two buttons)
        # sits on the control itself
        candidates = first_group + second_group if large or not first_group else first_group
        chosen = None
        if candidates:
            if busy is None:
                chosen = candidates[0]
            else:
                scores = [busy(c) for c in candidates]
                chosen = next((c for c, v in zip(candidates, scores) if v <= BUSY_LIMIT), None)
                if chosen is None:
                    # Nothing quiet: the least busy place of the preferred side (a small control's badge grazes the text beside it rather
                    # than hiding the control's own label from inside)
                    group = scores[:len(first_group)] or scores
                    chosen = candidates[group.index(min(group))]
        if chosen is None:                                  # nothing passes (a thin bar on the picture edge): its middle line, from the preferred end
            yc = min(max(cy, r + 1), height - r - 1)
            cols = max(1, int((x1 - x0 - 2 * r) // 4))      # every 4 px along the bar, so the badge can stop right after a word
            sign, start = (1, x0 + r + 3) if index in left_first else (-1, x1 - r - 3)
            scan = [QPointF(min(max(start + sign * 4 * i, r + 1), width - r - 1), yc) for i in range(cols)]
            clear = [c for c in scan if all(math.hypot(c.x() - p.x(), c.y() - p.y()) >= step for p in placed)] or scan[:1]
            scores = [busy(c, box) if busy else 0.0 for c in clear]    # only the detail of the bar itself: the disc must overlap its neighbours
            k = next((i for i, v in enumerate(scores) if v <= BUSY_LIMIT), scores.index(min(scores)))
            if k + 2 < len(clear) and scores[k + 2] <= BUSY_LIMIT:    # 8 px further on: a little air after the last word (the antialiased edge of a letter reads as plain)
                k += 2
            chosen = clear[k]
        placed.append(chosen)
    return placed


def busyness(image: QImage, centre: QPointF, radius: float, clip: Optional[QRectF] = None) -> float:
    """!
    @brief How much detail a badge at `centre` would hide: the share of the pixels of the disc that differ much from the typical (median) brightness there.
    @param image The picture (RGB), outlines of the boxes already drawn.
    @param centre Centre of the badge, pixels of `image`.
    @param radius Radius of the badge in pixels.
    @param clip Count only the pixels inside this QRectF (None: the whole disc).
    @return A number between 0 (a plain background) and 1 (all of the disc is text, lines or an image).
    """
    values = []
    cx, cy, r = int(round(centre.x())), int(round(centre.y())), int(radius)
    for y in range(max(0, cy - r), min(image.height(), cy + r + 1)):
        for x in range(max(0, cx - r), min(image.width(), cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (clip is None or clip.contains(QPointF(x, y))):
                c = QColor(image.pixel(x, y))
                values.append((c.red() + c.green() + c.blue()) / 3.0)
    if not values:
        return 1.0
    typical = sorted(values)[len(values) // 2]
    return sum(1 for v in values if abs(v - typical) > 40) / len(values)


def annotate(image: QImage, boxes: Sequence[QRectF], colour: str = BOX_COLOUR, left_first: Sequence[int] = (), inside_first: Sequence[int] = ()) -> list:
    """!
    @brief Draw the numbered boxes on a picture, in place.
    @param image QImage (the final picture, already at its stored width); drawn on directly.
    @param boxes Rectangles in the pixels of `image`, in the order of the numbers (the first box is number 1).
    @param colour Colour of the outlines and the badges, `#rrggbb`.
    @param left_first Indices of the boxes whose badge goes at the left end of the top edge when it has to go inside (see `place_badges`).
    @param inside_first Indices of the boxes whose badge goes inside first (see `place_badges`).
    @return List of QPointF with the centre of each badge, in pixels of `image`.
    """
    # The content under a badge is judged on the picture WITHOUT the outlines: the red line of the badge's own box is not detail it hides
    # (judged with the outlines, every place next to a corner looked busy and the badges drifted away from their boxes); keeping off a
    # neighbour's box is the ownership test of place_badges
    clean = image.copy()
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
    centres = place_badges(boxes, image.width(), image.height(), left_first=left_first, busy=lambda c, clip=None: busyness(clean, c, BADGE_RADIUS_PX, clip), inside_first=inside_first)
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


def render(widget, callouts: Sequence[Callout], path: str, max_width: int = 1400, region: Optional[QRect] = None, zoom: float = 1.0, pad_top: int = 0) -> list:
    """!
    @brief Grab a widget, draw the numbered boxes of its callouts, save the PNG and write the list beside it.
    @param widget The window or dialog to grab (it must be shown and laid out).
    @param callouts The callouts in the order of the numbers.
    @param path The PNG to write; the list goes to the same name with the suffix `.md`, in the same folder.
    @param max_width Widest picture stored, in pixels (the grab is scaled down to it, then the boxes are drawn so that the outline stays BOX_WIDTH_PX wide).
    @param region Part of the widget to keep, a QRect in the logical pixels of the widget (None: the whole widget); the boxes follow the crop.
    @param zoom Enlargement of a small crop (a tool bar strip) before the boxes are drawn; the width still stops at `max_width`.
    @param pad_top Pixels of the final picture added above the grab, in the colour of its top left pixel: room for the badges of a strip (the tool bar) whose
                   controls fill its whole height, so that each badge sits above its own control instead of beside it, between two controls.
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
    if pad_top > 0:
        padded = QImage(image.width(), image.height() + pad_top, QImage.Format_RGB32)
        padded.fill(image.pixelColor(0, 0))
        painter = QPainter(padded)
        painter.drawImage(0, pad_top, image)
        painter.end()
        image = padded
    origin = region.topLeft() if region is not None else QPoint(0, 0)
    boxes = [scale_rect(resolve(c.target, widget).translated(-origin), factor).translated(0, pad_top) for c in callouts]
    centres = annotate(image, boxes, left_first=[i for i, c in enumerate(callouts) if c.badge_left], inside_first=[i for i, c in enumerate(callouts) if c.badge_inside])
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
