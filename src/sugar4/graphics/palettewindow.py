# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
# Copyright (C) 2011, Benjamin Berg <benjamin@sipsolutions.net>
# Copyright (C) 2011, Marco Pesenti Gritti <marco@marcopg.org>
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


import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gtk, GObject, GLib

from sugar4.graphics import palettegroup
from sugar4.graphics import animator
from sugar4.graphics import style
from sugar4.graphics.icon import CellRendererIcon
from sugar4.debug import debug_print


_pointer = None

# Route all palette debug output through the centralized helper so that it
# honours the SUGAR_DEBUG flag without sprinkling conditionals everywhere.
print = debug_print


def _get_pointer_position(widget):
    """Get pointer position relative to widget ."""
    global _pointer
    if _pointer is None:
        display = widget.get_display()
        seat = display.get_default_seat()
        _pointer = seat.get_pointer()

    native = widget.get_native()
    if not native:
        return (0, 0)

    surface = native.get_surface()
    if not surface:
        return (0, 0)

    try:
        device_position = surface.get_device_position(_pointer)
        return (device_position[1], device_position[2])  # x, y
    except Exception:
        return (0, 0)


def _calculate_gap(a, b):
    """Helper function to find the gap position and size of widget a"""
    gap = True

    if a.y + a.height == b.y:
        gap_side = Gtk.PositionType.BOTTOM
    elif a.x + a.width == b.x:
        gap_side = Gtk.PositionType.RIGHT
    elif a.x == b.x + b.width:
        gap_side = Gtk.PositionType.LEFT
    elif a.y == b.y + b.height:
        gap_side = Gtk.PositionType.TOP
    else:
        gap = False

    if gap:
        if gap_side == Gtk.PositionType.BOTTOM or gap_side == Gtk.PositionType.TOP:
            gap_start = min(a.width, max(0, b.x - a.x))
            gap_size = max(0, min(a.width, (b.x + b.width) - a.x) - gap_start)
        elif gap_side == Gtk.PositionType.RIGHT or gap_side == Gtk.PositionType.LEFT:
            gap_start = min(a.height, max(0, b.y - a.y))
            gap_size = max(0, min(a.height, (b.y + b.height) - a.y) - gap_start)

    if gap and gap_size > 0:
        return (gap_side, gap_start, gap_size)
    else:
        return False


