"""
Tests for PaletteGroup
"""

import unittest
from unittest.mock import Mock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sugar4.graphics.palettegroup import get_group, popdown_all, Group


class MockPalette:
    """Mock palette for testing."""

    def __init__(self, name="test_palette"):
        self.name = name
        self._is_up = False
        self.palette_state = "invoker"
        self._signals = {}

    def connect(self, signal, callback):
        if signal not in self._signals:
            self._signals[signal] = []
        self._signals[signal].append(callback)
        return len(self._signals[signal]) - 1

    def disconnect(self, handler_id):
        pass

    def emit(self, signal):
        if signal in self._signals:
            for callback in self._signals[signal]:
                callback(self)

    def is_up(self):
        return self._is_up

    def popdown(self, immediate=False):
        if self._is_up:
            self._is_up = False
            self.emit("popdown")

    def popup(self):
        if not self._is_up:
            self._is_up = True
            self.emit("popup")


class TestPaletteGroup(unittest.TestCase):

    def setUp(self):
        import sugar4.graphics.palettegroup as pg

        pg._groups.clear()

    def test_get_group(self):
        """Test getting/creating groups."""
        group1 = get_group("test1")
        group2 = get_group("test1")  # Should return same group
        group3 = get_group("test2")  # Should create new group

        self.assertIs(group1, group2)
        self.assertIsNot(group1, group3)
        self.assertIsInstance(group1, Group)

    def test_group_initialization(self):
        """Test Group initialization."""
        group = Group()
        self.assertFalse(group.is_up())
        self.assertIsNone(group.get_state())

    def test_add_remove_palette(self):
        """Test adding and removing palettes."""
        group = Group()
        palette = MockPalette("test")

        group.add(palette)
        self.assertIn(palette, group.get_palettes())
        self.assertIn(palette, group.get_sig_ids())

        group.remove(palette)
        self.assertNotIn(palette, group.get_palettes())
        self.assertNotIn(palette, group.get_sig_ids())

        group.remove(palette)

    def test_palette_coordination(self):
        """Test that palettes coordinate properly."""
        group = Group()
        palette1 = MockPalette("palette1")
        palette2 = MockPalette("palette2")

        group.add(palette1)
        group.add(palette2)

        palette1.popup()
        self.assertTrue(group.is_up())
        self.assertTrue(palette1.is_up())

        palette2.popup()
        self.assertTrue(group.is_up())
        self.assertFalse(palette1.is_up())
        self.assertTrue(palette2.is_up())

    def test_group_signals(self):
        """Test group signals."""
        group = Group()
        palette = MockPalette("test")
        group.add(palette)

        popup_called = False
        popdown_called = False

        def on_popup(g):
            nonlocal popup_called
            popup_called = True

        def on_popdown(g):
            nonlocal popdown_called
            popdown_called = True

        group.connect("popup", on_popup)
        group.connect("popdown", on_popdown)

        palette.popup()
        self.assertTrue(popup_called)

        palette.popdown()
        self.assertTrue(popdown_called)

    def test_get_state(self):
        """Test getting palette state."""
        group = Group()
        palette = MockPalette("test")
        palette.palette_state = "expanded"
        group.add(palette)

        # No state when palette is down
        self.assertIsNone(group.get_state())

        # Should return palette state when up
        palette._is_up = True
        self.assertEqual(group.get_state(), "expanded")

    def test_popdown_all(self):
        """Test popdown_all function."""
        group1 = get_group("group1")
        group2 = get_group("group2")

        palette1 = MockPalette("p1")
        palette2 = MockPalette("p2")

        group1.add(palette1)
        group2.add(palette2)

        palette1.popup()
        palette2.popup()

        self.assertTrue(palette1.is_up())
        self.assertTrue(palette2.is_up())

        popdown_all()

        self.assertFalse(palette1.is_up())
        self.assertFalse(palette2.is_up())


if __name__ == "__main__":
    unittest.main()
