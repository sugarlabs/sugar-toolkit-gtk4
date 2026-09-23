"""Tests for ProgressIcon."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import cairo
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

if GTK_AVAILABLE:
    from sugar4.graphics.progressicon import ProgressIcon
    from sugar4.graphics import style


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestProgressIcon(unittest.TestCase):
    """Test cases for ProgressIcon."""

    def setUp(self):
        if not Gtk.is_initialized():
            Gtk.init()

    def _make(self, **kwargs):
        kwargs.setdefault("icon_name", "document-new")
        kwargs.setdefault("pixel_size", style.STANDARD_ICON_SIZE)
        kwargs.setdefault("stroke_color", style.COLOR_BLACK.get_svg())
        kwargs.setdefault("fill_color", style.COLOR_WHITE.get_svg())
        return ProgressIcon(**kwargs)

    def _draw(self, icon, size=64):
        """Run the draw function against an offscreen cairo surface.

        This drives the same callback set_draw_func() installs, without
        needing the widget to be realized or allocated.
        """
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        icon._draw_cb(icon, cairo.Context(surface), size, size)

    def test_is_a_drawing_area(self):
        """ProgressIcon is drawn, so it must be a Gtk.DrawingArea."""
        self.assertIsInstance(self._make(), Gtk.DrawingArea)

    def test_requests_the_size_it_was_given(self):
        """The widget sizes itself rather than collapsing to zero.

        In GTK3 this came from do_get_preferred_width()/height(); in GTK4 it
        has to be set as the drawing area's content size, so a regression
        here is a widget that does not appear at all.
        """
        icon = self._make(pixel_size=style.LARGE_ICON_SIZE)
        self.assertGreater(icon.get_content_width(), 0)
        self.assertGreater(icon.get_content_height(), 0)

    def test_missing_icon_still_sizes_and_draws(self):
        """get_surface() returns None for an unknown icon.

        An activity passing an icon name the theme does not have should get
        an empty icon, not a widget with no size and not a crash inside the
        draw function.
        """
        icon = self._make(icon_name="sugar-no-such-icon-exists-here")
        self.assertEqual(icon.get_content_width(), style.STANDARD_ICON_SIZE)
        self.assertEqual(icon.get_content_height(), style.STANDARD_ICON_SIZE)
        self._draw(icon)

    def test_update_stores_progress(self):
        icon = self._make()
        self.assertEqual(icon._progress, 0.0)
        icon.update(0.5)
        self.assertEqual(icon._progress, 0.5)

    def test_default_direction_is_vertical(self):
        self.assertEqual(self._make()._direction, "vertical")

    def test_horizontal_direction_is_kept(self):
        self.assertEqual(self._make(direction="horizontal")._direction, "horizontal")

    def test_draws_at_every_progress_value(self):
        """Drawing must not raise for any progress, including the ends.

        At 0.0 the clip rectangle has zero area and at 1.0 it covers the
        whole surface; both are easy to get wrong when porting the cairo
        clip, and neither may raise.
        """
        for direction in ("vertical", "horizontal"):
            icon = self._make(direction=direction)
            for progress in (0.0, 0.25, 1.0):
                with self.subTest(direction=direction, progress=progress):
                    icon.update(progress)
                    self._draw(icon)

    def test_draws_when_the_widget_is_smaller_than_the_icon(self):
        """The centering maths produces negative margins, which is fine.

        A drawing area can be allocated less than its content size; the
        GTK3 version handled this by translating by a negative margin, and
        the port has to keep doing so rather than clamping or raising.
        """
        icon = self._make(pixel_size=style.LARGE_ICON_SIZE)
        icon.update(0.5)
        self._draw(icon, size=8)


if __name__ == "__main__":
    unittest.main()
