# Copyright (C) 2007, One Laptop Per Child
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
Tray
===============
Tray widgets for displaying collections of items with scrolling support.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import GObject, Gtk, Gdk
import logging
from sugar4.graphics import style
from sugar4.graphics.palette import ToolInvoker
from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics.icon import Icon

GRID_CELL_SIZE = style.GRID_CELL_SIZE
_PREVIOUS_PAGE = 0
_NEXT_PAGE = 1

# GTK4 compatibility for GObject properties
if not hasattr(GObject.ParamFlags, "READWRITE"):
    GObject.ParamFlags.READWRITE = (
        GObject.ParamFlags.WRITABLE | GObject.ParamFlags.READABLE
    )


class _TrayViewport(Gtk.ScrolledWindow):
    """
    Scrollable viewport implementation using ScrolledWindow.
    """

    __gproperties__ = {
        "scrollable": (bool, None, None, False, GObject.ParamFlags.READABLE),
        "can-scroll-prev": (bool, None, None, False, GObject.ParamFlags.READABLE),
        "can-scroll-next": (bool, None, None, False, GObject.ParamFlags.READABLE),
    }

    def __init__(self, orientation):
        super().__init__()

        self.orientation = orientation
        self._scrollable = False
        self._can_scroll_next = False
        self._can_scroll_prev = False

        # scrolled window for GTK4
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        else:
            self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # using Box instead of Toolbar for GTK4
        self.traybar = Gtk.Box(orientation=orientation)
        self.traybar.set_homogeneous(False)
        self.traybar.set_spacing(2)
        self.set_child(self.traybar)

        self.connect("notify::hadjustment", self._adjustment_changed_cb)
        self.connect("notify::vadjustment", self._adjustment_changed_cb)

        self.connect("notify::width-request", self._size_changed_cb)
        self.connect("notify::height-request", self._size_changed_cb)

    def scroll(self, direction):
        """Scroll the viewport in the specified direction."""
        if direction == _PREVIOUS_PAGE:
            self._scroll_previous()
        elif direction == _NEXT_PAGE:
            self._scroll_next()

    def scroll_to_item(self, item):
        """Scroll the viewport so that item will be visible."""
        if item not in self.get_children():
            logging.warning("Item not found in tray children")
            return

        # Get the item's allocation
        allocation = item.get_allocation()
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
            start = allocation.x
            stop = allocation.x + allocation.width
        else:
            adj = self.get_vadjustment()
            start = allocation.y
            stop = allocation.y + allocation.height

        # Scroll if needed
        if start < adj.get_value():
            adj.set_value(start)
        elif stop > adj.get_value() + adj.get_page_size():
            adj.set_value(stop - adj.get_page_size())

    def _scroll_next(self):
        """Scroll to next page."""
        allocation = self.get_allocation()
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
            new_value = adj.get_value() + allocation.width
            adj.set_value(min(new_value, adj.get_upper() - allocation.width))
        else:
            adj = self.get_vadjustment()
            new_value = adj.get_value() + allocation.height
            adj.set_value(min(new_value, adj.get_upper() - allocation.height))

    def _scroll_previous(self):
        """Scroll to previous page."""
        allocation = self.get_allocation()
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
            new_value = adj.get_value() - allocation.width
            adj.set_value(max(adj.get_lower(), new_value))
        else:
            adj = self.get_vadjustment()
            new_value = adj.get_value() - allocation.height
            adj.set_value(max(adj.get_lower(), new_value))

    def do_get_preferred_width(self):
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            return 0, -1  # Minimum 0, natural unlimited
        else:
            child_min, child_nat = self.traybar.get_preferred_size()
            return child_min.width, child_nat.width

    def do_get_preferred_height(self):
        if self.orientation == Gtk.Orientation.VERTICAL:
            return 0, -1  # Minimum 0, natural unlimited
        else:
            child_min, child_nat = self.traybar.get_preferred_size()
            return child_min.height, child_nat.height

    def do_get_property(self, pspec):
        if pspec.name == "scrollable":
            return self._scrollable
        elif pspec.name == "can-scroll-next":
            return self._can_scroll_next
        elif pspec.name == "can-scroll-prev":
            return self._can_scroll_prev

    def _size_changed_cb(self, widget, pspec):
        self._update_scrollable_state()

    def _update_scrollable_state(self):
        allocation = self.get_allocation()
        if allocation.width <= 1 and allocation.height <= 1:
            return

        traybar_min, traybar_nat = self.traybar.get_preferred_size()

        if self.orientation == Gtk.Orientation.HORIZONTAL:
            scrollable = traybar_nat.width > allocation.width
        else:
            scrollable = traybar_nat.height > allocation.height

        if scrollable != self._scrollable:
            self._scrollable = scrollable
            self.notify("scrollable")

    def _adjustment_changed_cb(self, widget, pspec):
        """Handle adjustment changes to update scroll button states."""
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
        else:
            adj = self.get_vadjustment()

        if not adj:
            return

        can_scroll_prev = adj.get_value() > adj.get_lower()
        if can_scroll_prev != self._can_scroll_prev:
            self._can_scroll_prev = can_scroll_prev
            self.notify("can-scroll-prev")

        can_scroll_next = (adj.get_value() + adj.get_page_size()) < adj.get_upper()
        if can_scroll_next != self._can_scroll_next:
            self._can_scroll_next = can_scroll_next
            self.notify("can-scroll-next")

    def get_children(self):
        """Get children of the traybar."""
        child = self.traybar.get_first_child()
        children = []
        while child:
            children.append(child)
            child = child.get_next_sibling()
        return children

    def add_item(self, item, index=-1):
        """Add item to traybar."""
        if index == -1:
            self.traybar.append(item)
        else:
            # GTK4 doesn't have direct index insertion, so we use reorder
            self.traybar.append(item)
            if index < len(self.get_children()) - 1:
                self.traybar.reorder_child_after(
                    item, self.get_children()[index - 1] if index > 0 else None
                )

    def remove_item(self, item):
        """Remove item from traybar."""
        self.traybar.remove(item)


