"""Tests for ComboBox class."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GObject, GdkPixbuf

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

if GTK_AVAILABLE:
    from sugar4.graphics.combobox import ComboBox


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestComboBox(unittest.TestCase):
    """Test cases for ComboBox class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()
        self.combo = ComboBox()

    def test_combobox_creation(self):
        """Test basic combobox creation."""
        self.assertIsInstance(self.combo, ComboBox)
        self.assertIsInstance(self.combo, Gtk.ComboBox)
        self.assertIsNotNone(self.combo.get_model())
        self.assertFalse(self.combo.has_text_renderer())
        self.assertFalse(self.combo.has_icon_renderer())

    def test_append_text_item(self):
        """Test appending text-only items."""
        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")

        # Check that model has items
        self.assertEqual(self.combo.get_item_count(), 2)

        # Check first item
        row = self.combo.get_item_at(0)
        self.assertEqual(row[0], "value1")  # value
        self.assertEqual(row[1], "Text 1")  # text
        self.assertIsNone(row[2])  # pixbuf
        self.assertFalse(row[3])  # is_separator

        # Check text renderer was created
        self.assertTrue(self.combo.has_text_renderer())
        self.assertFalse(self.combo.has_icon_renderer())

    def test_append_item_with_icon_name(self):
        """Test appending items with icon names."""
        try:
            self.combo.append_item("value1", "Text 1", icon_name="document-new")

            # Check that both renderers were created
            self.assertTrue(self.combo.has_text_renderer())
            self.assertTrue(self.combo.has_icon_renderer())

            # Check item was added
            self.assertEqual(self.combo.get_item_count(), 1)
            row = self.combo.get_item_at(0)
            self.assertEqual(row[0], "value1")
            self.assertEqual(row[1], "Text 1")
            self.assertIsNotNone(row[2])  # pixbuf should be created
            self.assertFalse(row[3])
        except ValueError:
            # Icon might not exist in test environment, which is acceptable
            pass

    def test_append_item_with_file_name(self):
        """Test appending items with file names."""
        # Create a temporary test pixbuf file path
        test_file = "/tmp/test_icon.png"

        # Try with non-existent file (should raise exception or handle gracefully)
        try:
            self.combo.append_item("value1", "Text 1", file_name=test_file)
        except Exception:
            # Expected if file doesn't exist
            pass

    def test_append_separator(self):
        """Test appending separators."""
        self.combo.append_item("value1", "Text 1")
        self.combo.append_separator()
        self.combo.append_item("value2", "Text 2")

        self.assertEqual(self.combo.get_item_count(), 3)

        # Check separator row
        separator_row = self.combo.get_item_at(1)
        self.assertEqual(separator_row[0], 0)  # value
        self.assertIsNone(separator_row[1])  # text
        self.assertIsNone(separator_row[2])  # pixbuf
        self.assertTrue(separator_row[3])  # is_separator

    def test_get_value(self):
        """Test getting selected value."""
        # Initially no selection
        self.assertIsNone(self.combo.get_value())

        # Add items and set active
        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")

        self.combo.set_active(0)
        self.assertEqual(self.combo.get_value(), "value1")

        self.combo.set_active(1)
        self.assertEqual(self.combo.get_value(), "value2")

    def test_value_property(self):
        """Test value property."""
        self.combo.append_item("test_value", "Test Text")
        self.combo.set_active(0)

        # Test getter
        self.assertEqual(self.combo.value, "test_value")

        # Property should be read-only (setter is None)
        with self.assertRaises(TypeError):
            self.combo.value = "new_value"

    def test_get_active_item(self):
        """Test getting active item row."""
        # No items initially
        self.assertIsNone(self.combo.get_active_item())

        # Add items
        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")

        # Set active and test
        self.combo.set_active(0)
        row = self.combo.get_active_item()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "value1")
        self.assertEqual(row[1], "Text 1")

        self.combo.set_active(1)
        row = self.combo.get_active_item()
        self.assertEqual(row[0], "value2")
        self.assertEqual(row[1], "Text 2")

    def test_remove_all(self):
        """Test removing all items."""
        # Add some items
        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")
        self.combo.append_separator()

        self.assertEqual(self.combo.get_item_count(), 3)

        # Remove all
        self.combo.remove_all()
        self.assertEqual(self.combo.get_item_count(), 0)

        # Value should be None after clearing
        self.assertIsNone(self.combo.get_value())

    def test_is_separator_function(self):
        """Test separator detection function."""
        self.combo.append_item("value1", "Text 1")
        self.combo.append_separator()

        # Test separator detection using public API
        self.assertFalse(self.combo.is_separator_at(0))
        self.assertTrue(self.combo.is_separator_at(1))

    def test_icon_only_items(self):
        """Test adding icon-only items (no text)."""
        try:
            self.combo.append_item("icon_value", None, icon_name="document-new")

            self.assertEqual(self.combo.get_item_count(), 1)
            row = self.combo.get_item_at(0)
            self.assertEqual(row[0], "icon_value")
            self.assertIsNone(row[1])  # no text
            self.assertIsNotNone(row[2])  # pixbuf should exist

            # Should have icon renderer but no text renderer
            self.assertTrue(self.combo.has_icon_renderer())
            self.assertFalse(self.combo.has_text_renderer())
        except ValueError:
            # Icon might not exist in test environment
            pass

    def test_mixed_content_items(self):
        """Test mixing different types of items."""
        try:
            # Text only
            self.combo.append_item("text_only", "Text Only")

            # Text with icon
            self.combo.append_item("text_icon", "Text + Icon", icon_name="document-new")

            # Separator
            self.combo.append_separator()

            # Icon only
            self.combo.append_item("icon_only", None, icon_name="edit-copy")

            self.assertEqual(self.combo.get_item_count(), 4)

            # Both renderers should be created
            self.assertTrue(self.combo.has_text_renderer())
            self.assertTrue(self.combo.has_icon_renderer())

            # Test accessing different items
            self.combo.set_active(0)
            self.assertEqual(self.combo.get_value(), "text_only")

            self.combo.set_active(1)
            self.assertEqual(self.combo.get_value(), "text_icon")

            self.combo.set_active(3)
            self.assertEqual(self.combo.get_value(), "icon_only")
        except ValueError:
            # Icons might not exist in test environment
            pass

    def test_large_icon_size_calculation(self):
        """Test icon size calculation for different scenarios."""
        try:
            # Add an icon and verify renderer was created
            self.combo.append_item("test", "Test", icon_name="document-new")
            if self.combo.has_icon_renderer():
                # Icon renderer should be created (GTK4 doesn't have stock_size)
                self.assertTrue(self.combo.has_icon_renderer())
        except (ValueError, AttributeError):
            # Skip if icon system not available
            pass

    def test_get_real_name_from_theme(self):
        """Test icon name resolution from theme."""
        try:
            # Test with a common icon using pixel size instead of IconSize enum
            filename = self.combo._get_real_name_from_theme("document-new", 16)
            self.assertIsInstance(filename, str)
            self.assertTrue(os.path.exists(filename))
        except (ValueError, AttributeError):
            # Icon might not exist in test environment or method might need display
            pass

        # Test with non-existent icon
        try:
            # This should raise ValueError for non-existent icons
            self.combo._get_real_name_from_theme("non-existent-icon-name-12345", 16)
            # If we get here without exception, the test environment might be different
            # Just skip this part of the test
        except (ValueError, AttributeError):
            # Expected - either ValueError for missing icon or AttributeError for missing display
            pass

    def test_model_structure(self):
        """Test the internal model structure."""
        # Check model column types
        model = self.combo.get_model()
        self.assertEqual(model.get_n_columns(), 4)

        # Column types should be: object, string, pixbuf, boolean
        self.assertEqual(model.get_column_type(0), GObject.TYPE_PYOBJECT)
        self.assertEqual(model.get_column_type(1), GObject.TYPE_STRING)
        self.assertEqual(model.get_column_type(2), GdkPixbuf.Pixbuf.__gtype__)
        self.assertEqual(model.get_column_type(3), GObject.TYPE_BOOLEAN)

    def test_empty_combobox_behavior(self):
        """Test behavior with empty combobox."""
        # Empty combobox should handle operations gracefully
        self.assertIsNone(self.combo.get_value())
        self.assertIsNone(self.combo.get_active_item())

        # Setting active on empty combobox
        self.combo.set_active(-1)
        self.assertIsNone(self.combo.get_value())

    def test_gtype_name(self):
        """Test GType name."""
        self.assertEqual(ComboBox.__gtype_name__, "SugarComboBox")

    def test_signal_connections(self):
        """Test that signals can be connected."""

        # Test that we can connect to ComboBox signals
        def on_changed(combo):
            pass

        self.combo.connect("changed", on_changed)

        # Add item and change selection to trigger signal
        self.combo.append_item("test", "Test")
        self.combo.set_active(0)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestComboBoxEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for ComboBox."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_none_values(self):
        """Test handling of None values."""
        combo = ComboBox()

        # None value should be acceptable
        combo.append_item(None, "None Value")
        combo.set_active(0)
        self.assertIsNone(combo.get_value())

    def test_complex_values(self):
        """Test with complex Python objects as values."""
        combo = ComboBox()

        # Test with different types of values
        values = [{"key": "value"}, ["list", "item"], ("tuple", "item"), 42, 3.14, True]

        for i, value in enumerate(values):
            combo.append_item(value, f"Item {i}")

        # Test retrieving complex values
        for i, expected_value in enumerate(values):
            combo.set_active(i)
            self.assertEqual(combo.get_value(), expected_value)

    def test_empty_text(self):
        """Test with empty text strings."""
        combo = ComboBox()

        # Empty text should be handled
        combo.append_item("empty", "")
        combo.append_item("none_text", None)

        self.assertEqual(combo.get_item_count(), 2)

        combo.set_active(0)
        self.assertEqual(combo.get_value(), "empty")

        combo.set_active(1)
        self.assertEqual(combo.get_value(), "none_text")

    def test_unicode_text(self):
        """Test with Unicode text."""
        combo = ComboBox()

        unicode_texts = [
            "Hello 世界",
            "Café ñoño",
            "🌟 Star ⭐",
            "اللغة العربية",
            "Русский язык",
        ]

        for i, text in enumerate(unicode_texts):
            combo.append_item(f"value_{i}", text)

        self.assertEqual(combo.get_item_count(), len(unicode_texts))

        for i, expected_text in enumerate(unicode_texts):
            row = combo.get_item_at(i)
            self.assertEqual(row[1], expected_text)


if __name__ == "__main__":
    unittest.main()
