"""Tests for Toolbox module."""

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

from sugar4.graphics.toolbox import Toolbox


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToolbox(unittest.TestCase):
    """Test cases for Toolbox class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()
        self.toolbox = Toolbox()

    def test_toolbox_creation(self):
        """Test basic toolbox creation."""
        self.assertIsInstance(self.toolbox, Gtk.Box)
        self.assertEqual(self.toolbox.get_orientation(), Gtk.Orientation.VERTICAL)
        self.assertEqual(self.toolbox.get_toolbar_count(), 0)

    def test_add_toolbar(self):
        """Test adding toolbars."""
        toolbar1 = Gtk.Box()
        toolbar2 = Gtk.Box()

        # Add first toolbar
        index1 = self.toolbox.add_toolbar("Edit", toolbar1)
        self.assertEqual(index1, 0)
        self.assertEqual(self.toolbox.get_toolbar_count(), 1)

        # Add second toolbar
        index2 = self.toolbox.add_toolbar("View", toolbar2)
        self.assertEqual(index2, 1)
        self.assertEqual(self.toolbox.get_toolbar_count(), 2)

    def test_toolbar_labels(self):
        """Test toolbar label management."""
        toolbar = Gtk.Box()
        self.toolbox.add_toolbar("Test Toolbar", toolbar)

        # Check initial label
        self.assertEqual(self.toolbox.get_toolbar_label(0), "Test Toolbar")

        # Change label
        self.toolbox.set_toolbar_label(0, "Modified Toolbar")
        self.assertEqual(self.toolbox.get_toolbar_label(0), "Modified Toolbar")

    def test_current_toolbar(self):
        """Test current toolbar management."""
        toolbar1 = Gtk.Box()
        toolbar2 = Gtk.Box()

        self.toolbox.add_toolbar("First", toolbar1)
        self.toolbox.add_toolbar("Second", toolbar2)

        # Initially first toolbar should be current
        self.assertEqual(self.toolbox.get_current_toolbar(), 0)

        # Switch to second toolbar
        self.toolbox.set_current_toolbar(1)
        self.assertEqual(self.toolbox.get_current_toolbar(), 1)

        # Test property access
        self.assertEqual(self.toolbox.current_toolbar, 1)
        self.toolbox.current_toolbar = 0
        self.assertEqual(self.toolbox.current_toolbar, 0)

    def test_remove_toolbar(self):
        """Test removing toolbars."""
        toolbar1 = Gtk.Box()
        toolbar2 = Gtk.Box()
        toolbar3 = Gtk.Box()

        self.toolbox.add_toolbar("First", toolbar1)
        self.toolbox.add_toolbar("Second", toolbar2)
        self.toolbox.add_toolbar("Third", toolbar3)

        self.assertEqual(self.toolbox.get_toolbar_count(), 3)

        # Remove middle toolbar
        self.toolbox.remove_toolbar(1)
        self.assertEqual(self.toolbox.get_toolbar_count(), 2)

        # Check remaining labels
        self.assertEqual(self.toolbox.get_toolbar_label(0), "First")
        self.assertEqual(self.toolbox.get_toolbar_label(1), "Third")

    def test_get_toolbar_at(self):
        """Test getting toolbar widget by index."""
        toolbar1 = Gtk.Box()
        toolbar2 = Gtk.Box()

        self.toolbox.add_toolbar("First", toolbar1)
        self.toolbox.add_toolbar("Second", toolbar2)

        # Get toolbars
        retrieved1 = self.toolbox.get_toolbar_at(0)
        retrieved2 = self.toolbox.get_toolbar_at(1)

        self.assertEqual(retrieved1, toolbar1)
        self.assertEqual(retrieved2, toolbar2)

        # Test invalid index
        self.assertIsNone(self.toolbox.get_toolbar_at(10))
        self.assertIsNone(self.toolbox.get_toolbar_at(-1))

    def test_toolbar_changed_signal(self):
        """Test current-toolbar-changed signal."""
        toolbar1 = Gtk.Box()
        toolbar2 = Gtk.Box()

        self.toolbox.add_toolbar("First", toolbar1)
        self.toolbox.add_toolbar("Second", toolbar2)

        signal_data = []

        def on_toolbar_changed(toolbox, page_num):
            signal_data.append(page_num)

        self.toolbox.connect("current-toolbar-changed", on_toolbar_changed)

        # Change toolbar
        self.toolbox.set_current_toolbar(1)

        # Check signal was emitted
        self.assertEqual(len(signal_data), 1)
        self.assertEqual(signal_data[0], 1)

    def test_index_validation(self):
        """Test index validation for toolbar operations."""
        toolbar = Gtk.Box()
        self.toolbox.add_toolbar("Test", toolbar)

        # Test invalid indices for set_current_toolbar
        with self.assertRaises(IndexError):
            self.toolbox.set_current_toolbar(5)

        with self.assertRaises(IndexError):
            self.toolbox.set_current_toolbar(-1)

        # Test invalid indices for remove_toolbar
        with self.assertRaises(IndexError):
            self.toolbox.remove_toolbar(5)

        with self.assertRaises(IndexError):
            self.toolbox.remove_toolbar(-1)

        # Test invalid indices for set_toolbar_label
        with self.assertRaises(IndexError):
            self.toolbox.set_toolbar_label(5, "Invalid")

        with self.assertRaises(IndexError):
            self.toolbox.set_toolbar_label(-1, "Invalid")

    def test_toolbar_label_invalid_index(self):
        """Test getting toolbar label with invalid index."""
        toolbar = Gtk.Box()
        self.toolbox.add_toolbar("Test", toolbar)

        # Test invalid indices return None
        self.assertIsNone(self.toolbox.get_toolbar_label(5))
        self.assertIsNone(self.toolbox.get_toolbar_label(-1))

    def test_empty_toolbox(self):
        """Test operations on empty toolbox."""
        # Empty toolbox should have 0 toolbars
        self.assertEqual(self.toolbox.get_toolbar_count(), 0)

        # Current toolbar should be -1 for empty toolbox
        self.assertEqual(self.toolbox.get_current_toolbar(), -1)

        # Invalid operations should raise IndexError
        with self.assertRaises(IndexError):
            self.toolbox.set_current_toolbar(0)

    def test_single_toolbar_tabs_hidden(self):
        """Test that tabs are hidden when there's only one toolbar."""
        toolbar = Gtk.Box()
        self.toolbox.add_toolbar("Single", toolbar)

        # With single toolbar, tabs should not be shown
        notebook = self.toolbox.get_notebook()
        self.assertFalse(notebook.get_show_tabs())

    def test_multiple_toolbar_tabs_shown(self):
        """Test that tabs are shown when there are multiple toolbars."""
        toolbar1 = Gtk.Box()
        toolbar2 = Gtk.Box()

        self.toolbox.add_toolbar("First", toolbar1)

        # Still only one toolbar
        notebook = self.toolbox.get_notebook()
        self.assertFalse(notebook.get_show_tabs())

        # Add second toolbar
        self.toolbox.add_toolbar("Second", toolbar2)

        # Now tabs should be shown
        self.assertTrue(notebook.get_show_tabs())

    def test_toolbox_styling(self):
        """Test that toolbox has correct CSS classes."""
        notebook = self.toolbox.get_notebook()
        separator = self.toolbox.get_separator()

        self.assertTrue(notebook.has_css_class("toolbox"))
        self.assertTrue(separator.has_css_class("toolbox-separator"))


class TestToolboxWithoutGTK(unittest.TestCase):
    """Test cases that work without GTK."""

    def test_toolbox_import(self):
        """Test that Toolbox can be imported."""
        from sugar4.graphics.toolbox import Toolbox

        self.assertTrue(hasattr(Toolbox, "__init__"))


if __name__ == "__main__":
    unittest.main()
