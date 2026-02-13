"""Tests for Activity class."""

import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gtk, Gdk, GLib

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

# Mock environment variables before importing sugar modules
os.environ.setdefault("SUGAR_BUNDLE_ID", "org.sugarlabs.TestActivity")
os.environ.setdefault("SUGAR_BUNDLE_NAME", "Test Activity")
os.environ.setdefault("SUGAR_BUNDLE_PATH", "/tmp/test_bundle")
os.environ.setdefault("SUGAR_ACTIVITY_ROOT", "/tmp/test_activity")

if GTK_AVAILABLE:
    from sugar4.activity.activity import (
        Activity,
        SimpleActivity,
        get_bundle_name,
        get_bundle_path,
        get_activity_root,
    )
    from sugar4.activity.activityhandle import ActivityHandle
    from sugar4.datastore.datastore import DSMetadata


class MockMetadata(DSMetadata):
    """Mock metadata object that extends DSMetadata for testing."""

    def __init__(self):
        properties = {
            "title": "Test Activity",
            "activity": "org.sugarlabs.TestActivity",
            "activity_id": "test-activity-123",
            "keep": "0",
            "preview": "",
            "share-scope": "private",
            "icon-color": "#FF0000,#00FF00",
            "launch-times": "1234567890",
            "spent-times": "0",
        }
        super().__init__(properties)


class MockJobject:
    """Mock journal object for testing."""

    def __init__(self):
        self.metadata = MockMetadata()
        self.file_path = ""
        self.object_id = "test-object-123"
        self._destroyed = False

    def destroy(self):
        self._destroyed = True


