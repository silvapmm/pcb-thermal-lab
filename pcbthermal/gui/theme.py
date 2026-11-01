#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file theme.py
@brief Light and dark themes, canvas colours and painted icons for the GUI.
"""

import shiboken6
from PySide6.QtCore import QEvent, QLocale, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QKeyEvent, QKeySequence, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QLineEdit, QProxyStyle, QStyle, QWidget

THEMES = {
    "dark": {
        "window": "#1e2127", "base": "#15181d", "alt": "#23272e", "text": "#e6e8eb", "muted": "#8b949e", "hint": "#9aa3ad",
        "accent": "#4c8dff", "accent_hover": "#4c8dff", "accent_pressed": "#4c8dff", "on_accent": "#ffffff", "link": "#6cb0ff",
        # Notes and warnings: the text and the symbol of an entry take the same token (the Run panel list was link blue with a text-coloured symbol)
        "alert": "#6cb0ff", "alert_note": "#e6e8eb", "link_visited": "#b79cf0", "indicator": "#8b949e", "border": "#343a43", "canvas": "#101317", "board": "#17402f",
        "grid_minor": "#ffffff12", "grid_major": "#ffffff2a", "solver_grid": "#4cc9f040",
        "copper": "#d08a3c", "heater": "#ff5b4f", "heatsink": "#3aa0ff", "via": "#f2c14e",
        "ok": "#66bb6a", "warn": "#ffb74d", "bad": "#ef5350", "error": "#ef5350",
        "selection": "#ffffff", "on_element": "#ffffff", "run": "#34d399",
        "diel_low": "#4a6f5a", "diel_mid": "#6c8f9d", "diel_high": "#9aa7b4",
        "doc_note": "#4d4730", "doc_note_edge": "#e0a800", "doc_tip": "#31465e", "doc_th": "#404750", "doc_border": "#566069",
        # The HTML pages are a softer grey than the near-black window: a medium-dark page, light-grey text, brighter headings
        "doc_bg": "#353b43", "doc_text": "#d8dce1", "doc_head": "#f0f2f4", "doc_link": "#9ccbff",
    },
    "light": {
        "window": "#f3f4f6", "base": "#ffffff", "alt": "#eef0f3", "text": "#1f2328", "muted": "#6b7280", "hint": "#5f6570",
        "accent": "#2563eb", "accent_hover": "#2563eb", "accent_pressed": "#2563eb", "on_accent": "#ffffff", "link": "#0000ff",
        "alert": "#0000ff", "alert_note": "#1f2328", "link_visited": "#6d28d9", "indicator": "#6b7280", "border": "#d0d5dd", "canvas": "#dfe3e8", "board": "#2f7d5b",
        "grid_minor": "#00000014", "grid_major": "#00000030", "solver_grid": "#0077aa50",
        "copper": "#c77d2e", "heater": "#e0392d", "heatsink": "#1d78d8", "via": "#c9971c",
        "ok": "#2e7d32", "warn": "#b26a00", "bad": "#c62828", "error": "#c62828",
        "selection": "#ffffff", "on_element": "#ffffff", "run": "#34d399",
        "diel_low": "#4a6f5a", "diel_mid": "#6c8f9d", "diel_high": "#9aa7b4",
        "doc_note": "#fff7e0", "doc_note_edge": "#e0a800", "doc_tip": "#e8f3ff", "doc_th": "#eef0f3", "doc_border": "#c8ccd2",
        "doc_bg": "#ffffff", "doc_text": "#1f2328", "doc_head": "#1f2328", "doc_link": "#0000ff",
    },
}


def fix_number_locale():
    """!
    @brief Make every number of the application use the decimal point and no thousands separator, whatever the system language.

    @details Qt spin boxes, line edits and number-to-text conversions follow QLocale.default(); the application sets it
    once to US English without the group separator, so "0.45" is shown on a Portuguese or German system too (the
    international way of writing numbers in engineering). It must run before the widgets are created.
    @note In the US English locale a comma is the thousands separator, so "0,45" typed in a spin box (the habit of a Portuguese
          or German user, and the decimal key of their numeric keypad) was read as 45, a silent factor of 100. The group separator
          is therefore rejected, and a comma typed in a number field is turned into the decimal point by an application event filter.
    """
    global _COMMA_FILTER
    loc = QLocale(QLocale.English, QLocale.UnitedStates)
    loc.setNumberOptions(QLocale.OmitGroupSeparator | QLocale.RejectGroupSeparator)
    QLocale.setDefault(loc)
    app = QApplication.instance()
    if app is not None and _COMMA_FILTER is None:
        _COMMA_FILTER = _CommaToPoint(app)
        app.installEventFilter(_COMMA_FILTER)


class _CommaToPoint(QObject):
    """!
    @brief Application event filter: a comma typed in a number field (a spin box) is typed as the decimal point.
    """

    def eventFilter(self, obj, event):
        """!
        @brief Replace a comma key press, or the commas of a pasted text, in a spin box (or the line edit inside it) by a point.
        @param obj Object that receives the event.
        @param event The event.
        @return True when the event was replaced (and so consumed), otherwise False.
        """
        if event.type() == QEvent.ContextMenu:
            return self._context_menu(obj, event)
        if event.type() != QEvent.KeyPress:
            return False
        spin = obj if isinstance(obj, QAbstractSpinBox) else (obj.parentWidget() if isinstance(obj, QWidget) else None)
        if not isinstance(spin, QAbstractSpinBox):
            return False
        if event.text() == ",":
            QApplication.sendEvent(obj, QKeyEvent(QEvent.KeyPress, Qt.Key_Period, event.modifiers(), "."))
            return True
        if event.matches(QKeySequence.Paste) and "," in QApplication.clipboard().text():
            # A pasted "0,45" would be read as 45 too: paste it with the point
            spin.lineEdit().insert(QApplication.clipboard().text().replace(",", "."))
            return True
        return False


    def _context_menu(self, obj, event):
        """!
        @brief Show the menu of a spin box (Qt's own: Undo to Select All, Step up, Step down) with a Paste that turns commas into points.
        @details Qt's QAbstractSpinBox builds this menu inside its C++ contextMenuEvent, where its Paste cannot be reached; the
                 same menu is rebuilt here so that Paste can be replaced. The event comes to the line edit (right click on the
                 text, menu key) or to the spin box itself (right click on the arrows).
        @param obj Object that receives the event.
        @param event The QContextMenuEvent.
        @return True when the menu was shown here, False for any other widget.
        """
        if isinstance(obj, QAbstractSpinBox):
            spin = obj
        elif isinstance(obj, QLineEdit) and isinstance(obj.parentWidget(), QAbstractSpinBox) and obj is obj.parentWidget().lineEdit():
            spin = obj.parentWidget()
        else:
            return False
        edit = spin.lineEdit()
        menu = edit.createStandardContextMenu()
        for a in menu.actions():
            # Found by object name, not by text, so that a translated Qt keeps the conversion
            if a.objectName() == "edit-paste":
                a.triggered.disconnect()                       # The default slot would paste "0,45" as typed, which the spin box reads as 45
                a.triggered.connect(lambda: edit.insert(QApplication.clipboard().text().replace(",", ".")))
            elif a.objectName() == "select-all":
                a.triggered.disconnect()                       # As in Qt's spin box menu: select the number, not the prefix or the suffix
                a.triggered.connect(spin.selectAll)
        menu.addSeparator()
        enabled = spin.stepEnabled()
        up = menu.addAction("Step up")
        up.setEnabled(bool(enabled & QAbstractSpinBox.StepUpEnabled))
        up.triggered.connect(lambda: spin.stepBy(1))
        down = menu.addAction("Step down")
        down.setEnabled(bool(enabled & QAbstractSpinBox.StepDownEnabled))
        down.triggered.connect(lambda: spin.stepBy(-1))
        menu.exec(event.globalPos())
        shiboken6.delete(menu)                                 # As Qt's own menu: deleted now (a deleteLater on top of the Python owner crashed)
        event.accept()
        return True


_COMMA_FILTER = None    # The single event filter installed by fix_number_locale


def colors(name):
    """!
    @brief Colour table of a theme.
    @param name "dark" or "light".
    @return Dict of colour strings.
    """
    return THEMES.get(name, THEMES["dark"])


def contrast(a, b):
    """!
    @brief WCAG contrast ratio of two colours.
    @param a QColor.
    @param b QColor.
    @return float ratio, 1 to 21.
    """
    def lum(q):
        def lin(v):
            v /= 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * lin(q.red()) + 0.7152 * lin(q.green()) + 0.0722 * lin(q.blue())
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def readable_on(background, light="#ffffff", dark="#101317", minimum=3.0):
    """!
    @brief The text colour for a label drawn on a fill: the light colour as before, the darker one only where the light one does not read.
    @details The labels of the stack-up bars were always white; the maintainer likes that look, so white is kept wherever it reaches
             the minimum (3:1, the WCAG level for the short bold labels) and only the fills where it falls below (the high-k grey,
             2.4:1, and the dark theme's copper, 2.8:1) get the colour with the higher contrast.
    @param background QColor of the fill.
    @param light Colour string preferred (the look of the program).
    @param dark Colour string used where the preferred one is below the minimum.
    @param minimum Contrast ratio (1 to 21) the preferred colour must reach.
    @return QColor of the label.
    """
    a, b = QColor(light), QColor(dark)
    if contrast(a, background) >= minimum:
        return a
    return a if contrast(a, background) >= contrast(b, background) else b


def qcolor(spec, alpha=None):
    """!
    @brief Build a QColor from a #rrggbb or #rrggbbaa string.
    @param spec Colour string.
    @param alpha Optional alpha (0..255) that overrides the string alpha.
    @return QColor.
    """
    c = QColor(spec) if len(spec) != 9 else QColor(f"#{spec[7:9]}{spec[1:7]}")   # Qt reads #aarrggbb
    if alpha is not None:
        c.setAlpha(alpha)
    return c


class _ThemeStyle(QProxyStyle):
    """!
    @brief Fusion style that outlines the indicators of radio buttons and check boxes with a visible colour.
    @details Fusion derives the outline of an indicator from the window colour (darker), which is invisible on a dark window
             (1.12:1) and weak on a light one (1.7 to 2.1:1), so an unchecked radio group looked as if it had no choices.
             The outline is drawn again on top of Fusion's own drawing, so the check mark and the dot are kept.
    """

    def __init__(self, outline):
        """!
        @brief Build the style.
        @param outline Outline colour string of the indicators (the theme's "indicator" entry).
        """
        super().__init__("Fusion")
        self._outline = QColor(outline)

    def drawPrimitive(self, element, option, painter, widget=None):
        """!
        @brief Draw a primitive; for a radio button or check box indicator add the contrast outline.
        @param element QStyle primitive element.
        @param option QStyleOption of the element.
        @param painter QPainter.
        @param widget The widget being drawn, or None.
        """
        super().drawPrimitive(element, option, painter, widget)
        if element not in (QStyle.PE_IndicatorRadioButton, QStyle.PE_IndicatorCheckBox):
            return
        if (option.state & QStyle.State_HasFocus) and (option.state & QStyle.State_KeyboardFocusChange):
            return                                              # Fusion's accent focus ring (keyboard focus) reads already; the grey would hide it
        col = QColor(self._outline)
        if not (option.state & QStyle.State_Enabled):
            col.setAlpha(110)                                   # a disabled control stays visible but quieter
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(col, 1.0))
        painter.setBrush(Qt.NoBrush)
        r = QRectF(option.rect).adjusted(0.5, 0.5, -0.5, -0.5)
        if element == QStyle.PE_IndicatorRadioButton:
            painter.drawEllipse(r)
        else:
            painter.drawRoundedRect(r, 2, 2)
        painter.restore()


_STYLE = None           # Keeps the Python side of the current style alive
_CURRENT = "dark"       # Name of the theme last applied: windows made later (dialogs, help pages) read it


def current_name():
    """!
    @brief Name of the theme applied last (the one the whole application shows now).
    @return "dark" or "light".
    """
    return _CURRENT


def document_css(name):
    """!
    @brief Style sheet of the HTML documents shown inside the program (user guide, calculator help), from the colour table.
    @details The HTML files carry their own sheet for a web browser (with a prefers-color-scheme block that Qt's rich text
             ignores, so the pages stayed white on the dark theme); inside the program that sheet is replaced by this one,
             which uses only the constructs Qt supports and the same tokens as every other window.
    @param name "dark" or "light".
    @return str CSS text.
    """
    c = colors(name)
    return f"""
  body {{ font-family: "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.5; max-width: 62em; margin: 0 auto; padding: 1em 1.5em 4em; color: {c['doc_text']}; background: {c['doc_bg']}; }}
  h1, h2, h3 {{ color: {c['doc_head']}; }}
  h1 {{ border-bottom: 2px solid {c['accent']}; padding-bottom: .2em; }}
  h2 {{ margin-top: 2em; border-bottom: 1px solid {c['border']}; padding-bottom: .15em; }}
  h3 {{ margin-top: 1.4em; }}
  table {{ border-collapse: collapse; margin: .8em 0; }}
  th, td {{ border: 1px solid {c['doc_border']}; padding: .3em .6em; text-align: left; vertical-align: top; }}
  th {{ background: {c['doc_th']}; }}
  code, kbd {{ background: {c['doc_th']}; padding: 0 .3em; border-radius: 3px; font-family: Consolas, Menlo, monospace; }}
  .note {{ background: {c['doc_note']}; border-left: 4px solid {c['doc_note_edge']}; padding: .4em .8em; margin: .8em 0; }}
  .tip {{ background: {c['doc_tip']}; border-left: 4px solid {c['accent']}; padding: .4em .8em; margin: .8em 0; }}
  nav li {{ margin: .1em 0; }}
  a {{ color: {c['doc_link']}; }}
"""


def apply_theme(app, name):
    """!
    @brief Apply the Fusion style, a palette and a style sheet to the whole application.
    @param app QApplication.
    @param name "dark" or "light".
    """
    c = colors(name)
    global _STYLE, _CURRENT
    _CURRENT = name if name in THEMES else "dark"
    style = _ThemeStyle(c["indicator"])
    app.setStyle(style)                     # The application owns the new style and deletes the old one
    _STYLE = style                          # Only now drop the Python reference to the old style, which the application no longer uses
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["window"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["base"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["alt"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["alt"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["base"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.Highlight, QColor(c["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor(c["on_accent"]))
    pal.setColor(QPalette.Link, QColor(c["link"]))
    pal.setColor(QPalette.LinkVisited, QColor(c["link_visited"]))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(c["muted"]))
    pal.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(c["muted"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["muted"]))
    app.setPalette(pal)
    q = QColor(c["accent"])
    accent_soft = f"rgba({q.red()}, {q.green()}, {q.blue()}, 60)"       # QSS has no #rrggbbaa form
    app.setStyleSheet(f"""
        QToolBar {{ spacing: 4px; padding: 4px; border: none; border-bottom: 1px solid {c['border']}; }}
        QToolButton {{ border: 1px solid transparent; border-radius: 6px; padding: 5px; }}
        QToolButton:hover {{ background: {c['alt']}; border-color: {c['border']}; }}
        QToolButton:checked {{ background: {accent_soft}; border-color: {c['accent']}; }}
        QDockWidget::title {{ background: {c['alt']}; padding: 6px 8px; font-weight: 600; }}
        QGroupBox {{ border: 1px solid {c['border']}; border-radius: 6px; margin-top: 10px; padding-top: 8px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {c['muted']}; }}
        QTabBar::tab {{ padding: 7px 14px; border: none; border-bottom: 2px solid transparent; color: {c['muted']}; }}
        QTabBar::tab:selected {{ color: {c['text']}; border-bottom-color: {c['accent']}; }}
        QListWidget#sections {{ border: none; border-right: 1px solid {c['border']}; background: transparent; outline: 0; }}
        QListWidget#sections::item {{ padding: 8px 12px; border-left: 2px solid transparent; color: {c['muted']}; }}
        QListWidget#sections::item:hover {{ background: {c['alt']}; }}
        QListWidget#sections::item:selected {{ background: {accent_soft}; border-left-color: {c['accent']}; color: {c['text']}; }}
        QTabWidget::pane {{ border: none; border-top: 1px solid {c['border']}; }}
        QPushButton {{ border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 14px; background: {c['alt']}; }}
        QPushButton:hover {{ border-color: {c['accent']}; }}
        QPushButton#primary {{ background: {c['accent']}; border-color: {c['accent']}; color: {c['on_accent']}; font-weight: 600; }}
        QPushButton#primary:hover {{ background: {c['accent_hover']}; }}
        QPushButton#primary:pressed {{ background: {c['accent_pressed']}; }}
        QPushButton#primary:disabled {{ background: {c['border']}; color: {c['muted']}; }}
        QStatusBar {{ border-top: 1px solid {c['border']}; }}
        QHeaderView::section {{ background: {c['alt']}; border: none; padding: 4px 8px; }}
        QTableWidget, QTreeWidget {{ border: 1px solid {c['border']}; gridline-color: {c['border']}; }}
        QProgressBar {{ border: 1px solid {c['border']}; border-radius: 4px; text-align: center; height: 14px; }}
        QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
        QLabel[error="true"] {{ color: {c['error']}; }}
        QLabel[hint="true"] {{ font-size: 11px; color: {c['hint']}; }}
    """)


def hint(label):
    """!
    @brief Show a label as a small explanatory note in the theme's hint colour.

    @param label QLabel.
    @return The same label.
    @note The notes used a fixed grey (#808080): 3.6:1 against the light window and 4.1:1 against the dark one, below the 4.5:1 that small text
          needs. The hint colour of each theme gives 5.3:1 (light) and 6.3:1 (dark), and follows a theme switch.
    """
    label.setProperty("hint", True)
    return label


def _icon(size, painter_fn, color):
    """!
    @brief Paint a square icon.
    @param size Edge in pixels.
    @param painter_fn Callable(painter, size) that draws on a transparent pixmap.
    @param color Stroke colour string.
    @return QIcon.
    """
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter_fn(p, size)
    p.end()
    return QIcon(pm)


def tool_icon(kind, theme="dark", size=22):
    """!
    @brief Painted icon of a tool or action.
    @param kind select, zone, heater, heatsink, via, outline, run, fit, grid, solver_grid, overlay, polygon.
    @param theme "dark" or "light" (stroke colour follows it).
    @param size Edge in pixels.
    @return QIcon.
    """
    c = colors(theme)
    ink = c["text"]

    def draw(p, s):
        m = s * 0.18
        r = QRectF(m, m, s - 2 * m, s - 2 * m)
        if kind == "select":
            poly = QPolygonF([QPointF(s * .25, s * .15), QPointF(s * .25, s * .8), QPointF(s * .42, s * .64),
                              QPointF(s * .55, s * .88), QPointF(s * .66, s * .82), QPointF(s * .53, s * .58),
                              QPointF(s * .76, s * .56)])
            p.setBrush(QColor(ink))
            p.drawPolygon(poly)
        elif kind == "zone":
            p.setBrush(qcolor(c["copper"], 140))
            p.setPen(QPen(QColor(c["copper"]), 1.8))
            p.drawRoundedRect(r, 2, 2)
        elif kind == "heater":
            p.setBrush(qcolor(c["heater"], 150))
            p.setPen(QPen(QColor(c["heater"]), 1.8))
            p.drawRoundedRect(r, 2, 2)
            p.setPen(QPen(QColor(c["on_element"]), 1.6))
            p.drawLine(QPointF(s * .36, s * .62), QPointF(s * .5, s * .36))
            p.drawLine(QPointF(s * .5, s * .36), QPointF(s * .64, s * .62))
        elif kind == "heatsink":
            p.setBrush(qcolor(c["heatsink"], 120))
            p.setPen(QPen(QColor(c["heatsink"]), 1.8, Qt.DashLine))
            p.drawRoundedRect(r, 2, 2)
        elif kind == "via":
            p.setBrush(qcolor(c["via"], 220))
            p.setPen(QPen(QColor(c["via"]), 1.8))
            p.drawEllipse(QPointF(s / 2, s / 2), s * .28, s * .28)
            p.setBrush(QColor(c["canvas"]))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(s / 2, s / 2), s * .11, s * .11)
        elif kind == "outline":
            p.setBrush(qcolor(c["board"], 200))
            p.setPen(QPen(QColor(c["accent"]), 1.8))
            p.drawPolygon(QPolygonF([QPointF(s * .18, s * .18), QPointF(s * .82, s * .18), QPointF(s * .82, s * .5), QPointF(s * .5, s * .5),
                                     QPointF(s * .5, s * .82), QPointF(s * .18, s * .82)]))
        elif kind == "overlay":
            for k, col in enumerate(("#ffe27a", "#ff9a3c", "#e0392d", "#7a1f5c")):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(col))
                p.drawRoundedRect(QRectF(m, m + k * (s - 2 * m) / 4, s - 2 * m, (s - 2 * m) / 4 + 0.5), 1, 1)
        elif kind == "run":
            p.setBrush(QColor(c["run"]))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(s * .30, s * .2), QPointF(s * .30, s * .8), QPointF(s * .80, s * .5)]))
        elif kind == "fit":
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                cx, cy = s / 2 + sx * s * .3, s / 2 + sy * s * .3
                p.drawLine(QPointF(cx, cy), QPointF(cx - sx * s * .16, cy))
                p.drawLine(QPointF(cx, cy), QPointF(cx, cy - sy * s * .16))
        elif kind == "grid":
            for k in (1, 2):
                p.drawLine(QPointF(m + k * (s - 2 * m) / 3, m), QPointF(m + k * (s - 2 * m) / 3, s - m))
                p.drawLine(QPointF(m, m + k * (s - 2 * m) / 3), QPointF(s - m, m + k * (s - 2 * m) / 3))
            p.drawRect(r)
        elif kind == "solver_grid":
            # The cells of the solver: a finer grid in the solver-grid colour with a dot at each cell centre (cell-centred finite volumes),
            # so it is not mistaken for the drawing grid next to it on the tool bar (both used the same icon)
            mesh = QColor(c["solver_grid"][:7])
            p.setPen(QPen(mesh, 1.2))
            n = 4
            step = (s - 2 * m) / n
            for k in range(1, n):
                p.drawLine(QPointF(m + k * step, m), QPointF(m + k * step, s - m))
                p.drawLine(QPointF(m, m + k * step), QPointF(s - m, m + k * step))
            p.drawRect(r)
            p.setPen(Qt.NoPen)
            p.setBrush(mesh)
            for i in range(n):
                for j in range(n):
                    p.drawEllipse(QPointF(m + (i + 0.5) * step, m + (j + 0.5) * step), 0.9, 0.9)
        elif kind == "polygon":
            p.drawPolygon(QPolygonF([QPointF(s * .2, s * .75), QPointF(s * .35, s * .22), QPointF(s * .78, s * .3),
                                     QPointF(s * .8, s * .78)]))

    return _icon(size, draw, ink)
