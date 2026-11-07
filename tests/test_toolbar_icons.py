#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_toolbar_icons.py
@brief The Matplotlib toolbar of the results plots is painted with the text token of the theme, with enough contrast on the window.
"""

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon
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


def _tab(theme):
    """!
    @brief A PlotTab for a theme.
    @param theme Theme name.
    @return PlotTab.
    """
    QApplication.instance() or QApplication([])
    return PlotTab("temperature", theme)


def test_every_standard_tool_item_has_a_painted_icon():
    """!
    @brief Each Matplotlib tool item has a drawing of ours, and the subclass really used it (fails clearly if `_icon` stops being called).
    """
    from pcbthermal.gui import toolbar_icons as ti
    tab = _tab("light")
    assert isinstance(tab.toolbar, ti.ThemedToolbar)
    names = [it[2] + ".png" for it in tab.toolbar.toolitems if it[0] is not None]
    assert names, "Matplotlib has no tool items?"
    missing = [n for n in names if n not in ti.DRAW]
    assert not missing, f"no own icon for {missing}"
    # Every named action must carry our multi-size icon (the stock one has one size), proving the private _icon hook is still called
    by_text = {a.text(): a for a in tab.toolbar.actions()}
    for text, _tip, image, _cb in tab.toolbar.toolitems:
        if text is None:
            continue
        sizes = by_text[text].icon().availableSizes()
        assert len({s.width() for s in sizes}) >= len(ti.SIZES), f"{text}: stock icon, Matplotlib no longer calls NavigationToolbar2QT._icon"


def test_unknown_icon_name_falls_back_to_the_stock_icon():
    """!
    @brief A name we do not draw gives None from `toolbar_icon`; the toolbar then uses Matplotlib's own icon.
    """
    from pcbthermal.gui import toolbar_icons as ti
    assert ti.toolbar_icon("no_such_tool.png", "dark") is None
    assert not _tab("dark").toolbar._icon("home.png").isNull()


def test_icons_are_crisp_at_ratio_1_and_2():
    """!
    @brief The icon has real pixmaps for 16, 20 and 24 px at both pixel ratios, painted (not empty) in the token colour.
    """
    from pcbthermal.gui import toolbar_icons as ti
    token = QColor(th.colors("dark")["text"])
    for name in ti.DRAW:
        icon = ti.toolbar_icon(name, "dark")
        for size in (16, 20, 24):
            for ratio in (1, 2):
                img = icon.pixmap(QSize(size, size), mode=QIcon.Normal, state=QIcon.Off).toImage() if ratio == 1 else \
                    icon.pixmap(QSize(size * 2, size * 2)).toImage()
                assert img.width() >= size
                px = [img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())]
                # A 1 px line centred between two pixel rows is anti-aliased: demand ink (alpha > 100), colour check on the solid pixels
                assert any(c.alpha() > 100 for c in px), f"{name} {size}px x{ratio}: nothing painted"
                cols = {(c.red(), c.green(), c.blue()) for c in px if c.alpha() == 255}
                assert all(max(abs(a - b) for a, b in zip(c, (token.red(), token.green(), token.blue()))) <= 2 for c in cols)
