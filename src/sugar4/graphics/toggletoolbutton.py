# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2012, Daniel Francis
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

"""
STABLE.
"""

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk

from sugar4.graphics.icon import Icon
from sugar4.graphics.palette import Palette, ToolInvoker


def _add_accelerator(tool_button):
    """Add accelerator when widget is properly added to app window."""
    if not hasattr(tool_button, "_accelerator") or not tool_button._accelerator:
        return

    root = tool_button.get_root()
    if not root:
        return

    app = getattr(root, "get_application", lambda: None)()
    if not app:
        return

    # Remove previous action if exists
    if hasattr(tool_button, "_accel_action_name"):
        try:
            app.remove_action(tool_button._accel_action_name)
        except:
            pass

    # unique action name
    action_name = f"toggle-tool-{id(tool_button)}"
    action = Gio.SimpleAction.new(action_name, None)

    def on_activate(action, param):
        tool_button.set_active(not tool_button.get_active())
        tool_button.emit("toggled")

    action.connect("activate", on_activate)
    app.add_action(action)
    app.set_accels_for_action(f"app.{action_name}", [tool_button._accelerator])

    # Store for later removal
    tool_button._accel_action = action
    tool_button._accel_action_name = action_name


def _on_root_changed(tool_button, pspec=None):
    """Called when widget's root changes (added to/removed from window)."""
    _add_accelerator(tool_button)


class ToggleToolButton(Gtk.ToggleButton):
    """
    UI for toggletoolbutton.
    A ToggleToolButton is a toggle button widget that can be used in toolbars,
    having an icon, a tooltip palette, and an accelerator.
    Use ToggleToolButton() to create a new ToggleToolButton.

    Args:
        accelerator (string): keyboard shortcut to be used to
        activate this button.
        Find about format here :
        https://docs.gtk.org/gtk4/func.accelerator_parse.html

        tooltip (string): tooltip to be displayed when user
        hovers over toggle button.

    Keyword Args:
        icon_name(string): name of themed icon which is to be used.
    """

    __gtype_name__ = "SugarToggleToolButton"

    def __init__(self, icon_name=None):
        super().__init__()

        self._palette_invoker = ToolInvoker(self)
        self._accelerator = None

        self.add_css_class("toolbar-button")
        self.add_css_class("flat")
        self.set_has_frame(False)
        self.set_can_focus(True)

        if icon_name:
            self.set_icon_name(icon_name)

        # Connect to root changes and map signal to setup accelerator
        self.connect("notify::root", _on_root_changed)
        self.connect("map", self._on_mapped)

        self._apply_toolbar_button_css()

    def _apply_toolbar_button_css(self):
        css = """
        .toolbar-button {
            border-radius: 6px;
            margin: 2px;
            padding: 6px;
            min-width: 32px;
            min-height: 32px;
            background: transparent;
            border: none;
        }

        .toolbar-button:hover {
            background: alpha(currentColor, 0.1);
        }

        .toolbar-button:active,
        .toolbar-button:checked {
            background: alpha(currentColor, 0.2);
            border: 1px solid alpha(currentColor, 0.3);
            box-shadow: none;
        }

        .toolbar-button:focus {
            outline: 2px solid rgb(53, 132, 228);
            outline-offset: 2px;
        }
        """
        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_string(css)
            self.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as e:
            import logging
            logging.warning(f"Could not apply toolbar button CSS: {e}")

    def _on_mapped(self, widget):
        """Called when widget is mapped (visible and added to window)."""
        _add_accelerator(self)

    def do_dispose(self):
        if getattr(self, "_palette_invoker", None) is not None:
            self._palette_invoker.detach()
            self._palette_invoker = None
        # Remove accelerator action
        if hasattr(self, "_accel_action_name"):
            root = self.get_root()
            if root:
                app = getattr(root, "get_application", lambda: None)()
                if app:
                    try:
                        app.remove_action(self._accel_action_name)
                    except:
                        pass
        super().do_dispose()

    def set_icon_name(self, icon_name):
        """
        Sets the icon for the tool button from a named themed icon.
        If it is none then no icon will be shown.

        Args:
            icon_name(string): The name for a themed icon.
            It can be set as 'None' too.

        Example:
            set_icon_name('view-radial')
        """
        icon = Icon(icon_name=icon_name)
        self.set_child(icon)

    def get_icon_name(self):
        """
        The get_icon_name() method returns the value of the icon_name
        property that contains the name of a themed icon or None.
        """
        child = self.get_child()
        if isinstance(child, Icon):
            return child.get_icon_name()
        else:
            return None

    icon_name = GObject.Property(type=str, setter=set_icon_name, getter=get_icon_name)

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.Property(type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker
    )

    def set_tooltip(self, text):
        """
        Sets the tooltip of the toogle tool button. Displays when
        user hovers over the button with cursor.

        Args:
            tooltip (string): tooltip to be added to the button
        """
        self.set_palette(Palette(text))

    def set_accelerator(self, accelerator):
        """
        Sets keyboard shortcut that activates this button.

        Args:
            accelerator(string): accelerator to be set. Should be in
            form <modifier>Letter
            Find about format here :
            https://docs.gtk.org/gtk4/func.accelerator_parse.html

        Example:
            set_accelerator(self, 'accel')
        """
        self._accelerator = accelerator
        # Try to setup accelerator immediately if already in window
        _add_accelerator(self)

    def get_accelerator(self):
        """
        Returns above accelerator string.
        """
        return self._accelerator

    accelerator = GObject.Property(
        type=str, setter=set_accelerator, getter=get_accelerator
    )

    def do_snapshot(self, snapshot):
        """
        Render the toggle tool button using snapshot-based drawing.
        """
        child = self.get_first_child()
        while child is not None:
            self.snapshot_child(child, snapshot)
            child = child.get_next_sibling()

        # Custom drawing can be implemented here using the snapshot API
        # if self.palette and self.palette.is_up():
        #     # Custom palette drawing would go here using snapshot API
        #     pass

    def do_clicked(self):
        """
        Implementation method for hiding the tooltip when the
        toggle button is clicked
        """
        # Call parent implementation first to handle toggle behavior
        Gtk.ToggleButton.do_clicked(self)

        if self.palette:
            self.palette.popdown(True)
