# Copyright (C) 2009, Aleksey Lim
# Copyright (C) 2025 MostlyK
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
ToolbarBox
======================

The ToolbarBox provides a horizontal toolbar container for Sugar activities,
supporting both regular toolbar buttons and expandable toolbar sections.

"""

import math
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")

from gi.repository import Gtk, GObject, Gdk, Graphene
import logging

from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics.palettewindow import (
    PaletteWindow,
    ToolInvoker,
    _PaletteWindowWidget,
)
from sugar4.graphics import palettegroup
from sugar4.graphics import style

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolbarButton(ToolButton):
    """
    A toolbar button that can expand to show a toolbar page inline.

    This is the main difference from regular ToolButton - it can show
    an entire toolbar page when clicked, similar to a collapsible section.
    """

    __gtype_name__ = "SugarToolbarButton"

    def __init__(self, page=None, **kwargs):
        super().__init__(**kwargs)

        self.page_widget = None
        self._expanded = False

        self.set_page(page)

        self.connect("clicked", self._clicked_cb)
        self.connect("notify::parent", self._hierarchy_changed_cb)

        self.add_css_class("toolbar-expandable-button")

    def _clicked_cb(self, widget):
        self.set_expanded(not self.is_expanded())

    def _hierarchy_changed_cb(self, widget, pspec):
        parent = self.get_parent()
        if hasattr(parent, "owner"):
            if self.page_widget and self.get_root():
                self._unparent()
                parent.owner.append(self.page_widget)
                self.set_expanded(False)

    def get_toolbar_box(self):
        parent = self.get_parent()
        if not hasattr(parent, "owner"):
            return None
        return parent.owner

    toolbar_box = property(get_toolbar_box)

    def get_page(self):
        if self.page_widget is None:
            return None
        return _get_embedded_page(self.page_widget)

    def set_page(self, page):
        if page is None:
            self.page_widget = None
            return

        self.page_widget, alignment_ = _embed_page(_Box(self), page)
        self.page_widget.set_size_request(-1, style.GRID_CELL_SIZE)
        page.show()

        if self.get_palette() is None:
            self.set_palette(_ToolbarPalette(invoker=ToolInvoker(self)))
        self._move_page_to_palette()

    page = GObject.Property(type=object, getter=get_page, setter=set_page)

    def is_in_palette(self):
        palette = self.get_palette()
        return (
            self.page is not None
            and palette is not None
            and self.page_widget.get_parent() == palette._widget
        )

    def is_expanded(self):
        return self.page is not None and not self.is_in_palette()

    def popdown(self):
        palette = self.get_palette()
        if palette is not None:
            palette.popdown(immediate=True)

    def set_expanded(self, expanded):
        self.popdown()
        palettegroup.popdown_all()

        if self.page is None or self.is_expanded() == expanded:
            return

        if not expanded:
            self._move_page_to_palette()
            self._expanded = False
            self.remove_css_class("expanded")
            return

        box = self.toolbar_box
        if box is None:
            return

        if box.expanded_button is not None:
            box.expanded_button.set_expanded(False)
        box.expanded_button = self

        self._unparent()
        _setup_page(self.page_widget, style.COLOR_TOOLBAR_GREY, box.get_padding())
        box.append(self.page_widget)

        self._expanded = True
        self.add_css_class("expanded")

    def _move_page_to_palette(self):
        """Move the page widget to the palette."""
        if self.is_in_palette():
            return

        self._unparent()

        palette = self.get_palette()
        if isinstance(palette, _ToolbarPalette) and palette._widget:
            palette._widget.set_child(self.page_widget)

    def _unparent(self):
        """Remove the page widget from its current parent."""
        if self.page_widget is None:
            return
        page_parent = self.page_widget.get_parent()
        if page_parent is None:
            return

        if isinstance(page_parent, Gtk.Window):
            # For windows (like _PaletteWindowWidget), use set_child(None)
            page_parent.set_child(None)
        elif hasattr(page_parent, "remove"):
            # For containers that have remove method
            page_parent.remove(self.page_widget)
        else:
            # Fallback: try to unparent directly
            self.page_widget.unparent()

    def do_snapshot(self, snapshot):
        """GTK4 drawing implementation with arrow indicator."""
        Gtk.Widget.do_snapshot(self, snapshot)

        width = self.get_width()
        height = self.get_height()

        if width > 0 and height > 0:
            palette = self.get_palette()
            angle = (
                math.pi
                if (not self.is_expanded() or (palette is not None and palette.is_up()))
                else 0
            )

            self._paint_arrow(snapshot, width, height, angle)

    def _paint_arrow(self, snapshot, width, height, angle):
        """Paint the arrow indicator."""
        arrow_size = style.TOOLBAR_ARROW_SIZE / 2
        y = height - arrow_size
        x = (width - arrow_size) / 2

        rect = Graphene.Rect()
        rect.init(x, y, arrow_size, arrow_size)

        color = Gdk.RGBA()
        color.red = 0.5
        color.green = 0.5
        color.blue = 0.5
        color.alpha = 1.0

        snapshot.append_color(color, rect)


class ToolbarBox(Gtk.Box):
    """
    A container for toolbars that provides expandable toolbar sections.

    The ToolbarBox contains a main horizontal toolbar and can show
    expanded toolbar pages below it when ToolbarButtons are activated.
    """

    __gtype_name__ = "SugarToolbarBox"

    def __init__(self, padding=style.TOOLBOX_HORIZONTAL_PADDING):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._expanded_button_index = -1
        self._padding = padding

        self._toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._toolbar.owner = self
        # GTK4: Box doesn't have a "remove" signal, we'll handle removal differently

        self._toolbar_widget, self._toolbar_alignment = _embed_page(
            Gtk.Box(orientation=Gtk.Orientation.VERTICAL), self._toolbar
        )
        self.append(self._toolbar_widget)

        self._apply_styling()

    def _apply_styling(self):
        # Apply Sugar-toolkit CSS classes that are defined in sugar-gtk4.css
        # or sugar-artwork themes. The CSS is loaded centrally by the theme
        # loader to avoid duplication and maintain consistency with sugar-artwork.
        self.add_css_class("sugar-toolbarbox")

    def get_toolbar(self):
        return self._toolbar

    toolbar = property(get_toolbar)

    def get_expanded_button(self):
        if self._expanded_button_index == -1:
            return None
        return self._get_nth_toolbar_item(self._expanded_button_index)

    def set_expanded_button(self, button):
        if button is None:
            self._expanded_button_index = -1
            return

        index = self._get_toolbar_item_index(button)
        if index != -1:
            self._expanded_button_index = index
        else:
            self._expanded_button_index = -1

    expanded_button = property(get_expanded_button, set_expanded_button)

    def get_padding(self):
        return self._padding

    def set_padding(self, pad):
        self._padding = pad
        if self._toolbar_alignment:
            # GTK4: Use margins instead of alignment padding
            self._toolbar_alignment.set_margin_start(pad)
            self._toolbar_alignment.set_margin_end(pad)

    padding = GObject.Property(type=object, getter=get_padding, setter=set_padding)

    def _get_nth_toolbar_item(self, index):
        """Get the nth item from the toolbar."""
        child = self._toolbar.get_first_child()
        current_index = 0

        while child and current_index < index:
            child = child.get_next_sibling()
            current_index += 1

        return child

    def _get_toolbar_item_index(self, widget):
        """Get the index of a widget in the toolbar."""
        child = self._toolbar.get_first_child()
        index = 0

        while child:
            if child == widget:
                return index
            child = child.get_next_sibling()
            index += 1

        return -1

    def _remove_cb(self, sender, button):
        """Handle removal of toolbar items."""
        if not isinstance(button, ToolbarButton):
            return
        button.popdown()
        if button == self.expanded_button:
            if button.page_widget and button.page_widget.get_parent() == self:
                self.remove(button.page_widget)
            self._expanded_button_index = -1


class _ToolbarPalette(PaletteWindow):
    """
    A palette window specifically for toolbar buttons.

    This palette shows the toolbar page when the button is not expanded inline.
    """

    def __init__(self, **kwargs):
        # Remove invoker from kwargs before calling super().__init__
        invoker = kwargs.pop("invoker", None)
        super().__init__(**kwargs)
        self._has_focus = False

        group = palettegroup.get_group("default")
        group.connect("popdown", self._group_popdown_cb)
        self.set_group_id("toolbarbox")

        self._widget = _PaletteWindowWidget(self)
        self._widget.set_margin_start(0)
        self._widget.set_margin_end(0)
        self._widget.set_margin_top(0)
        self._widget.set_margin_bottom(0)
        self._setup_widget()

        self._widget.connect("realize", self._realize_cb)

        if invoker is not None:
            self.set_invoker(invoker)

    def set_primary_text(self, text):
        """Set primary text for the palette (required by ToolButton)."""
        # No-op for toolbar palettes
        pass

    def set_secondary_text(self, text):
        """Set secondary text for the palette (required by ToolButton)."""
        # No-op for toolbar palettes
        pass

    def get_expanded_button(self):
        return self.invoker.parent

    expanded_button = property(get_expanded_button)

    def on_invoker_enter(self):
        super().on_invoker_enter()
        self._set_focus(True)

    def on_invoker_leave(self):
        super().on_invoker_leave()
        self._set_focus(False)

    def on_enter(self):
        super().on_enter()
        self._set_focus(True)

    def on_leave(self):
        super().on_leave()
        self._set_focus(False)

    def _set_focus(self, new_focus):
        self._has_focus = new_focus
        if not self._has_focus:
            group = palettegroup.get_group("default")
            if not group.is_up():
                self.popdown()

    def _realize_cb(self, widget):
        display = widget.get_display()
        monitor = display.get_monitor_at_surface(widget.get_surface())
        if monitor:
            geometry = monitor.get_geometry()
            widget.set_size_request(geometry.width, -1)

    def popup(self, immediate=False):
        """Show the palette."""
        button = self.expanded_button
        if button and button.is_expanded():
            return
        if button and button.toolbar_box:
            _setup_page(
                button.page_widget, style.COLOR_BLACK, button.toolbar_box.get_padding()
            )
        super().popup(immediate)

    def _group_popdown_cb(self, group):
        """Handle group popdown event."""
        if not self._has_focus:
            self.popdown(immediate=True)


class _Box(Gtk.Box):
    """
    A container box for toolbar pages with custom drawing.
    """

    def __init__(self, toolbar_button):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._toolbar_button = toolbar_button

    def do_snapshot(self, snapshot):
        """Render palette using snapshot drawing."""
        Gtk.Widget.do_snapshot(self, snapshot)

        button_alloc = self._toolbar_button.get_allocation()
        my_width = self.get_width()

        if my_width > 0:
            color = Gdk.RGBA()
            color.red = 0.7
            color.green = 0.7
            color.blue = 0.7
            color.alpha = 1.0

            line_width = style.FOCUS_LINE_WIDTH * 2

            rect1 = Graphene.Rect()
            rect1.init(0, 0, button_alloc.x + style.FOCUS_LINE_WIDTH, line_width)
            snapshot.append_color(color, rect1)

            rect2 = Graphene.Rect()
            rect2.init(
                button_alloc.x + button_alloc.width - style.FOCUS_LINE_WIDTH,
                0,
                my_width
                - (button_alloc.x + button_alloc.width - style.FOCUS_LINE_WIDTH),
                line_width,
            )
            snapshot.append_color(color, rect2)


def _setup_page(page_widget, color, hpad):
    if not page_widget:
        return

    # margins instead of padding
    child = page_widget.get_first_child()
    if child:
        child.set_margin_start(hpad)
        child.set_margin_end(hpad)

    page = _get_embedded_page(page_widget)
    if page:
        # Apply background color to page dynamically
        # Note: This uses a dynamic color, so we keep this CSS generation
        # but could be improved by supporting theme variables
        css = f"""
        * {{
            background: {color.get_css_rgba()};
        }}
        """
        style.apply_css_to_widget(page, css)


def _embed_page(page_widget, page):
    page.show()

    # Box instead of Alignment
    container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    container.set_hexpand(True)
    # Prevent the embedded toolbar/page container from expanding vertically.
    # The toolbar should not absorb extra vertical space; keep it compact.
    container.set_vexpand(False)
    container.append(page)
    container.show()

    page_widget.append(container)
    page_widget.show()

    return (page_widget, container)


def _get_embedded_page(page_widget):
    if not page_widget:
        return None
    child = page_widget.get_first_child()
    if child:
        return child.get_first_child()
    return None