class MockDatastore:
    """Mock datastore for testing."""

    @staticmethod
    def create():
        return MockJobject()

    @staticmethod
    def get(object_id):
        jobject = MockJobject()
        jobject.object_id = object_id
        return jobject

    @staticmethod
    def write(
        jobject, transfer_ownership=False, reply_handler=None, error_handler=None
    ):
        if reply_handler:
            GLib.idle_add(reply_handler)

    @staticmethod
    def copy(jobject, mount_point):
        new_jobject = MockJobject()
        new_jobject.metadata.update(dict(jobject.metadata._properties))
        return new_jobject

    @staticmethod
    def delete(object_id):
        pass


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestActivity(unittest.TestCase):
    """Test cases for Activity functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Initialize GTK if not already done
        if not Gtk.is_initialized():
            Gtk.init()

        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.activity_root = os.path.join(self.temp_dir, "activity_root")
        os.makedirs(self.activity_root, exist_ok=True)

        # Mock environment
        os.environ["SUGAR_ACTIVITY_ROOT"] = self.activity_root

        self.handle = ActivityHandle("test-activity-123")
        self.handle.object_id = None
        self.handle.invited = False

        # Patch datastore
        self.datastore_patcher = patch(
            "sugar4.activity.activity.datastore", MockDatastore()
        )
        self.datastore_patcher.start()

        # Patch other dependencies
        self.bundle_patcher = patch("sugar4.activity.activity.get_bundle_instance")
        self.mock_bundle = self.bundle_patcher.start()
        mock_bundle_instance = Mock()
        mock_bundle_instance.get_icon.return_value = "activity-icon"
        mock_bundle_instance.get_max_participants.return_value = 4
        self.mock_bundle.return_value = mock_bundle_instance

        self.color_patcher = patch("sugar4.activity.activity.get_color")
        self.mock_color = self.color_patcher.start()
        mock_color_instance = Mock()
        mock_color_instance.to_string.return_value = "#FF0000,#00FF00"
        self.mock_color.return_value = mock_color_instance

        self.save_as_patcher = patch("sugar4.activity.activity.get_save_as")
        self.mock_save_as = self.save_as_patcher.start()
        self.mock_save_as.return_value = False

    def tearDown(self):
        """Clean up test fixtures."""
        self.datastore_patcher.stop()
        self.bundle_patcher.stop()
        self.color_patcher.stop()
        self.save_as_patcher.stop()

        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_activity_creation(self):
        """Test basic Activity creation."""
        activity = Activity(self.handle)
        self.assertIsNotNone(activity.get_id())
        self.assertIsInstance(activity.get_id(), str)
        self.assertEqual(activity.get_id(), "test-activity-123")
        self.assertIsInstance(activity.get_title(), str)
        self.assertFalse(activity.get_active())  # Default is False

    def test_activity_metadata(self):
        """Test activity metadata handling."""
        activity = Activity(self.handle)
        metadata = activity.get_metadata()
        # The get_metadata() method returns the DSMetadata object, not a dict
        # We need to check if it has dict-like behavior instead
        self.assertTrue(hasattr(metadata, "__getitem__"))
        self.assertTrue(hasattr(metadata, "__setitem__"))
        self.assertIn("title", metadata)
        self.assertIn("activity", metadata)

    def test_save_functionality(self):
        """Test activity save functionality."""
        activity = Activity(self.handle)

        original_write_file = activity.write_file
        activity.write_file = Mock(side_effect=NotImplementedError)

        # Test save - should handle NotImplementedError gracefully
        activity.save()

        # Should call write_file but handle the NotImplementedError
        activity.write_file.assert_called_once()

    def test_activity_title(self):
        """Test activity title setting."""
        activity = Activity(self.handle)
        activity.set_title("Test Activity Title")
        self.assertEqual(activity.get_title(), "Test Activity Title")

    def test_activity_active_state(self):
        """Test activity active state."""
        activity = Activity(self.handle)
        self.assertFalse(activity.get_active())

        activity.set_active(True)
        self.assertTrue(activity.get_active())

        activity.set_active(False)
        self.assertFalse(activity.get_active())

    def test_canvas_operations(self):
        """Test canvas setting and getting."""
        activity = Activity(self.handle)

        # Initially no canvas
        self.assertIsNone(activity.get_canvas())

        # Set the canvas
        label = Gtk.Label(label="Test Canvas")
        activity.set_canvas(label)
        self.assertEqual(activity.get_canvas(), label)

    def test_sharing_state(self):
        """Test activity sharing state."""
        activity = Activity(self.handle)
        self.assertFalse(activity.get_shared())
        self.assertIsNone(activity.get_shared_activity())

    def test_can_close(self):
        """Test activity close permission."""
        activity = Activity(self.handle)
        self.assertTrue(activity.can_close())

    def test_max_participants(self):
        """Test max participants property."""
        activity = Activity(self.handle)
        self.assertEqual(activity.get_max_participants(), 4)  # From mock

        activity.set_max_participants(8)
        self.assertEqual(activity.get_max_participants(), 8)

    def test_bundle_methods(self):
        """Test bundle-related methods."""
        activity = Activity(self.handle)
        self.assertEqual(activity.get_bundle_id(), "org.sugarlabs.TestActivity")

    def test_activity_root(self):
        """Test activity root directory."""
        activity = Activity(self.handle)
        root = activity.get_activity_root()
        self.assertEqual(root, get_activity_root())

    def test_busy_state(self):
        """Test busy/unbusy functionality."""
        activity = Activity(self.handle)

        activity.busy()
        self.assertEqual(activity._busy_count, 1)

        # Test nested busy
        activity.busy()
        self.assertEqual(activity._busy_count, 2)

        # Test unbusy
        remaining = activity.unbusy()
        self.assertEqual(remaining, 1)

        remaining = activity.unbusy()
        self.assertEqual(remaining, 0)

    def test_stop_buttons(self):
        """Test stop button management."""
        activity = Activity(self.handle)

        button = Gtk.Button()
        activity.add_stop_button(button)

        self.assertIn(button, activity._stop_buttons)

    def test_copy_functionality(self):
        """Test activity copy functionality."""
        activity = Activity(self.handle)

        activity.save = Mock()

        # Test copy
        activity.copy()

        # Should call save
        activity.save.assert_called_once()

    def test_read_write_file_not_implemented(self):
        """Test that read_file and write_file raise NotImplementedError."""
        activity = Activity(self.handle)

        with self.assertRaises(NotImplementedError):
            activity.read_file("/tmp/test.txt")

        with self.assertRaises(NotImplementedError):
            activity.write_file("/tmp/test.txt")

    def test_handle_view_source_not_implemented(self):
        """Test that handle_view_source raises NotImplementedError."""
        activity = Activity(self.handle)

        with self.assertRaises(NotImplementedError):
            activity.handle_view_source()

    def test_share_not_implemented(self):
        """Test that share raises NotImplementedError in GTK4 port."""
        activity = Activity(self.handle)

        with self.assertRaises(NotImplementedError):
            activity.share()

    def test_invite_functionality(self):
        """Test invite functionality."""
        activity = Activity(self.handle)
        activity.share = Mock()

        activity.invite("account_path", "contact_id")

        # Should add to invites queue and call share
        self.assertEqual(len(activity._invites_queue), 1)
        activity.share.assert_called_once_with(True)

    def test_notification_functionality(self):
        """Test notification functionality."""
        activity = Activity(self.handle)
        mock_app = Mock()
        activity.get_application = Mock(return_value=mock_app)

        # Test notification
        activity.notify_user("Test Summary", "Test Body")

        # Should call send_notification
        mock_app.send_notification.assert_called_once()

    def test_preview_generation_without_cairo(self):
        """Test preview generation when Cairo is not available."""
        with patch("sugar4.activity.activity.HAS_CAIRO", False):
            activity = Activity(self.handle)
            preview = activity.get_preview()
            self.assertIsNone(preview)

    def test_preview_generation_without_canvas(self):
        """Test preview generation when no canvas is set."""
        activity = Activity(self.handle)
        preview = activity.get_preview()
        self.assertIsNone(preview)

    def test_preview_returns_none_for_zero_size_canvas(self):
        """Test preview returns None when canvas has zero dimensions."""
        activity = Activity(self.handle)
        canvas = Gtk.Label(label="test")
        activity.set_canvas(canvas)
        # Canvas not realized → get_width()/get_height() return 0
        preview = activity.get_preview()
        self.assertIsNone(preview)

    def test_preview_returns_none_without_native(self):
        """Test preview returns None when canvas has no native ancestor."""
        activity = Activity(self.handle)
        canvas = Gtk.Label(label="test")
        activity.set_canvas(canvas)
        # Mock non-zero size but no native window
        with patch.object(canvas, "get_width", return_value=100), \
             patch.object(canvas, "get_height", return_value=100), \
             patch.object(canvas, "get_native", return_value=None):
            preview = activity.get_preview()
            self.assertIsNone(preview)

    def test_preview_returns_png_bytes(self):
        """Test preview returns valid PNG data via the GTK4 pipeline."""
        import cairo as _cairo

        activity = Activity(self.handle)
        canvas = Gtk.Label(label="test")
        activity.set_canvas(canvas)

        # Build a small real PNG to use as the fake texture output
        surf = _cairo.ImageSurface(_cairo.FORMAT_ARGB32, 80, 60)
        cr = _cairo.Context(surf)
        cr.set_source_rgb(0.2, 0.4, 0.8)
        cr.paint()
        del cr
        import io as _io
        buf = _io.BytesIO()
        surf.write_to_png(buf)
        fake_png = buf.getvalue()

        # Mock the GTK4 rendering pipeline:
        #   canvas.get_width/get_height → 80×60
        #   canvas.get_native() → mock native
        #   native.get_renderer() → mock renderer
        #   Gtk.WidgetPaintable.new() → mock paintable
        #   renderer.render_texture() → mock texture
        #   texture.save_to_png_bytes() → GLib.Bytes with our PNG
        mock_texture = MagicMock()
        mock_texture.save_to_png_bytes.return_value = GLib.Bytes.new(fake_png)

        mock_renderer = MagicMock()
        mock_renderer.render_texture.return_value = mock_texture

        mock_native = MagicMock()
        mock_native.get_renderer.return_value = mock_renderer

        mock_node = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.to_node.return_value = mock_node

        mock_paintable = MagicMock()

        with patch.object(canvas, "get_width", return_value=80), \
             patch.object(canvas, "get_height", return_value=60), \
             patch.object(canvas, "get_native", return_value=mock_native), \
             patch("sugar4.activity.activity.Gtk.WidgetPaintable") as wp_cls, \
             patch("sugar4.activity.activity.Gtk.Snapshot", return_value=mock_snapshot):
            wp_cls.new.return_value = mock_paintable

            preview = activity.get_preview()

        self.assertIsNotNone(preview)
        self.assertIsInstance(preview, bytes)
        # Valid PNG starts with the 8-byte PNG signature
        self.assertTrue(preview[:8] == b"\x89PNG\r\n\x1a\n")

    def test_session_management(self):
        """Test session management functionality."""
        activity = Activity(self.handle)

        # Activity should be registered with session
        session = activity._session
        self.assertIn(activity, session._activities)

    def test_resumed_activity(self):
        """Test resuming an activity from journal object."""
        self.handle.object_id = "test-object-123"

        activity = Activity(self.handle)

        # Should be marked as resumed
        self.assertTrue(activity._is_resumed)
        self.assertIsNotNone(activity._jobject)


class TestActivityWithoutGTK(unittest.TestCase):
    """Test cases that don't require GTK."""

    def setUp(self):
        """Set up test environment."""
        # Create the activity root directory if it doesn't exist
        activity_root = get_activity_root()
        os.makedirs(activity_root, exist_ok=True)

    def test_utility_functions(self):
        """Test utility functions."""
        # These should return strings from environment
        self.assertEqual(get_bundle_name(), "Test Activity")
        self.assertEqual(get_bundle_path(), "/tmp/test_bundle")

        # Activity root should be created if it doesn't exist
        root = get_activity_root()
        self.assertIsInstance(root, str)
        self.assertTrue(os.path.exists(root))