class _PaletteMenuWidget(Gtk.Popover):
    """Palette menu widget using Popover."""

    __gtype_name__ = "SugarPaletteMenuWidget"

    __gsignals__ = {
        "enter-notify": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "leave-notify": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        super().__init__()

        # container for menu items
        self._menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._menu_box.set_spacing(2)
        self.set_child(self._menu_box)

        self._popup_position = (0, 0)
        self._entered = False
        self._mouse_in_palette = False
        self._mouse_in_invoker = False
        self._up = False
        self._invoker = None

        # Set up event controllers
        self._motion_controller = Gtk.EventControllerMotion()
        self._motion_controller.connect("enter", self._enter_notify_cb)
        self._motion_controller.connect("leave", self._leave_notify_cb)
        self._motion_controller.connect("motion", self._motion_notify_cb)
        self.add_controller(self._motion_controller)

        self._click_controller = Gtk.GestureClick()
        self._click_controller.connect("released", self._button_release_cb)
        self.add_controller(self._click_controller)

    def append(self, menu_item):
        """Add a menu item to the menu."""
        self._menu_box.append(menu_item)

    def remove(self, menu_item):
        """Remove a menu item from the menu."""
        self._menu_box.remove(menu_item)

    def get_children(self):
        """Get all menu items."""
        children = []
        child = self._menu_box.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()
        return children

    def set_accept_focus(self, focus):
        """Set whether the menu accepts focus."""
        self.set_can_focus(focus)

    def get_origin(self):
        """Get the origin position of the menu."""
        # TODO
        # we can't get top level, so keeping this for now
        return (0, 0)

    def move(self, x, y):
        """Set the popup position."""
        self._popup_position = (x, y)

    def set_transient_for(self, window):
        """Set the transient parent window."""
        pass  # Handled automatically by Popover in GTK4

    def set_invoker(self, invoker):
        """Set the invoker widget."""
        self._invoker = invoker

    def popup(self, invoker=None):
        """Show the menu."""
        if self._up:
            return

        self._invoker = invoker or self._invoker
        if self._invoker and hasattr(self._invoker, "_widget"):
            self.set_parent(self._invoker._widget)

        self._entered = False
        self._mouse_in_palette = False
        self._mouse_in_invoker = False

        super().popup()
        self._up = True

    def popdown(self):
        """Hide the menu."""
        if not self._up:
            return

        super().popdown()
        self._up = False

    # https://docs.gtk.org/gtk4/signal.EventControllerMotion.enter.html
    def _enter_notify_cb(self, controller, x, y):
        """Handle enter notify events."""
        self._mouse_in_palette = True
        self._reevaluate_state()

    def _leave_notify_cb(self, controller):
        """Handle leave notify events."""
        self._mouse_in_palette = False
        self._reevaluate_state()

    def _motion_notify_cb(self, controller, x, y):
        """Handle motion notify events."""
        if not self._invoker:
            return

        # Convert coordinates to root window coordinates
        try:
            native = self.get_native()
            if native and native.get_surface():
                surface = native.get_surface()
                device_position = surface.get_device_position(_pointer)  # type: ignore
                root_x, root_y = device_position[1], device_position[2]
            else:
                return
        except Exception:
            return

        rect = self._invoker.get_rect()
        in_invoker = (
            root_x >= rect.x
            and root_x < (rect.x + rect.width)
            and root_y >= rect.y
            and root_y < (rect.y + rect.height)
        )

        if in_invoker != self._mouse_in_invoker:
            self._mouse_in_invoker = in_invoker
            self._reevaluate_state()

    def _button_release_cb(self, gesture, n_press, x, y):
        """Handle button release events."""
        if not self._invoker:
            return False

        # Check if click is in invoker area
        try:
            native = self.get_native()
            if native and native.get_surface():
                surface = native.get_surface()
                device_position = surface.get_device_position(_pointer)  # type: ignore
                root_x, root_y = device_position[1], device_position[2]
            else:
                return False
        except Exception:
            return False

        rect = self._invoker.get_rect()
        in_invoker = (
            root_x >= rect.x
            and root_x < (rect.x + rect.width)
            and root_y >= rect.y
            and root_y < (rect.y + rect.height)
        )

        return in_invoker

    def _reevaluate_state(self):
        """Reevaluate mouse state and emit appropriate signals."""
        if self._entered:
            # If we previously advised that the mouse was inside, but now the
            # mouse is outside both the invoker and the palette, notify that
            # the mouse has left.
            if not self._mouse_in_palette and not self._mouse_in_invoker:
                self._entered = False
                self.emit("leave-notify")
        else:
            # If we previously advised that the mouse had left, but now the
            # mouse is inside either the palette or the invoker, notify that
            # the mouse has entered.
            if self._mouse_in_palette or self._mouse_in_invoker:
                self._entered = True
                self.emit("enter-notify")


class _PaletteWindowWidget(Gtk.Window):
    """Palette window widget with modern event handling."""

    __gtype_name__ = "SugarPaletteWindowWidget"

    __gsignals__ = {
        "enter-notify": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "leave-notify": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, palette=None):
        super().__init__()

        self._palette = palette
        self.set_decorated(False)
        self.set_resizable(False)

        # Apply palette styling
        self.add_css_class("palette")

        self._old_alloc = None
        self._invoker = None
        self._should_accept_focus = True

        # Set up event controllers for GTK4
        self._motion_controller = Gtk.EventControllerMotion()
        self._motion_controller.connect("enter", self._enter_notify_cb)
        self._motion_controller.connect("leave", self._leave_notify_cb)
        self.add_controller(self._motion_controller)

    def set_accept_focus(self, focus):
        """Set whether the window accepts focus."""
        self._should_accept_focus = focus
        self.set_can_focus(focus)

    def get_origin(self):
        """Get the origin position of the window."""
        # GTK4: Window position is managed by compositor
        return (0, 0)

    def do_measure(self, orientation, for_size):
        """Calculate size requirements for the palette window."""
        min_size, nat_size, min_baseline, nat_baseline = Gtk.Window.do_measure(
            self, orientation, for_size
        )

        label_width = 0
        if self._palette is not None and hasattr(self._palette, "get_label_width"):
            label_width = self._palette.get_label_width()

        if orientation == Gtk.Orientation.HORIZONTAL:
            size = max(
                nat_size, label_width + 2 * 6, style.GRID_CELL_SIZE * 3
            )  # 6 = border width
            return size, size, -1, -1

        return min_size, nat_size, min_baseline, nat_baseline

    def do_size_allocate(self, width, height, baseline):
        """Allocate size to the palette window and its children."""
        Gtk.Window.do_size_allocate(self, width, height, baseline)

        allocation = Gdk.Rectangle()
        allocation.x = 0
        allocation.y = 0
        allocation.width = width
        allocation.height = height

        if (
            self._old_alloc is None
            or self._old_alloc.x != allocation.x
            or self._old_alloc.y != allocation.y
            or self._old_alloc.width != allocation.width
            or self._old_alloc.height != allocation.height
        ):
            self.queue_draw()

        self._old_alloc = allocation

    def set_invoker(self, invoker):
        self._invoker = invoker

    def get_rect(self):
        """Get the rectangle occupied by this window."""
        rect = Gdk.Rectangle()
        rect.x = 0  # GTK4: Position managed by compositor
        rect.y = 0
        rect.width = self.get_width()
        rect.height = self.get_height()
        return rect

    def set_content(self, widget):
        """Set the main content widget for the palette window."""
        # Ensure _widget exists and is a Gtk.Window
        if not hasattr(self, "_widget") or self._widget is None:
            self._widget = Gtk.Window()
        self._widget.set_child(widget)

    def _enter_notify_cb(self, controller, x, y):
        """Handle enter notify events."""
        self.emit("enter-notify")

    def _leave_notify_cb(self, controller):
        """Handle leave notify events."""
        self.emit("leave-notify")

    def popup(self, invoker=None):
        """Show the window."""
        if self.get_visible():
            return
        print("PaletteWindow.popup called")
        self.present()

    def popdown(self):
        """Hide the window."""
        if not self.get_visible():
            return
        print("PaletteWindow.popdown called")
        self.set_visible(False)


class MouseSpeedDetector(GObject.GObject):
    """Detects mouse movement speed for palette activation."""

    __gsignals__ = {
        "motion-slow": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "motion-fast": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    _MOTION_SLOW = 1
    _MOTION_FAST = 2

    def __init__(self, delay, thresh):
        """Create MouseSpeedDetector object.

        Args:
            delay: delay in msec
            thresh: threshold in pixels (per tick of 'delay' msec)
        """
        super().__init__()

        self.parent = None
        self._threshold = thresh
        self._delay = delay
        self._state = None
        self._timeout_hid = None
        self._mouse_pos = None

    def start(self):
        """Start detecting mouse speed."""
        self.stop()

        if self.parent:
            self._mouse_pos = _get_pointer_position(self.parent)
            self._timeout_hid = GLib.timeout_add(self._delay, self._timer_cb)

    def stop(self):
        """Stop detecting mouse speed."""
        if self._timeout_hid is not None:
            GLib.source_remove(self._timeout_hid)
            self._timeout_hid = None
        self._state = None

    def _detect_motion(self):
        """Detect if the mouse has moved significantly."""
        if not self.parent or not self._mouse_pos:
            return False

        oldx, oldy = self._mouse_pos
        try:
            x, y = _get_pointer_position(self.parent)
        except Exception:
            return False

        self._mouse_pos = (x, y)

        dist2 = (oldx - x) ** 2 + (oldy - y) ** 2
        return dist2 > self._threshold**2

    def _timer_cb(self):
        """Timer callback to check mouse motion."""
        motion = self._detect_motion()
        if motion and self._state != self._MOTION_FAST:
            self.emit("motion-fast")
            self._state = self._MOTION_FAST
        elif not motion and self._state != self._MOTION_SLOW:
            self.emit("motion-slow")
            self._state = self._MOTION_SLOW

        return GLib.SOURCE_CONTINUE


class PaletteWindow(GObject.GObject):
    """Base class for palette windows."""

    __gsignals__ = {
        "popup": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "popdown": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._group_id = None
        self._invoker = None
        self._invoker_hids = []
        self._cursor_x = 0
        self._cursor_y = 0
        self._alignment = None
        self._up = False
        self._widget = None

        self._popup_anim = animator.Animator(0.5, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        self.set_group_id("default")

        self._mouse_detector = MouseSpeedDetector(200, 5)

    def _setup_widget(self):
        """Set up the widget with necessary connections."""
        if self._widget is not None:
            self._widget.connect("realize", self.__realize_cb)
            self._widget.connect("unrealize", self.__unrealize_cb)
            self._widget.connect("destroy", self.__destroy_cb)
            self._widget.connect("enter-notify", self.__enter_notify_cb)
            self._widget.connect("leave-notify", self.__leave_notify_cb)

        # Set up key event controller for GTK4
        self._key_controller = Gtk.EventControllerKey()
        self._key_controller.connect("key-pressed", self.__key_press_event_cb)
        if self._widget is not None:
            self._widget.add_controller(self._key_controller)

        self._set_effective_group_id(self._group_id)
        if self._widget is not None and hasattr(self._widget, "set_invoker"):
            self._widget.set_invoker(self._invoker)

        self._mouse_detector.connect("motion-slow", self._mouse_slow_cb)
        self._mouse_detector.parent = self._widget

    def _teardown_widget(self):
        """Clean up widget connections."""
        try:
            if self._widget is not None:
                self._widget.disconnect_by_func(self.__realize_cb)
                self._widget.disconnect_by_func(self.__unrealize_cb)
                self._widget.disconnect_by_func(self.__destroy_cb)
                self._widget.disconnect_by_func(self.__enter_notify_cb)
                self._widget.disconnect_by_func(self.__leave_notify_cb)

            if self._widget is not None and hasattr(self, "_key_controller"):
                self._widget.remove_controller(self._key_controller)
        except (TypeError, AttributeError):
            pass  # Already disconnected

        self._set_effective_group_id(None)

    def destroy(self):
        if self._widget is not None:
            self._widget.destroy()

    def __destroy_cb(self, palette):
        """Handle widget destruction."""
        try:
            self._mouse_detector.disconnect_by_func(self._mouse_slow_cb)
        except TypeError:
            pass  # Already disconnected

    def __realize_cb(self, widget):
        """Handle widget realization."""
        pass

    def __unrealize_cb(self, widget):
        """Handle widget unrealization."""
        pass

    def set_invoker(self, invoker):
        for hid in self._invoker_hids[:]:
            if self._invoker:
                self._invoker.disconnect(hid)
            self._invoker_hids.remove(hid)

        self._invoker = invoker
        if self._widget is not None and hasattr(self._widget, "set_invoker"):
            self._widget.set_invoker(invoker)

        if invoker is not None:
            self._invoker_hids.append(
                self._invoker.connect("mouse-enter", self._invoker_mouse_enter_cb)
            )
            self._invoker_hids.append(
                self._invoker.connect("mouse-leave", self._invoker_mouse_leave_cb)
            )
            self._invoker_hids.append(
                self._invoker.connect("right-click", self._invoker_right_click_cb)
            )
            self._invoker_hids.append(
                self._invoker.connect("toggle-state", self._invoker_toggle_state_cb)
            )

    def get_invoker(self):
        return self._invoker

    invoker = GObject.Property(type=object, getter=get_invoker, setter=set_invoker)

    def set_content(self, widget):
        """Set the main content widget for the palette window."""
        if self._widget is None:
            self._widget = _PaletteWindowWidget(self)
            self._setup_widget()
        self._widget.set_child(widget)

    def _mouse_slow_cb(self, widget):
        self._mouse_detector.stop()
        self._palette_do_popup()

    def _palette_do_popup(self):
        """Actually show the palette."""
        immediate = False

        if self.is_up():
            self._popdown_anim.stop()
            return

        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            if group and group.is_up():
                immediate = True
                group.popdown()

        self.popup(immediate=immediate)

    def is_up(self):
        return self._up

    def _set_effective_group_id(self, group_id):
        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            group.remove(self)
        if group_id:
            group = palettegroup.get_group(group_id)
            group.add(self)

    def set_group_id(self, group_id):
        self._set_effective_group_id(group_id)
        self._group_id = group_id

    def get_group_id(self):
        """Get the current group ID."""
        return self._group_id

    group_id = GObject.Property(type=str, getter=get_group_id, setter=set_group_id)

    def update_position(self):
        """Update the position of the palette."""
        invoker = self._invoker
        if invoker is None or self._alignment is None:
            logging.error("Cannot update the palette position.")
            return

        if self._widget is None:
            return

        # Get size request
        try:
            if hasattr(self._widget, "get_preferred_size"):
                minimum, natural = self._widget.get_preferred_size()  # type: ignore
                req = natural
            else:
                req = Gdk.Rectangle()
                req.width = style.GRID_CELL_SIZE * 3
                req.height = style.GRID_CELL_SIZE * 2
        except Exception:
            req = Gdk.Rectangle()
            req.width = style.GRID_CELL_SIZE * 3
            req.height = style.GRID_CELL_SIZE * 2

        # Handle menu widget size calculation
        if isinstance(self._widget, _PaletteMenuWidget):
            total_height = 0
            for child in self._widget.get_children():  # type: ignore
                try:
                    if hasattr(child, "get_preferred_size"):
                        minimum, natural = child.get_preferred_size()
                        total_height += natural.height
                    else:
                        total_height += style.GRID_CELL_SIZE
                except Exception:
                    total_height += style.GRID_CELL_SIZE

            # Add border width
            line_width = 2
            total_height += line_width * 2
            req.height = total_height

        position = invoker.get_position_for_alignment(self._alignment, req)
        if position is None:
            position = invoker.get_position(req)

        if hasattr(self._widget, "move"):
            self._widget.move(position.x, position.y)

    def get_full_size_request(self):
        """Get the full size request for the palette."""
        if self._widget and hasattr(self._widget, "get_preferred_size"):
            try:
                return self._widget.get_preferred_size()[1]  # natural size
            except Exception:
                pass

        # Fallback
        req = Gdk.Rectangle()
        req.width = style.GRID_CELL_SIZE * 3
        req.height = style.GRID_CELL_SIZE * 2
        return req

    def popup(self, immediate=False):
        """Show the palette."""
        print(f"PaletteWindow.popup called with immediate={immediate}")
        if self._widget is None:
            return

        if self._invoker is not None:
            full_size_request = self.get_full_size_request()
            if hasattr(self._invoker, "get_alignment"):
                self._alignment = self._invoker.get_alignment(full_size_request)

            self.update_position()

            try:
                if hasattr(self._widget, "set_transient_for") and hasattr(
                    self._invoker, "get_toplevel"
                ):
                    toplevel = self._invoker.get_toplevel()
                    if toplevel and isinstance(toplevel, Gtk.Window):
                        self._widget.set_transient_for(toplevel)
            except (TypeError, AttributeError):
                self.emit("popdown")
                return

        self._popdown_anim.stop()

        if not immediate:
            self._popup_anim.start()
        else:
            self._popup_anim.stop()
            if hasattr(self._widget, "popup"):
                self._widget.popup(self._invoker)
            else:
                self._widget.present()
            self.update_position()

    def popdown(self, immediate=False):
        """Hide the palette."""
        print(f"PaletteWindow.popdown called with immediate={immediate}")
        print(f"PaletteWindow.popdown: is_up={self._up}, widget={self._widget}")
        self._popup_anim.stop()
        self._mouse_detector.stop()

        if not immediate:
            self._popdown_anim.start()
        else:
            self._popdown_anim.stop()
            if self._widget is not None:
                if hasattr(self._widget, "popdown"):
                    print("PaletteWindow.popdown: calling widget.popdown()")
                    self._widget.popdown()
                else:
                    print("PaletteWindow.popdown: setting widget invisible")
                    self._widget.set_visible(False)

    def on_invoker_enter(self):
        self._popdown_anim.stop()
        self._mouse_detector.start()

    def on_invoker_leave(self):
        self._mouse_detector.stop()
        self.popdown()

    def on_enter(self):
        self._popdown_anim.stop()

    def on_leave(self):
        self.popdown()

    def _invoker_mouse_enter_cb(self, invoker):
        if not getattr(self._invoker, "locked", False):
            self.on_invoker_enter()

    def _invoker_mouse_leave_cb(self, invoker):
        if not getattr(self._invoker, "locked", False):
            self.on_invoker_leave()

    def _invoker_right_click_cb(self, invoker):
        self.popup(immediate=True)

    def _invoker_toggle_state_cb(self, invoker):
        print(f"PaletteWindow._invoker_toggle_state_cb called with invoker={invoker}")
        if self.is_up():
            print(
                "PaletteWindow._invoker_toggle_state_cb: palette is up, calling popdown"
            )
            self.popdown(immediate=True)
        else:
            print(
                "PaletteWindow._invoker_toggle_state_cb: palette is down, calling popup"
            )
            self.popup(immediate=True)

    def __enter_notify_cb(self, widget):
        if not getattr(self._invoker, "locked", False):
            self.on_enter()

    def __leave_notify_cb(self, widget):
        if not getattr(self._invoker, "locked", False):
            self.on_leave()

    def __key_press_event_cb(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.popdown()
            return True

    def __show_cb(self, widget):
        if self._invoker is not None and hasattr(self._invoker, "notify_popup"):
            self._invoker.notify_popup()

        self._up = True
        self.emit("popup")

    def __hide_cb(self, widget):
        if self._invoker and hasattr(self._invoker, "notify_popdown"):
            self._invoker.notify_popdown()

        self._up = False
        self.emit("popdown")

    def get_rect(self):
        if not self._widget:
            return Gdk.Rectangle()

        if hasattr(self._widget, "get_rect"):
            return self._widget.get_rect()

        # Fallback implementation
        rect = Gdk.Rectangle()
        rect.width = self._widget.get_width()
        rect.height = self._widget.get_height()
        rect.x = rect.y = 0  # GTK4: Position managed by compositor
        return rect


class _PopupAnimation(animator.Animation):
    def __init__(self, palette):
        super().__init__(0.0, 1.0)
        self._palette = palette

    def next_frame(self, frame):
        # overriding classes hence the name change
        """Handle animation frame."""
        if frame == 1.0:
            self._palette.popup(immediate=True)


class _PopdownAnimation(animator.Animation):

    def __init__(self, palette):
        super().__init__(0.0, 1.0)
        self._palette = palette

    def next_frame(self, frame):
        if frame == 1.0:
            self._palette.popdown(immediate=True)


class Invoker(GObject.GObject):
    """Base class for palette invokers."""

    __gtype_name__ = "SugarPaletteInvoker"

    __gsignals__ = {
        "mouse-enter": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "mouse-leave": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "right-click": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "toggle-state": (GObject.SignalFlags.RUN_FIRST, None, ([])),
        "focus-out": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    ANCHORED = 0
    AT_CURSOR = 1

    BOTTOM = [(0.0, 0.0, 0.0, 1.0), (-1.0, 0.0, 1.0, 1.0)]
    RIGHT = [(0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 1.0, 1.0)]
    TOP = [(0.0, -1.0, 0.0, 0.0), (-1.0, -1.0, 1.0, 0.0)]
    LEFT = [(-1.0, 0.0, 0.0, 0.0), (-1.0, -1.0, 0.0, 1.0)]

    def __init__(self):
        super().__init__()

        self.parent = None

        # Get screen dimensions for GTK4
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_monitors().get_item(0)
            geometry = monitor.get_geometry()  # type: ignore
            self._screen_area = geometry
        else:
            self._screen_area = Gdk.Rectangle()
            self._screen_area.x = self._screen_area.y = 0
            self._screen_area.width = 1024
            self._screen_area.height = 768

        self._position_hint = self.ANCHORED
        self._cursor_x = -1
        self._cursor_y = -1
        self._palette = None
        self._cache_palette = True
        self._toggle_palette = False
        self._lock_palette = False
        self.locked = False

    def attach(self, parent):
        self.parent = parent

    def detach(self):
        self.parent = None
        if self._palette is not None:
            self._palette.destroy()
            self._palette = None

    def _get_position_for_alignment(self, alignment, palette_dim):
        palette_halign = alignment[0]
        palette_valign = alignment[1]
        invoker_halign = alignment[2]
        invoker_valign = alignment[3]

        if self._cursor_x == -1 or self._cursor_y == -1:
            if self.parent:
                try:
                    position = _get_pointer_position(self.parent)
                    (self._cursor_x, self._cursor_y) = position
                except Exception:
                    self._cursor_x = self._cursor_y = 0

        if self._position_hint is self.ANCHORED:
            rect = self.get_rect()
        else:
            dist = style.PALETTE_CURSOR_DISTANCE
            rect = Gdk.Rectangle()
            rect.x = self._cursor_x - dist
            rect.y = self._cursor_y - dist
            rect.width = rect.height = dist * 2

        if hasattr(palette_dim, "width"):
            palette_width = palette_dim.width
            palette_height = palette_dim.height
        else:
            # Handle tuple/list case
            palette_width, palette_height = palette_dim[0], palette_dim[1]

        x = rect.x + rect.width * invoker_halign + palette_width * palette_halign

        y = rect.y + rect.height * invoker_valign + palette_height * palette_valign

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = palette_width
        rect.height = palette_height
        return rect

    def _in_screen(self, rect):
        """Check if rectangle is within screen bounds."""
        return (
            rect.x >= self._screen_area.x
            and rect.y >= self._screen_area.y
            and rect.x + rect.width <= self._screen_area.x + self._screen_area.width
            and rect.y + rect.height <= self._screen_area.y + self._screen_area.height
        )

    def _get_area_in_screen(self, rect):
        """Return area of rectangle visible in the screen."""
        x1 = max(rect.x, self._screen_area.x)
        y1 = max(rect.y, self._screen_area.y)
        x2 = min(rect.x + rect.width, self._screen_area.x + self._screen_area.width)
        y2 = min(rect.y + rect.height, self._screen_area.y + self._screen_area.height)

        return max(0, (x2 - x1) * (y2 - y1))

    def _get_alignments(self):
        """Get possible alignments for this invoker."""
        if self._position_hint is self.AT_CURSOR:
            return [
                (0.0, 0.0, 1.0, 1.0),
                (0.0, -1.0, 1.0, 0.0),
                (-1.0, -1.0, 0.0, 0.0),
                (-1.0, 0.0, 0.0, 1.0),
            ]
        else:
            return self.BOTTOM + self.RIGHT + self.TOP + self.LEFT

    def get_position_for_alignment(self, alignment, palette_dim):
        """Get position for specific alignment if it fits on screen."""
        rect = self._get_position_for_alignment(alignment, palette_dim)
        if self._in_screen(rect):
            return rect
        else:
            return None

    def get_position(self, palette_dim):
        alignment = self.get_alignment(palette_dim)
        rect = self._get_position_for_alignment(alignment, palette_dim)

        # In case our efforts to find an optimum place inside the screen
        # failed, just make sure the palette fits inside the screen if at all
        # possible.
        rect.x = max(0, rect.x)
        rect.y = max(0, rect.y)

        rect.x = min(rect.x, self._screen_area.width - rect.width)
        rect.y = min(rect.y, self._screen_area.height - rect.height)

        return rect

    def get_alignment(self, palette_dim):
        best_alignment = None
        best_area = -1

        for alignment in self._get_alignments():
            pos = self._get_position_for_alignment(alignment, palette_dim)
            if self._in_screen(pos):
                return alignment

            area = self._get_area_in_screen(pos)
            if area > best_area:
                best_alignment = alignment
                best_area = area

        if not best_alignment:
            return self._get_alignments()[0]

        # Palette horiz/vert alignment
        ph = best_alignment[0]
        pv = best_alignment[1]

        # Invoker horiz/vert alignment
        ih = best_alignment[2]
        iv = best_alignment[3]

        rect = self.get_rect()
        screen_area = self._screen_area

        if hasattr(palette_dim, "width"):
            palette_width = palette_dim.width
            palette_height = palette_dim.height
        else:
            palette_width, palette_height = palette_dim[0], palette_dim[1]

        if best_alignment in self.LEFT or best_alignment in self.RIGHT:
            dtop = rect.y - screen_area.y
            dbottom = screen_area.y + screen_area.height - rect.y - rect.height

            iv = 0

            # Set palette_valign to align to screen
            if dtop > dbottom:
                pv = -float(dtop) / palette_height
            else:
                pv = -float(palette_height - dbottom - rect.height) / palette_height

        elif best_alignment in self.TOP or best_alignment in self.BOTTOM:
            dleft = rect.x - screen_area.x
            dright = screen_area.x + screen_area.width - rect.x - rect.width

            ih = 0

            if palette_width > 0:
                # Set palette_halign to align to screen
                if dleft > dright:
                    ph = -float(dleft) / palette_width
                else:
                    ph = -float(palette_width - dright - rect.width) / palette_width

        return (ph, pv, ih, iv)

    def has_rectangle_gap(self):
        return False

    def draw_rectangle(self, event, palette):
        pass

    def notify_popup(self):
        pass

    def notify_popdown(self):
        self._cursor_x = -1
        self._cursor_y = -1

    def _ensure_palette_exists(self):
        if self.parent and self.palette is None:
            if hasattr(self.parent, "create_palette"):
                palette = self.parent.create_palette()
                if palette is not None:
                    self.palette = palette

    def notify_mouse_enter(self):
        self._ensure_palette_exists()
        self.emit("mouse-enter")

    def notify_mouse_leave(self):
        self.emit("mouse-leave")

    def notify_right_click(self, x=None, y=None):
        """
        Notify the palette invoker of a right click and expand the
        palette as required.  The x and y args should be that of
        where the event happened, relative to the root of the screen.

        Args
            x (float): the x coord of the event relative to the root
                of the screen, eg. :class:`Gdk.EventTouch.x_root`
            y (float): the y coord of the event relative to the root
                of the screen, eg. :class:`Gdk.EventTouch.y_root`
        """
        self._ensure_palette_exists()
        self._process_event(x, y)
        self.emit("right-click")

    def notify_toggle_state(self):
        print("ToolInvoker.notify_toggle_state called")
        self._ensure_palette_exists()
        print("ToolInvoker emitting 'toggle-state' signal")
        self.emit("toggle-state")

    def _process_event(self, x, y):
        if x is not None and y is not None:
            self._cursor_x = x
            self._cursor_y = y

    def get_palette(self):
        return self._palette

    def set_palette(self, palette):
        if self._palette is not None:
            self._palette.popdown(immediate=True)
            self._palette.props.invoker = None
            GLib.idle_add(
                lambda old_palette=self._palette: old_palette.destroy(),
                priority=GLib.PRIORITY_LOW,
            )  # type: ignore

        self._palette = palette

        if self._palette is not None:
            self._palette.props.invoker = self
            self._palette.connect("popdown", self.__palette_popdown_cb)

    palette = GObject.Property(type=object, setter=set_palette, getter=get_palette)

    def get_cache_palette(self):
        return self._cache_palette

    def set_cache_palette(self, cache_palette):
        self._cache_palette = cache_palette

    cache_palette = GObject.Property(
        type=bool, default=True, setter=set_cache_palette, getter=get_cache_palette
    )

    def get_toggle_palette(self):
        return self._toggle_palette

    def set_toggle_palette(self, toggle_palette):
        self._toggle_palette = toggle_palette

    toggle_palette = GObject.Property(
        type=bool, default=False, setter=set_toggle_palette, getter=get_toggle_palette
    )

    def get_lock_palette(self):
        return self._lock_palette

    def set_lock_palette(self, lock_palette):
        self._lock_palette = lock_palette

    lock_palette = GObject.Property(
        type=bool, default=False, setter=set_lock_palette, getter=get_lock_palette
    )

    def __palette_popdown_cb(self, palette):
        if not self.props.cache_palette:
            self.set_palette(None)

    def primary_text_clicked(self):
        pass

    def get_rect(self):
        """Get the rectangle for this invoker - implemented by subclasses."""
        return Gdk.Rectangle()

    def get_toplevel(self):
        """Get the toplevel window - implemented by subclasses."""
        if self.parent:
            return self.parent.get_root()
        return None


class WidgetInvoker(Invoker):
    """Invoker for general widgets."""

    def __init__(self, parent=None, widget=None):
        super().__init__()

        self._widget = None
        self._expanded = False
        self._pointer_position = (-1, -1)
        self._motion_controller = None
        self._click_controller = None
        self._long_press_gesture = None
        self._long_pressed_recognized = False

        if parent or widget:
            self.attach_widget(parent, widget)

    def attach_widget(self, parent, widget=None):
        if widget:
            self._widget = widget
        else:
            self._widget = parent

        if self._widget:
            try:
                self._pointer_position = _get_pointer_position(self._widget)
            except Exception:
                self._pointer_position = (0, 0)

        self.notify("widget")

        # Set up GTK4 event controllers
        self._setup_controllers()
        self.attach(parent)

    def _setup_controllers(self):
        """Set up event controllers for palette interaction."""
        if not self._widget:
            return

        # Ensure widget is focusable and sensitive for event handling
        self._widget.set_can_focus(True)
        self._widget.set_sensitive(True)
        print(
            f"WidgetInvoker._setup_controllers: set_can_focus and set_sensitive for {self._widget}"
        )

        # Motion controller for enter/leave events
        self._motion_controller = Gtk.EventControllerMotion()
        self._motion_controller.connect("enter", self.__enter_notify_event_cb)
        self._motion_controller.connect("leave", self.__leave_notify_event_cb)
        self._widget.add_controller(self._motion_controller)

        # Click controller for button events
        self._click_controller = Gtk.GestureClick()
        self._click_controller.connect("released", self.__button_release_event_cb)
        self._widget.add_controller(self._click_controller)

        # Long press gesture
        self._long_press_gesture = Gtk.GestureLongPress()
        self._long_press_gesture.connect("pressed", self.__long_pressed_event_cb)
        self._widget.add_controller(self._long_press_gesture)

        # Connect to clicked signal if available
        try:
            if GObject.signal_lookup("clicked", self._widget):
                print(
                    f"WidgetInvoker._setup_controllers: connecting to 'clicked' signal for {self._widget}"
                )
                self._widget.connect("clicked", self.__click_event_cb)
        except (TypeError, AttributeError):
            pass

    def detach(self):
        if self._widget:
            try:
                if self._motion_controller:
                    self._widget.remove_controller(self._motion_controller)
                if self._click_controller:
                    self._widget.remove_controller(self._click_controller)
                if self._long_press_gesture:
                    self._widget.remove_controller(self._long_press_gesture)
            except Exception:
                pass

        super().detach()

    def get_rect(self):
        if not self._widget:
            return Gdk.Rectangle()

        width = self._widget.get_width()
        height = self._widget.get_height()

        # Get widget position - GTK4
        x = y = 0
        try:
            native = self._widget.get_native()
            if native:
                success, transform = self._widget.compute_transform(native)
                if success and transform:
                    x = transform.get_value(0, 3)
                    y = transform.get_value(1, 3)
        except Exception:
            x = y = 0

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = width
        rect.height = height
        return rect

    def has_rectangle_gap(self):
        return True

    def draw_rectangle(self, cr, palette):
        if not self.parent:
            return

        allocation = self.parent.get_allocation()
        context = self.parent.get_style_context()
        context.add_class("toolitem")
        context.add_class("palette-down")

        gap = _calculate_gap(self.get_rect(), palette.get_rect())
        if gap:
            # GTK4: Would need to use snapshot API for drawing
            # TODO
            pass

    def __enter_notify_event_cb(self, controller, x, y):
        if (x, y) == self._pointer_position:
            self._pointer_position = (-1, -1)
            return False
        self.notify_mouse_enter()

    def __leave_notify_event_cb(self, controller):
        self.notify_mouse_leave()

    def __button_release_event_cb(self, gesture, n_press, x, y):
        button = gesture.get_current_button()

        print(
            f"ToolInvoker.__button_release_event_cb called: button={button}, n_press={n_press}, x={x}, y={y}"
        )
        if button == 3:  # Right click
            print("ToolInvoker: right click detected")
            self.notify_right_click(x, y)
            return True
        elif button == 1:  # Left click
            print("ToolInvoker: left click detected")
            if self._lock_palette and not self.locked:
                self.locked = True
                if hasattr(self.parent, "set_expanded"):
                    self.parent.set_expanded(True)  # type: ignore

            if self._toggle_palette:
                print(
                    "ToolInvoker: toggle_palette is True, calling notify_toggle_state"
                )
                self.notify_toggle_state()
                return True
        return False

    def __long_pressed_event_cb(self, gesture, x, y):
        self._long_pressed_recognized = True
        self.notify_right_click(x, y)

    def __click_event_cb(self, widget):
        print(f"WidgetInvoker.__click_event_cb: 'clicked' signal received for {widget}")
        if not self._long_pressed_recognized:
            if self._lock_palette and not self.locked:
                self.locked = True
                if hasattr(self.parent, "set_expanded"):
                    self.parent.set_expanded(True)  # type: ignore

            if self._toggle_palette:
                print(
                    "WidgetInvoker.__click_event_cb: toggle_palette is True, calling notify_toggle_state"
                )
                self.notify_toggle_state()
        self._long_pressed_recognized = False

    def get_widget(self):
        return self._widget

    def set_widget(self, widget):
        if self._widget:
            self.detach()
        self._widget = widget
        if widget:
            self.attach_widget(widget.get_parent(), widget)

    widget = GObject.Property(type=object, getter=get_widget, setter=set_widget)

    def get_toplevel(self):
        if self._widget:
            return self._widget.get_root()
        return None

    def notify_popup(self):
        super().notify_popup()
        if self._widget:
            self._widget.queue_draw()

    def notify_popdown(self):
        self.locked = False
        super().notify_popdown()
        if self._widget:
            self._widget.queue_draw()


class CursorInvoker(Invoker):
    """Invoker that tracks cursor position."""

    def __init__(self, parent=None):
        super().__init__()
        self._position_hint = self.AT_CURSOR
        self._pointer_position = (-1, -1)
        self._motion_controller = None
        self._click_controller = None
        self._long_press_gesture = None
        self._long_pressed_recognized = False

        if parent:
            self.attach(parent)

    def attach(self, parent):
        super().attach(parent)

        if self.parent:
            try:
                self._pointer_position = _get_pointer_position(self.parent)
            except Exception:
                self._pointer_position = (0, 0)

            # Set up event controllers
            self._motion_controller = Gtk.EventControllerMotion()
            self._motion_controller.connect("enter", self.__enter_notify_event_cb)
            self._motion_controller.connect("leave", self.__leave_notify_event_cb)
            self.parent.add_controller(self._motion_controller)

            self._click_controller = Gtk.GestureClick()
            self._click_controller.connect("released", self.__button_release_event_cb)
            self.parent.add_controller(self._click_controller)

            self._long_press_gesture = Gtk.GestureLongPress()
            self._long_press_gesture.connect("pressed", self.__long_pressed_event_cb)
            self.parent.add_controller(self._long_press_gesture)

    def detach(self):
        """Detach from the parent."""
        if self.parent:
            try:
                if self._motion_controller:
                    self.parent.remove_controller(self._motion_controller)
                if self._click_controller:
                    self.parent.remove_controller(self._click_controller)
                if self._long_press_gesture:
                    self.parent.remove_controller(self._long_press_gesture)
            except Exception:
                pass

        super().detach()

    def get_rect(self):
        if self.parent:
            try:
                x, y = _get_pointer_position(self.parent)
            except Exception:
                x = y = 0
        else:
            x = y = 0

        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        rect.width = 0
        rect.height = 0
        return rect

    def __enter_notify_event_cb(self, controller, x, y):
        if (x, y) == self._pointer_position:
            self._pointer_position = (-1, -1)
            return False
        self.notify_mouse_enter()

    def __leave_notify_event_cb(self, controller):
        self.notify_mouse_leave()

    def __button_release_event_cb(self, gesture, n_press, x, y):
        if self._long_pressed_recognized:
            self._long_pressed_recognized = False
            return True

        button = gesture.get_current_button()
        if button == 1:
            if self._toggle_palette:
                self.notify_toggle_state()
        elif button == 3:
            self.notify_right_click(x, y)
            return True
        return False

    def __long_pressed_event_cb(self, gesture, x, y):
        self._long_pressed_recognized = True
        self.notify_right_click(x, y)

    def get_toplevel(self):
        if self.parent:
            return self.parent.get_root()
        return None


class ToolInvoker(WidgetInvoker):
    """
    A palette invoker for toolbar buttons and other items.  this invoker
    will properly align the palette so that is perpendicular to the toolbar
    (a horizontal toolbar will spawn a palette going downwards).  it also
    draws the highlights specific to a toolitem.

    for :class:`sugar4.graphics.toolbutton.toolbutton` and subclasses, you
    should not use the toolinvoker directly.  instead, just subclass the
    tool button and override the `create_palette` function.

    args:
        parent (gtk.widget):  toolitem to connect invoker to
    """

    def __init__(self, parent=None):
        super().__init__()
        self._tool = None

        if parent:
            self.attach_tool(parent)

    def attach_tool(self, widget):
        """
        Attach a toolitem to the invoker.  Same behaviour as passing the
        `parent` argument to the constructor.

        Args:
            widget (Gtk.Widget):  toolitem to connect invoker to
        """
        self._tool = widget
        child = widget.get_child() if hasattr(widget, "get_child") else widget
        self.attach_widget(widget, child)

    def get_tool(self):
        """Get the tool widget."""
        return self._tool

    def _get_alignments(self):
        if not self._widget or not self._widget.get_parent():
            return super()._get_alignments()

        parent = self._widget.get_parent()
        if hasattr(parent, "get_orientation"):
            if parent.get_orientation() == Gtk.Orientation.HORIZONTAL:
                return self.BOTTOM + self.TOP
            else:
                return self.LEFT + self.RIGHT

        return super()._get_alignments()

    def primary_text_clicked(self):
        if self._widget and hasattr(self._widget, "emit"):
            self._widget.emit("clicked")

    def notify_popup(self):
        super().notify_popup()
        if self._tool:
            self._tool.queue_draw()

    def notify_popdown(self):
        super().notify_popdown()
        if self._tool:
            self._tool.queue_draw()


class TreeViewInvoker(Invoker):
    """Invoker for TreeView cells."""

    def __init__(self):
        super().__init__()

        self._tree_view = None
        self._motion_controller = None
        self._click_controller = None
        self._long_press_gesture = None
        self._position_hint = self.AT_CURSOR

        self._path = None
        self._column = None
        self.palette = None

    def attach_treeview(self, tree_view):
        self._tree_view = tree_view

        # Set up event controllers
        self._motion_controller = Gtk.EventControllerMotion()
        self._motion_controller.connect("motion", self.__motion_notify_event_cb)
        tree_view.add_controller(self._motion_controller)

        self._click_controller = Gtk.GestureClick()
        self._click_controller.connect("released", self.__button_release_event_cb)
        tree_view.add_controller(self._click_controller)

        self._long_press_gesture = Gtk.GestureLongPress()
        self._long_press_gesture.connect("pressed", self.__long_pressed_event_cb)
        tree_view.add_controller(self._long_press_gesture)

        self.attach(tree_view)

    def detach(self):
        if self._tree_view:
            try:
                if self._motion_controller:
                    self._tree_view.remove_controller(self._motion_controller)
                if self._click_controller:
                    self._tree_view.remove_controller(self._click_controller)
                if self._long_press_gesture:
                    self._tree_view.remove_controller(self._long_press_gesture)
            except Exception:
                pass

        super().detach()

    def get_rect(self):
        if not self._tree_view or not self._path or not self._column:
            rect = Gdk.Rectangle()
            rect.x = rect.y = 0
            rect.width = rect.height = 50
            return rect

        try:
            # Get cell area
            cell_area = self._tree_view.get_cell_area(self._path, self._column)

            # Convert to widget coordinates
            widget_x, widget_y = self._tree_view.convert_tree_to_widget_coords(
                cell_area.x, cell_area.y
            )

            # Get widget position in root coordinates
            root_x = root_y = 0
            try:
                native = self._tree_view.get_native()
                if native:
                    success, transform = self._tree_view.compute_transform(native)
                    if success and transform:
                        root_x = transform.get_value(0, 3) + widget_x
                        root_y = transform.get_value(1, 3) + widget_y
            except Exception:
                root_x = widget_x
                root_y = widget_y

            rect = Gdk.Rectangle()
            rect.x = int(root_x)
            rect.y = int(root_y)
            rect.width = cell_area.width
            rect.height = cell_area.height
            return rect
        except Exception:
            rect = Gdk.Rectangle()
            rect.x = rect.y = 0
            rect.width = rect.height = 50
            return rect

    def get_toplevel(self):
        if self._tree_view:
            return self._tree_view.get_root()
        return None

    def __motion_notify_event_cb(self, controller, x, y):
        if not self._tree_view:
            return

        here = self._tree_view.get_path_at_pos(int(x), int(y))
        if here is None:
            if self._path is not None:
                self.notify_mouse_leave()
            self._path = None
            self._column = None
            return

        path, column, x_, y_ = here
        if path != self._path or column != self._column:
            self._redraw_cell(self._path, self._column)
            self._redraw_cell(path, column)

            self._path = path
            self._column = column

            if self.palette is not None:
                self.palette.popdown(immediate=True)
                self.palette = None

            self.notify_mouse_enter()

    def _redraw_cell(self, path, column):
        if not self._tree_view or not path or not column:
            return

        try:
            area = self._tree_view.get_background_area(path, column)
            x, y = self._tree_view.convert_bin_window_to_widget_coords(area.x, area.y)
            self._tree_view.queue_draw_area(x, y, area.width, area.height)
        except Exception:
            pass

    def __button_release_event_cb(self, gesture, n_press, x, y):
        x, y = int(x), int(y)
        here = self._tree_view.get_path_at_pos(x, y)  # type: ignore
        if here is None:
            return False

        path, column, cell_x, cell_y = here
        self._path = path
        self._column = column

        button = gesture.get_current_button()
        if button == 1:
            # Left mouse button
            if self.palette is not None:
                self.palette.popdown(immediate=True)

            # Handle cell renderer click
            if column and hasattr(column, "get_cells"):
                cells = column.get_cells()
                if cells:
                    cellrenderer = cells[0]
                    if (
                        CellRendererIcon
                        and cellrenderer is not None
                        and isinstance(cellrenderer, CellRendererIcon)
                    ):
                        cellrenderer.emit("clicked", path)  # type: ignore
            return False
        elif button == 3:
            # Right mouse button
            self._ensure_palette_exists()
            self.notify_right_click(x, y)
            return True
        return False

    def __long_pressed_event_cb(self, gesture, x, y):
        if not self._tree_view:
            return

        here = self._tree_view.get_path_at_pos(x, y)
        if here is None:
            return

        path, column, x_, y_ = here
        self._path = path
        self._column = column
        self._ensure_palette_exists()

        # Convert coordinates to root window coordinates for the notify call
        try:
            native = self._tree_view.get_native()
            if native:
                surface = native.get_surface()
                if surface:
                    device_position = surface.get_device_position(_pointer)
                    root_x, root_y = device_position[1], device_position[2]
                    self.notify_right_click(root_x, root_y)
                    return
        except Exception:
            pass

        # Fallback to widget coordinates
        self.notify_right_click(x, y)

    def _ensure_palette_exists(self):
        """Ensure the palette exists for the current cell."""
        if hasattr(self._tree_view, "create_palette"):
            self.palette = self._tree_view.create_palette(  # type: ignore
                self._path, self._column
            )
        else:
            self.palette = None

    def notify_popdown(self):
        super().notify_popdown()
        self.palette = None
