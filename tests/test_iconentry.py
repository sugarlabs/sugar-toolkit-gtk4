"""Tests for IconEntry module."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gdk, GdkPixbuf, Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

if GTK_AVAILABLE:
    from sugar4.graphics.iconentry import (
        ICON_ENTRY_PRIMARY,
        ICON_ENTRY_SECONDARY,
        IconEntry,
    )


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestIconEntry(unittest.TestCase):
    """Test cases for IconEntry class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()
        self.entry = IconEntry()

    def test_creation(self):
        """Test basic IconEntry creation."""
        self.assertIsInstance(self.entry, IconEntry)
        self.assertIsInstance(self.entry, Gtk.Entry)

    def test_gtype_name(self):
        """Test GType name."""
        self.assertEqual(IconEntry.__gtype_name__, "SugarIconEntry")

    def test_icon_position_constants(self):
        """Test icon position constants match GTK4 values."""
        self.assertEqual(ICON_ENTRY_PRIMARY, Gtk.EntryIconPosition.PRIMARY)
        self.assertEqual(ICON_ENTRY_SECONDARY, Gtk.EntryIconPosition.SECONDARY)

    def test_set_icon_with_pixbuf(self):
        """Test setting icon from a pixbuf."""
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 16, 16)
        pixbuf.fill(0xFF0000FF)
        # Should not raise
        self.entry.set_icon(ICON_ENTRY_PRIMARY, pixbuf)

    def test_set_icon_invalid_argument(self):
        """Test that set_icon raises ValueError for non-pixbuf."""
        with self.assertRaises(ValueError):
            self.entry.set_icon(ICON_ENTRY_PRIMARY, "not a pixbuf")

    def test_remove_icon(self):
        """Test removing an icon."""
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 16, 16)
        self.entry.set_icon(ICON_ENTRY_PRIMARY, pixbuf)
        # Should not raise
        self.entry.remove_icon(ICON_ENTRY_PRIMARY)

    def test_remove_icon_when_none_set(self):
        """Test removing icon when no icon is set."""
        # Should not raise
        self.entry.remove_icon(ICON_ENTRY_PRIMARY)
        self.entry.remove_icon(ICON_ENTRY_SECONDARY)

    def test_add_clear_button(self):
        """Test adding a clear button."""
        self.entry.add_clear_button()
        self.assertTrue(self.entry._clear_button_added)

    def test_add_clear_button_idempotent(self):
        """Test that calling add_clear_button multiple times is safe."""
        self.entry.add_clear_button()
        self.entry.add_clear_button()
        self.entry.add_clear_button()
        self.assertTrue(self.entry._clear_button_added)

    def test_clear_button_hidden_when_empty(self):
        """Test clear button is hidden when entry is empty."""
        self.entry.set_text("")
        self.entry.add_clear_button()
        self.assertFalse(self.entry._clear_shown)

    def test_clear_button_shown_when_text(self):
        """Test clear button is shown when entry has text."""
        self.entry.set_text("hello")
        self.entry.add_clear_button()
        self.assertTrue(self.entry._clear_shown)

    def test_clear_button_toggles_on_text_change(self):
        """Test clear button visibility toggles with text changes."""
        self.entry.add_clear_button()
        self.assertFalse(self.entry._clear_shown)

        self.entry.set_text("some text")
        self.assertTrue(self.entry._clear_shown)

        self.entry.set_text("")
        self.assertFalse(self.entry._clear_shown)

    def test_show_hide_clear_button(self):
        """Test show/hide clear button methods directly."""
        self.assertFalse(self.entry._clear_shown)

        self.entry.show_clear_button()
        self.assertTrue(self.entry._clear_shown)

        self.entry.hide_clear_button()
        self.assertFalse(self.entry._clear_shown)

    def test_show_clear_button_idempotent(self):
        """Test that calling show_clear_button multiple times is safe."""
        self.entry.show_clear_button()
        self.entry.show_clear_button()
        self.assertTrue(self.entry._clear_shown)

    def test_hide_clear_button_idempotent(self):
        """Test that calling hide_clear_button multiple times is safe."""
        self.entry.hide_clear_button()
        self.entry.hide_clear_button()
        self.assertFalse(self.entry._clear_shown)

    def test_text_operations(self):
        """Test standard text operations work normally."""
        self.entry.set_text("hello world")
        self.assertEqual(self.entry.get_text(), "hello world")

        self.entry.set_text("")
        self.assertEqual(self.entry.get_text(), "")

    def test_icon_pressed_clears_text(self):
        """Test that pressing the secondary icon clears text."""
        self.entry.add_clear_button()
        self.entry.set_text("test text")
        self.assertTrue(self.entry._clear_shown)

        # Simulate the icon press callback
        self.entry._icon_pressed_cb(self.entry, ICON_ENTRY_SECONDARY)
        self.assertEqual(self.entry.get_text(), "")
        self.assertFalse(self.entry._clear_shown)

    def test_icon_pressed_primary_no_effect(self):
        """Test that pressing the primary icon does not clear text."""
        self.entry.add_clear_button()
        self.entry.set_text("test text")

        self.entry._icon_pressed_cb(self.entry, ICON_ENTRY_PRIMARY)
        self.assertEqual(self.entry.get_text(), "test text")

    def test_set_icon_from_name_invalid(self):
        """Test set_icon_from_name with non-existent icon name."""
        # Should log a warning but not crash
        self.entry.set_icon_from_name(ICON_ENTRY_PRIMARY, "nonexistent-icon-name-xyz")

    def test_key_controller_attached(self):
        """Test that the key event controller is attached."""
        controllers = []
        controller = self.entry.observe_controllers()
        n = controller.get_n_items()
        for i in range(n):
            controllers.append(type(controller.get_item(i)).__name__)
        self.assertIn("EventControllerKey", controllers)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestIconEntryEdgeCases(unittest.TestCase):
    """Test edge cases for IconEntry."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_unicode_text_with_clear(self):
        """Test clear button works with unicode text."""
        entry = IconEntry()
        entry.add_clear_button()

        unicode_texts = ["Hello 世界", "Café ñoño", "Русский язык"]
        for text in unicode_texts:
            entry.set_text(text)
            self.assertTrue(entry._clear_shown)
            self.assertEqual(entry.get_text(), text)

            entry._icon_pressed_cb(entry, ICON_ENTRY_SECONDARY)
            self.assertEqual(entry.get_text(), "")
            self.assertFalse(entry._clear_shown)

    def test_set_icon_both_positions(self):
        """Test setting icons at both positions."""
        entry = IconEntry()
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 16, 16)
        entry.set_icon(ICON_ENTRY_PRIMARY, pixbuf)
        entry.set_icon(ICON_ENTRY_SECONDARY, pixbuf)
        # Remove both
        entry.remove_icon(ICON_ENTRY_PRIMARY)
        entry.remove_icon(ICON_ENTRY_SECONDARY)

    def test_rapid_text_changes(self):
        """Test rapid text changes with clear button."""
        entry = IconEntry()
        entry.add_clear_button()

        for i in range(100):
            entry.set_text(f"text {i}")
            self.assertTrue(entry._clear_shown)

        entry.set_text("")
        self.assertFalse(entry._clear_shown)

    def test_changed_signal_emission(self):
        """Test that changed signal fires normally."""
        entry = IconEntry()
        changed_count = 0

        def on_changed(widget):
            nonlocal changed_count
            changed_count += 1

        entry.connect("changed", on_changed)
        entry.set_text("test")
        self.assertEqual(changed_count, 1)

        entry.set_text("")
        self.assertEqual(changed_count, 2)

    def test_size_request(self):
        """Test that size request can be set."""
        entry = IconEntry()
        entry.set_size_request(300, -1)
        min_width = entry.get_size_request()[0]
        self.assertEqual(min_width, 300)

    def test_multiple_entries(self):
        """Test creating multiple IconEntry instances."""
        entries = [IconEntry() for _ in range(5)]
        for entry in entries:
            self.assertIsInstance(entry, IconEntry)
            entry.add_clear_button()
            entry.set_text("test")
            self.assertTrue(entry._clear_shown)


if __name__ == "__main__":
    unittest.main()
