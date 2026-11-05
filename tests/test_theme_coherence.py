#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_theme_coherence.py
@brief Every window of the application follows the same theme tokens: no colour literals in the GUI code outside theme.py, the help pages,
       the plots, the warning list and the memory verdicts change with a live theme switch, and the status colours read in both themes.
"""

import re
import tokenize
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from pcbthermal.examples import example_board
from pcbthermal.gui import theme as th
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

GUI = Path(th.__file__).parent

# A colour written in the code of a widget is a colour that does not follow a theme switch. Allowed: nothing at the moment (every colour
# of the GUI is a token of theme.THEMES); an entry would be (file name, literal) with a comment that gives the reason.
ALLOWED = []

LITERAL = re.compile(r"""#[0-9a-fA-F]{6,8}\b|#[0-9a-fA-F]{3}\b|QColor\(\s*["'][a-z]+["']|QColor\(\s*\d|QColor\.fromRgb|rgba?\("""
                     r"""|Qt\.(red|green|blue|white|black|gray|darkGray|lightGray|yellow|cyan|magenta)\b"""
                     r"""|["'](white|black|red|green|blue|gray|grey|orange|yellow)["']""")


def _code_lines(path):
    """!
    @brief The code of a Python file line by line with the comments removed (a '#' inside a string, as in "#ffffff", is kept).
    @param path Path of the file.
    @return dict line number -> code text of that line without its comment.
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = dict(enumerate(text.splitlines(), 1))
    with open(path, encoding="utf-8") as fh:
        for tok in tokenize.generate_tokens(fh.readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                lines[row] = lines[row][:col]               # cut at the real comment, found by the tokenizer
    return lines


def _literals(folder, skip=("theme.py",)):
    """!
    @brief Colour literals written in the code of the GUI files of a folder.
    @param folder Folder of the GUI modules.
    @param skip File names left out (the theme table).
    @return list of "file:line: literal".
    """
    bad = []
    for f in sorted(Path(folder).glob("*.py")):
        if f.name in skip:
            continue
        for n, code in sorted(_code_lines(f).items()):
            for m in LITERAL.finditer(code):
                if (f.name, m.group(0)) not in ALLOWED:
                    bad.append(f"{f.name}:{n}: {m.group(0)}")
    return bad


def _ratio(a, b):
    """!
    @brief WCAG contrast ratio of two colour strings.
    @param a Colour string.
    @param b Colour string.
    @return float ratio.
    """
    return th.contrast(QColor(a), QColor(b))


def test_no_colour_literals_in_the_gui_outside_the_theme_table():
    # Comments may name a colour; the code may not
    bad = _literals(GUI)
    assert not bad, "colour literals outside theme.py (read them from the theme table):\n" + "\n".join(bad)


def test_the_literal_check_finds_hex_strings_and_skips_comments(tmp_path):
    # The first version of the check cut each line at its first '#', so every "#rrggbb" string slipped through
    (tmp_path / "w.py").write_text('a = QColor("#4c8dff")\nb.setStyleSheet("color: #e5534b;")\nc = QColor("white")\n'
                                   'd = 1   # white text, #ffffff in a comment\n', encoding="utf-8")
    bad = _literals(tmp_path)
    assert [b.split(":")[1] for b in bad] == ["1", "2", "3"], bad


@pytest.mark.parametrize("name", ["dark", "light"])
def test_status_and_document_colours_read_in_both_themes(name):
    c = th.colors(name)
    # The status tones were chosen by hand and kept (the maintainer likes the look): the light "slow" orange is 3.85:1, so these are held to 3.5:1
    for key in ("ok", "warn", "bad", "error"):
        assert _ratio(c[key], c["window"]) >= 3.5, (name, key, "on the window")
        assert _ratio(c[key], c["base"]) >= 3.5, (name, key, "on the base")
    # The HTML pages have their own tokens (the dark page is a softer grey than the window)
    for key in ("doc_note", "doc_tip", "doc_th", "doc_bg"):
        assert _ratio(c["doc_text"], c[key]) >= 4.5, (name, key)
        assert _ratio(c["doc_link"], c[key]) >= 4.5, (name, key, "link")
    assert _ratio(c["doc_head"], c["doc_bg"]) >= 4.5
    assert _ratio(c["link"], c["base"]) >= 4.5 and _ratio(c["text"], c["base"]) >= 4.5
    # Borders and code backgrounds are visible against the page
    assert _ratio(c["doc_border"], c["doc_bg"]) >= 1.3 and _ratio(c["doc_th"], c["doc_bg"]) >= 1.05
    if name == "dark":
        assert QColor(c["doc_bg"]).lightness() > QColor(c["base"]).lightness() + 15


def test_readable_on_picks_a_label_colour_for_any_fill():
    for fill in ("#4a6f5a", "#6c8f9d", "#9aa7b4", "#d08a3c", "#ffffff", "#000000"):
        pick = th.readable_on(QColor(fill))
        assert th.contrast(pick, QColor(fill)) >= 3.0, fill
    # White stays wherever it reads (the look of the stack-up bars), the dark text only where white is below 3:1
    for fill, want in (("#c77d2e", "#ffffff"), ("#2f7d5b", "#ffffff"), ("#6c8f9d", "#ffffff"), ("#9aa7b4", "#101317"), ("#d08a3c", "#101317")):
        assert th.readable_on(QColor(fill)).name() == want, fill


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window with the example board and one run, in the light theme.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder for the settings file.
    @return MainWindow.
    """
    from pcbthermal import api
    st = QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat)
    st.setValue("theme", "light")
    w = MainWindow(Document(), st)
    qtbot.addWidget(w)
    w.resize(1400, 850)
    w.show()
    w.doc.open_problem(example_board(), "example")
    w._after_load()
    w._on_done(api.simulate(w.doc.problem, w.doc.options))
    return w


