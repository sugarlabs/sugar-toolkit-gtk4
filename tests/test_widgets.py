"""Tests for Sugar Activity Widgets module."""

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


class MockActivity:
    """Mock activity for testing."""

    def __init__(self):
        self.metadata = {
            "title": "Test Activity",
            "description": "Test description",
            "icon-color": "#FF0000,#00FF00",
        }
        self.max_participants = 5
        self._shared_activity = None
        self._signals = {}
        self._stop_buttons = []

    def get_stop_buttons(self):
        return self._stop_buttons

    def connect(self, signal, callback):
        if signal not in self._signals:
            self._signals[signal] = []
        self._signals[signal].append(callback)
        return len(self._signals[signal]) - 1

    def share(self):
        pass

    def close(self):
        pass

    def save(self):
        pass

    def set_title(self, title):
        pass

    def get_shared_activity(self):
        return self._shared_activity

    def add_stop_button(self, button):
        self._stop_buttons.append(button)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestActivityWidgets(unittest.TestCase):
    """Test cases for activity widgets."""

    def setUp(self):
        """Set up test fixtures."""
        self.activity = MockActivity()

    def test_activity_button_creation(self):
        """Test ActivityButton can be created."""
        from sugar4.activity.widgets import ActivityButton

        button = ActivityButton(self.activity)
        self.assertIsNotNone(button)
        self.assertEqual(button.props.tooltip, "Test Activity")

    def test_activity_toolbar_button_creation(self):
        """Test ActivityToolbarButton can be created."""
        from sugar4.activity.widgets import ActivityToolbarButton

        button = ActivityToolbarButton(self.activity)
        self.assertIsNotNone(button)

    def test_stop_button_creation(self):
        """Test StopButton can be created."""
        from sugar4.activity.widgets import StopButton

        button = StopButton(self.activity)
        self.assertIsNotNone(button)
        self.assertEqual(button.props.tooltip, "Stop")
        self.assertEqual(button.props.accelerator, "<Ctrl>Q")
        self.assertIn(button, self.activity.get_stop_buttons())

    def test_edit_buttons_creation(self):
        """Test edit buttons can be created."""
        from sugar4.activity.widgets import (
            UndoButton,
            RedoButton,
            CopyButton,
            PasteButton,
        )

        undo = UndoButton()
        self.assertIsNotNone(undo)
        self.assertEqual(undo.props.tooltip, "Undo")
        self.assertEqual(undo.props.accelerator, "<Ctrl>Z")

        redo = RedoButton()
        self.assertIsNotNone(redo)
        self.assertEqual(redo.props.tooltip, "Redo")
        self.assertEqual(redo.props.accelerator, "<Ctrl>Y")

        copy = CopyButton()
        self.assertIsNotNone(copy)
        self.assertEqual(copy.props.tooltip, "Copy")
        self.assertEqual(copy.props.accelerator, "<Ctrl>C")

        paste = PasteButton()
        self.assertIsNotNone(paste)
        self.assertEqual(paste.props.tooltip, "Paste")
        self.assertEqual(paste.props.accelerator, "<Ctrl>V")

    def test_share_button_creation(self):
        """Test ShareButton can be created."""
        from sugar4.activity.widgets import ShareButton

        button = ShareButton(self.activity)
        self.assertIsNotNone(button)
        self.assertIsNotNone(button.private)
        self.assertIsNotNone(button.neighborhood)

    def test_share_button_single_participant(self):
        """Test ShareButton with single participant activity."""
        from sugar4.activity.widgets import ShareButton

        self.activity.max_participants = 1
        button = ShareButton(self.activity)
        self.assertFalse(button.props.sensitive)

    def test_title_entry_creation(self):
        """Test TitleEntry can be created."""
        from sugar4.activity.widgets import TitleEntry

        entry = TitleEntry(self.activity)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.entry.get_text(), "Test Activity")

    def test_title_entry_save_title(self):
        """Test TitleEntry save_title method."""
        from sugar4.activity.widgets import TitleEntry

        entry = TitleEntry(self.activity)
        entry.entry.set_text("New Title")
        entry.save_title(self.activity)
        self.assertEqual(self.activity.metadata["title"], "New Title")
        self.assertEqual(self.activity.metadata["title_set_by_user"], "1")

    def test_description_item_creation(self):
        """Test DescriptionItem can be created."""
        from sugar4.activity.widgets import DescriptionItem

        item = DescriptionItem(self.activity)
        self.assertIsNotNone(item)
        self.assertEqual(item.props.tooltip, "Description")

    def test_activity_toolbar_creation(self):
        """Test ActivityToolbar can be created."""
        from sugar4.activity.widgets import ActivityToolbar

        toolbar = ActivityToolbar(self.activity)
        self.assertIsNotNone(toolbar)
        self.assertIsNotNone(toolbar.share)
        self.assertIsNotNone(toolbar.title)

    def test_activity_toolbar_no_metadata(self):
        """Test ActivityToolbar with activity without metadata."""
        from sugar4.activity.widgets import ActivityToolbar

        activity_no_meta = MockActivity()
        activity_no_meta.metadata = None

        toolbar = ActivityToolbar(activity_no_meta)
        self.assertIsNotNone(toolbar)
        self.assertIsNotNone(toolbar.share)

    def test_edit_toolbar_creation(self):
        """Test EditToolbar can be created."""
        from sugar4.activity.widgets import EditToolbar

        toolbar = EditToolbar()
        self.assertIsNotNone(toolbar)
        self.assertIsNotNone(toolbar.undo)
        self.assertIsNotNone(toolbar.redo)
        self.assertIsNotNone(toolbar.copy)
        self.assertIsNotNone(toolbar.paste)
        self.assertIsNotNone(toolbar.separator)

    def test_create_activity_icon(self):
        """Test _create_activity_icon function."""
        from sugar4.activity.widgets import _create_activity_icon

        # Test with metadata
        icon = _create_activity_icon(self.activity.metadata)
        self.assertIsNotNone(icon)

        # Test with custom icon name
        icon = _create_activity_icon(self.activity.metadata, "test-icon")
        self.assertIsNotNone(icon)

        # Test with None metadata
        icon = _create_activity_icon(None)
        self.assertIsNotNone(icon)

    def test_activity_button_signal_connection(self):
        """Test ActivityButton signal connections."""
        from sugar4.activity.widgets import ActivityButton

        # Mock metadata object with connect method
        class MockMetadata(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._signals = {}

            def connect(self, signal, callback):
                if signal not in self._signals:
                    self._signals[signal] = []
                self._signals[signal].append(callback)

        self.activity.metadata = MockMetadata(self.activity.metadata)
        button = ActivityButton(self.activity)
        self.assertIsNotNone(button)

    def test_widgets_with_missing_methods(self):
        """Test widgets handle missing activity methods gracefully."""
        from sugar4.activity.widgets import StopButton, ShareButton

        # Create minimal activity mock
        minimal_activity = type(
            "MockActivity", (), {"metadata": {"title": "Test"}, "max_participants": 5}
        )()

        # These should not raise exceptions
        stop_button = StopButton(minimal_activity)
        self.assertIsNotNone(stop_button)

        share_button = ShareButton(minimal_activity)
        self.assertIsNotNone(share_button)


@unittest.skipUnless(GTK_AVAILABLE, "GTK4 not available")
class TestActivityWidgetsSignals(unittest.TestCase):
    """Test signal handling in activity widgets."""

    def setUp(self):
        """Set up test fixtures."""
        self.activity = MockActivity()
        self.signal_received = False
        self.signal_data = None

    def signal_handler(self, *args):
        """Generic signal handler for testing."""
        self.signal_received = True
        self.signal_data = args

    def test_title_entry_enter_signal(self):
        """Test TitleEntry enter-key-press signal."""
        from sugar4.activity.widgets import TitleEntry

        entry = TitleEntry(self.activity)
        entry.connect("enter-key-press", self.signal_handler)

        # Simulate enter key press
        entry.emit("enter-key-press")
        self.assertTrue(self.signal_received)

    def test_activity_toolbar_enter_signal(self):
        """Test ActivityToolbar enter-key-press signal."""
        from sugar4.activity.widgets import ActivityToolbar

        toolbar = ActivityToolbar(self.activity)
        toolbar.connect("enter-key-press", self.signal_handler)

        # Simulate enter key press
        toolbar.emit("enter-key-press")
        self.assertTrue(self.signal_received)


class TestActivityWidgetsWithoutGTK(unittest.TestCase):
    """Test that activity widgets can be imported without GTK."""

    def test_import_activity_widgets(self):
        """Test that activity widgets module can be imported."""
        try:
            from sugar4.activity import widgets

            self.assertTrue(hasattr(widgets, "ActivityButton"))
            self.assertTrue(hasattr(widgets, "EditToolbar"))
            self.assertTrue(hasattr(widgets, "ShareButton"))
        except ImportError:
            self.fail("Could not import sugar4.activity.widgets")


if __name__ == "__main__":
    unittest.main()
