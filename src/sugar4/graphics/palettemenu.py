# Copyright 2012 One Laptop Per Child
# Copyright (C) 2025 MostlyK
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
PaletteMenu
=======================

The palettemenu module is the main port of call for making palettes.
It covers creating menu items, separators and placing them in a box.

This implementation modernizes the palette menu system while maintaining
compatibility with Sugar's palette interface patterns.

Example:

    Create a palette menu with 2 items with a separator in the middle.

    .. code-block:: python

        from gi.repository import Gtk
        from gettext import gettext as _

        from sugar4.graphics.palette import Palette
        from sugar4.graphics.palettemenu import PaletteMenuBox
        from sugar4.graphics.palettemenu import PaletteMenuItem
        from sugar4.graphics.palettemenu import PaletteMenuItemSeparator


        class ItemPalette(Palette):
            def __init__(self):
                Palette.__init__(
                    self, primary_text='List Item')
                box = PaletteMenuBox()
                self.set_content(box)

                menu_item = PaletteMenuItem(
                    _('Edit'), icon_name='toolbar-edit')
                menu_item.connect('activate', self.__edit_cb)
                box.append_item(menu_item)

                sep = PaletteMenuItemSeparator()
                box.append_item(sep)

                menu_item = PaletteMenuItem(
                    _('Delete'), icon_name='edit-delete')
                box.append_item(menu_item)

            def __edit_cb(self, menu_item):
                print('Edit...')

        # Usually the Palette instance is returned in a create_palette function
        p = ItemPalette()
        p.popup()

    Add a palettebox to a toolbutton:

    .. code-block:: python

        image = ToolButton('insert-picture')
        image.set_tooltip(_('Insert Image'))
        toolbar_box.toolbar.insert(image, -1)

        palette = image.get_palette()
        box = PaletteMenuBox()
        palette.set_content(box)

        menu_item = PaletteMenuItem(_('Floating'))
        menu_item.connect('activate', self.__image_cb, True)
        box.append_item(menu_item)
