#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_callouts.py
@brief The numbered red boxes of the manual pictures (tools/manual/callouts.py): the geometry of a widget becomes the box in the picture, the badge sits outside the corner and never over another badge, the list and the count in the PNG agree.
"""

import math

import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QImage

from tools.manual import callouts as co


class FakeWidget:
    """!
    @brief A widget of a fake tree: a rectangle in the coordinates of its parent, with `mapTo` as QWidget has it.
    """

    def __init__(self, x, y, w, h, parent=None):
        """!
        @brief Build the fake widget.
        @param x Left edge in the parent, pixels.
        @param y Top edge in the parent, pixels.
        @param w Width in pixels.
        @param h Height in pixels.
        @param parent The fake parent, or None for the root.
        @return None
        """
        self.x, self.y, self._w, self._h, self.parent = x, y, w, h, parent

    def width(self):
        """!
        @brief Width of the widget.
        @return Width in pixels.
        """
        return self._w

    def height(self):
        """!
        @brief Height of the widget.
        @return Height in pixels.
        """
        return self._h

    def mapTo(self, root, point):
        """!
        @brief Map a point of this widget to the coordinates of an ancestor.
        @param root The ancestor.
        @param point QPoint in this widget.
        @return QPoint in the ancestor.
        """
        node, px, py = self, point.x(), point.y()
        while node is not root:
            px, py, node = px + node.x, py + node.y, node.parent
        return QPoint(px, py)


def pixel(image, x, y):
    """!
    @brief Colour of one pixel as `#rrggbb`.
    @param image The QImage.
    @param x Column.
    @param y Row.
    @return Lower-case colour string.
    """
    return QColor(image.pixel(int(x), int(y))).name()


def test_widget_rect_adds_the_offsets_of_the_parents():
    root = FakeWidget(0, 0, 800, 600)
    dock = FakeWidget(100, 50, 300, 400, root)
    button = FakeWidget(20, 30, 60, 25, dock)
    assert co.widget_rect(button, root) == QRect(120, 80, 60, 25)
    assert co.widget_rect(dock, root) == QRect(100, 50, 300, 400)


def test_resolve_accepts_widget_path_callable_and_rect():
    class Window(FakeWidget):
        pass

    root = Window(0, 0, 800, 600)
    root.panel = FakeWidget(10, 10, 100, 100, root)
    root.panel.button = FakeWidget(5, 5, 20, 20, root.panel)
    root.menu = lambda: FakeWidget(0, 0, 800, 30, root)       # an accessor such as QMainWindow.menuBar
    assert co.resolve("panel.button", root) == QRect(15, 15, 20, 20)
    assert co.resolve(root.panel, root) == QRect(10, 10, 100, 100)
    assert co.resolve(lambda r: r.panel.button, root) == QRect(15, 15, 20, 20)
    assert co.resolve(QRect(1, 2, 3, 4), root) == QRect(1, 2, 3, 4)
    assert co.resolve("menu", root) == QRect(0, 0, 800, 30)
    with pytest.raises(TypeError):
        co.resolve(lambda r: 42, root)
    with pytest.raises(AttributeError):
        co.resolve("panel.nothing", root)


def test_union_and_grow_targets():
    root = FakeWidget(0, 0, 800, 600)
    a, b = FakeWidget(10, 10, 20, 20, root), FakeWidget(50, 40, 30, 10, root)
    assert co.union(a, b)(root) == QRect(10, 10, 70, 40)
    assert co.grow(a, 3)(root) == QRect(7, 7, 26, 26)


def test_scale_rect_applies_the_factor():
    assert co.scale_rect(QRect(10, 20, 30, 40), 0.5) == QRectF(5, 10, 15, 20)


def test_annotate_draws_the_box_outline_and_the_badge_outside_the_corner(qapp):
    image = QImage(400, 300, QImage.Format_RGB32)
    image.fill(QColor("#ffffff"))
    box = QRectF(100, 100, 200, 120)
    centres = co.annotate(image, [box])
    red = QColor(co.BOX_COLOUR).name()
    # The outline: the two pixel rows and columns inside the edges carry the box colour on a straight stretch (away from the badge)
    assert pixel(image, 200, 100) == red and pixel(image, 200, 101) == red
    assert pixel(image, 200, 218) == red and pixel(image, 200, 219) == red
    assert pixel(image, 100, 160) == red and pixel(image, 299, 160) == red
    assert pixel(image, 200, 160) == "#ffffff"              # the inside of the box is untouched
    # The badge is centred on the top left corner, with its centre on the box colour
    assert centres[0].x() < box.left() and centres[0].y() < box.top()
    # The ring of the badge is white, its disc red: a point 6 px left of the centre is red
    assert pixel(image, centres[0].x() - 6, centres[0].y() + 5) == red


def test_badge_does_not_hide_the_inside_of_a_box_with_room_around_it():
    box = QRectF(100, 100, 200, 120)
    (c,) = co.place_badges([box], 400, 300)
    # The centre is outside the box on both axes: at most a sliver of the disc reaches into the box
    assert c.x() < box.left() and c.y() < box.top()
    assert c.x() + co.BADGE_RADIUS_PX - box.left() < co.BADGE_RADIUS_PX and c.y() + co.BADGE_RADIUS_PX - box.top() < co.BADGE_RADIUS_PX


def test_badges_never_overlap_and_stay_inside_the_picture():
    # Ten boxes that share a corner and one at the very top left of the picture: every badge must find its own place
    boxes = [QRectF(0, 0, 50, 50), QRectF(0, 0, 60, 60), QRectF(0, 0, 70, 70)] + [QRectF(100, 100, 40 + k, 40) for k in range(7)]
    centres = co.place_badges(boxes, 300, 300)
    r = co.BADGE_RADIUS_PX
    for i, a in enumerate(centres):
        assert r <= a.x() <= 300 - r and r <= a.y() <= 300 - r
        for b in centres[i + 1:]:
            assert math.hypot(a.x() - b.x(), a.y() - b.y()) >= 2 * r


def test_badge_of_a_box_at_the_picture_edge_goes_inside_the_picture():
    (c,) = co.place_badges([QRectF(0, 0, 100, 30)], 400, 300)
    assert c.x() >= co.BADGE_RADIUS_PX and c.y() >= co.BADGE_RADIUS_PX


def test_markdown_list_is_numbered_like_the_badges():
    items = [co.Callout("a", "**Menu bar.** File and Edit."), co.Callout("b", "**Tool bar.** The tools.")]
    assert co.callouts_markdown(items) == "1. **Menu bar.** File and Edit.\n2. **Tool bar.** The tools.\n"


def test_render_scales_the_boxes_with_the_pixel_ratio_and_writes_png_and_list(tmp_path, qapp):
    from PySide6.QtWidgets import QPushButton, QWidget

    root = QWidget()
    root.resize(300, 200)
    button = QPushButton("Run", root)
    button.setGeometry(50, 60, 80, 30)
    root.show()
    qapp.processEvents()
    out = tmp_path / "pic.png"
    # A max_width of 150 halves the picture: the box of the button must follow
    centres = co.render(root, [co.Callout(button, "**Run.** Starts the simulation.")], str(out), max_width=150)
    image = QImage(str(out))
    assert image.width() == 150
    red = QColor(co.BOX_COLOUR).name()
    ratio = root.grab().devicePixelRatio()
    f = ratio * 150 / (300 * ratio)
    # The top edge of the button box (y = 60 * f) and its right edge (x = (50 + 80) * f), on a stretch away from the badge
    assert pixel(image, (50 + 40) * f, 60 * f + 0.5) == red
    assert pixel(image, (50 + 80) * f - 1, (60 + 15) * f) == red
    assert co.count_in_png(str(out)) == 1
    assert (tmp_path / "pic.md").read_text(encoding="utf-8") == "1. **Run.** Starts the simulation.\n"
    assert len(centres) == 1


def test_count_in_png_is_none_for_a_plain_picture(tmp_path):
    image = QImage(10, 10, QImage.Format_RGB32)
    image.fill(QColor("#ffffff"))
    image.save(str(tmp_path / "plain.png"))
    assert co.count_in_png(str(tmp_path / "plain.png")) is None


def test_render_of_a_region_moves_the_boxes_with_the_crop(tmp_path, qapp):
    from PySide6.QtWidgets import QPushButton, QWidget

    root = QWidget()
    root.resize(400, 300)
    button = QPushButton("Run", root)
    button.setGeometry(200, 100, 80, 40)
    root.show()
    qapp.processEvents()
    out = tmp_path / "crop.png"
    # Keep only x 150..350, y 50..200 and enlarge it twice: the box of the button starts at (50, 50) of the crop, (100, 100) after the zoom
    co.render(root, [co.Callout(button, "**Run.**")], str(out), region=QRect(150, 50, 200, 150), zoom=2.0)
    image = QImage(str(out))
    assert image.width() == 400                             # the crop is 200 logical pixels wide and enlarged twice, whatever the pixel ratio of the screen
    red = QColor(co.BOX_COLOUR).name()
    assert pixel(image, 100 + 40, 100 + 0.5) == red         # top edge of the box, away from the badge


def test_busyness_is_zero_on_plain_background_and_high_on_detail(qapp):
    image = QImage(100, 60, QImage.Format_RGB32)
    image.fill(QColor("#f0f0f0"))
    for x in range(60, 100, 2):                              # vertical black stripes: text-like detail on the right
        for y in range(60):
            image.setPixelColor(x, y, QColor("#000000"))
    assert co.busyness(image, QPointF(20, 30), 11) == 0.0
    assert co.busyness(image, QPointF(80, 30), 11) > 0.3


def test_badge_passes_over_a_busy_corner_and_takes_a_quiet_one():
    box = QRectF(100, 100, 200, 120)
    corner = co.place_badges([box], 400, 300)[0]
    # The first corner is declared busy (text under it): the badge goes to the next free place, which is not at that corner
    busy = lambda c: 1.0 if math.hypot(c.x() - corner.x(), c.y() - corner.y()) < 2 * co.BADGE_RADIUS_PX else 0.0
    moved = co.place_badges([box], 400, 300, busy=busy)[0]
    assert math.hypot(moved.x() - corner.x(), moved.y() - corner.y()) >= 2 * co.BADGE_RADIUS_PX


def test_left_first_puts_an_inside_badge_at_the_left_end():
    # A box that fills the picture has no room outside: the badge goes inside, at the right end of the top edge or, with left_first, at the left end
    box = QRectF(0, 0, 300, 40)
    right = co.place_badges([box], 300, 40)[0]
    left = co.place_badges([box], 300, 40, left_first=[0])[0]
    assert right.x() > 200 and left.x() < 100


def test_a_large_box_hemmed_in_by_a_neighbour_gets_its_badge_inside():
    # Two big boxes side by side: the badge of the second must not touch the first box (it would read as the first's number)
    a, b = QRectF(10, 40, 200, 200), QRectF(212, 40, 200, 200)
    ca, cb = co.place_badges([a, b], 430, 260)
    near_a = max(a.left() - cb.x(), 0.0, cb.x() - a.right())      # horizontal gap from the badge centre to the first box (the vertical one may be zero)
    assert near_a >= co.BADGE_RADIUS_PX or cb.y() < a.top() - co.BADGE_RADIUS_PX
    assert ca.x() > 0 and cb.x() > 0
