import unittest
from unittest.mock import Mock, patch
import sys
import os
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GdkPixbuf

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

from sugar4.graphics.objectchooser import (
    ObjectChooser,
    get_preview_pixbuf,
    FILTER_TYPE_GENERIC_MIME,
    FILTER_TYPE_ACTIVITY,
    FILTER_TYPE_MIME_BY_ACTIVITY,
)

# Mock PNG data for testing
MOCK_PNG_DATA = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAADMElEQVR4nOzVwQnAIBQFQYXff81RUkQCOyDj1YOPnbXWPmeTRef+/3O/OyBjzh3CD95BfqICMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMO0TAAD//2Anhf4QtqobAAAAAElFTkSuQmCC"
)


class TestGetPreviewPixbuf(unittest.TestCase):
    """Test cases for get_preview_pixbuf function."""

    def test_get_preview_pixbuf_empty_data(self):
        """Test with empty preview data."""
        result = get_preview_pixbuf(b"")
        self.assertIsNone(result)

        result = get_preview_pixbuf(b"abc")  # Too short
        self.assertIsNone(result)

    def test_get_preview_pixbuf_valid_png(self):
        """Test with valid PNG data."""
        result = get_preview_pixbuf(MOCK_PNG_DATA)
        self.assertIsInstance(result, GdkPixbuf.Pixbuf)

    def test_get_preview_pixbuf_base64_encoded(self):
        """Test with base64 encoded PNG data."""
        encoded_data = base64.b64encode(MOCK_PNG_DATA)
        result = get_preview_pixbuf(encoded_data)
        self.assertIsInstance(result, GdkPixbuf.Pixbuf)

    def test_get_preview_pixbuf_custom_dimensions(self):
        """Test with custom width and height."""
        result = get_preview_pixbuf(MOCK_PNG_DATA, width=50, height=50)
        self.assertIsInstance(result, GdkPixbuf.Pixbuf)
        # Note: actual size may be scaled to maintain aspect ratio

    def test_get_preview_pixbuf_invalid_data(self):
        """Test with invalid data."""
        result = get_preview_pixbuf(b"invalid_png_data_here")
        self.assertIsNone(result)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestObjectChooser(unittest.TestCase):
    """Test cases for ObjectChooser class."""

    def setUp(self):
        """Set up test fixtures."""
        if not Gtk.is_initialized():
            Gtk.init()

    def test_objectchooser_creation_no_parent(self):
        """Test ObjectChooser creation without parent."""
        chooser = ObjectChooser()
        self.assertEqual(chooser.get_parent_xid(), 0)
        self.assertIsNone(chooser.get_what_filter())
        self.assertIsNone(chooser.get_filter_type())
        self.assertFalse(chooser.get_show_preview())

    def test_objectchooser_creation_with_parent(self):
        """Test ObjectChooser creation with parent widget."""
        parent = Gtk.Box()
        chooser = ObjectChooser(parent=parent)
        self.assertIsNotNone(chooser.get_parent_xid())

    def test_objectchooser_creation_with_int_parent(self):
        """Test ObjectChooser creation with integer parent."""
        chooser = ObjectChooser(parent=12345)
        self.assertEqual(chooser.get_parent_xid(), 12345)

    def test_objectchooser_creation_with_filters(self):
        """Test ObjectChooser creation with various filters."""
        chooser = ObjectChooser(
            what_filter="image/*",
            filter_type=FILTER_TYPE_GENERIC_MIME,
            show_preview=True,
        )
        self.assertEqual(chooser.get_what_filter(), "image/*")
        self.assertEqual(chooser.get_filter_type(), FILTER_TYPE_GENERIC_MIME)
        self.assertTrue(chooser.get_show_preview())

    def test_objectchooser_invalid_filter_type(self):
        """Test ObjectChooser with invalid filter type."""
        with self.assertRaises(ValueError):
            ObjectChooser(filter_type="invalid_filter")

    def test_objectchooser_valid_filter_types(self):
        """Test ObjectChooser with all valid filter types."""
        valid_types = [
            FILTER_TYPE_GENERIC_MIME,
            FILTER_TYPE_ACTIVITY,
            FILTER_TYPE_MIME_BY_ACTIVITY,
        ]

        for filter_type in valid_types:
            chooser = ObjectChooser(filter_type=filter_type)
            self.assertEqual(chooser.get_filter_type(), filter_type)

    @patch("dbus.SessionBus")
    @patch("sugar4.datastore.datastore.get")
    def test_get_selected_object_none(self, mock_datastore_get, mock_bus):
        """Test get_selected_object when no object is selected."""
        chooser = ObjectChooser()
        result = chooser.get_selected_object()
        self.assertIsNone(result)
        mock_datastore_get.assert_not_called()

    @patch("dbus.SessionBus")
    @patch("sugar4.datastore.datastore.get")
    def test_get_selected_object_with_id(self, mock_datastore_get, mock_bus):
        """Test get_selected_object when object is selected."""
        mock_object = Mock()
        mock_datastore_get.return_value = mock_object

        chooser = ObjectChooser()
        chooser._object_id = "test_object_id"

        result = chooser.get_selected_object()
        self.assertEqual(result, mock_object)
        mock_datastore_get.assert_called_once_with("test_object_id")

    def test_cleanup(self):
        """Test cleanup method."""
        chooser = ObjectChooser()
        chooser._main_loop = Mock()
        chooser._main_loop.is_running.return_value = True
        chooser._bus = Mock()

        mock_main_loop = chooser._main_loop  # Save reference

        chooser._cleanup()

        mock_main_loop.quit.assert_called_once()  # Assert on saved reference
        self.assertIsNone(chooser._main_loop)
        self.assertIsNone(chooser._bus)

    def test_destroy(self):
        """Test destroy method."""
        chooser = ObjectChooser()
        chooser._cleanup = Mock()

        chooser.destroy()

        chooser._cleanup.assert_called_once()

    @patch("dbus.SessionBus")
    def test_chooser_response_callback(self, mock_bus):
        """Test chooser response callback."""
        chooser = ObjectChooser()
        chooser._chooser_id = "test_chooser_id"
        chooser._cleanup = Mock()

        # Test with matching chooser_id
        chooser._ObjectChooser__chooser_response_cb("test_chooser_id", "object_123")
        self.assertEqual(chooser.get_response_code(), Gtk.ResponseType.ACCEPT)
        self.assertEqual(chooser.get_object_id(), "object_123")
        chooser._cleanup.assert_called_once()

        # Test with non-matching chooser_id
        chooser._cleanup.reset_mock()
        chooser._ObjectChooser__chooser_response_cb("different_id", "object_456")
        chooser._cleanup.assert_not_called()

    @patch("dbus.SessionBus")
    def test_chooser_cancelled_callback(self, mock_bus):
        """Test chooser cancelled callback."""
        chooser = ObjectChooser()
        chooser._chooser_id = "test_chooser_id"
        chooser._cleanup = Mock()

        # Test with matching chooser_id
        chooser._ObjectChooser__chooser_cancelled_cb("test_chooser_id")
        self.assertEqual(chooser.get_response_code(), Gtk.ResponseType.CANCEL)
        chooser._cleanup.assert_called_once()

        # Test with non-matching chooser_id
        chooser._cleanup.reset_mock()
        chooser._ObjectChooser__chooser_cancelled_cb("different_id")
        chooser._cleanup.assert_not_called()

    @patch("dbus.SessionBus")
    def test_name_owner_changed_callback(self, mock_bus):
        """Test name owner changed callback."""
        chooser = ObjectChooser()
        chooser._cleanup = Mock()

        chooser._ObjectChooser__name_owner_changed_cb("service", "old", "new")
        self.assertEqual(chooser.get_response_code(), Gtk.ResponseType.CANCEL)
        chooser._cleanup.assert_called_once()


