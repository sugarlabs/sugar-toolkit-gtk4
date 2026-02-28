"""
Tests for Palette (GTK4)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GObject

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

from sugar4.graphics.palette import Palette, PaletteActionBar, _HeaderItem
from sugar4.graphics.palettewindow import (
    PaletteWindow,
    _PaletteWindowWidget,
    _PaletteMenuWidget,
    MouseSpeedDetector,
    Invoker,
    WidgetInvoker,
    CursorInvoker,
    ToolInvoker,
    TreeViewInvoker,
)
from sugar4.graphics.icon import Icon
from sugar4.graphics.palettemenu import PaletteMenuItem

pytestmark = pytest.mark.skipif(not GTK_AVAILABLE, reason="GTK4 not available")


def test_palette_creation():
    palette = Palette()
    assert isinstance(palette, Palette)
    assert isinstance(palette, PaletteWindow)


def test_primary_text_property():
    palette = Palette()
    palette.set_primary_text("Primary")
    assert palette.get_primary_text() == "Primary"
    palette.props.primary_text = "New Primary"
    assert palette.props.primary_text == "New Primary"


def test_secondary_text_property():
    palette = Palette()
    palette.set_secondary_text("Secondary")
    assert palette.get_secondary_text() == "Secondary"
    palette.props.secondary_text = "Another"
    assert palette.props.secondary_text == "Another"


def test_icon_property():
    palette = Palette()
    icon = Icon(icon_name="document-new")
    palette.set_icon(icon)
    assert palette.get_icon() == icon
    palette.set_icon(None)
    assert palette.get_icon() is None


def test_icon_visible_property():
    palette = Palette()
    palette.set_icon_visible(False)
    assert not palette.get_icon_visible()
    palette.set_icon_visible(True)
    assert palette.get_icon_visible()


def test_set_content_and_remove():
    palette = Palette()
    label = Gtk.Label(label="Content")
    palette.set_content(label)
    assert palette.get_content_widget() is label
    palette.set_content(None)
    assert palette.get_content_widget() is None


def test_menu_switching():
    palette = Palette()
    menu = palette.get_menu()
    assert isinstance(menu, _PaletteMenuWidget)
    menu2 = palette.get_menu()
    assert menu is menu2


def test_palette_action_bar():
    palette = Palette()
    bar = palette.action_bar
    assert isinstance(bar, PaletteActionBar)
    btn = bar.add_action("Test", icon_name="document-new")
    assert isinstance(btn, Gtk.Button)


def test_header_item():
    label = Gtk.Label(label="Header")
    header = _HeaderItem(label)
    assert header.get_child() is label


def test_accel_widget_update():
    palette = Palette()

    class DummyInvoker(GObject.GObject):
        class Props:
            widget = Gtk.Button()

        props = Props()

    palette.props.invoker = DummyInvoker()
    palette._update_accel_widget()  # Should not raise


def test_palette_signals():
    palette = Palette()
    activated = []

    def on_activate(pal):
        activated.append(True)

    palette.connect("activate", on_activate)
    palette.emit("activate")
    assert activated


def test_palette_popup_popdown():
    palette = Palette()
    palette.popup(immediate=True)
    palette.popdown(immediate=True)


def test_palette_menuitem_popdown():
    palette = Palette()
    menu = palette.get_menu()
    item = PaletteMenuItem(text_label="Test")
    menu.append(item)
    gesture = Gtk.GestureClick()
    item.add_controller(gesture)
    palette.popdown(immediate=True)


def test_palette_window_widget():
    widget = _PaletteWindowWidget()
    widget.set_accept_focus(True)
    assert widget.get_can_focus()
    widget.set_accept_focus(False)
    assert not widget.get_can_focus()


def test_palette_menu_widget():
    menu = _PaletteMenuWidget()
    btn = Gtk.Button(label="Test")
    menu.append(btn)
    assert btn in menu.get_children()
    menu.remove(btn)
    assert btn not in menu.get_children()


def test_mouse_speed_detector():
    detector = MouseSpeedDetector(10, 1)
    detector.start()
    detector.stop()


def test_invoker_properties():
    invoker = Invoker()
    invoker.set_cache_palette(False)
    assert not invoker.get_cache_palette()
    invoker.set_toggle_palette(True)
    assert invoker.get_toggle_palette()
    invoker.set_lock_palette(True)
    assert invoker.get_lock_palette()


def test_widget_invoker():
    btn = Gtk.Button()
    invoker = WidgetInvoker(widget=btn)
    assert invoker.get_widget() is btn
    invoker.set_widget(None)
    assert invoker.get_widget() is None


def test_cursor_invoker():
    box = Gtk.Box()
    invoker = CursorInvoker(parent=box)
    assert invoker.parent is box
    invoker.detach()
    assert invoker.parent is None


def test_tool_invoker():
    btn = Gtk.Button()
    invoker = ToolInvoker(parent=btn)
    assert invoker.get_tool() is not None


def test_tree_view_invoker():
    tree = Gtk.TreeView()
    invoker = TreeViewInvoker()
    invoker.attach_treeview(tree)
    invoker.detach()
