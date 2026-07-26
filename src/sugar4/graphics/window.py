# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2009, Aleksey Lim, Sayamindu Dasgupta
# Copyright (C) 2025 MostlyK
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Window Management
=================

Window management for Sugar activities.

Provides window classes for managing Sugar activity windows with
fullscreen support, toolbar management, and tray integration.

Classes:
    UnfullscreenButton: Button to exit fullscreen mode
    Window: Main activity window container
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import GObject, GLib, Gdk, Gtk

from sugar4.graphics.icon import Icon

_UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT = 2


class UnfullscreenButton(Gtk.Window):
    """
    A ready-made "Unfullscreen" button.

    Used by :class:`~sugar4.graphics.window.Window` to exit fullscreen
    mode using modern window management.
    """

    __gtype_name__ = "SugarUnfullscreenButton"

    def __init__(self):
        super().__init__()

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(False)

        # GTK4 doesn't have accept_focus property
        self.set_can_focus(False)

        # Set up size estimation
        self._width = 48
        self._height = 48

        # Create the button
        self._button = Gtk.Button()
        self._button.add_css_class("unfullscreen-button")

        # Create icon
        self._icon = Icon(icon_name="view-fullscreen", pixel_size=24)
        self._button.set_child(self._icon)

        self.set_child(self._button)

        # Position the button
        self._reposition()

        # Monitor display changes
        # display = Gdk.Display.get_default()
        # if display and hasattr(display, "connect") and "monitors-changed" in Gdk.Display.list_signals():
        #     display.connect("monitors-changed", self._on_monitors_changed)

    def connect_button_clicked(self, callback):
        """Connect a callback to button click."""
        self._button.connect("clicked", callback)

    def _reposition(self):
        """Position button in top-right corner."""
        display = Gdk.Display.get_default()
        if not display:
            return

        # Wayland: get_primary_monitor() may not exist
        monitor = None
        if hasattr(display, "get_primary_monitor"):
            monitor = display.get_primary_monitor()
        if not monitor:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                monitor = monitors.get_item(0)

        if monitor:
            geometry = monitor.get_geometry()
            x = geometry.x + geometry.width - self._width
            y = geometry.y
            # Note: GTK4 window positioning is more limited
            # We rely on window manager for positioning

    def _on_monitors_changed(self, display):
        """Handle monitor configuration changes."""
        self._reposition()


