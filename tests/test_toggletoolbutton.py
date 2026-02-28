"""Tests for ToggleToolButton class."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GObject

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

if GTK_AVAILABLE:
    from sugar4.graphics.toggletoolbutton import ToggleToolButton
    from sugar4.graphics.palette import Palette
    from sugar4.graphics.icon import Icon


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToggleToolButton(unittest.TestCase):
    """Test cases for ToggleToolButton class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()
        self.button = ToggleToolButton()

    def test_toggletoolbutton_creation(self):
        """Test basic toggle tool button creation."""
        self.assertIsInstance(self.button, ToggleToolButton)
        self.assertIsInstance(self.button, Gtk.ToggleButton)
        self.assertIsNotNone(self.button.get_palette_invoker())

    def test_toggletoolbutton_creation_with_icon(self):
        """Test toggle tool button creation with icon name."""
        button = ToggleToolButton(icon_name="document-new")
        self.assertIsInstance(button, ToggleToolButton)
        self.assertEqual(button.get_icon_name(), "document-new")

    def test_icon_name_property(self):
        """Test icon name property setting and getting."""
        # Initially no icon
        self.assertIsNone(self.button.get_icon_name())

        # Set icon name
        self.button.set_icon_name("edit-copy")
        self.assertEqual(self.button.get_icon_name(), "edit-copy")

        # Verify icon widget was created (child of the button)
        child = self.button.get_child()
        self.assertIsNotNone(child)
        self.assertIsInstance(child, Icon)

        # Test property access
        self.assertEqual(self.button.icon_name, "edit-copy")

        # Set to None
        self.button.set_icon_name(None)
        self.assertIsNone(self.button.get_icon_name())

    def test_palette_property(self):
        """Test palette property setting and getting."""
        self.assertIsNone(self.button.get_palette())

        palette = Palette("Test Palette")
        self.button.set_palette(palette)
        self.assertEqual(self.button.get_palette(), palette)

        # Test property access
        self.assertEqual(self.button.palette, palette)

        # Set to None
        self.button.set_palette(None)
        self.assertIsNone(self.button.get_palette())

    def test_palette_invoker_property(self):
        """Test palette invoker property."""
        # Should have default invoker
        original_invoker = self.button.get_palette_invoker()
        self.assertIsNotNone(original_invoker)

        # Create mock invoker
        class MockInvoker:
            def detach(self):
                pass

        mock_invoker = MockInvoker()
        self.button.set_palette_invoker(mock_invoker)
        self.assertEqual(self.button.get_palette_invoker(), mock_invoker)

        # Test property access
        self.assertEqual(self.button.palette_invoker, mock_invoker)

    def test_tooltip_setting(self):
        """Test tooltip setting."""
        self.button.set_tooltip("Test Tooltip")

        # Should create a palette with the tooltip text
        palette = self.button.get_palette()
        self.assertIsNotNone(palette)
        self.assertIsInstance(palette, Palette)

    def test_accelerator_property(self):
        """Test accelerator property setting and getting."""
        # Set accelerator
        self.button.set_accelerator("<Ctrl>T")
        self.assertEqual(self.button.get_accelerator(), "<Ctrl>T")

        # Test property access
        self.assertEqual(self.button.accelerator, "<Ctrl>T")

    def test_gtype_name(self):
        """Test GType name."""
        self.assertEqual(ToggleToolButton.__gtype_name__, "SugarToggleToolButton")

    def test_create_palette_method(self):
        """Test create_palette method."""
        # Default implementation should return None
        self.assertIsNone(self.button.create_palette())

    def test_clicked_signal(self):
        """Test clicked signal behavior."""
        # Set up signal tracking
        clicked_count = 0

        def on_clicked(button):
            nonlocal clicked_count
            clicked_count += 1

        self.button.connect("clicked", on_clicked)

        # Emit clicked signal
        self.button.emit("clicked")
        self.assertEqual(clicked_count, 1)

    def test_toggled_signal(self):
        """Test toggled signal behavior."""
        # Set up signal tracking
        toggled_count = 0
        last_active_state = None

        def on_toggled(button):
            nonlocal toggled_count, last_active_state
            toggled_count += 1
            last_active_state = button.get_active()

        self.button.connect("toggled", on_toggled)

        # Toggle the button
        self.button.set_active(True)
        self.assertEqual(toggled_count, 1)
        self.assertTrue(last_active_state)

        self.button.set_active(False)
        self.assertEqual(toggled_count, 2)
        self.assertFalse(last_active_state)

    def test_active_state(self):
        """Test active/toggle state."""
        # Initially not active
        self.assertFalse(self.button.get_active())

        # Set active
        self.button.set_active(True)
        self.assertTrue(self.button.get_active())

        # Toggle off
        self.button.set_active(False)
        self.assertFalse(self.button.get_active())

    def test_do_clicked_method(self):
        """Test do_clicked method."""
        # Create button with palette
        button = ToggleToolButton()
        palette = Palette("Test")
        button.set_palette(palette)

        # Method should exist and be callable
        self.assertTrue(hasattr(button, "do_clicked"))
        button.do_clicked()

        # Should work without palette too
        button.set_palette(None)
        button.do_clicked()

    def test_multiple_icon_changes(self):
        """Test changing icon multiple times."""
        icons = ["document-new", "edit-copy", "edit-paste", "document-save"]

        for icon_name in icons:
            self.button.set_icon_name(icon_name)
            self.assertEqual(self.button.get_icon_name(), icon_name)
            self.assertIsNotNone(self.button.get_child())

    def test_palette_property_direct(self):
        """Test direct palette property access."""
        # Test the property decorator
        palette1 = Palette("Test 1")
        palette2 = Palette("Test 2")

        self.button.palette = palette1
        self.assertEqual(self.button.palette, palette1)

        self.button.palette = palette2
        self.assertEqual(self.button.palette, palette2)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToggleToolButtonAccelerator(unittest.TestCase):
    """Test accelerator functionality for ToggleToolButton."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_setup_accelerator_function(self):
        """Test setup_accelerator function."""
        button = ToggleToolButton()
        button.set_accelerator("<Ctrl>T")
        # Should work even without proper toplevel window
        self.assertTrue(True)  # If we get here, no exception was raised

    def test_accelerator_with_window(self):
        """Test accelerator setup with proper window hierarchy."""
        # Create a window with mock accel group (GTK4 style)
        window = Gtk.Window()
        window.sugar_accel_group = {}  # Mock accelerator group for GTK4

        button = ToggleToolButton()
        button.set_accelerator("<Ctrl>T")

        # Add button to window
        window.set_child(button)

        # Clean up
        window.destroy()

    def test_accelerator_without_window(self):
        """Test accelerator setup without proper window."""
        button = ToggleToolButton()
        button.set_accelerator("<Ctrl>T")

    def test_accelerator_parsing(self):
        """Test accelerator string parsing."""
        button = ToggleToolButton()

        valid_accelerators = [
            "<Ctrl>a",
            "<Alt>F4",
            "<Shift><Ctrl>S",
            "F1",
            "Delete",
            "<Primary>q",
        ]

        for accel in valid_accelerators:
            button.set_accelerator(accel)
            self.assertEqual(button.get_accelerator(), accel)

    def test_accelerator_setting(self):
        """Test accelerator setting and getting."""
        button = ToggleToolButton()

        # Initially no accelerator
        self.assertIsNone(button.get_accelerator())

        # Set accelerator
        accel = "<Ctrl>B"
        button.set_accelerator(accel)
        self.assertEqual(button.get_accelerator(), accel)

        # Change accelerator
        new_accel = "<Ctrl>I"
        button.set_accelerator(new_accel)
        self.assertEqual(button.get_accelerator(), new_accel)

    def test_accelerator_with_app(self):
        """Test accelerator with application context."""
        app = Gtk.Application(application_id="org.sugar4.test")
        button = ToggleToolButton()

        # Set accelerator
        button.set_accelerator("<Ctrl>T")

        # Simulate adding to window with app
        window = Gtk.ApplicationWindow(application=app)
        window.set_child(button)

        # The accelerator should be set up
        self.assertEqual(button.get_accelerator(), "<Ctrl>T")

        window.destroy()


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToggleToolButtonEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for ToggleToolButton."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_none_icon_name(self):
        """Test setting None as icon name."""
        button = ToggleToolButton()

        # Set valid icon first
        button.set_icon_name("document-new")
        self.assertEqual(button.get_icon_name(), "document-new")

        # Set to None
        button.set_icon_name(None)
        # Icon widget might still exist but icon_name should be None
        self.assertIsNone(button.get_icon_name())

    def test_empty_string_icon(self):
        """Test setting empty string as icon name."""
        button = ToggleToolButton()

        # Empty string should be handled gracefully
        button.set_icon_name("")
        # Behavior may vary - either None or empty string
        result = button.get_icon_name()
        self.assertTrue(result is None or result == "")

    def test_invalid_accelerator(self):
        """Test invalid accelerator strings."""
        button = ToggleToolButton()

        # These should not crash
        invalid_accelerators = ["", "invalid", "<InvalidMod>a", None]

        for accel in invalid_accelerators:
            try:
                button.set_accelerator(accel)
                # If it doesn't crash, that's good
            except (TypeError, ValueError):
                # Some invalid accelerators might raise exceptions
                pass

    def test_palette_invoker_detach(self):
        """Test palette invoker detachment."""
        button = ToggleToolButton()
        original_invoker = button.get_palette_invoker()

        # Mock invoker with detach tracking
        class MockInvoker:
            def __init__(self):
                self.detached = False

            def detach(self):
                self.detached = True

        mock_invoker = MockInvoker()
        button.set_palette_invoker(mock_invoker)

        # Setting new invoker should detach the old one
        new_mock = MockInvoker()
        button.set_palette_invoker(new_mock)

        self.assertTrue(mock_invoker.detached)
        self.assertFalse(new_mock.detached)

    def test_multiple_palette_changes(self):
        """Test changing palette multiple times."""
        button = ToggleToolButton()

        palettes = [
            Palette("Palette 1"),
            Palette("Palette 2"),
            Palette("Palette 3"),
            None,
        ]

        for palette in palettes:
            button.set_palette(palette)
            self.assertEqual(button.get_palette(), palette)

    def test_button_without_icon_widget(self):
        """Test button behavior without icon widget."""
        button = ToggleToolButton()

        # Initially no icon widget
        self.assertIsNone(button.get_child())

        # get_icon_name should return None
        self.assertIsNone(button.get_icon_name())

        # Setting accelerator should work
        button.set_accelerator("<Ctrl>T")
        self.assertEqual(button.get_accelerator(), "<Ctrl>T")

    def test_unicode_tooltip(self):
        """Test Unicode tooltip text."""
        button = ToggleToolButton()

        unicode_tooltips = [
            "Hello 世界",
            "Café ñoño",
            "🌟 Star ⭐",
            "اللغة العربية",
            "Русский язык",
        ]

        for tooltip in unicode_tooltips:
            button.set_tooltip(tooltip)
            palette = button.get_palette()
            self.assertIsNotNone(palette)

    def test_signal_connection_edge_cases(self):
        """Test signal connections with edge cases."""
        button = ToggleToolButton()

        # Connect multiple handlers to same signal
        handlers = []

        def make_handler(index):
            def handler(btn):
                handlers.append(index)

            return handler

        # Connect multiple handlers
        for i in range(3):
            button.connect("clicked", make_handler(i))

        # Emit signal
        button.emit("clicked")

        # All handlers should have been called
        self.assertEqual(len(handlers), 3)
        self.assertEqual(handlers, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
