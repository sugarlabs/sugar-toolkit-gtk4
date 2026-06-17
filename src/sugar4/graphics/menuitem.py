# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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
MenuItem
===================

Sugar-style menu items with icon and accelerator support.
This implementation replaces deprecated ImageMenuItem with modern equivalents.
"""

import logging
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk, Gio

from sugar4.graphics.icon import Icon
from sugar4.graphics import style


class MenuItem(Gtk.Button):
    """
    A Sugar-style menu item with icon and text support.

    This replaces the deprecated ImageMenuItem with a Button
    that can be used in menus and popover menus.

    Args:
        text_label (str): Text to display on the menu item
        icon_name (str): Name of icon to display
        text_maxlen (int): Maximum text length before ellipsizing
        xo_color: XO color scheme for the icon
        file_name (str): Path to icon file
    """

    __gtype_name__ = "SugarMenuItem"

    def __init__(
        self,
        text_label: Optional[str] = None,
        icon_name: Optional[str] = None,
        text_maxlen: int = style.MENU_WIDTH_CHARS,
        xo_color=None,
        file_name: Optional[str] = None,
    ):
        super().__init__()

        self._accelerator = None
        self._action_name = None

        # horizontal box for content
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content_box.set_margin_start(6)
        content_box.set_margin_end(6)
        content_box.set_margin_top(4)
        content_box.set_margin_bottom(4)

        if icon_name is not None:
            icon = Icon(icon_name=icon_name, pixel_size=style.SMALL_ICON_SIZE)
            if xo_color is not None:
                icon.set_xo_color(xo_color)
            content_box.append(icon)
        elif file_name is not None:
            icon = Icon(file_name=file_name, pixel_size=style.SMALL_ICON_SIZE)
            if xo_color is not None:
                icon.set_xo_color(xo_color)
            content_box.append(icon)

        if text_label is not None:
            self._label = Gtk.Label(label=text_label)
            self._label.set_halign(Gtk.Align.START)
            self._label.set_hexpand(True)
            self._label.set_hexpand(True)

            if text_maxlen > 0:
                self._label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
                self._label.set_max_width_chars(text_maxlen)

            content_box.append(self._label)
        else:
            self._label = None

        self.set_child(content_box)

        # Style the button to look like a menu item
        self.add_css_class("menuitem")
        self.add_css_class("flat")
        self._apply_menu_item_styling()

        # Connect signals for accelerator handling
        self.connect("map", self._on_mapped)
        self.connect("unmap", self._on_unmapped)

    def set_image(self, icon):
        """
        Set the icon of the menu item.
        """
        content_box = self.get_child()
        if not content_box:
            return
            
        # Remove existing icon if there is one
        child = content_box.get_first_child()
        while child:
            if isinstance(child, Icon):
                content_box.remove(child)
                break
            child = child.get_next_sibling()
            
        if icon:
            content_box.prepend(icon)

    def _apply_menu_item_styling(self):
        """Apply CSS styling to make button look like a menu item."""
        css = """
        button.menuitem {
            background: transparent;
            border: none;
            border-radius: 4px;
            padding: 4px 6px;
        }
        button.menuitem:hover {
            background: alpha(currentColor, 0.1);
        }
        button.menuitem:active {
            background: alpha(currentColor, 0.2);
        }
        """
        style.apply_css_to_widget(self, css)

    def _on_mapped(self, widget):
        """Handle widget being mapped (shown)."""
        self._add_accelerator()

    def _on_unmapped(self, widget):
        """Handle widget being unmapped (hidden)."""
        self._remove_accelerator()

    def _add_accelerator(self):
        """Add keyboard accelerator to the menu item."""
        if self._accelerator is None:
            return

        # Get the application and add accelerator
        app = Gio.Application.get_default()
        if app is None:
            logging.debug("No application available for accelerator")
            return

        # Parse accelerator
        success, _, _ = Gtk.accelerator_parse(self._accelerator)
        if not success:
            logging.warning(f"Invalid accelerator: {self._accelerator}")
            return

        action_name = f"menuitem-{id(self)}"
        action = Gio.SimpleAction.new(action_name, None)
        action.connect("activate", self._on_accelerator_activated)
        app.add_action(action)

        # I added the fallback in case the application does not support set_accels_for_action
        if hasattr(app, "set_accels_for_action"):
            app.set_accels_for_action(f"app.{action_name}", [self._accelerator])
        else:
            logging.warning(
                "set_accels_for_action is not available on this Application instance"
            )

        self._action_name = action_name

    def _remove_accelerator(self):
        """Remove keyboard accelerator."""
        if self._action_name:
            app = Gio.Application.get_default()
            if app:
                app.remove_action(self._action_name)
                if hasattr(app, "set_accels_for_action"):
                    app.set_accels_for_action(f"app.{self._action_name}", [])
                else:
                    logging.warning(
                        "set_accels_for_action is not available on this Application instance"
                    )
                self._action_name = None

    def _on_accelerator_activated(self, action, parameter):
        """Handle accelerator activation."""
        if self.get_sensitive():
            self.emit("clicked")

    def set_accelerator(self, accelerator: Optional[str]):
        """
        Set keyboard accelerator for this menu item.

        Args:
            accelerator (str): Accelerator string (e.g., '<Ctrl>s')
        """
        if self._accelerator == accelerator:
            return

        self._remove_accelerator()
        self._accelerator = accelerator
        self._add_accelerator()

    def get_accelerator(self) -> Optional[str]:
        """
        Get the current accelerator string.

        Returns:
            str: Current accelerator or None
        """
        return self._accelerator

    def set_text(self, text: str):
        """
        Set the text label of the menu item.

        Args:
            text (str): New text to display
        """
        if self._label:
            self._label.set_text(text)

    def get_text(self) -> str:
        """
        Get the current text of the menu item.

        Returns:
            str: Current text or empty string
        """
        if self._label:
            return self._label.get_text()
        return ""

    def get_submenu(self):
        return getattr(self, '_submenu', None)

    def set_submenu(self, submenu):
        self._submenu = submenu
        if hasattr(self, '_popover') and self._popover:
            self._popover.unparent()
            self._popover = None
            
        if submenu is not None:
            self._popover = Gtk.PopoverMenu.new_from_model(submenu)
            self._popover.set_parent(self)
            self._popover.set_position(Gtk.PositionType.RIGHT)
            
            # Show popover when clicked
            if not hasattr(self, '_popover_click_handler'):
                self._popover_click_handler = self.connect('clicked', self._show_popover)
        else:
            if hasattr(self, '_popover_click_handler'):
                self.disconnect(self._popover_click_handler)
                del self._popover_click_handler

    def _show_popover(self, button):
        if hasattr(self, '_popover') and self._popover:
            self._popover.popup()

    # Properties for compatibility
    accelerator = GObject.Property(
        type=str,
        setter=set_accelerator,
        getter=get_accelerator,
        nick="Accelerator",
        blurb="Keyboard accelerator for this menu item",
    )


class MenuSeparator(Gtk.Separator):
    """
    A separator for use in menus.

    Simple wrapper around Gtk.Separator with menu-appropriate styling.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("menu-separator")
        self._apply_separator_styling()

    def _apply_separator_styling(self):
        """Apply styling for menu separator."""
        css = """
        separator.menu-separator {
            margin: 2px 6px;
            min-height: 1px;
            background: alpha(@theme_fg_color, 0.2);
        }
        """
        style.apply_css_to_widget(self, css)