class TestActivitySession(unittest.TestCase):
    """Test activity session management."""

    def setUp(self):
        """Set up test fixtures."""
        from sugar4.activity.activity import _ActivitySession

        self.session = _ActivitySession()

    def test_session_creation(self):
        """Test session creation."""
        self.assertEqual(len(self.session._activities), 0)
        self.assertEqual(len(self.session._will_quit), 0)

    def test_activity_registration(self):
        """Test activity registration."""
        mock_activity = Mock()

        self.session.register(mock_activity)
        self.assertIn(mock_activity, self.session._activities)

    def test_activity_unregistration(self):
        """Test activity unregistration."""
        mock_activity = Mock()

        self.session.register(mock_activity)
        self.session.unregister(mock_activity)
        self.assertNotIn(mock_activity, self.session._activities)

    def test_quit_handling(self):
        """Test quit request handling."""
        mock_activity1 = Mock()
        mock_activity2 = Mock()

        self.session.register(mock_activity1)
        self.session.register(mock_activity2)

        # First activity wants to quit
        self.session.will_quit(mock_activity1, True)
        self.assertIn(mock_activity1, self.session._will_quit)

        # Second activity doesn't want to quit yet
        self.assertNotIn(mock_activity2, self.session._will_quit)


if __name__ == "__main__":
    unittest.main()
