"""Tests for Icon classes."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

if GTK_AVAILABLE:
    from sugar4.graphics.icon import (
        Icon,
        EventIcon,
        CanvasIcon,
        CellRendererIcon,
        get_icon_file_name,
        get_surface,
        get_icon_state,
    )
    from sugar4.graphics.xocolor import XoColor
    from sugar4.graphics.palette import Palette
    from sugar4.graphics.palettewindow import CursorInvoker


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestIcon(unittest.TestCase):
    """Test cases for Icon class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_icon_creation(self):
        """Test basic icon creation."""
        icon = Icon(icon_name="document-new", pixel_size=48)
        self.assertEqual(icon.get_icon_name(), "document-new")
        self.assertEqual(icon.get_pixel_size(), 48)

    def test_icon_properties(self):
        """Test icon property setting."""
        icon = Icon()

        # Test icon name
        icon.set_icon_name("edit-copy")
        self.assertEqual(icon.get_icon_name(), "edit-copy")

        # Test pixel size
        icon.set_pixel_size(64)
        self.assertEqual(icon.get_pixel_size(), 64)

        # Test colors
        icon.set_fill_color("#FF0000")
        icon.set_stroke_color("#0000FF")
        self.assertEqual(icon.get_fill_color(), "#FF0000")
        self.assertEqual(icon.get_stroke_color(), "#0000FF")

    def test_xo_color(self):
        """Test XO color setting."""
        icon = Icon(icon_name="emblem-favorite")

        xo_color = XoColor("#FF0000,#00FF00")
        icon.set_xo_color(xo_color)

        retrieved_color = icon.get_xo_color()
        self.assertEqual(retrieved_color.get_stroke_color(), "#FF0000")
        self.assertEqual(retrieved_color.get_fill_color(), "#00FF00")

    def test_badge_properties(self):
        """Test badge properties."""
        icon = Icon(icon_name="document-new", pixel_size=48)

        # Test badge name
        icon.set_badge_name("emblem-favorite")
        self.assertEqual(icon.get_badge_name(), "emblem-favorite")

        # Test badge size calculation
        badge_size = icon.get_badge_size()
        expected_size = int(0.45 * 48)  # _BADGE_SIZE * pixel_size
        self.assertEqual(badge_size, expected_size)

    def test_alpha_and_scale(self):
        """Test alpha and scale properties."""
        icon = Icon()

        # Test alpha
        icon.set_alpha(0.5)
        self.assertEqual(icon.get_alpha(), 0.5)

        # Test scale
        icon.set_scale(1.5)
        self.assertEqual(icon.get_scale(), 1.5)

    def test_file_name(self):
        """Test setting icon from file."""
        icon = Icon()
        icon.set_file_name("/path/to/icon.svg")
        self.assertEqual(icon.get_file_name(), "/path/to/icon.svg")

    def test_pixbuf_property(self):
        """Test pixbuf property."""
        icon = Icon()
        self.assertIsNone(icon.get_pixbuf())

        # Setting pixbuf would require actual pixbuf creation
        # Just test that the method exists
        self.assertTrue(hasattr(icon, "set_pixbuf"))

    def test_gtk_image_creation(self):
        """Test creating Gtk.Image from icon."""
        icon = Icon(icon_name="document-new")
        gtk_image = icon.get_gtk_image()
        self.assertIsInstance(gtk_image, Gtk.Image)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestEventIcon(unittest.TestCase):
    """Test cases for EventIcon class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_event_icon_creation(self):
        """Test event icon creation."""
        icon = EventIcon(icon_name="media-playback-start", pixel_size=48)
        self.assertEqual(icon.get_icon_name(), "media-playback-start")
        self.assertEqual(icon.get_pixel_size(), 48)

    def test_signal_connections(self):
        """Test that signals can be connected."""
        icon = EventIcon(icon_name="edit-copy")

        # Test signal connection (should not raise errors)
        clicked_handler = lambda icon: None
        pressed_handler = lambda icon, x, y: None
        released_handler = lambda icon, x, y: None
        activate_handler = lambda icon: None

        icon.connect("clicked", clicked_handler)
        icon.connect("pressed", pressed_handler)
        icon.connect("released", released_handler)
        icon.connect("activate", activate_handler)

    def test_background_color(self):
        """Test background color property."""
        icon = EventIcon()

        # Should start with no background color
        self.assertIsNone(icon.get_background_color())

        from gi.repository import Gdk

        color = Gdk.RGBA()
        color.red = 1.0
        color.green = 0.0
        color.blue = 0.0
        color.alpha = 1.0

        icon.set_background_color(color)
        bg_color = icon.get_background_color()
        self.assertIsNotNone(bg_color)

    def test_cache_property(self):
        """Test cache property."""
        icon = EventIcon()

        # Default should be True
        self.assertTrue(icon.get_cache())

        # Test setting cache
        icon.set_cache(False)
        self.assertFalse(icon.get_cache())

    def test_palette_invoker_present(self):
        """EventIcon owns a CursorInvoker as its palette invoker."""
        icon = EventIcon(icon_name="edit-copy")
        self.assertIsInstance(icon.get_palette_invoker(), CursorInvoker)
        self.assertIs(icon.palette_invoker, icon.get_palette_invoker())

    def test_create_palette_default_none(self):
        """The default create_palette returns None (no palette)."""
        icon = EventIcon()
        self.assertIsNone(icon.create_palette())

    def test_set_get_palette(self):
        """set_palette stores a palette that get_palette returns."""
        icon = EventIcon(icon_name="folder")
        palette = Palette("Folder")
        icon.set_palette(palette)
        self.assertIs(icon.get_palette(), palette)
        self.assertIs(icon.props.palette, palette)

    def test_palette_invoker_toggle_and_cache(self):
        """The invoker properties the shell sets are settable, mirrors BuddyIcon."""
        icon = EventIcon(icon_name="folder")
        icon.palette_invoker.props.toggle_palette = True
        icon.palette_invoker.cache_palette = False
        self.assertTrue(icon.palette_invoker.props.toggle_palette)
        self.assertFalse(icon.palette_invoker.props.cache_palette)

    def test_set_tooltip_creates_palette(self):
        """set_tooltip installs a palette."""
        icon = EventIcon(icon_name="folder")
        icon.set_tooltip("a tooltip")
        self.assertIsNotNone(icon.get_palette())

    def test_set_palette_invoker_replaces(self):
        """set_palette_invoker swaps the invoker."""
        icon = EventIcon(icon_name="folder")
        new_invoker = CursorInvoker()
        icon.set_palette_invoker(new_invoker)
        self.assertIs(icon.get_palette_invoker(), new_invoker)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestCanvasIcon(unittest.TestCase):
    """Test cases for CanvasIcon class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_canvas_icon_creation(self):
        """Test canvas icon creation."""
        icon = CanvasIcon(icon_name="document-new", pixel_size=48)
        self.assertEqual(icon.get_icon_name(), "document-new")
        self.assertEqual(icon.get_pixel_size(), 48)

    def test_canvas_icon_inheritance(self):
        """Test that CanvasIcon inherits from EventIcon."""
        icon = CanvasIcon()
        self.assertIsInstance(icon, EventIcon)

    def test_connect_to_palette_pop_events(self):
        """Prelight is held while a palette popped from the icon is up."""
        icon = CanvasIcon(icon_name="folder")
        self.assertFalse(icon._palette_up)

        palette = Palette("Folder")
        icon.connect_to_palette_pop_events(palette)

        palette.emit("popup")
        self.assertTrue(icon._palette_up)

        palette.emit("popdown")
        self.assertFalse(icon._palette_up)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestCellRendererIcon(unittest.TestCase):
    """Test cases for CellRendererIcon class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_cell_renderer_creation(self):
        """Test cell renderer creation."""
        renderer = CellRendererIcon()
        self.assertIsInstance(renderer, CellRendererIcon)

    def test_cell_renderer_properties(self):
        """Test cell renderer property setting."""
        renderer = CellRendererIcon()

        # Test icon name
        renderer.set_icon_name("document-new")

        # Test size
        renderer.set_size(32)

        # Test colors
        renderer.set_fill_color("#FF0000")
        renderer.set_stroke_color("#0000FF")

    def test_cell_renderer_surface(self):
        """Test cell renderer surface creation."""
        renderer = CellRendererIcon()
        renderer.set_icon_name("document-new")
        renderer.set_size(32)

        surface = renderer.get_surface()
        # Surface might be None if icon not found, which is okay for test
        self.assertTrue(surface is None or hasattr(surface, "get_width"))


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""

    def test_get_icon_file_name(self):
        """Test icon file name resolution."""
        if not GTK_AVAILABLE:
            self.skipTest("GTK4 not available")

        # Test with common system icon
        file_name = get_icon_file_name("document-new")
        if file_name:  # could not be there in all envs
            self.assertIsInstance(file_name, str)
            self.assertTrue(os.path.exists(file_name))

    def test_get_icon_state(self):
        """Test icon state resolution."""
        if not GTK_AVAILABLE:
            self.skipTest("GTK4 not available")

        # Test with hypothetical state icons
        # This will likely return None unless specific icons exist
        state_icon = get_icon_state("network-wireless", 67.8, 20)
        if state_icon:
            self.assertIsInstance(state_icon, str)
            self.assertTrue(state_icon.startswith("network-wireless-"))

    def test_get_surface(self):
        """Test surface creation."""
        if not GTK_AVAILABLE:
            self.skipTest("GTK4 not available")

        # Test with system icon
        surface = get_surface(icon_name="document-new", pixel_size=48)
        if surface:  # could not be there in all envs
            self.assertEqual(surface.get_width(), 48)
            self.assertEqual(surface.get_height(), 48)

    def test_get_surface_with_colors(self):
        """Test surface creation with colors."""
        if not GTK_AVAILABLE:
            self.skipTest("GTK4 not available")

        surface = get_surface(
            icon_name="emblem-favorite",
            fill_color="#FF0000",
            stroke_color="#0000FF",
            pixel_size=32,
        )
        if surface:
            self.assertEqual(surface.get_width(), 32)
            self.assertEqual(surface.get_height(), 32)

    def test_get_surface_with_badge(self):
        """Test surface creation with badge."""
        if not GTK_AVAILABLE:
            self.skipTest("GTK4 not available")

        surface = get_surface(
            icon_name="document-new", badge_name="emblem-favorite", pixel_size=48
        )
        if surface:
            self.assertGreaterEqual(surface.get_width(), 48)
            self.assertGreaterEqual(surface.get_height(), 48)


if __name__ == "__main__":
    unittest.main()
