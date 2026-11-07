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
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy


class ElidedLabel(QLabel):
    """!
    @brief QLabel that shows its text on one line, cut with an ellipsis at the right when it does not fit; the full text is the tooltip.
    """

    def __init__(self, text="", parent=None):
        """!
        @param text Initial text (plain text; it may list file names).
        @param parent Qt parent widget or None.
        """
        super().__init__(parent)
        self._full = ""
        self.setTextFormat(Qt.PlainText)
        # Ignored horizontally: the layout gives the label what is left and never asks for more
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setText(text)

    def setText(self, text):
        """!
        @brief Set the full text; the shown text is cut to the width and the tooltip holds all of it.
        @param text Text to show (plain).
        """
        self._full = str(text)
        super().setText("")                       # the painting is done here; the base class keeps no text to measure
        self.setToolTip(self._full)
        self.updateGeometry()
        self.update()

    def text(self):
        """!
        @brief The full text, not the cut one.
        @return str
        """
        return self._full

    def minimumSizeHint(self):
        """!
        @brief Zero width: the text never asks the layout for room.
        @return QSize
        """
        return QSize(0, super().minimumSizeHint().height() or self.fontMetrics().height())

    def sizeHint(self):
        """!
        @brief A small width and one line of height (the label takes what the layout gives).
        @return QSize
        """
        return QSize(0, self.fontMetrics().height() + 2 * self.margin() + 2)

    def paintEvent(self, event):
        """!
        @brief Draw the text cut with an ellipsis to the width of the label.
        @param event QPaintEvent (unused).
        """
        painter = QPainter(self)
        r = self.contentsRect()
        text = QFontMetrics(self.font()).elidedText(self._full, Qt.ElideRight, max(r.width(), 0))
        painter.setPen(self.palette().windowText().color())
        painter.drawText(r, int(self.alignment()), text)


def clamp_to_screen(widget, margin=0):
    """!
    @brief Make a top-level window no larger than the available area of its screen (pixels) and keep it on the screen.
    @param widget Top-level QWidget.
    @param margin Pixels kept free on each side of the available area.
    @return bool True when the size or the position was changed.
    """
    screen = widget.screen() or QApplication.primaryScreen()
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
