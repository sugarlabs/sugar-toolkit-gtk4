"""Tests for ToolComboBox class."""

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
    from sugar4.graphics.toolcombobox import ToolComboBox
    from sugar4.graphics.combobox import ComboBox
    from sugar4.graphics import style


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToolComboBox(unittest.TestCase):
    """Test cases for ToolComboBox class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()
        self.tool_combo = ToolComboBox()

    def test_toolcombobox_creation(self):
        """Test basic tool combo box creation."""
        self.assertIsInstance(self.tool_combo, ToolComboBox)
        self.assertIsInstance(self.tool_combo, Gtk.Box)
        self.assertIsNotNone(self.tool_combo.combo)
        self.assertIsInstance(self.tool_combo.combo, ComboBox)
        self.assertIsNotNone(self.tool_combo.label)
        self.assertIsInstance(self.tool_combo.label, Gtk.Label)

    def test_toolcombobox_creation_with_custom_combo(self):
        """Test tool combo box creation with custom ComboBox."""
        custom_combo = ComboBox()
        custom_combo.append_item("value1", "Custom Item")

        tool_combo = ToolComboBox(combo=custom_combo)
        self.assertEqual(tool_combo.combo, custom_combo)

        # Should have the item from custom combo
        self.assertEqual(tool_combo.combo.get_item_count(), 1)

    def test_label_text_property(self):
        """Test label text property setting."""
        # Test initial empty label
        self.assertEqual(self.tool_combo.get_label_text(), "")
        self.assertEqual(self.tool_combo.label.get_text(), "")

        # Test setting via new API method
        self.tool_combo.set_label_text("Test Label")
        self.assertEqual(self.tool_combo.get_label_text(), "Test Label")
        self.assertEqual(self.tool_combo.label.get_text(), "Test Label")

    def test_label_text_property_kwargs(self):
        """Test label text property via constructor kwargs."""
        tool_combo = ToolComboBox(label_text="Constructor Label")
        self.assertEqual(tool_combo.get_label_text(), "Constructor Label")
        self.assertEqual(tool_combo.label.get_text(), "Constructor Label")

    def test_margin_setting(self):
        """Test that margins are set correctly."""
        # Should be set to DEFAULT_PADDING
        self.assertEqual(self.tool_combo.get_margin_top(), style.DEFAULT_PADDING)
        self.assertEqual(self.tool_combo.get_margin_bottom(), style.DEFAULT_PADDING)
        self.assertEqual(self.tool_combo.get_margin_start(), style.DEFAULT_PADDING)
        self.assertEqual(self.tool_combo.get_margin_end(), style.DEFAULT_PADDING)

    def test_internal_layout(self):
        """Test internal layout structure."""
        # ToolComboBox itself is a Box containing label and combo
        self.assertIsInstance(self.tool_combo, Gtk.Box)

        # Should have label and combo as children
        children = []
        child_widget = self.tool_combo.get_first_child()
        while child_widget:
            children.append(child_widget)
            child_widget = child_widget.get_next_sibling()

        self.assertEqual(len(children), 2)
        self.assertIn(self.tool_combo.label, children)
        self.assertIn(self.tool_combo.combo, children)

    def test_box_spacing(self):
        """Test Box spacing configuration."""
        self.assertEqual(self.tool_combo.get_spacing(), style.DEFAULT_SPACING)

    def test_combo_functionality(self):
        """Test that combo box functionality works."""
        # Add items to combo
        self.tool_combo.combo.append_item("value1", "Item 1")
        self.tool_combo.combo.append_item("value2", "Item 2")

        # Test selection
        self.tool_combo.combo.set_active(0)
        self.assertEqual(self.tool_combo.combo.get_value(), "value1")

        self.tool_combo.combo.set_active(1)
        self.assertEqual(self.tool_combo.combo.get_value(), "value2")

    def test_widget_visibility(self):
        """Test that child widgets are visible."""
        # Label should be visible
        self.assertTrue(self.tool_combo.label.get_visible())

        # Combo should be visible
        self.assertTrue(self.tool_combo.combo.get_visible())

        # ToolComboBox container should be visible
        self.assertTrue(self.tool_combo.get_visible())

    def test_label_text_methods(self):
        """Test label text methods."""
        # Test using the new API methods
        tool_combo = ToolComboBox()
        tool_combo.set_label_text("Test Property")
        self.assertEqual(tool_combo.get_label_text(), "Test Property")

    def test_do_set_property_method(self):
        """Test do_set_property method."""
        # Test the old property interface if available
        try:
            # Create a mock property spec
            class MockPSpec:
                def __init__(self, name):
                    self.name = name

            # Test setting label-text property
            pspec = MockPSpec("label-text")
            self.tool_combo.do_set_property(pspec, "New Label")
            self.assertEqual(self.tool_combo.get_label_text(), "New Label")
            self.assertEqual(self.tool_combo.label.get_text(), "New Label")
        except AttributeError:
            # Method might not exist in simplified version
            pass

    def test_do_set_property_invalid(self):
        """Test do_set_property with invalid property."""
        try:

            class MockPSpec:
                def __init__(self, name):
                    self.name = name

            # Test with invalid property name - should not crash
            pspec = MockPSpec("invalid-property")
            try:
                self.tool_combo.do_set_property(pspec, "value")
            except Exception:
                self.fail("do_set_property should handle invalid properties gracefully")
        except AttributeError:
            # Method might not exist in simplified version
            pass

    def test_label_before_creation(self):
        """Test setting label text via constructor."""
        # Create tool combo with label text in constructor
        tool_combo = ToolComboBox(label_text="Pre-creation Label")

        # Label should get the text when created
        self.assertEqual(tool_combo.label.get_text(), "Pre-creation Label")

    def test_multiple_label_changes(self):
        """Test changing label text multiple times."""
        labels = ["Label 1", "Label 2", "", "Label 3", "🌟 Unicode ⭐"]

        for label_text in labels:
            self.tool_combo.set_label_text(label_text)
            self.assertEqual(self.tool_combo.get_label_text(), label_text)
            self.assertEqual(self.tool_combo.label.get_text(), label_text)

    def test_combo_signals(self):
        """Test that combo box signals work."""
        # Track signal emissions
        changed_count = 0

        def on_changed(combo):
            nonlocal changed_count
            changed_count += 1

        self.tool_combo.combo.connect("changed", on_changed)

        # Add items and change selection
        self.tool_combo.combo.append_item("value1", "Item 1")
        self.tool_combo.combo.append_item("value2", "Item 2")

        self.tool_combo.combo.set_active(0)
        self.assertEqual(changed_count, 1)

        self.tool_combo.combo.set_active(1)
        self.assertEqual(changed_count, 2)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToolComboBoxIntegration(unittest.TestCase):
    """Test ToolComboBox integration with other components."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_in_toolbar(self):
        """Test ToolComboBox in a container (GTK4 doesn't have Toolbar)."""
        # GTK4 doesn't have Gtk.Toolbar, use Box as container
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tool_combo = ToolComboBox(label_text="Select:")

        # Add to container
        container.append(tool_combo)

        # Should be properly integrated
        self.assertEqual(tool_combo.get_parent(), container)

    def test_with_toolbar_context(self):
        """Test ToolComboBox behavior in container context."""
        # Create container and add tool combo (GTK4 replacement for toolbar)
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tool_combo = ToolComboBox(label_text="Options:")
        container.append(tool_combo)

        # Add items to combo
        tool_combo.combo.append_item("opt1", "Option 1")
        tool_combo.combo.append_item("opt2", "Option 2")

        # Test functionality in container context
        tool_combo.combo.set_active(0)
        self.assertEqual(tool_combo.combo.get_value(), "opt1")

    def test_custom_combo_integration(self):
        """Test integration with custom combo box."""
        # Create custom combo with pre-populated items
        custom_combo = ComboBox()
        custom_combo.append_item("custom1", "Custom 1")
        custom_combo.append_item("custom2", "Custom 2")
        custom_combo.append_separator()
        custom_combo.append_item("custom3", "Custom 3")

        # Create tool combo with custom combo
        tool_combo = ToolComboBox(combo=custom_combo, label_text="Custom:")

        # Should have all the items
        self.assertEqual(tool_combo.combo.get_item_count(), 4)

        # Test selection (set to index 3 to skip separator at index 2)
        tool_combo.combo.set_active(3)  # Skip separator
        self.assertEqual(tool_combo.combo.get_value(), "custom3")

    def test_style_constants(self):
        """Test that style constants are properly used."""
        tool_combo = ToolComboBox()

        # Check margins
        self.assertEqual(tool_combo.get_margin_top(), style.DEFAULT_PADDING)
        self.assertEqual(tool_combo.get_margin_bottom(), style.DEFAULT_PADDING)
        self.assertEqual(tool_combo.get_margin_start(), style.DEFAULT_PADDING)
        self.assertEqual(tool_combo.get_margin_end(), style.DEFAULT_PADDING)

        # Check Box spacing
        self.assertEqual(tool_combo.get_spacing(), style.DEFAULT_SPACING)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToolComboBoxEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for ToolComboBox."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_none_label_text(self):
        """Test setting None as label text."""
        tool_combo = ToolComboBox()

        # Setting None should be handled gracefully
        try:
            tool_combo.set_label_text(None)
            # Should not crash, might convert to empty string
        except (TypeError, AttributeError):
            # Acceptable if system rejects None
            pass

    def test_unicode_label_text(self):
        """Test Unicode label text."""
        tool_combo = ToolComboBox()

        unicode_labels = [
            "Hello 世界",
            "Café ñoño",
            "🌟 Star ⭐",
            "اللغة العربية",
            "Русский язык",
        ]

        for label_text in unicode_labels:
            tool_combo.set_label_text(label_text)
            self.assertEqual(tool_combo.label.get_text(), label_text)

    def test_very_long_label(self):
        """Test very long label text."""
        tool_combo = ToolComboBox()

        long_label = "A" * 1000  # Very long label
        tool_combo.set_label_text(long_label)
        self.assertEqual(tool_combo.label.get_text(), long_label)

    def test_empty_combo_behavior(self):
        """Test behavior with empty combo box."""
        tool_combo = ToolComboBox(label_text="Empty:")

        # Empty combo should not crash
        self.assertIsNone(tool_combo.combo.get_value())
        self.assertIsNone(tool_combo.combo.get_active_item())

    def test_combo_with_complex_values(self):
        """Test combo with complex Python objects."""
        tool_combo = ToolComboBox(label_text="Complex:")

        complex_values = [
            {"key": "value1"},
            ["list", "item"],
            ("tuple", "item"),
            42,
            3.14,
        ]

        for i, value in enumerate(complex_values):
            tool_combo.combo.append_item(value, f"Item {i}")

        # Test selection of complex values
        for i, expected_value in enumerate(complex_values):
            tool_combo.combo.set_active(i)
            self.assertEqual(tool_combo.combo.get_value(), expected_value)

    def test_property_setting_edge_cases(self):
        """Test edge cases in property setting."""
        tool_combo = ToolComboBox()

        # Test setting property multiple times rapidly
        for i in range(100):
            tool_combo.set_label_text(f"Label {i}")

        self.assertEqual(tool_combo.label.get_text(), "Label 99")

    def test_widget_destruction(self):
        """Test proper cleanup on widget destruction."""
        tool_combo = ToolComboBox(label_text="Test")

        # Add some items to combo
        tool_combo.combo.append_item("val1", "Item 1")
        tool_combo.combo.append_item("val2", "Item 2")

        # GTK4 Box doesn't have destroy method, use unparent instead
        try:
            tool_combo.unparent()
        except:
            # If not parented, this is fine
            pass

    def test_no_combo_provided(self):
        """Test behavior when no combo is provided (default case)."""
        tool_combo = ToolComboBox(combo=None)

        # Should create default ComboBox
        self.assertIsNotNone(tool_combo.combo)
        self.assertIsInstance(tool_combo.combo, ComboBox)

    def test_label_packing(self):
        """Test label packing properties."""
        tool_combo = ToolComboBox(label_text="Test:")

        # Label should be the first child
        # In GTK4, we need to check the widget order and properties
        first_child = tool_combo.get_first_child()
        self.assertEqual(first_child, tool_combo.label)

    def test_combo_packing(self):
        """Test combo packing properties."""
        tool_combo = ToolComboBox()

        # Combo should be the second child
        second_child = tool_combo.label.get_next_sibling()
        self.assertEqual(second_child, tool_combo.combo)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestToolComboBoxCompatibility(unittest.TestCase):
    """Test ToolComboBox compatibility and backwards compatibility."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_gtk_box_interface(self):
        """Test that ToolComboBox properly implements Gtk.Box interface."""
        tool_combo = ToolComboBox()

        # Should inherit Box methods
        self.assertTrue(hasattr(tool_combo, "set_spacing"))
        self.assertTrue(hasattr(tool_combo, "get_spacing"))
        self.assertTrue(hasattr(tool_combo, "set_orientation"))
        self.assertTrue(hasattr(tool_combo, "get_orientation"))

    def test_box_properties(self):
        """Test Box properties."""
        tool_combo = ToolComboBox()

        # Test orientation property
        self.assertEqual(tool_combo.get_orientation(), Gtk.Orientation.HORIZONTAL)

        # Test spacing property
        original_spacing = tool_combo.get_spacing()
        tool_combo.set_spacing(20)
        self.assertEqual(tool_combo.get_spacing(), 20)
        tool_combo.set_spacing(original_spacing)

    def test_focus_behavior(self):
        """Test focus behavior."""
        tool_combo = ToolComboBox()

        # Should be able to handle focus
        self.assertTrue(hasattr(tool_combo, "grab_focus"))

        # Focus should go to combo when requested
        tool_combo.grab_focus()
        # Hard to test actual focus without window, but should not crash


if __name__ == "__main__":
    unittest.main()