class _TrayScrollButton(ToolButton):
    """Scroll button for tray navigation."""

    __gtype_name__ = "SugarTrayScrollButton"

    def __init__(self, icon_name, scroll_direction):
        super().__init__()

        self._viewport = None
        self._scroll_direction = scroll_direction

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

        self.icon = Icon(icon_name=icon_name, pixel_size=style.SMALL_ICON_SIZE)

        # set_child instead of set_icon_widget
        self.set_child(self.icon)

        self.connect("clicked", self._clicked_cb)

    def set_viewport(self, viewport):
        """Set the viewport this button controls."""
        self._viewport = viewport
        self._viewport.connect(
            "notify::scrollable", self._viewport_scrollable_changed_cb
        )

        if self._scroll_direction == _PREVIOUS_PAGE:
            self._viewport.connect(
                "notify::can-scroll-prev", self._viewport_can_scroll_dir_changed_cb
            )
            self.set_sensitive(self._viewport.props.can_scroll_prev)
        else:
            self._viewport.connect(
                "notify::can-scroll-next", self._viewport_can_scroll_dir_changed_cb
            )
            self.set_sensitive(self._viewport.props.can_scroll_next)

    def _viewport_scrollable_changed_cb(self, viewport, pspec):
        """Handle viewport scrollable state changes."""
        self.set_visible(self._viewport.props.scrollable)

    def _viewport_can_scroll_dir_changed_cb(self, viewport, pspec):
        """Handle scroll direction capability changes."""
        if self._scroll_direction == _PREVIOUS_PAGE:
            sensitive = self._viewport.props.can_scroll_prev
        else:
            sensitive = self._viewport.props.can_scroll_next
        self.set_sensitive(sensitive)

    def _clicked_cb(self, button):
        """Handle button click."""
        self._viewport.scroll(self._scroll_direction)

    viewport = property(fset=set_viewport)


ALIGN_TO_START = 0
ALIGN_TO_END = 1


