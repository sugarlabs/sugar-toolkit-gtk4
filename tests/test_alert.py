import unittest
from unittest.mock import Mock, patch
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sugar4.graphics.alert import (
    Alert,
    ConfirmationAlert,
    ErrorAlert,
    TimeoutAlert,
    NotifyAlert,
    _TimeoutAlert,
    _TimeoutIcon,
)


class TestAlert(unittest.TestCase):
    def setUp(self):
        self.alert = Alert()

    def test_alert_creation(self):
        """Test basic alert creation"""
        self.assertIsInstance(self.alert, Alert)
        self.assertIsInstance(self.alert, Gtk.Box)

    def test_title_property(self):
        """Test setting and getting title property"""
        test_title = "Test Title"
        self.alert.props.title = test_title
        self.assertEqual(self.alert.props.title, test_title)

    def test_msg_property(self):
        """Test setting and getting message property"""
        test_msg = "Test message"
        self.alert.props.msg = test_msg
        self.assertEqual(self.alert.props.msg, test_msg)

    def test_add_button(self):
        """Test adding buttons to alert"""
        button = self.alert.add_button(1, "Test Button")
        self.assertIsInstance(button, Gtk.Button)
        self.assertEqual(button.get_label(), "Test Button")

    def test_remove_button(self):
        """Test removing buttons from alert"""
        self.alert.add_button(1, "Test Button")
        self.alert.remove_button(1)
        self.assertNotIn(1, self.alert._buttons)

    def test_add_entry(self):
        """Test adding entry to alert"""
        entry = self.alert.add_entry()
        self.assertIsInstance(entry, Gtk.Entry)

    def test_response_signal(self):
        """Test response signal emission"""
        response_received = []

        def on_response(alert, response_id):
            response_received.append(response_id)

        self.alert.connect("response", on_response)
        self.alert._response(123)
        self.assertEqual(response_received, [123])


class TestConfirmationAlert(unittest.TestCase):
    def setUp(self):
        self.alert = ConfirmationAlert()

    def test_confirmation_alert_creation(self):
        """Test confirmation alert has OK and Cancel buttons"""
        self.assertIsInstance(self.alert, ConfirmationAlert)
        self.assertIn(Gtk.ResponseType.OK, self.alert._buttons)
        self.assertIn(Gtk.ResponseType.CANCEL, self.alert._buttons)


class TestErrorAlert(unittest.TestCase):
    def setUp(self):
        self.alert = ErrorAlert()

    def test_error_alert_creation(self):
        """Test error alert has OK button"""
        self.assertIsInstance(self.alert, ErrorAlert)
        self.assertIn(Gtk.ResponseType.OK, self.alert._buttons)


class TestTimeoutAlert(unittest.TestCase):
    def setUp(self):
        self.alert = TimeoutAlert(timeout=2)

    def test_timeout_alert_creation(self):
        """Test timeout alert creation"""
        self.assertIsInstance(self.alert, TimeoutAlert)
        self.assertIn(Gtk.ResponseType.OK, self.alert._buttons)
        self.assertIn(Gtk.ResponseType.CANCEL, self.alert._buttons)

    def tearDown(self):
        if hasattr(self.alert, "_timeout_sid"):
            from gi.repository import GLib

            GLib.source_remove(self.alert._timeout_sid)


class TestNotifyAlert(unittest.TestCase):
    def setUp(self):
        self.alert = NotifyAlert(timeout=2)

    def test_notify_alert_creation(self):
        """Test notify alert creation"""
        self.assertIsInstance(self.alert, NotifyAlert)
        self.assertIn(Gtk.ResponseType.OK, self.alert._buttons)

    def tearDown(self):
        if hasattr(self.alert, "_timeout_sid"):
            from gi.repository import GLib

            GLib.source_remove(self.alert._timeout_sid)


class TestTimeoutIcon(unittest.TestCase):
    def setUp(self):
        self.icon = _TimeoutIcon()

    def test_set_text_with_int(self):
        """Test set_text converts int to string (countdown passes integers)."""
        self.icon.set_text(5)
        self.assertEqual(self.icon._text, "5")
        self.assertIsInstance(self.icon._text, str)

    def test_set_text_with_string(self):
        """Test set_text works with string input."""
        self.icon.set_text("3")
        self.assertEqual(self.icon._text, "3")

    def test_do_snapshot_uses_graphene_rect(self):
        """Test do_snapshot creates Graphene.Rect instead of crashing."""
        from gi.repository import Graphene

        mock_snapshot = Mock()
        mock_cr = Mock()
        mock_snapshot.append_cairo.return_value = mock_cr

        with patch.object(self.icon, "get_width", return_value=48), \
             patch.object(self.icon, "get_height", return_value=48), \
             patch.object(self.icon, "get_style_context") as mock_ctx, \
             patch.object(self.icon, "create_pango_layout") as mock_layout:
            mock_color = Mock()
            mock_color.red = 1.0
            mock_color.green = 1.0
            mock_color.blue = 1.0
            mock_color.alpha = 1.0
            mock_ctx.return_value.get_color.return_value = mock_color
            mock_layout.return_value.get_pixel_size.return_value = (20, 14)

            self.icon.set_text("5")
            self.icon.do_snapshot(mock_snapshot)

        mock_snapshot.append_cairo.assert_called_once()
        arg = mock_snapshot.append_cairo.call_args[0][0]
        self.assertIsInstance(arg, Graphene.Rect)


if __name__ == "__main__":
    unittest.main()
