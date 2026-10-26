"""!
@file theme.py
@brief Light and dark themes, canvas colours and painted icons for the GUI.
"""

from PySide6.QtCore import QLocale, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

THEMES = {
    "dark": {
        "window": "#1e2127", "base": "#15181d", "alt": "#23272e", "text": "#e6e8eb", "muted": "#8b949e", "hint": "#9aa3ad",
        "accent": "#4c8dff", "border": "#343a43", "canvas": "#101317", "board": "#17402f",
        "grid_minor": "#ffffff12", "grid_major": "#ffffff2a", "solver_grid": "#4cc9f040",
        "copper": "#d08a3c", "heater": "#ff5b4f", "heatsink": "#3aa0ff", "via": "#f2c14e",
    },
    "light": {
        "window": "#f3f4f6", "base": "#ffffff", "alt": "#eef0f3", "text": "#1f2328", "muted": "#6b7280", "hint": "#5f6570",
        "accent": "#2563eb", "border": "#d0d5dd", "canvas": "#dfe3e8", "board": "#2f7d5b",
        "grid_minor": "#00000014", "grid_major": "#00000030", "solver_grid": "#0077aa50",
        "copper": "#c77d2e", "heater": "#e0392d", "heatsink": "#1d78d8", "via": "#c9971c",
    },
}


def fix_number_locale():
    """!
    @brief Make every number of the application use the decimal point and no thousands separator, whatever the system language.

    @details Qt spin boxes, line edits and number-to-text conversions follow QLocale.default(); the application sets it
    once to US English without the group separator, so "0.45" is shown on a Portuguese or German system too (the
    international way of writing numbers in engineering). It must run before the widgets are created.
    """
    loc = QLocale(QLocale.English, QLocale.UnitedStates)
    loc.setNumberOptions(QLocale.OmitGroupSeparator)
    QLocale.setDefault(loc)


def colors(name):
    """!
    @brief Colour table of a theme.
    @param name "dark" or "light".
    @return Dict of colour strings.
    """
    return THEMES.get(name, THEMES["dark"])


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


def apply_theme(app, name):
    """!
    @brief Apply the Fusion style, a palette and a style sheet to the whole application.
    @param app QApplication.
    @param name "dark" or "light".
    """
    c = colors(name)
    app.setStyle("Fusion")
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
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
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
        QTabWidget::pane {{ border: none; border-top: 1px solid {c['border']}; }}
        QPushButton {{ border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 14px; background: {c['alt']}; }}
        QPushButton:hover {{ border-color: {c['accent']}; }}
        QPushButton#primary {{ background: {c['accent']}; border-color: {c['accent']}; color: white; font-weight: 600; }}
        QPushButton#primary:disabled {{ background: {c['border']}; color: {c['muted']}; }}
        QStatusBar {{ border-top: 1px solid {c['border']}; }}
        QHeaderView::section {{ background: {c['alt']}; border: none; padding: 4px 8px; }}
        QTableWidget, QTreeWidget {{ border: 1px solid {c['border']}; gridline-color: {c['border']}; }}
        QProgressBar {{ border: 1px solid {c['border']}; border-radius: 4px; text-align: center; height: 14px; }}
        QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
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
            p.setPen(QPen(QColor("white"), 1.6))
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
            p.setBrush(QColor("#34d399"))
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
