#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_toolbar_icons.py
@brief The Matplotlib toolbar of the results plots is painted with the text token of the theme, with enough contrast on the window.
"""

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from pcbthermal.gui import theme as th
from pcbthermal.gui.results_view import PlotTab


def _opaque_pixels(toolbar):
    """!
    @brief Colours of the opaque pixels of every toolbar icon.
    @param toolbar NavigationToolbar2QT.
    @return set of (r, g, b) tuples.
    """
    seen = set()
    for act in toolbar.actions():
        if act.isSeparator() or act.icon().isNull():
            continue
        img = act.icon().pixmap(32, 32).toImage()
        for y in range(img.height()):
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                if c.alpha() == 255:
                    seen.add((c.red(), c.green(), c.blue()))
    return seen


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_toolbar_icons_follow_theme(theme):
    """!
    @brief Icons are the text token and contrast >= 3.0 with the window colour; a switch recolours them.
    @param theme Theme name.
    """
    QApplication.instance() or QApplication([])
    tab = PlotTab("temperature", theme)
    token = QColor(th.colors(theme)["text"])
    px = _opaque_pixels(tab.toolbar)
    assert px and all(max(abs(a - b) for a, b in zip(c, (token.red(), token.green(), token.blue()))) <= 2 for c in px)
    assert th.contrast(token, QColor(th.colors(theme)["window"])) >= 3.0
    assert (255, 255, 255) not in px        # The old icons of the dark theme were pure white
    other = "light" if theme == "dark" else "dark"
    tab.set_theme(other)
    tok2 = QColor(th.colors(other)["text"])
    assert all(max(abs(a - b) for a, b in zip(c, (tok2.red(), tok2.green(), tok2.blue()))) <= 2 for c in _opaque_pixels(tab.toolbar))
