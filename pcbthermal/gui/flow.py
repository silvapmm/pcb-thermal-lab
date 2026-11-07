#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file flow.py
@brief A layout that puts its widgets in a row and wraps them to a new line when the width is not enough.
@details Used for the control row of the Temperature and Gradients tabs, so that the row never asks for more width than the centre area has (the Results tab
         then has no horizontal scroll bar with both side docks open). The minimum width is that of the widest single widget.
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy


class FlowLayout(QLayout):
    """!
    @brief Left-to-right layout with line wrapping (the Qt "flow layout" pattern).
    """

    def __init__(self, parent=None, spacing=6):
        """!
        @brief Create the layout.
        @param parent Parent widget or None.
        @param spacing Horizontal and vertical gap between widgets in pixels.
        """
        super().__init__(parent)
        self._items = []
        self._space = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        """!
        @brief Add a layout item (called by Qt for addWidget).
        @param item QLayoutItem.
        """
        self._items.append(item)

    def count(self):
        """!
        @brief Number of items.
        @return int.
        """
        return len(self._items)

    def itemAt(self, index):
        """!
        @brief Item at an index.
        @param index Position.
        @return QLayoutItem or None.
        """
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        """!
        @brief Remove and return the item at an index.
        @param index Position.
        @return QLayoutItem or None.
        """
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        """!
        @brief The layout does not ask for extra space.
        @return Qt.Orientations (none).
        """
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        """!
        @brief The height depends on the width (the number of lines).
        @return bool.
        """
        return True

    def heightForWidth(self, width):
        """!
        @brief Height needed for a width.
        @param width Available width in pixels.
        @return int.
        """
        return self._lay_out(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        """!
        @brief Place the widgets.
        @param rect QRect given to the layout.
        """
        super().setGeometry(rect)
        self._lay_out(rect, False)

    def sizeHint(self):
        """!
        @brief Preferred size: every widget on one line.
        @return QSize.
        """
        w = sum(i.sizeHint().width() + self._space for i in self._items if not i.isEmpty())
        h = max((i.sizeHint().height() for i in self._items), default=0)
        m = self.contentsMargins()
        return QSize(w + m.left() + m.right(), h + m.top() + m.bottom())

    def minimumSize(self):
        """!
        @brief Smallest size: the widest single widget (the rest wraps).
        @return QSize.
        """
        w = max((i.minimumSize().width() for i in self._items), default=0)
        h = max((i.minimumSize().height() for i in self._items), default=0)
        m = self.contentsMargins()
        return QSize(w + m.left() + m.right(), h + m.top() + m.bottom())

    def line_count(self, width):
        """!
        @brief Number of lines the widgets take at a width (for tests).
        @param width Available width in pixels.
        @return int.
        """
        return len(self._lines(width))

    def _lines(self, width):
        """!
        @brief Split the items into lines for a width.
        @param width Available width in pixels.
        @return list of lists of QLayoutItem.
        """
        lines, cur, x = [], [], 0
        for it in self._items:
            if it.isEmpty():
                continue
            w = it.sizeHint().width()
            if cur and x + w > width:
                lines.append(cur)
                cur, x = [], 0
            cur.append(it)
            x += w + self._space
        if cur:
            lines.append(cur)
        return lines

    def _lay_out(self, rect, test_only):
        """!
        @brief Place the items line by line.
        @param rect Area in pixels.
        @param test_only True to only compute the height.
        @return int Height used.
        """
        m = self.contentsMargins()
        inner = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        y = inner.y()
        for line in self._lines(inner.width()):
            x = inner.x()
            lh = max(i.sizeHint().height() for i in line)
            for it in line:
                sz = it.sizeHint()
                if not test_only:
                    it.setGeometry(QRect(QPoint(x, y + (lh - sz.height()) // 2), sz))
                x += sz.width() + self._space
            y += lh + self._space
        return y - self._space - rect.y() + m.bottom() if y > inner.y() else m.top() + m.bottom()