"""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk, Gdk
import logging

from sugar4.graphics.icon import Icon
from sugar4.graphics import style


class PaletteMenuBox(Gtk.Box):
    """
    The PaletteMenuBox is a box that is useful for making palettes.

    It supports adding :class:`sugar4.graphics.palettemenu.PaletteMenuItem`,
    :class:`sugar4.graphics.palettemenu.PaletteMenuItemSeparator` and
    it automatically adds padding to other widgets.

    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_spacing(2)  # Small default spacing

    def append_item(
        self, item_or_widget, horizontal_padding=None, vertical_padding=None
    ):
        """
        Add a menu item, separator or other widget to the end of the palette
        (similar to `Gtk.Box.append`).

        If an item is appended
        (a :class:`sugar4.graphics.palettemenu.PaletteMenuItem` or a
        :class:`sugar4.graphics.palettemenu.PaletteMenuItemSeparator`) no
        padding will be added, as that is handled by the item. If a widget is
        appended (:class:`Gtk.Widget` subclass) padding will be added.

        Args:
            item_or_widget (:class:`Gtk.Widget` or menu item or separator):
                item or widget to add to the palette
            horizontal_padding (int): by default,
                :class:`sugar4.graphics.style.DEFAULT_SPACING` is applied
            vertical_padding (int): by default,
                :class:`sugar4.graphics.style.DEFAULT_SPACING` is applied

        Returns:
            None
        """
        item = None
        if isinstance(item_or_widget, PaletteMenuItem) or isinstance(
            item_or_widget, PaletteMenuItemSeparator
        ):
            item = item_or_widget
        else:
            item = self._wrap_widget(
                item_or_widget, horizontal_padding, vertical_padding
            )

        self.append(item)

    def _wrap_widget(self, widget, horizontal_padding, vertical_padding):
        """Wrap a widget with padding containers."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        if horizontal_padding is None:
            horizontal_padding = style.DEFAULT_SPACING

        if vertical_padding is None:
            vertical_padding = style.DEFAULT_SPACING

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_margin_top(vertical_padding)
        hbox.set_margin_bottom(vertical_padding)
        vbox.append(hbox)

        hbox.set_margin_start(horizontal_padding)
        hbox.set_margin_end(horizontal_padding)
        hbox.append(widget)

        return vbox


class PaletteMenuItemSeparator(Gtk.Separator):
    """
    Horizontal separator to put in a palette.

    """

    __gtype_name__ = "SugarPaletteMenuItemSeparator"

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        # Set minimum height for the separator
        self.set_size_request(-1, style.DEFAULT_SPACING * 2)

        self.add_css_class("palette-menu-separator")

    def _apply_separator_styling(self):
        """Apply CSS styling for the separator using centralized theme.
        
        CSS is defined in sugar-gtk4.css or sugar-artwork themes to avoid
        duplication and maintain consistency with Sugar design.
        """
        # CSS styling is managed by the centralized theme loader


class PaletteMenuItem(Gtk.Button):
    """
    A palette menu item is a line of text, and optionally an icon, that the
    user can activate.

    The `activate` signal is usually emitted when the item is clicked. It has
    no arguments. When a menu item is activated, the palette is also closed.

    This implementation replaces EventBox with Button for better accessibility
    and modern interaction patterns.

    Args:
        text_label (str): a text to display in the menu

        icon_name (str): the name of a sugar icon to be displayed. Takes
            precedence over file_name

        text_maxlen (int): the desired maximum width of the label, in
            characters. By default set to 60 chars

        xo_color (:class:`sugar4.graphics.XoColor`): the color to be applied to
            the icon

        file_name (str): the path to a svg file used as icon

        accelerator (str): a text used to display the keyboard shortcut
            associated to the menu
    """

    __gtype_name__ = "SugarPaletteMenuItem"

    __gsignals__ = {"item-activated": (GObject.SignalFlags.RUN_FIRST, None, [])}

    def __init__(
        self,
        text_label=None,
        icon_name=None,
        text_maxlen=60,
        xo_color=None,
        file_name=None,
        accelerator=None,
    ):
        super().__init__()

        self.icon = None
        self._accelerator_label = None

        # main horizontal box
        self._hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._hbox.set_margin_start(style.DEFAULT_PADDING)
        self._hbox.set_margin_end(style.DEFAULT_PADDING)
        self._hbox.set_margin_top(style.DEFAULT_PADDING // 2)
        self._hbox.set_margin_bottom(style.DEFAULT_PADDING // 2)

        # icon if specified
        if icon_name is not None:
            self.icon = Icon(icon_name=icon_name, pixel_size=style.SMALL_ICON_SIZE)
            if xo_color is not None:
                self.icon.set_xo_color(xo_color)
            self._hbox.append(self.icon)
        elif file_name is not None:
            self.icon = Icon(file_name=file_name, pixel_size=style.SMALL_ICON_SIZE)
            if xo_color is not None:
                self.icon.set_xo_color(xo_color)
            self._hbox.append(self.icon)

        if text_label is not None:
            self.label = Gtk.Label(label=text_label)
            self.label.set_halign(Gtk.Align.START)
            self.label.set_hexpand(True)
            # Force black text
            # TODO: Can also not do this based on feedback
            self.label.add_css_class("force-black")
            from sugar4.graphics import style as _style

            _style.apply_css_to_widget(self.label, ".force-black { color: #000000; }")

            if text_maxlen > 0:
                self.label.set_max_width_chars(text_maxlen)
                self.label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)

            self._hbox.append(self.label)
        else:
            self.label = None

        if accelerator is not None:
            self.set_accelerator(accelerator)

        self.set_child(self._hbox)

        self.add_css_class("palette-menu-item")
        self._apply_menu_item_styling()

        # gesture controllers for hover effects
        self._setup_gestures()

        # Connect to activate signal
        self.connect("activate", self._clicked_cb)

    def _on_activate(self, button):
        """Handle button activation - emits our custom signal."""
        # this has been done to remove the conflict with Gtk.Button's activate
        self.emit("item-activated")

    def _apply_menu_item_styling(self):
        """Apply CSS styling for palette menu items using centralized theme.
        
        CSS is defined in sugar-gtk4.css (.palette-menu-item class) or 
        sugar-artwork themes to avoid duplication and maintain consistency.
        """
        # CSS styling is managed by the centralized theme loader

    def _setup_gestures(self):
        """Set up gesture controllers for hover effects."""
        # Mouse enter/leave events
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self._on_enter_notify)
        motion_controller.connect("leave", self._on_leave_notify)
        self.add_controller(motion_controller)

    def _clicked_cb(self, button):
        """Handle button click and emit activate signal."""
        self.emit("activate")

    def _on_enter_notify(self, controller, x, y):
        """Handle mouse enter event."""
        # TODO: Add Hover Effect
        pass

    def _on_leave_notify(self, controller):
        """Handle mouse leave event."""
        # TODO: Add hover Effect
        pass

    def set_label(self, text_label):
        # Overriding parameter here!
        """
        Set the text label of the menu item.

        Args:
            text_label (str): New text to display
        """
        if self.label:
            self.label.set_text(text_label)

    def get_label(self):
        """
        Get the current text of the menu item.

        Returns:
            str: Current text or empty string
        """
        if self.label:
            return self.label.get_text()
        return ""

    def set_image(self, icon):
        """
        Set the icon of the menu item.

        Args:
            icon (Icon): Icon widget to display
        """
        if self.icon:
            self._hbox.remove(self.icon)

        self.icon = icon
        if icon:
            # Insert icon at the beginning
            self._hbox.prepend(icon)

    def set_accelerator(self, text):
        """
        Set the accelerator text for the menu item.

        Args:
            text (str): Accelerator text to display (e.g., "Ctrl+S")
        """
        if self._accelerator_label:
            self._hbox.remove(self._accelerator_label)
            self._accelerator_label = None

        if text:
            self._accelerator_label = Gtk.Label(label=text)
            self._accelerator_label.set_halign(Gtk.Align.END)
            self._accelerator_label.add_css_class("dim-label")
            # Force black text for accelerator label
            self._accelerator_label.add_css_class("force-black")
            from sugar4.graphics import style as _style

            _style.apply_css_to_widget(
                self._accelerator_label, ".force-black { color: #000000; }"
            )
            self._hbox.append(self._accelerator_label)

    def set_sensitive(self, sensitive):
        """
        Set the sensitivity of the menu item.

        Args:
            sensitive (bool): Whether the item should be sensitive
        """
        super().set_sensitive(sensitive)

        if sensitive:
            self.remove_css_class("disabled")
        else:
            self.add_css_class("disabled")


# Convenience functions for creating common menu items


def create_menu_item(text, icon_name=None, callback=None, accelerator=None):
    """
    Create a basic menu item with common parameters.

    Args:
        text (str): Menu item text
        icon_name (str): Optional icon name
        callback (function): Optional callback function
        accelerator (str): Optional accelerator text

    Returns:
        PaletteMenuItem: The created menu item
    """
    item = PaletteMenuItem(
        text_label=text, icon_name=icon_name, accelerator=accelerator
    )
    if callback:
        item.connect("activate", callback)
    return item


def create_separator():
    """
    Create a menu separator.

    Returns:
        PaletteMenuItemSeparator: The created separator
    """
    return PaletteMenuItemSeparator()


def create_submenu_item(text, submenu_items, icon_name=None):
    """
    Create a menu item that expands to show submenu items.

    Args:
        text (str): Menu item text
        submenu_items (list): List of submenu items
        icon_name (str): Optional icon name

    Returns:
        PaletteMenuItem: The created submenu item
    """
    # This is a placeholder for submenu functionality
    # In a full implementation, this would create an expandable menu item
    item = PaletteMenuItem(text_label=f"{text} ►", icon_name=icon_name)
    return item


# Additional utility classes


class PaletteMenuGroup:
    """
    A group of related menu items that can be managed together.
    """

    def __init__(self, name=None):
        self.name = name
        self.items = []

    def add_item(self, item):
        """Add an item to this group."""
        self.items.append(item)

    def set_sensitive(self, sensitive):
        """Set sensitivity of all items in the group."""
        for item in self.items:
            item.set_sensitive(sensitive)

    def set_visible(self, visible):
        """Set visibility of all items in the group."""
        for item in self.items:
            item.set_visible(visible)


class PaletteMenuBuilder:
    """
    Builder class for creating complex palette menus.
    """

    def __init__(self):
        self.menu_box = PaletteMenuBox()
        self.groups = {}

    def add_item(
        self, text, icon_name=None, callback=None, accelerator=None, group=None
    ):
        """Add a menu item to the builder."""
        item = create_menu_item(text, icon_name, callback, accelerator)
        self.menu_box.append_item(item)

        if group:
            if group not in self.groups:
                self.groups[group] = PaletteMenuGroup(group)
            self.groups[group].add_item(item)

        return item

    def add_separator(self):
        """Add a separator to the builder."""
        separator = create_separator()
        self.menu_box.append_item(separator)
        return separator

    def get_menu_box(self):
        """Get the constructed menu box."""
        return self.menu_box

    def get_group(self, name):
        """Get a menu group by name."""
        return self.groups.get(name)