class HTray(Gtk.Widget):
    """
    Horizontal tray widget with custom layout management.
    """

    __gtype_name__ = "SugarHTray"

    __gproperties__ = {
        "align": (
            int,
            None,
            None,
            0,
            1,
            ALIGN_TO_START,
            GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
        ),
        "drag-active": (bool, None, None, False, GObject.ParamFlags.READWRITE),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._drag_active = False
        self.align = kwargs.get("align", ALIGN_TO_START)

        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.set_parent(self)

        scroll_left = _TrayScrollButton("go-left", _PREVIOUS_PAGE)
        self._box.append(scroll_left)

        self._viewport = _TrayViewport(Gtk.Orientation.HORIZONTAL)
        self._box.append(self._viewport)
        self._viewport.set_hexpand(True)

        scroll_right = _TrayScrollButton("go-right", _NEXT_PAGE)
        self._box.append(scroll_right)

        scroll_left.viewport = self._viewport
        scroll_right.viewport = self._viewport

        if self.align == ALIGN_TO_END:
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            self._viewport.add_item(spacer, 0)

    def do_dispose(self):
        """Clean up widget on disposal."""
        if self._box:
            self._box.unparent()
        ## TODO: well could be a bug
        super().do_dispose()

    def do_measure(self, orientation, for_size):
        return self._box.measure(orientation, for_size)

    def do_size_allocate(self, width, height, baseline):
        self._box.allocate(width, height, baseline, None)

    def do_set_property(self, pspec, value):
        if pspec.name == "align":
            self.align = value
        elif pspec.name == "drag-active":
            self._set_drag_active(value)
        else:
            raise AssertionError(f"Unknown property: {pspec.name}")

    def do_get_property(self, pspec):
        if pspec.name == "align":
            return self.align
        elif pspec.name == "drag-active":
            return self._drag_active
        else:
            raise AssertionError(f"Unknown property: {pspec.name}")

    def _set_drag_active(self, active):
        if self._drag_active != active:
            self._drag_active = active
            if self._drag_active:
                # GTK4: Use CSS for background color changes
                self._viewport.add_css_class("drag-active")
            else:
                self._viewport.remove_css_class("drag-active")

    def get_drag_active(self):
        return self._drag_active

    def set_drag_active(self, active):
        self._set_drag_active(active)

    def get_children(self):
        children = self._viewport.get_children()
        if self.align == ALIGN_TO_END and children:
            return children[1:]  # Skip spacer
        return children

    def add_item(self, item, index=-1):
        if self.align == ALIGN_TO_END and index > -1:
            index += 1  # Account for spacer
        self._viewport.add_item(item, index)

    def remove_item(self, item):
        self._viewport.remove_item(item)

    def get_item_index(self, item):
        """Get index of item in tray."""
        children = self._viewport.get_children()
        try:
            index = children.index(item)
            if self.align == ALIGN_TO_END:
                index -= 1  # Account for spacer
            return index
        except ValueError:
            return -1

    def scroll_to_item(self, item):
        self._viewport.scroll_to_item(item)


class VTray(Gtk.Widget):
    """
    Vertical tray widget with custom layout management.
    """

    __gtype_name__ = "SugarVTray"

    __gproperties__ = {
        "align": (
            int,
            None,
            None,
            0,
            1,
            ALIGN_TO_START,
            GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
        ),
        "drag-active": (bool, None, None, False, GObject.ParamFlags.READWRITE),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._drag_active = False
        self.align = kwargs.get("align", ALIGN_TO_START)

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._box.set_parent(self)

        scroll_up = _TrayScrollButton("go-up", _PREVIOUS_PAGE)
        self._box.append(scroll_up)

        self._viewport = _TrayViewport(Gtk.Orientation.VERTICAL)
        self._box.append(self._viewport)
        self._viewport.set_vexpand(True)

        scroll_down = _TrayScrollButton("go-down", _NEXT_PAGE)
        self._box.append(scroll_down)

        scroll_up.viewport = self._viewport
        scroll_down.viewport = self._viewport

        if self.align == ALIGN_TO_END:
            spacer = Gtk.Box()
            spacer.set_vexpand(True)
            self._viewport.add_item(spacer, 0)

    def do_dispose(self):
        """Clean up widget on disposal."""
        if self._box:
            self._box.unparent()
        ## TODO: well could be a bug
        super().do_dispose()

    def do_measure(self, orientation, for_size):
        """Calculate size requirements."""
        return self._box.measure(orientation, for_size)

    def do_size_allocate(self, width, height, baseline):
        """Allocate size to child widgets."""
        self._box.allocate(width, height, baseline, None)

    def do_set_property(self, pspec, value):
        """Set property values."""
        if pspec.name == "align":
            self.align = value
        elif pspec.name == "drag-active":
            self._set_drag_active(value)
        else:
            raise AssertionError(f"Unknown property: {pspec.name}")

    def do_get_property(self, pspec):
        """Get property values."""
        if pspec.name == "align":
            return self.align
        elif pspec.name == "drag-active":
            return self._drag_active
        else:
            raise AssertionError(f"Unknown property: {pspec.name}")

    def _set_drag_active(self, active):
        """Set drag active state with visual feedback."""
        if self._drag_active != active:
            self._drag_active = active
            if self._drag_active:
                self._viewport.add_css_class("drag-active")
            else:
                self._viewport.remove_css_class("drag-active")

    def get_drag_active(self):
        """Get drag active state."""
        return self._drag_active

    def set_drag_active(self, active):
        """Set drag active state."""
        self._set_drag_active(active)

    def get_children(self):
        """Get tray children."""
        children = self._viewport.get_children()
        if self.align == ALIGN_TO_END and children:
            return children[1:]  # Skip spacer
        return children

    def add_item(self, item, index=-1):
        """Add item to tray."""
        if self.align == ALIGN_TO_END and index > -1:
            index += 1  # Account for spacer
        self._viewport.add_item(item, index)

    def remove_item(self, item):
        """Remove item from tray."""
        self._viewport.remove_item(item)

    def get_item_index(self, item):
        """Get index of item in tray."""
        children = self._viewport.get_children()
        try:
            index = children.index(item)
            if self.align == ALIGN_TO_END:
                index -= 1  # Account for spacer
            return index
        except ValueError:
            return -1

    def scroll_to_item(self, item):
        """Scroll to make item visible."""
        self._viewport.scroll_to_item(item)


class TrayButton(ToolButton):
    """A button for use in trays."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class _IconWidget(Gtk.Widget):
    """Widget for displaying tray icons."""

    __gtype_name__ = "SugarTrayIconWidget"

    def __init__(self, icon_name=None, xo_color=None):
        super().__init__()

        self._box = Gtk.Box()
        self._box.set_parent(self)

        self._icon = Icon(pixel_size=style.STANDARD_ICON_SIZE)
        if icon_name is not None:
            self.set_icon_name(icon_name)
        if xo_color is not None:
            self._icon.set_xo_color(xo_color)
        self._box.append(self._icon)

        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self._on_button_press)
        click_gesture.connect("released", self._on_button_release)
        self.add_controller(click_gesture)

    def set_icon_name(self, icon_name):
        # If icon_name is a path to a file, use it as file_name
        import os

        if icon_name and isinstance(icon_name, str) and os.path.isfile(icon_name):
            self._icon.set_file_name(icon_name)
            self._icon.set_icon_name(None)
        else:
            self._icon.set_icon_name(icon_name)
            self._icon.set_file_name(None)

    def get_icon_name(self):
        # Prefer icon_name, but if not set, return file_name
        name = self._icon.get_icon_name()
        if name:
            return name
        return self._icon.get_file_name()

    def do_dispose(self):
        """Clean up widget on disposal."""
        if self._box:
            self._box.unparent()
        ## TODO: Might be a bug
        super().do_dispose()

    def do_measure(self, orientation, for_size):
        return self._box.measure(orientation, for_size)

    def do_size_allocate(self, width, height, baseline):
        self._box.allocate(width, height, baseline, None)

    def do_snapshot(self, snapshot):
        """Render widget using snapshot-based drawing."""
        palette = (
            self.get_parent().palette if hasattr(self.get_parent(), "palette") else None
        )

        if palette and palette.is_up():
            width = self.get_width()
            height = self.get_height()

            # Use snapshot API for drawing background
            color = Gdk.RGBA()
            color.parse("#000000")
            snapshot.append_color(color, Graphene.Rect().init(0, 0, width, height))

        # Draw the child widget
        self.snapshot_child(self._box, snapshot)

    def _on_button_press(self, gesture, n_press, x, y):
        pass

    def _on_button_release(self, gesture, n_press, x, y):
        pass

    def get_icon(self):
        return self._icon

    def set_xo_color(self, xo_color):
        self._icon.set_xo_color(xo_color)

    def get_xo_color(self):
        return self._icon.get_xo_color()


class TrayIcon(Gtk.Button):
    """An icon for use in trays with palette support."""

    __gtype_name__ = "SugarTrayIcon"

    def __init__(self, icon_name=None, xo_color=None):
        super().__init__()

        self._icon_widget = _IconWidget()
        if icon_name is not None:
            self.set_icon_name(icon_name)
        if xo_color is not None:
            self.set_xo_color(xo_color)
        self.set_child(self._icon_widget)

        self._palette_invoker = ToolInvoker(self)

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

        self.connect("destroy", self.__destroy_cb)

    def __destroy_cb(self, icon):
        """Clean up on destruction."""
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def create_palette(self):
        """Create palette - override in subclasses."""
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.Property(type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        """Get the palette invoker."""
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        """Set the palette invoker."""
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker
    )

    def get_icon(self):
        return self._icon_widget.get_icon()

    def get_icon_name(self):
        return self._icon_widget.get_icon_name()

    def set_icon_name(self, icon_name):
        self._icon_widget.set_icon_name(icon_name)

    def get_xo_color(self):
        return self._icon_widget.get_xo_color()

    def set_xo_color(self, xo_color):
        self._icon_widget.set_xo_color(xo_color)

    icon = property(get_icon, None)


def _apply_tray_css():
    """Apply CSS styling for tray widgets.
    
    CSS styling is defined in sugar-gtk4.css (.drag-active class and 
    htray/vtray element styles) or sugar-artwork themes to avoid duplication.
    This function is kept for backward compatibility.
    """
    # CSS is now managed by the centralized theme loader
    # See: sugar4.graphics.theme.SugarThemeLoader
    pass


try:
    _apply_tray_css()
except Exception:
    pass  # Ignore if GTK is not available


if hasattr(HTray, "set_css_name"):
    HTray.set_css_name("htray")

if hasattr(VTray, "set_css_name"):
    VTray.set_css_name("vtray")
