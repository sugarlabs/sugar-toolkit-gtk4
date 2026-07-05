"""Tests for ComboBox class."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, Gio, GObject

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

if GTK_AVAILABLE:
    from sugar4.graphics.combobox import ComboBox, _ComboBoxItem


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
        self.assertIsInstance(self.combo, Gtk.Box)
        self.assertIsNotNone(self.combo._model)
        self.assertIsInstance(self.combo._model, Gio.ListStore)
        self.assertIsNotNone(self.combo._dropdown)
        self.assertIsInstance(self.combo._dropdown, Gtk.DropDown)

    def test_append_text_item(self):
        """Test appending text-only items."""
        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")

        self.assertEqual(self.combo._model.get_n_items(), 2)

        item0 = self.combo._model.get_item(0)
        self.assertEqual(item0.value, "value1")
        self.assertEqual(item0.text, "Text 1")
        self.assertFalse(item0.is_separator)

        item1 = self.combo._model.get_item(1)
        self.assertEqual(item1.value, "value2")
        self.assertEqual(item1.text, "Text 2")

    def test_append_item_with_icon_name(self):
        """Test appending items with icon names stores the icon_name."""
        self.combo.append_item("value1", "Text 1", icon_name="document-new")

        self.assertEqual(self.combo._model.get_n_items(), 1)
        item = self.combo._model.get_item(0)
        self.assertEqual(item.value, "value1")
        self.assertEqual(item.text, "Text 1")
        self.assertEqual(item.icon_name, "document-new")
        self.assertTrue(self.combo._has_icons)

    def test_append_item_with_file_name(self):
        """Test appending items with file names stores the file_name."""
        self.combo.append_item("value1", "Text 1", file_name="/tmp/icon.png")

        self.assertEqual(self.combo._model.get_n_items(), 1)
        item = self.combo._model.get_item(0)
        self.assertEqual(item.file_name, "/tmp/icon.png")
        self.assertTrue(self.combo._has_icons)

    def test_append_separator(self):
        """Test appending separators."""
        self.combo.append_item("value1", "Text 1")
        self.combo.append_separator()
        self.combo.append_item("value2", "Text 2")

        self.assertEqual(self.combo._model.get_n_items(), 3)

        sep = self.combo._model.get_item(1)
        self.assertTrue(sep.is_separator)

    def test_get_value(self):
        """Test getting selected value."""
        # Initially no selection
        self.assertIsNone(self.combo.get_value())

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

        self.assertEqual(self.combo.value, "test_value")

    def test_get_active_item(self):
        """Test getting active item row."""
        self.assertIsNone(self.combo.get_active_item())

        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")

        self.combo.set_active(0)
        row = self.combo.get_active_item()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "value1")
        self.assertEqual(row[1], "Text 1")

        self.combo.set_active(1)
        row = self.combo.get_active_item()
        self.assertEqual(row[0], "value2")
        self.assertEqual(row[1], "Text 2")

    def test_get_active(self):
        """Test get_active returns correct index."""
        self.assertEqual(self.combo.get_active(), -1)

        self.combo.append_item("v1", "T1")
        self.combo.append_item("v2", "T2")

        self.combo.set_active(0)
        self.assertEqual(self.combo.get_active(), 0)

        self.combo.set_active(1)
        self.assertEqual(self.combo.get_active(), 1)

    def test_set_active_deselect(self):
        """Test set_active(-1) deselects."""
        self.combo.append_item("v1", "T1")
        self.combo.set_active(0)
        self.assertEqual(self.combo.get_active(), 0)

        self.combo.set_active(-1)
        self.assertEqual(self.combo.get_active(), -1)
        self.assertIsNone(self.combo.get_value())

    def test_set_active_out_of_range(self):
        """Test set_active with out-of-range index deselects."""
        self.combo.append_item("v1", "T1")
        self.combo.set_active(99)
        self.assertEqual(self.combo.get_active(), -1)

    def test_remove_all(self):
        """Test removing all items."""
        self.combo.append_item("value1", "Text 1")
        self.combo.append_item("value2", "Text 2")
        self.combo.append_separator()

        self.assertEqual(self.combo._model.get_n_items(), 3)

        self.combo.remove_all()
        self.assertEqual(self.combo._model.get_n_items(), 0)
        self.assertIsNone(self.combo.get_value())
        self.assertFalse(self.combo._has_icons)

    def test_empty_combobox_behavior(self):
        """Test behavior with empty combobox."""
        self.assertIsNone(self.combo.get_value())
        self.assertIsNone(self.combo.get_active_item())
        self.assertEqual(self.combo.get_active(), -1)

    def test_gtype_name(self):
        """Test GType name."""
        self.assertEqual(ComboBox.__gtype_name__, "SugarComboBox")

    def test_changed_signal(self):
        """Test that changed signal fires on selection change."""
        changed_count = [0]

        def on_changed(combo):
            changed_count[0] += 1

        self.combo.connect("changed", on_changed)
        self.combo.append_item("test", "Test")
        self.combo.set_active(0)

        self.assertGreaterEqual(changed_count[0], 1)

    def test_dropdown_is_child(self):
        """Test that DropDown is a child of the Box."""
        child = self.combo.get_first_child()
        self.assertIsInstance(child, Gtk.DropDown)


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

        combo.append_item(None, "None Value")
        combo.set_active(0)
        self.assertIsNone(combo.get_value())

    def test_complex_values(self):
        """Test with complex Python objects as values."""
        combo = ComboBox()

        values = [
            {"key": "value"},
            ["list", "item"],
            ("tuple", "item"),
            42,
            3.14,
            True,
        ]

        for i, value in enumerate(values):
            combo.append_item(value, f"Item {i}")

        for i, expected_value in enumerate(values):
            combo.set_active(i)
            self.assertEqual(combo.get_value(), expected_value)

    def test_empty_text(self):
        """Test with empty text strings."""
        combo = ComboBox()

        combo.append_item("empty", "")
        combo.append_item("none_text", None)

        self.assertEqual(combo._model.get_n_items(), 2)

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

        self.assertEqual(combo._model.get_n_items(), len(unicode_texts))

        for i, expected_text in enumerate(unicode_texts):
            item = combo._model.get_item(i)
            self.assertEqual(item.text, expected_text)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestComboBoxItem(unittest.TestCase):
    """Test _ComboBoxItem GObject wrapper."""

    def setUp(self):
        if not Gtk.is_initialized():
            Gtk.init()

    def test_item_creation(self):
        """Test creating a _ComboBoxItem."""
        item = _ComboBoxItem(
            value="test", text="Test", icon_name="doc", is_separator=False
        )
        self.assertEqual(item.value, "test")
        self.assertEqual(item.text, "Test")
        self.assertEqual(item.icon_name, "doc")
        self.assertFalse(item.is_separator)

    def test_item_defaults(self):
        """Test _ComboBoxItem default values."""
        item = _ComboBoxItem()
        self.assertIsNone(item.value)
        self.assertEqual(item.text, "")
        self.assertEqual(item.icon_name, "")
        self.assertEqual(item.file_name, "")
        self.assertFalse(item.is_separator)

    def test_separator_item(self):
        """Test separator item creation."""
        item = _ComboBoxItem(is_separator=True)
        self.assertTrue(item.is_separator)

    def test_gtype_name(self):
        """Test _ComboBoxItem GType name."""
        self.assertEqual(_ComboBoxItem.__gtype_name__, "SugarComboBoxItem")


if __name__ == "__main__":
    unittest.main()
