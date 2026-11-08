#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file elided.py
@brief A one-line label whose width never depends on its text, and the clamp of a window to the screen.
@details A QLabel without word wrap asks for the full width of its text as its minimum width, so a long file name or a long list of problems made the import window (and with it
         the layout of any window that holds such a label) grow wider than the screen. `ElidedLabel` reports a minimum width of zero, draws the text cut with an ellipsis and keeps
         the whole text in its tooltip. `clamp_to_screen` is the generic guard for the size a window may take (or restore) from the saved settings.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy


class ElidedLabel(QLabel):
    """!
    @brief QLabel whose text never asks the layout for width: wrapped on at most `max_lines` lines (anywhere when a word is longer than the line), the last line cut with an
           ellipsis when the text does not fit; the full text is the tooltip and the accessible description.
    """

    def __init__(self, text="", parent=None, max_lines=1):
        """!
        @param text Initial text (plain text; it may list file names).
        @param parent Qt parent widget or None.
        @param max_lines Most lines shown (1 = one line cut with an ellipsis); the height follows the lines the text needs at the current width, up to this number.
        """
        super().__init__(parent)
        self._full = ""
        self.max_lines = max(1, int(max_lines))
        self.setTextFormat(Qt.PlainText)
        # Ignored horizontally: the layout gives the label what is left and never asks for more
        policy = QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        policy.setHeightForWidth(self.max_lines > 1)
        self.setSizePolicy(policy)
        self.setText(text)

    def setText(self, text):
        """!
        @brief Set the full text; the shown text is cut to the width and the tooltip holds all of it.
        @param text Text to show (plain).
        """
        self._full = str(text)
        super().setText("")                       # the painting is done here; the base class keeps no text to measure
        self.setToolTip(self._full)
        self.setAccessibleDescription(self._full)  # a screen reader gets the whole text, not the cut one
        self.updateGeometry()
        self.update()

    def text(self):
        """!
        @brief The full text, not the cut one.
        @return str
        """
        return self._full

    def _lines(self, width):
        """!
        @brief The lines drawn at a width: the text wrapped (at spaces, anywhere inside a word longer than the line), at most `max_lines`, the last one elided.
        @param width Width in pixels.
        @return list of str (empty for an empty text).
        """
        if not self._full:
            return []
        fm = QFontMetrics(self.font())
        width = max(int(width), 1)
        if self.max_lines == 1:
            return [fm.elidedText(self._full.replace("\n", " "), Qt.ElideRight, width)]
        out, rest = [], " ".join(self._full.split())
        while rest and len(out) < self.max_lines - 1:
            if fm.horizontalAdvance(rest) <= width:
                break
            # The longest prefix that fits, cut at the last space when there is one
            n = len(rest)
            lo, hi = 1, n
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if fm.horizontalAdvance(rest[:mid]) <= width:
                    lo = mid
                else:
                    hi = mid - 1
            cut = rest.rfind(" ", 0, lo + 1)
            cut = cut if cut > 0 else lo
            out.append(rest[:cut].rstrip())
            rest = rest[cut:].lstrip()
        if rest:
            # The last line as it is when it fits (elidedText measures a little wider and would cut a line that fits), else cut with an ellipsis
            out.append(rest if fm.horizontalAdvance(rest) <= width else fm.elidedText(rest, Qt.ElideRight, width))
        return out

    def _height(self, lines):
        """!
        @brief Height in pixels for a number of lines (at least one).
        @param lines Number of lines.
        @return int
        """
        return max(1, lines) * self.fontMetrics().lineSpacing() + 2 * self.margin() + 2

    def hasHeightForWidth(self):
        """!
        @brief Only a label of several lines has a height that depends on its width.
        @return bool
        """
        return self.max_lines > 1

    def heightForWidth(self, width):
        """!
        @brief The height of the lines the text needs at a width (at most `max_lines`).
        @param width Width in pixels.
        @return int
        """
        return self._height(len(self._lines(width - 2 * self.margin())))

    def minimumSizeHint(self):
        """!
        @brief Zero width: the text never asks the layout for room.
        @return QSize
        """
        return QSize(0, self._height(1))

    def sizeHint(self):
        """!
        @brief Zero width and the height of the lines at the current width (the label takes the width the layout gives).
        @return QSize
        """
        return QSize(0, self.heightForWidth(self.width()) if self.max_lines > 1 else self._height(1))

    def resizeEvent(self, event):
        """!
        @brief A new width may need another number of lines: ask the layout again.
        @param event QResizeEvent.
        """
        super().resizeEvent(event)
        if self.max_lines > 1:
            self.updateGeometry()

    def paintEvent(self, event):
        """!
        @brief Draw the lines of the text, the last one cut with an ellipsis, to the width of the label.
        @param event QPaintEvent (unused).
        """
        painter = QPainter(self)
        r = self.contentsRect()
        painter.setPen(self.palette().color(self.foregroundRole()))
        step = self.fontMetrics().lineSpacing()
        lines = self._lines(r.width())
        # Vertical place of the block of lines as the alignment asks (one line: as before)
        top = r.top() + max(0, (r.height() - len(lines) * step) // 2) if self.alignment() & Qt.AlignVCenter else r.top()
        halign = int(self.alignment() & Qt.AlignHorizontal_Mask)
        for i, line in enumerate(lines):
            painter.drawText(r.left(), top + i * step, r.width(), step, halign | int(Qt.AlignVCenter), line)


def clamp_to_screen(widget, margin=0):
    """!
    @brief Make a top-level window no larger than the available area of its screen (pixels) and keep it on the screen.
    @details The screen is the one under the centre of the window (several monitors: a window restored on a large external monitor keeps its size there).
    @param widget Top-level QWidget.
    @param margin Pixels kept free on each side of the available area.
    @return bool True when the size or the position was changed.
    """
    # The screen under the centre of the window (a geometry restored on a second, larger monitor is judged against that monitor), else the widget's screen
    screen = QGuiApplication.screenAt(widget.geometry().center()) or widget.screen() or QApplication.primaryScreen()
    if screen is None:
        return False
    area = screen.availableGeometry().adjusted(margin, margin, -margin, -margin)
    w, h = min(widget.width(), area.width()), min(widget.height(), area.height())
    if not widget.isVisible():
        # Not shown yet: only the size matters (the window system or the parent places it)
        changed = (w, h) != (widget.width(), widget.height())
        if changed:
            widget.resize(w, h)
        return changed
    x = min(max(widget.x(), area.left()), max(area.right() - w + 1, area.left()))
    y = min(max(widget.y(), area.top()), max(area.bottom() - h + 1, area.top()))
    changed = (w, h) != (widget.width(), widget.height()) or (x, y) != (widget.x(), widget.y())
    if changed:
        widget.setGeometry(x, y, w, h)
    return changed