class TestObjectChooserIntegration(unittest.TestCase):
    """Integration tests for ObjectChooser (require mocking D-Bus)."""

    @patch("dbus.SessionBus")
    @patch("gi.repository.GObject.MainLoop")
    def test_run_method_success(self, mock_mainloop, mock_bus):
        """Test successful run method."""
        # Setup mocks
        mock_loop_instance = Mock()
        mock_mainloop.return_value = mock_loop_instance

        mock_bus_instance = Mock()
        mock_bus.return_value = mock_bus_instance

        mock_obj = Mock()
        mock_bus_instance.get_object.return_value = mock_obj

        mock_journal = Mock()
        mock_journal.ChooseObject.return_value = "chooser_123"

        with patch("dbus.Interface", return_value=mock_journal):
            chooser = ObjectChooser(what_filter="test_filter")
            chooser._cleanup = Mock()  # Prevent actual cleanup

            # Mock the main loop to exit immediately
            def mock_run():
                chooser._response_code = Gtk.ResponseType.ACCEPT

            mock_loop_instance.run.side_effect = mock_run

            result = chooser.run()

            self.assertEqual(result, Gtk.ResponseType.ACCEPT)
            mock_journal.ChooseObject.assert_called_once()

    @patch("dbus.SessionBus")
    @patch("gi.repository.GObject.MainLoop")
    def test_run_method_with_filter(self, mock_mainloop, mock_bus):
        """Test run method with filter type."""
        # Setup mocks
        mock_loop_instance = Mock()
        mock_mainloop.return_value = mock_loop_instance

        mock_bus_instance = Mock()
        mock_bus.return_value = mock_bus_instance

        mock_obj = Mock()
        mock_bus_instance.get_object.return_value = mock_obj

        mock_journal = Mock()
        mock_journal.ChooseObjectWithFilter.return_value = "chooser_456"

        with patch("dbus.Interface", return_value=mock_journal):
            chooser = ObjectChooser(
                what_filter="image/*",
                filter_type=FILTER_TYPE_GENERIC_MIME,
                show_preview=True,
            )
            chooser._cleanup = Mock()

            def mock_run():
                chooser._response_code = Gtk.ResponseType.CANCEL

            mock_loop_instance.run.side_effect = mock_run

            result = chooser.run()

            self.assertEqual(result, Gtk.ResponseType.CANCEL)
            mock_journal.ChooseObjectWithFilter.assert_called_once_with(
                0, "image/*", FILTER_TYPE_GENERIC_MIME, True
            )


if __name__ == "__main__":
    unittest.main()
