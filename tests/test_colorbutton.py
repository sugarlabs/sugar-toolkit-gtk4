import unittest
from unittest.mock import Mock, patch, MagicMock
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, GObject, Gtk

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sugar4.graphics.colorbutton import (
    ColorToolButton,
    _ColorButton,
    _add_accelerator,
    setup_accelerator,
)


class TestColorToolButton(unittest.TestCase):
    def test_creation(self):
        """Test basic ColorToolButton creation."""
        button = ColorToolButton()
        self.assertIsInstance(button, Gtk.Box)

    def test_creation_with_icon_name(self):
        """Test creation with custom icon name."""
        button = ColorToolButton(icon_name="color-preview")
        self.assertIsInstance(button, Gtk.Box)

    def test_set_get_color(self):
        """Test setting and getting color."""
        from gi.repository import Gdk

        button = ColorToolButton()
        color = Gdk.RGBA()
        color.red = 1.0
        color.green = 0.0
        color.blue = 0.5
        color.alpha = 1.0
        button.set_color(color)

        result = button.get_color()
        self.assertAlmostEqual(result.red, 1.0, places=2)
        self.assertAlmostEqual(result.green, 0.0, places=2)
        self.assertAlmostEqual(result.blue, 0.5, places=2)

    def test_set_get_accelerator(self):
        """Test setting and getting accelerator string."""
        button = ColorToolButton()
        button._accelerator = "<Ctrl>k"
        self.assertEqual(button.get_accelerator(), "<Ctrl>k")


class TestAddAccelerator(unittest.TestCase):
    def test_no_accelerator_is_noop(self):
        """Test _add_accelerator does nothing when no accelerator set."""
        button = Mock()
        button._accelerator = None
        _add_accelerator(button)
        button.get_root.assert_not_called()

    def test_no_root_is_noop(self):
        """Test _add_accelerator does nothing when widget has no root."""
        button = Mock()
        button._accelerator = "<Ctrl>k"
        button.get_root.return_value = None
        _add_accelerator(button)

    def test_accelerator_registers_action(self):
        """Test _add_accelerator creates Gio action and sets accel."""
        button = Mock(spec=[])
        button._accelerator = "<Ctrl>k"

        mock_app = Mock()
        mock_root = Mock()
        mock_root.get_application.return_value = mock_app

        button.get_root = Mock(return_value=mock_root)

        _add_accelerator(button)

        mock_app.add_action.assert_called_once()
        mock_app.set_accels_for_action.assert_called_once()

        action_call_args = mock_app.set_accels_for_action.call_args
        self.assertEqual(action_call_args[0][1], ["<Ctrl>k"])

    def test_accelerator_removes_previous_action(self):
        """Test _add_accelerator removes old action before adding new one."""
        button = Mock(spec=[])
        button._accelerator = "<Ctrl>k"
        button._accel_action_name = "old-action"

        mock_app = Mock()
        mock_root = Mock()
        mock_root.get_application.return_value = mock_app

        button.get_root = Mock(return_value=mock_root)

        _add_accelerator(button)

        mock_app.remove_action.assert_called_once_with("old-action")


class TestSetupAccelerator(unittest.TestCase):
    def test_connects_notify_root(self):
        """Test setup_accelerator connects to notify::root, not hierarchy-changed."""
        button = Mock()
        button._accelerator = None

        setup_accelerator(button)

        # Should connect to notify::root
        button.connect.assert_called_once()
        signal_name = button.connect.call_args[0][0]
        self.assertEqual(signal_name, "notify::root")

    def test_does_not_use_hierarchy_changed(self):
        """Test setup_accelerator does NOT use the removed hierarchy-changed signal."""
        button = Mock()
        button._accelerator = None

        setup_accelerator(button)

        for call in button.connect.call_args_list:
            signal_name = call[0][0]
            self.assertNotEqual(
                signal_name,
                "hierarchy-changed",
                "hierarchy-changed signal does not exist in GTK4",
            )


if __name__ == "__main__":
    unittest.main()
