#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file adaptive.py
@brief A splitter that puts its two panes one above the other in a narrow window (used by the Power profile and Stack-up pages).
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QSplitter


class AdaptiveSplitter(QSplitter):
    """!
    @brief A splitter that stacks its two panes one above the other when it is too narrow for them side by side (the Power profile and Stack-up pages were wider than the window at 1200 x 800).
    """

    NARROW_PX = 800     # Logical px: below this width the panes are stacked

    def resizeEvent(self, event):
        """!
        @brief Choose the orientation from the width, then lay out as usual.
        @param event QResizeEvent.
        """
        want = Qt.Vertical if event.size().width() < self.NARROW_PX else Qt.Horizontal
        if self.orientation() != want:
            self.setOrientation(want)
            self.updateGeometry()               # The minimum size changes with the orientation
        super().resizeEvent(event)

    def minimumSizeHint(self):
        """!
        @brief The minimum width is that of the wider pane only (the panes may be stacked), so that the page never forces a horizontal scroll bar.
        @return QSize.
        """
        w = max(self.widget(i).minimumSizeHint().width() for i in range(self.count()))
        heights = [self.widget(i).minimumSizeHint().height() for i in range(self.count())]
        # Stacked panes need the sum of their heights (the page scrolls vertically instead of squeezing the forms)
        h = sum(heights) + self.handleWidth() if self.orientation() == Qt.Vertical else max(heights)
        return QSize(w, h)
