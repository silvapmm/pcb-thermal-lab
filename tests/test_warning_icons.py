#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_warning_icons.py
@brief The solid severity badges of the warning rows: shape and colour from the theme tokens, no bullet, the badge centred on the lowercase letters of the first
       line (a measured offset of at most one logical pixel at device pixel ratio 1 and 2, both themes), the accessible names and the redraw on a theme change.
@details The alignment is measured on a rendered row, never calibrated: a title of letters without ascenders or descenders ("uxv") gives the x-height band, the
         badge ink gives its own centre. The ratio 2 case runs in a subprocess with QT_SCALE_FACTOR=2 (this file is its own script then).
"""

import json
import os
import subprocess
import sys

import pytest

FONT_POINTS = (11, 13, 16)


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window on the example board with its own settings file.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    from PySide6.QtCore import QSettings
    from pcbthermal.examples import example_board
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.main_window import MainWindow
    w = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1280, 800)
    w.show()
    w.activateWindow()
    qtbot.waitActive(w)
    w._load_problem(example_board(), "icons")
    return w


def _ink_rows(im, bg, x0, x1):
    """!
    @brief Rows (device px) that hold ink in the columns x0..x1-1.
    @param im QImage.
    @param bg QColor of the background.
    @param x0 First column.
    @param x1 One past the last column.
    @return List of int.
    """
    rows = []
    for y in range(im.height()):
        for x in range(x0, x1):
            q = im.pixelColor(x, y)
            if abs(q.red() - bg.red()) + abs(q.green() - bg.green()) + abs(q.blue() - bg.blue()) > 60:
                rows.append(y)
                break
    return rows


def measure(theme, severe, points):
    """!
    @brief Render one warning row and measure the badge against the lowercase letters of its title.
    @param theme "light" or "dark".
    @param severe True for the alert badge.
    @param points Font size in points.
    @return dict with dpr, offset (logical px, badge centre minus x-height centre), gap_arrow_badge (logical px), badge_height (logical px).
    """
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
    from pcbthermal import checks
    from pcbthermal.gui import theme as th, warning_box as wb
    app = QApplication.instance() or QApplication([])
    th.apply_theme(app, theme)
    font = app.font()
    font.setPointSize(points)
    app.setFont(font)
    w = checks.warn("uxv uxv uxv", "alert" if severe else "note")
    row = wb._TopicRow(w, False, False)
    row.title_label.setText("uxv uxv uxv")                    # No ascenders or descenders: the ink is the x-height band
    host = QWidget()
    lay = QVBoxLayout(host)
    lay.setContentsMargins(6, 6, 6, 6)
    lay.addWidget(row)
    host.setFixedWidth(330)
    host.show()
    app.processEvents()
    host.resize(330, lay.sizeHint().height())
    app.processEvents()
    im = host.grab().toImage()
    dpr = im.width() / host.width()
    bg = QColor(th.colors(theme)["window"])
    top = row.head.mapTo(host, row.head.rect().topLeft())
    y0, y1 = round(top.y() * dpr), round((top.y() + row.head.height()) * dpr)
    x0, x1 = round(top.x() * dpr), round((top.x() + row.head.width()) * dpr)
    sub = im.copy(x0, y0, x1 - x0, y1 - y0)
    cols = [x for x in range(sub.width()) if _ink_rows(sub, bg, x, x + 1)]
    groups, g = [], [cols[0]]
    for x in cols[1:]:
        if x - g[-1] > 3 * dpr:                              # Letters of one word are closer than this; the gaps next to the badge are 6 px
            groups.append(g)
            g = [x]
        else:
            g.append(x)
    groups.append(g)
    arrow, badge, text = groups[0], groups[1], (groups[2][0], groups[-1][-1])
    by, ty = _ink_rows(sub, bg, badge[0], badge[-1] + 1), _ink_rows(sub, bg, text[0], text[1] + 1)
    out = dict(dpr=float(dpr), offset=((by[0] + by[-1] + 1) / 2 - (ty[0] + ty[-1] + 1) / 2) / dpr,
               gap_arrow_badge=(badge[0] - arrow[-1] - 1) / dpr, badge_height=(by[-1] - by[0] + 1) / dpr)
    host.close()
    return out


def _all_cases():
    """!
    @brief Measure every combination of theme, severity and font size.
    @return dict keyed 'theme/severity/points'.
    """
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    from pcbthermal.gui import theme as th
    app = QApplication.instance() or QApplication([])
    font, theme = QFont(app.font()), th.current_name()
    try:
        return {f"{t}/{'alert' if s else 'note'}/{p}": measure(t, s, p) for t in ("light", "dark") for s in (True, False) for p in FONT_POINTS}
    finally:
        # The measurement sets the application font and theme: put them back, or the later tests of the battery run at 16 pt (review: the dock widths of
        # test_gui.py failed after this file)
        th.apply_theme(app, theme)
        app.setFont(font)


def _check(cases):
    """!
    @brief Assert the alignment rule on measured cases.
    @param cases dict from _all_cases.
    """
    for key, m in cases.items():
        assert abs(m["offset"]) <= 1.0, f"{key}: the badge centre is {m['offset']:.2f} px from the centre of the lowercase letters (at dpr {m['dpr']})"
        assert m["gap_arrow_badge"] >= 5.0 - 1e-9, f"{key}: only {m['gap_arrow_badge']:.2f} px between the arrow and the badge"
        assert m["badge_height"] >= 9, f"{key}: badge too small"


def test_the_badge_is_centred_on_the_lowercase_letters_at_dpr_1():
    """!
    @brief Offset at most 1 px, gap of at least 5 px, both themes, both severities, three font sizes (offscreen, device pixel ratio 1).
    """
    _check(_all_cases())


def test_the_badge_is_centred_at_dpr_2():
    """!
    @brief The same measurement in a subprocess with QT_SCALE_FACTOR=2 (a device pixel ratio of 2).
    """
    env = dict(os.environ, QT_SCALE_FACTOR="2", QT_QPA_PLATFORM="offscreen")
    done = subprocess.run([sys.executable, __file__], env=env, capture_output=True, text=True, timeout=300, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert done.returncode == 0, done.stderr[-800:]
    cases = json.loads(done.stdout.strip().splitlines()[-1])
    assert all(m["dpr"] == 2.0 for m in cases.values())
    _check(cases)


def test_no_bullet_no_warning_sign_in_the_text_and_tokens_colour_the_badges(win):
    """!
    @brief The title is plain text without the old symbols; the alert badge uses the `alert` token and the note badge the `muted` token, redrawn on a theme change.
    @param win MainWindow fixture.
    """
    from pcbthermal import checks
    from pcbthermal.gui import theme as th, warning_box as wb
    acc = win.solver_panel.checks
    a, n = checks.warn("U1: the whole footprint is outside the board", "alert", "heater", 0), checks.warn("U1: 9 vias under the footprint; x", "note", "heater", 0)
    acc.set_warnings([a, n])
    ra, rn = acc.rows
    for r in (ra, rn):
        assert r.title_label.textFormat().name == "PlainText" and "•" not in r.title_label.text() and "⚠" not in r.title_label.text()
    assert ra.glyphs.icon_token() == "alert" and rn.glyphs.icon_token() == "muted"
    for theme in ("light", "dark"):
        if win.theme_name != theme:
            win.toggle_theme()
        c = th.colors(theme)
        for r, token in ((ra, "alert"), (rn, "muted")):
            pm = wb.badge_pixmap(r.severe, r.glyphs.size_px, r.glyphs.devicePixelRatioF(), c[token])
            img = pm.toImage()
            seen = {img.pixelColor(x, y).name() for x in range(img.width()) for y in range(img.height()) if img.pixelColor(x, y).alpha() == 255}
            assert seen == {c[token]}, f"{theme}/{token}: {seen}"
        assert ra.glyphs.icon_token() == "alert"


def test_the_severity_is_in_the_accessible_name_and_the_tooltip(win):
    """!
    @brief The badge is never the only carrier of the severity: 'Warning: <title>' / 'Note: <title>' as the accessible name, the word in the tooltip.
    @param win MainWindow fixture.
    """
    from pcbthermal import checks
    acc = win.solver_panel.checks
    acc.set_warnings([checks.warn("Heater U1: outside the board; more", "alert", "heater", 0), checks.warn("U1: 9 vias under the footprint; x", "note", "heater", 0)])
    ra, rn = acc.rows
    assert ra.head.accessibleName() == "Warning: Heater U1: outside the board" and rn.head.accessibleName() == "Note: U1: 9 vias under the footprint"
    assert ra.glyphs.accessibleName() == "Warning" and rn.glyphs.accessibleName() == "Note"
    assert ra.head.toolTip().startswith("Warning") and rn.head.toolTip().startswith("Note")
    ra.set_open(True)
    assert ra.head.accessibleDescription() == "open" and ra.glyphs.open


def test_the_summary_and_the_dock_share_one_component():
    """!
    @brief The Results summary builds the same accordion class as the Simulation dock, so the icons change in both together.
    """
    from pcbthermal.gui import panels, results_view, warning_box
    assert panels.WarningAccordion is warning_box.WarningAccordion and results_view.WarningAccordion is warning_box.WarningAccordion


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(json.dumps(_all_cases()))
