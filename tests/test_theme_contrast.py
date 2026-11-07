#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_theme_contrast.py
@brief WCAG contrast of the key colour pairs of the light and dark themes: indicators of radio buttons and check boxes, text, disabled text, links.
"""

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QCheckBox, QRadioButton

from pcbthermal.gui import theme


def _luminance(c):
    """!
    @brief Relative luminance of a colour (WCAG 2.x).
    @param c QColor.
    @return float luminance, 0 (black) to 1 (white).
    """
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c.red()) + 0.7152 * lin(c.green()) + 0.0722 * lin(c.blue())


def _ratio(a, b):
    """!
    @brief WCAG contrast ratio of two colours.
    @param a QColor.
    @param b QColor.
    @return float ratio, 1 to 21.
    """
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.fixture(params=["dark", "light"])
def themed(request):
    """!
    @brief Apply one theme to the application and give its palette.
    @param request pytest request with the theme name.
    @return tuple (theme name, QPalette).
    """
    app = QApplication.instance() or QApplication([])
    theme.apply_theme(app, request.param)
    return request.param, app.palette()


@pytest.mark.parametrize("kind", [QRadioButton, QCheckBox])
def test_the_unchecked_indicator_stands_out_from_the_window(themed, kind):
    # Rendered, because the outline comes from the style and not from a palette role
    _, pal = themed
    w = kind("x")
    w.resize(60, 24)
    w.show()
    QApplication.processEvents()
    img = w.grab().toImage()
    bg = QColor(img.pixel(img.width() - 2, 2))
    best = max(_ratio(QColor(img.pixel(x, y)), bg) for x in range(0, 20) for y in range(img.height()))
    assert best >= 3.0, f"{kind.__name__} indicator reaches only {best:.2f}:1 against the window"


@pytest.mark.parametrize("fg, bg, group, minimum", [
    (QPalette.WindowText, QPalette.Window, QPalette.Normal, 4.5),
    (QPalette.Text, QPalette.Base, QPalette.Normal, 4.5),
    (QPalette.ButtonText, QPalette.Button, QPalette.Normal, 4.5),
    # The muted grey of the light theme (#6b7280) is the maintainer's choice: 4.3:1 on the window, so the dimmed texts are held to 4:1
    (QPalette.PlaceholderText, QPalette.Base, QPalette.Normal, 4.0),
    (QPalette.WindowText, QPalette.Window, QPalette.Disabled, 4.0),
    (QPalette.Text, QPalette.Base, QPalette.Disabled, 4.0),
    (QPalette.ButtonText, QPalette.Button, QPalette.Disabled, 3.9),
    (QPalette.Link, QPalette.Window, QPalette.Normal, 4.5),
    (QPalette.Link, QPalette.Base, QPalette.Normal, 4.5),
    (QPalette.LinkVisited, QPalette.Base, QPalette.Normal, 4.5),
    (QPalette.HighlightedText, QPalette.Highlight, QPalette.Normal, 3.0),     # white on the dark accent: 3.2:1, kept as designed
])
def test_text_pairs_of_the_palette(themed, fg, bg, group, minimum):
    _, pal = themed
    r = _ratio(pal.color(group, fg), pal.color(group, bg))
    assert r >= minimum, f"{fg} on {bg} ({group}) is {r:.2f}:1"


def test_text_of_the_primary_button_and_the_muted_text(themed):
    name, _ = themed
    c = theme.colors(name)
    # Deliberate design choices of the maintainer (he likes the look): white text on the dark theme's accent is 3.2:1 and the light muted
    # grey is about 4.3:1, so these pairs are held to 3:1 and 4:1 and not to the 4.5:1 of WCAG AA
    assert _ratio(QColor(c["on_accent"]), QColor(c["accent"])) >= 3.0
    assert _ratio(QColor(c["muted"]), QColor(c["window"])) >= 4.0
    assert _ratio(QColor(c["muted"]), QColor(c["alt"])) >= 3.9
    assert _ratio(QColor(c["muted"]), QColor(c["border"])) >= 3.0      # disabled primary button
    assert _ratio(QColor(c["indicator"]), QColor(c["window"])) >= 3.0


@pytest.mark.parametrize("role", [QPalette.WindowText, QPalette.Text, QPalette.ButtonText])
def test_disabled_text_is_dimmed(themed, role):
    # A disabled label (a field the chosen point does not use, the empty Properties note) must look disabled: Fusion's default kept the
    # disabled window text as dark as the enabled one, so the contrast rows above passed while the dimming was missing
    _, pal = themed
    normal, disabled = pal.color(QPalette.Normal, role), pal.color(QPalette.Disabled, role)
    assert _ratio(disabled, pal.color(QPalette.Normal, QPalette.Window)) < _ratio(normal, pal.color(QPalette.Normal, QPalette.Window)) - 1.0, \
        f"disabled {role} is not dimmed ({disabled.name()} against {normal.name()})"


@pytest.mark.parametrize("name", ["dark", "light"])
def test_results_map_copper_laminate_and_contour_tokens_are_distinct(name):
    """!
    @brief The grey copper, the laminate under it and the contour lines of the Results maps can be told apart in both themes.
    @param name Theme name.
    """
    c = theme.colors(name)
    assert _ratio(QColor(c["map_copper"]), QColor(c["map_laminate"])) >= 3.0
    assert _ratio(QColor(c["map_contour"]), QColor(c["map_laminate"])) >= 4.5