def _canvas_fig_colours(win):
    """!
    @brief Face colours of every matplotlib figure of the main window.
    @param win MainWindow.
    @return list of (name, QColor).
    """
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    out = []
    for cv in win.findChildren(FigureCanvasQTAgg):
        out.append((cv.figure, QColor.fromRgbF(*cv.figure.get_facecolor())))
    return out


def test_plots_follow_a_live_theme_switch(win):
    base = {n: QColor(th.colors(n)["base"]) for n in ("dark", "light")}
    figs = _canvas_fig_colours(win)
    assert len(figs) >= 5
    assert all(c.name() == base["light"].name() for _, c in figs)
    win.toggle_theme()
    assert win.theme_name == "dark"
    after = _canvas_fig_colours(win)
    assert all(c.name() == base["dark"].name() for _, c in after), [c.name() for _, c in after]
    # The empty-state message of the power profile results is drawn in the theme's text colour, not the default black
    win.results.time_sim.redraw()
    texts = [t for ax in win.results.time_sim.fig.axes for t in ax.texts]
    assert texts and QColor(texts[0].get_color()).name() == QColor(th.colors("dark")["text"]).name()


def test_help_pages_follow_a_live_theme_switch(win):
    win.show_guide()
    guide = win._guide
    from pcbthermal.gui.calculator import CalculatorHelp
    ch = CalculatorHelp(win)
    ch.show()

    def page_colours(view):
        html = view.document().toHtml()
        return re.search(r"background-color:(#[0-9a-fA-F]{6})", html), view._themed

    for view in (guide.view, ch.view):
        assert view._themed[1] == "light"
    win.toggle_theme()
    for view in (guide.view, ch.view):
        assert view._themed[1] == "dark"
        assert view.document().defaultStyleSheet() is not None
    # The text colour of the document is the theme's text and the page is not white any more
    css = th.document_css("dark")
    assert th.colors("dark")["doc_bg"] in css and "#ffffff" not in css
    img = guide.view.viewport().grab().toImage()
    px = QColor(img.pixel(img.width() // 2, 3))
    assert px.lightness() < 100, px.name()
    win.toggle_theme()
    assert guide.view._themed[1] == "light" and ch.view._themed[1] == "light"


def test_the_warning_list_and_the_memory_verdicts_take_the_new_colours(win):
    from pcbthermal.gui.panels import WarningList

    class Warn(str):
        kind, index = "heater", 0

    lst = win.findChildren(WarningList)[0]
    lst.set_warnings([Warn("one"), Warn("two")])

    def anchor_colour():
        # Colour of the first link of the list, as Qt stored it when the HTML was read
        block = lst.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                if it.fragment().charFormat().isAnchor():
                    return it.fragment().charFormat().foreground().color().name()
                it += 1
            block = block.next()
        return None

    assert anchor_colour() == QColor(th.colors("light")["alert"]).name()      # Entries take the alert token, not the link colour
    verdict_light = win.solver_panel.cells_label.text()
    win.toggle_theme()
    # The text of the label holds the theme's tones: the dark ones differ from the light ones
    verdict_dark = win.solver_panel.cells_label.text()
    assert verdict_light != verdict_dark
    assert th.colors("dark")["ok"] in verdict_dark or th.colors("dark")["warn"] in verdict_dark or th.colors("dark")["bad"] in verdict_dark
    link = QApplication.palette().link().color().name()
    assert link == QColor(th.colors("dark")["link"]).name()
    assert anchor_colour() == QColor(th.colors("dark")["alert"]).name()                     # the list was rebuilt: a link keeps the colour it was read with otherwise


def test_every_window_object_changes_its_palette_on_a_toggle(win):
    from pcbthermal.gui.stackup import StackupPage
    old = {n: w.palette().window().color().name() for n, w in (("win", win), ("stack", win.stackup_page))}
    win.toggle_theme()
    for n, w in (("win", win), ("stack", win.stackup_page)):
        assert w.palette().window().color().name() != old[n], n
    assert isinstance(win.stackup_page, StackupPage)
    assert win.canvas.theme == "dark"


def test_the_light_theme_keeps_its_look():
    # The maintainer likes the light theme as it was: the fixes are for the dark theme and for real defects only. The links stay Qt's blue
    # (8.6:1 on white) and the help pages keep the colours of their own light style sheet
    c = th.colors("light")
    assert QColor(c["link"]).name() == "#0000ff"
    page = (Path(th.__file__).parents[1] / "help" / "index.html").read_text(encoding="utf-8")
    sheet = re.search(r"<style>(.*?)@media", page, re.S).group(1)
    css = th.document_css("light")
    for rule in ("body", "h1", "h2", "th, td", "th", "code, kbd", ".note", ".tip"):
        own = re.search(r"\n\s*" + re.escape(rule) + r" \{([^}]*)\}", sheet).group(1).split()
        new = re.search(r"\n\s*" + re.escape(rule) + r" \{([^}]*)\}", css).group(1).split()
        assert own == new, (rule, own, new)


def test_the_keyboard_focus_ring_of_an_indicator_is_kept():
    # The contrast outline must not paint over Fusion's accent ring of a check box or radio button reached with Tab
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QStyle, QStyleFactory, QStyleOptionButton
    app = QApplication.instance() or QApplication([])
    for name in ("dark", "light"):
        th.apply_theme(app, name)
        for element in (QStyle.PE_IndicatorCheckBox, QStyle.PE_IndicatorRadioButton):
            pix = []
            for style in (QStyleFactory.create("Fusion"), app.style()):
                o = QStyleOptionButton()
                o.rect, o.palette = QRect(2, 2, 14, 14), app.palette()
                o.state = QStyle.State_Enabled | QStyle.State_Off | QStyle.State_HasFocus | QStyle.State_KeyboardFocusChange
                img = QImage(18, 18, QImage.Format_ARGB32)
                img.fill(app.palette().window().color())
                p = QPainter(img)
                style.drawPrimitive(element, o, p, None)
                p.end()
                pix.append([img.pixel(x, y) for x in range(18) for y in range(18)])
            assert pix[0] == pix[1], (name, element)
