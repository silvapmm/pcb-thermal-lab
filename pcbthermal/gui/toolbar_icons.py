#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file toolbar_icons.py
@brief Own drawn icons for the Matplotlib navigation toolbar of the Results plots (flat line style, theme colour, any size and pixel ratio).
@details `ThemedToolbar` is a `NavigationToolbar2QT` whose buttons are painted by `toolbar_icon` instead of the stock PNG files. Matplotlib builds
         each button with its private `_icon(name)`; the subclass overrides it and, for a name it does not draw, falls back to the stock icon.
"""

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

from . import theme as th

# Logical edges (px) and device pixel ratios the icon is rendered for; Qt picks the nearest, so no size is a rescaled bitmap
SIZES = (16, 20, 24, 32, 48)
RATIOS = (1.0, 2.0)

DRAW = {}


def _draw(name):
    """!
    @brief Register a drawing function under a Matplotlib icon file name.
    @param name Stock icon file name, for example "home.png".
    @return the decorator.
    """
    def deco(fn):
        DRAW[name] = fn
        return fn
    return deco


def _poly(p, pts):
    """!
    @brief Open polyline (no fill) through unit-square points.
    @param p QPainter in unit coordinates.
    @param pts list of (x, y) in 0..1.
    @return None.
    """
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(*q) for q in pts]))


def _line(p, x0, y0, x1, y1):
    """!
    @brief Straight line in unit coordinates.
    @param p QPainter in unit coordinates.
    @param x0 Start x (0..1).
    @param y0 Start y (0..1).
    @param x1 End x (0..1).
    @param y1 End y (0..1).
    @return None.
    """
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))


@_draw("home.png")
def _home(p, bg):
    """!
    @brief Home: a house outline with a door.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    _poly(p, [(.12, .5), (.5, .16), (.88, .5)])
    _poly(p, [(.22, .44), (.22, .84), (.78, .84), (.78, .44)])
    _poly(p, [(.42, .84), (.42, .6), (.58, .6), (.58, .84)])


@_draw("back.png")
def _back(p, bg):
    """!
    @brief Back: arrow to the left.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    _line(p, .82, .5, .2, .5)
    _poly(p, [(.45, .25), (.2, .5), (.45, .75)])


@_draw("forward.png")
def _forward(p, bg):
    """!
    @brief Forward: arrow to the right.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    _line(p, .18, .5, .8, .5)
    _poly(p, [(.55, .25), (.8, .5), (.55, .75)])


@_draw("move.png")
def _pan(p, bg):
    """!
    @brief Pan: four arrows from the centre.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    _line(p, .5, .1, .5, .9)
    _line(p, .1, .5, .9, .5)
    _poly(p, [(.4, .22), (.5, .1), (.6, .22)])
    _poly(p, [(.4, .78), (.5, .9), (.6, .78)])
    _poly(p, [(.22, .4), (.1, .5), (.22, .6)])
    _poly(p, [(.78, .4), (.9, .5), (.78, .6)])


@_draw("zoom_to_rect.png")
def _zoom(p, bg):
    """!
    @brief Zoom to rectangle: a magnifying glass with a plus.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(.43, .43), .28, .28)
    _line(p, .64, .64, .88, .88)
    _line(p, .43, .3, .43, .56)
    _line(p, .3, .43, .56, .43)


@_draw("subplots.png")
def _subplots(p, bg):
    """!
    @brief Configure subplots: a 2 x 2 grid of panels.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    p.setBrush(Qt.NoBrush)
    for i in (0, 1):
        for j in (0, 1):
            p.drawRoundedRect(QRectF(.1 + i * .47, .1 + j * .47, .33, .33), .05, .05)


@_draw("qt4_editor_options.png")
def _options(p, bg):
    """!
    @brief Figure options (curves): three sliders.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    for y, x in ((.25, .32), (.5, .68), (.75, .45)):
        # The track stops at the knob (no fill in the window colour, so the icon stays one colour on any background)
        _line(p, .1, y, x - .09, y)
        _line(p, x + .09, y, .9, y)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(x, y), .09, .09)


@_draw("filesave.png")
def _save(p, bg):
    """!
    @brief Save: an arrow into a tray.
    @param p QPainter in unit coordinates.
    @param bg Window colour (unused).
    @return None.
    """
    _line(p, .5, .12, .5, .6)
    _poly(p, [(.3, .42), (.5, .62), (.7, .42)])
    _poly(p, [(.14, .62), (.14, .86), (.86, .86), (.86, .62)])


def toolbar_icon(name, theme):
    """!
    @brief Icon of a Matplotlib toolbar button, drawn in the theme's text colour.
    @param name Stock icon file name ("home.png", "filesave.png", ...).
    @param theme "dark" or "light".
    @return QIcon with a pixmap for every size of `SIZES` at pixel ratios 1 and 2, or None when the name is not drawn here.
    """
    fn = DRAW.get(name)
    if fn is None:
        return None
    c = th.colors(theme)
    icon = QIcon()
    for size in SIZES:
        for ratio in RATIOS:
            px = int(round(size * ratio))
            pm = QPixmap(px, px)
            pm.setDevicePixelRatio(ratio)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.scale(size, size)                     # Unit square: one drawing for every size
            # Stroke of about 1.5 px at 24 px, never thinner than 1.1 px so that the 16 px icon stays visible
            width = max(1.1 / size, 0.062)
            p.setPen(QPen(QColor(c["text"]), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            fn(p, c["window"])
            p.end()
            icon.addPixmap(pm)
    return icon


class ThemedToolbar(NavigationToolbar2QT):
    """!
    @brief Matplotlib navigation toolbar with the program's own icons.
    @note Relies on the private `NavigationToolbar2QT._icon(name)` that Matplotlib calls once per tool item; `tests/test_toolbar_icons.py` fails
          clearly if a future Matplotlib stops doing so.
    """

    def __init__(self, canvas, parent=None, theme="dark"):
        """!
        @param canvas FigureCanvasQTAgg.
        @param parent Qt parent.
        @param theme "dark" or "light" for the first painting.
        """
        self._icon_theme = theme            # Must exist before the base class asks for the icons
        self._icon_names = {}               # Action text -> stock icon name, for the repaint after a theme change
        super().__init__(canvas, parent)
        for text, _tip, image, _cb in self.toolitems:
            if text is not None:
                self._icon_names[text] = image + ".png"     # toolitems hold the name without the extension

    def _icon(self, name, color=None):
        """!
        @brief Called by Matplotlib for each button.
        @param name Stock icon file name.
        @param color Ignored (the colour is the theme's text token).
        @return QIcon, ours when the name is drawn here and the stock icon otherwise.
        """
        icon = toolbar_icon(name, self._icon_theme)
        if icon is None:
            return super()._icon(name) if color is None else super()._icon(name, color)
        return icon

    def set_theme(self, theme):
        """!
        @brief Repaint every drawn icon for a theme.
        @param theme "dark" or "light".
        @return None.
        """
        self._icon_theme = theme
        for act in self.actions():
            name = self._icon_names.get(act.text())
            icon = toolbar_icon(name, theme) if name else None
            if icon is not None:
                act.setIcon(icon)
