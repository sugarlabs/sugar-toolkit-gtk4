# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2008, One Laptop Per Child
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
ToolButton
=====================

The toolbutton module provides the ToolButton class, which is a
Gtk.Button styled as a toolbar button with icon and tooltip for sugar4.

Example:
    Add a tool button to a window::

        from gi.repository import Gtk
        from sugar4.graphics.toolbutton import ToolButton

        def __clicked_cb(button):
            print("tool button was clicked")

        app = Gtk.Application()

        def on_activate(app):
            w = Gtk.ApplicationWindow(application=app)
            b = ToolButton(icon_name='dialog-ok', tooltip='a tooltip')
            b.connect('clicked', __clicked_cb)
            w.set_child(b)
            w.present()

        app.connect('activate', on_activate)
        app.run()

STABLE.
"""

import logging
import os
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GObject, Graphene, Gsk, Gtk, Pango

from sugar4.debug import debug_print
from sugar4.graphics import style
from sugar4.graphics.icon import Icon
from sugar4.graphics.palette import Palette, ToolInvoker

print = debug_print


def _add_accelerator(tool_button):
    """Add accelerator to tool button."""
    if not tool_button.props.accelerator:
        return

    root = tool_button.get_root()
    if not root:
        return

    # GTK4: Use application shortcuts instead of AccelGroup
    app = root.get_application() if hasattr(root, "get_application") else None
    if app and hasattr(app, "set_accels_for_action"):
        # Create a unique action name for this button
        action_name = f"toolbutton.{id(tool_button)}"

        # Add the action to trigger the button click
        action = Gio.SimpleAction.new(action_name, None)
        action.connect("activate", lambda a, p: tool_button.emit("clicked"))

        if hasattr(app, "add_action"):
            app.add_action(action)
            app.set_accels_for_action(
                f"app.{action_name}", [tool_button.props.accelerator]
            )
        elif hasattr(root, "add_action"):
            root.add_action(action)
            app.set_accels_for_action(
                f"win.{action_name}", [tool_button.props.accelerator]
            )


def _hierarchy_changed_cb(tool_button):
    _add_accelerator(tool_button)


def setup_accelerator(tool_button):
    _add_accelerator(tool_button)
    # GTK4: Connect to root notify signal since hierarchy-changed doesn't exist
    if hasattr(tool_button, "connect"):
        tool_button.connect(
            "notify::root", lambda *args: _hierarchy_changed_cb(tool_button)
        )


class ToolButton(Gtk.Button):
    """
    The ToolButton class manages a Gtk.Button styled as a toolbar button for sugar4.

    This replaces deprecated ToolButton with a modern Button implementation
    styled to look and behave like a traditional toolbar button.

    Args:
        icon_name (str, optional): name of themed icon.
        accelerator (str, optional): keyboard shortcut to activate this button.
        tooltip (str, optional): tooltip displayed on hover.
        hide_tooltip_on_click (bool, optional): Whether tooltip is hidden on click.
    """

    def __init__(self, icon_name=None, **kwargs):
        self._accelerator = kwargs.pop("accelerator", None)
        self._tooltip = kwargs.pop("tooltip", None)
        self._hide_tooltip_on_click = kwargs.pop("hide_tooltip_on_click", True)

        super().__init__(**kwargs)

        # button styling for toolbar appearance
        self.add_css_class("toolbar-button")
        self.set_has_frame(False)
        self.set_can_focus(True)

        self._palette_invoker = ToolInvoker()
        self._palette_invoker.attach(self)

        self._content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._content_box.set_halign(Gtk.Align.CENTER)
        self._content_box.set_valign(Gtk.Align.CENTER)
        self.set_child(self._content_box)

        self._icon_widget = None

        if icon_name:
            self.set_icon_name(icon_name)

        if self._tooltip:
            self.set_tooltip(self._tooltip)

        if self._accelerator:
            self.set_accelerator(self._accelerator)

        self.connect("destroy", self.__destroy_cb)
        self.connect("clicked", self.__clicked_cb)

        self._apply_toolbar_button_css()

    def _apply_toolbar_button_css(self):
        """Apply toolbar button CSS class.
        
        CSS styling is defined in sugar-gtk4.css (.toolbar-button class)
        or sugar-artwork themes, rather than hardcoded here to avoid
        duplication and maintain consistency with Sugar design.
        """
        # CSS classes are applied via sugar-gtk4.css (centralized theme)

    def __destroy_cb(self, widget):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()
            self._palette_invoker = None

    def __clicked_cb(self, button):
        print(f"ToolButton.__clicked_cb: 'clicked' signal received for {button}")
        # Hide tooltip if needed
        if self._hide_tooltip_on_click and self.get_palette():
            palette = self.get_palette()
            if palette is not None:
                if palette.is_up():
                    palette.popdown(immediate=True)
        # Explicitly trigger palette invoker toggle if present
        invoker = self.get_palette_invoker()
        if invoker and getattr(invoker, "_toggle_palette", False):
            print("ToolButton.__clicked_cb: calling invoker.notify_toggle_state()")
            invoker.notify_toggle_state()

    def set_tooltip(self, tooltip: Optional[str]):
        """
        Set the tooltip.

        Args:
            tooltip (string): tooltip to be set.
        """
        if tooltip is None:
            self._tooltip = None
            if hasattr(self, "_palette_invoker") and self._palette_invoker:
                self._palette_invoker.set_palette(None)
            return

        self._tooltip = tooltip

        if not self.get_palette():
            palette = Palette(tooltip)
            self.set_palette(palette)
        else:
            self.get_palette().set_primary_text(tooltip)

        # native tooltip as fallback
        self.set_tooltip_text(tooltip)

    def get_tooltip(self) -> Optional[str]:
        return self._tooltip

    tooltip = GObject.Property(
        type=str,
        setter=set_tooltip,
        getter=get_tooltip,
        nick="Tooltip",
        blurb="Tooltip text for the button",
    )

    def get_hide_tooltip_on_click(self) -> bool:
        """
        Return True if the tooltip is hidden when a user
        clicks on the button, otherwise return False.
        """
        return self._hide_tooltip_on_click

    def set_hide_tooltip_on_click(self, hide_tooltip_on_click: bool):
        """
        Set whether or not the tooltip is hidden when a user
        clicks on the button.

        Args:
            hide_tooltip_on_click (bool): True if the tooltip is
            hidden on click, and False otherwise.
        """
        self._hide_tooltip_on_click = hide_tooltip_on_click

    hide_tooltip_on_click = GObject.Property(
        type=bool,
        default=True,
        getter=get_hide_tooltip_on_click,
        setter=set_hide_tooltip_on_click,
        nick="Hide tooltip on click",
        blurb="Whether to hide tooltip when button is clicked",
    )

    def set_accelerator(self, accelerator: Optional[str]):
        """
        Set accelerator that activates the button.

        Args:
            accelerator(string): accelerator to be set.
        """
        self._accelerator = accelerator
        if accelerator:
            setup_accelerator(self)

    def get_accelerator(self) -> Optional[str]:
        """
        Return accelerator that activates the button.
        """
        return self._accelerator

    accelerator = GObject.Property(
        type=str,
        setter=set_accelerator,
        getter=get_accelerator,
        nick="Accelerator",
        blurb="Keyboard accelerator for the button",
    )

    def set_icon_name(self, icon_name: Optional[str]):
        print(f"[ToolButton] set_icon_name called with: {icon_name}")
        if self._icon_widget:
            self._content_box.remove(self._icon_widget)
            self._icon_widget = None
        if icon_name:
            import os

            if os.path.isabs(icon_name) or icon_name.endswith(
                (".svg", ".png", ".jpg", ".jpeg")
            ):
                print(
                    f"[ToolButton] Icon file exists: {os.path.exists(icon_name)} at {icon_name}"
                )
                self._icon_widget = Icon(
                    file_name=icon_name, pixel_size=style.STANDARD_ICON_SIZE
                )
            else:
                print(f"[ToolButton] Using icon name: {icon_name}")
                self._icon_widget = Icon(
                    icon_name=icon_name, pixel_size=style.STANDARD_ICON_SIZE
                )
            self._content_box.prepend(self._icon_widget)

    def get_icon_name(self) -> Optional[str]:
        """Get the icon name.

        Returns:
            The icon name or None if no icon is set.
        """
        if self._icon_widget and isinstance(self._icon_widget, Icon):
            return self._icon_widget.props.icon_name
        return None

    icon_name = GObject.Property(
        type=str,
        setter=set_icon_name,
        getter=get_icon_name,
        nick="Icon name",
        blurb="Name of the themed icon",
    )

    def set_icon_widget(self, icon_widget: Optional[Gtk.Widget]):
        """Set a custom icon widget.

        Args:
            icon_widget: widget to use as icon.
        """
        # Remove existing icon
        if self._icon_widget:
            self._content_box.remove(self._icon_widget)

        self._icon_widget = icon_widget

        if icon_widget:
            self._content_box.prepend(icon_widget)

    def get_icon_widget(self) -> Optional[Gtk.Widget]:
        return self._icon_widget

    def set_label(self, label: Optional[str]):
        child = self._content_box.get_last_child()
        if child and isinstance(child, Gtk.Label):
            self._content_box.remove(child)

        if label:
            label_widget = Gtk.Label(label=label)
            label_widget.set_ellipsize(Pango.EllipsizeMode.END)
            self._content_box.append(label_widget)

    def get_label(self) -> Optional[str]:
        child = self._content_box.get_last_child()
        if child and isinstance(child, Gtk.Label):
            return child.get_text()
        return None

    def create_palette(self) -> Optional[Palette]:
        return None

    def get_palette(self) -> Optional[Palette]:
        """Get the current palette."""
        if self._palette_invoker:
            return self._palette_invoker.get_palette()
        return None

    def set_palette(self, palette: Optional[Palette]):
        if self._palette_invoker:
            self._palette_invoker.set_palette(palette)

    palette = GObject.Property(
        type=object,
        setter=set_palette,
        getter=get_palette,
        nick="Palette",
        blurb="Palette for the button",
    )

    def get_palette_invoker(self) -> Optional[ToolInvoker]:
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker: Optional[ToolInvoker]):
        if self._palette_invoker:
            self._palette_invoker.detach()

        self._palette_invoker = palette_invoker

        if palette_invoker:
            palette_invoker.attach(self)

    palette_invoker = GObject.Property(
        type=object,
        setter=set_palette_invoker,
        getter=get_palette_invoker,
        nick="Palette invoker",
        blurb="Invoker for the palette",
    )

    def do_snapshot(self, snapshot):
        """Render tool button using snapshot-based drawing."""
        # Call parent implementation first
        Gtk.Widget.do_snapshot(self, snapshot)

        palette = self.get_palette()
        if palette and palette.is_up():
            # Get button allocation
            width = self.get_width()
            height = self.get_height()

            if width > 0 and height > 0:
                # Draw active state border
                color = Gdk.RGBA()
                color.red = 0.0
                color.green = 0.5
                color.blue = 1.0
                color.alpha = 0.8

                rect = Graphene.Rect()
                rect.init(0, 0, width, height)
                rounded = Gsk.RoundedRect()
                rounded.init_from_rect(rect, 6.0)

                # Draw border
                snapshot.append_border(
                    rounded,
                    [2, 2, 2, 2],  # border widths
                    [color, color, color, color],  # border colors
                )

    def set_active(self, active: bool):
        if active:
            self.add_css_class("active")
        else:
            self.remove_css_class("active")

    def get_active(self) -> bool:
        """Get the active state of the button."""
        return self.has_css_class("active")


def _apply_module_css():
    """Apply module-level CSS styling for toolbar buttons.
    
    CSS styling is centralized in sugar-gtk4.css to avoid duplication
    and maintain consistency with sugar-artwork themes. This function
    is kept for backward compatibility but delegates to the theme loader.
    """
    # CSS is now managed by the centralized theme loader
    # See: sugar4.graphics.theme.SugarThemeLoader
    pass


try:
    _apply_module_css()
except Exception:
    pass