class Window(Gtk.ApplicationWindow):
    """
    A Sugar activity window.

    Used as a container to display things that happen in an activity.
    A window contains a canvas widget, and may contain toolbar and tray widgets.

    The window layout is:
        * toolbar (optional)
        * alerts (as overlays)
        * canvas (main content)
        * tray (optional)

    Window supports fullscreen mode where toolbar and tray are hidden.

    Key bindings:
        * Escape: exit fullscreen mode
        * Alt+Space: toggle tray visibility
    """

    __gtype_name__ = "SugarWindow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._enable_fullscreen_mode = True
        self._is_fullscreen = False
        self._unfullscreen_button = None
        self._unfullscreen_button_timeout_id = None

        # Activity components
        self._canvas = None
        self._toolbar_box = None
        self._alerts = []
        self.tray = None

        # Set up window
        self.set_decorated(False)
        self.maximize()

        # Create main layout
        self._setup_layout()

        # Set up event handling
        self._setup_event_handling()

        # Set up unfullscreen button
        self._unfullscreen_button = UnfullscreenButton()
        self._unfullscreen_button.set_transient_for(self)
        self._unfullscreen_button.connect_button_clicked(
            self._on_unfullscreen_button_clicked
        )

    def _setup_layout(self):
        """Set up the main window layout."""
        # Main vertical box
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self._main_box)

        # Content area (horizontal box for canvas and tray)
        self._content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._content_box.set_hexpand(True)
        self._content_box.set_vexpand(True)
        self._main_box.append(self._content_box)

        # Overlay for alerts
        self._overlay = Gtk.Overlay()
        self._content_box.append(self._overlay)

    def _setup_event_handling(self):
        """Set up modern event handling with gesture controllers."""
        # Key events
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Motion events for unfullscreen button
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_motion)
        self.add_controller(motion_controller)

        # Click events
        click_controller = Gtk.GestureClick()
        click_controller.connect("released", self._on_button_released)
        self.add_controller(click_controller)

    def reveal(self):
        """
        Make window active.

        Brings the window to the top and makes it active, even after
        invoking on response to non-GTK events.
        """
        self.present()

    def is_fullscreen(self):
        """
        Check if the window is fullscreen.

        Returns:
            bool: window is fullscreen
        """
        return self._is_fullscreen

    def fullscreen(self):
        """
        Make the window fullscreen.

        The toolbar and tray will be hidden, and the UnfullscreenButton
        will be shown for a short time.
        """
        if self._toolbar_box:
            self._toolbar_box.set_visible(False)
        if self.tray:
            self.tray.set_visible(False)

        self._is_fullscreen = True
        super().fullscreen()

        if self._enable_fullscreen_mode:
            self._show_unfullscreen_button()

    def unfullscreen(self):
        """
        Restore the window to non-fullscreen mode.

        The UnfullscreenButton will be hidden, and the toolbar
        and tray will be shown.
        """
        if self._toolbar_box:
            self._toolbar_box.set_visible(True)
        if self.tray:
            self.tray.set_visible(True)

        self._is_fullscreen = False
        super().unfullscreen()

        if self._enable_fullscreen_mode:
            self._hide_unfullscreen_button()

    def set_canvas(self, canvas):
        """
        Set canvas widget.

        Args:
            canvas (Gtk.Widget): the canvas to set
        """
        if self._canvas:
            self._overlay.remove_overlay(self._canvas)
            self._overlay.set_child(None)

        if canvas:
            self._overlay.set_child(canvas)
            canvas.set_hexpand(True)
            canvas.set_vexpand(True)

        self._canvas = canvas

    def get_canvas(self):
        """
        Get canvas widget.

        Returns:
            Gtk.Widget: the canvas
        """
        return self._canvas

    def set_toolbar_box(self, toolbar_box):
        """
        Set toolbar box widget.

        Args:
            toolbar_box (Gtk.Widget): the toolbar box to set
        """
        if self._toolbar_box:
            self._main_box.remove(self._toolbar_box)

        if toolbar_box:
            self._main_box.prepend(toolbar_box)
            toolbar_box.set_hexpand(True)

        self._toolbar_box = toolbar_box

    def get_toolbar_box(self):
        """
        Get toolbar box widget.

        Returns:
            Gtk.Widget: the current toolbar box
        """
        return self._toolbar_box

    def set_tray(self, tray, position=Gtk.PositionType.BOTTOM):
        """
        Set the tray.

        Args:
            tray (Gtk.Widget): the tray to set
            position (Gtk.PositionType): the edge to set the tray at
        """
        if self.tray:
            parent = self.tray.get_parent()
            if parent:
                parent.remove(self.tray)

        if tray:
            if position == Gtk.PositionType.LEFT:
                self._content_box.prepend(tray)
            elif position == Gtk.PositionType.RIGHT:
                self._content_box.append(tray)
            elif position == Gtk.PositionType.BOTTOM:
                self._main_box.append(tray)

        self.tray = tray

    def add_alert(self, alert):
        """
        Add an alert to the window as an overlay.

        Args:
            alert (Gtk.Widget): the alert to add
        """
        self._alerts.append(alert)

        # Position the alert at the top
        alert.set_halign(Gtk.Align.FILL)
        alert.set_valign(Gtk.Align.START)

        self._overlay.add_overlay(alert)

    def remove_alert(self, alert):
        """
        Remove an alert from the window.

        Args:
            alert (Gtk.Widget): the alert to remove
        """
        if alert in self._alerts:
            self._alerts.remove(alert)
            self._overlay.remove_overlay(alert)

    def get_alerts(self):
        """Get the list of alerts."""
        return self._alerts


    def set_enable_fullscreen_mode(self, enable):
        """
        Set enable fullscreen mode.

        Args:
            enable (bool): enable fullscreen mode
        """
        self._enable_fullscreen_mode = enable

    def get_enable_fullscreen_mode(self):
        """
        Get enable fullscreen mode.

        Returns:
            bool: enable fullscreen mode
        """
        return self._enable_fullscreen_mode

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press events."""
        key_name = Gdk.keyval_name(keyval)

        # Alt+Space: toggle tray visibility
        if state & Gdk.ModifierType.ALT_MASK and key_name == "space" and self.tray:
            self.tray.set_visible(not self.tray.get_visible())
            return True

        # Escape: exit fullscreen
        elif (
            key_name == "Escape"
            and self._is_fullscreen
            and self._enable_fullscreen_mode
        ):
            self.unfullscreen()
            return True

        return False

    def _on_motion(self, controller, x, y):
        """Handle mouse motion events."""
        if self._is_fullscreen and self._enable_fullscreen_mode:
            self._show_unfullscreen_button()

    def _on_button_released(self, gesture, n_press, x, y):
        """Handle button release events."""
        if self._is_fullscreen and self._enable_fullscreen_mode:
            self._show_unfullscreen_button()

    def _show_unfullscreen_button(self):
        """Show the unfullscreen button with timeout."""
        if not self._unfullscreen_button.get_visible():
            self._unfullscreen_button.present()

        # Reset timeout
        if self._unfullscreen_button_timeout_id:
            GLib.source_remove(self._unfullscreen_button_timeout_id)

        self._unfullscreen_button_timeout_id = GLib.timeout_add_seconds(
            _UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT,
            self._unfullscreen_button_timeout_cb,
        )

    def _hide_unfullscreen_button(self):
        """Hide the unfullscreen button."""
        self._unfullscreen_button.set_visible(False)

        if self._unfullscreen_button_timeout_id:
            GLib.source_remove(self._unfullscreen_button_timeout_id)
            self._unfullscreen_button_timeout_id = None

    def _unfullscreen_button_timeout_cb(self):
        """Timeout callback to hide unfullscreen button."""
        self._hide_unfullscreen_button()
        return False

    def _on_unfullscreen_button_clicked(self, button):
        """Handle unfullscreen button click."""
        self.unfullscreen()

    # Properties
    canvas = property(get_canvas, set_canvas)
    toolbar_box = property(get_toolbar_box, set_toolbar_box)
    enable_fullscreen_mode = GObject.Property(
        type=bool,
        default=True,
        getter=get_enable_fullscreen_mode,
        setter=set_enable_fullscreen_mode,
    )
