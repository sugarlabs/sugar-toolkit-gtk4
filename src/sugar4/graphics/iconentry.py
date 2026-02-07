# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2025 Sugar Labs Community
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
IconEntry
=========

A text entry widget with support for displaying icons at primary and
secondary positions. Extends :class:`Gtk.Entry` with Sugar-styled icon
management (themed SVG icons with color substitution) and a built-in
clear button pattern.

Classes:
    IconEntry: Entry widget with icon support and clear button.

Constants:
    ICON_ENTRY_PRIMARY: Icon position at the start of the entry.
    ICON_ENTRY_SECONDARY: Icon position at the end of the entry.

Example usage::

    from sugar4.graphics import iconentry

    entry = iconentry.IconEntry()
    entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY, 'entry-search')
    entry.add_clear_button()
"""

import logging

import cairo
from gi.repository import Gdk, GdkPixbuf, GLib, GObject, Gtk, Rsvg

from sugar4.graphics import style
from sugar4.graphics.icon import _SVGLoader

ICON_ENTRY_PRIMARY = Gtk.EntryIconPosition.PRIMARY
ICON_ENTRY_SECONDARY = Gtk.EntryIconPosition.SECONDARY

_ICON_SIZE = 24


class IconEntry(Gtk.Entry):
    """A text entry widget with icon support at primary and secondary positions.

    Provides Sugar-specific SVG icon loading with color substitution and
    a built-in clear button that appears when text is present.
    """

    __gtype_name__ = "SugarIconEntry"

    def __init__(self):
        GObject.GObject.__init__(self)

        self._clear_shown = False
        self._clear_button_added = False
        self._loader = _SVGLoader()

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._keypress_event_cb)
        self.add_controller(key_controller)

    def set_icon_from_name(self, position, name):
        """Set an icon by theme name with Sugar color substitution.

        Looks up the icon in the current theme. If it is an SVG file,
        applies Sugar toolbar grey color substitution before rendering.

        Args:
            position: :data:`ICON_ENTRY_PRIMARY` or :data:`ICON_ENTRY_SECONDARY`
            name: Icon theme name (e.g. ``'entry-search'``, ``'entry-cancel'``)
        """
        display = Gdk.Display.get_default()
        if display is None:
            logging.warning("IconEntry set_icon_from_name: no display available.")
            return

        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_paintable = icon_theme.lookup_icon(
            name,
            None,
            _ICON_SIZE,
            1,
            Gtk.TextDirection.NONE,
            Gtk.IconLookupFlags.NONE,
        )

        if not icon_paintable:
            logging.warning(
                "IconEntry set_icon_from_name: icon '%s' not found in the theme.",
                name,
            )
            return

        file_obj = icon_paintable.get_file()
        if not file_obj:
            logging.warning(
                "IconEntry set_icon_from_name: could not resolve file for icon '%s'.",
                name,
            )
            return

        file_name = file_obj.get_path()
        if not file_name:
            logging.warning(
                "IconEntry set_icon_from_name: no local path for icon '%s'.",
                name,
            )
            return

        if file_name.endswith(".svg"):
            entities = {
                "fill_color": style.COLOR_TOOLBAR_GREY.get_svg(),
                "stroke_color": style.COLOR_TOOLBAR_GREY.get_svg(),
            }
            handle = self._loader.load(file_name, entities, True)
            if handle is None:
                logging.warning(
                    "IconEntry set_icon_from_name: failed to load SVG icon '%s'.",
                    name,
                )
                return

            svg_rect = handle.get_intrinsic_size_in_pixels()
            if svg_rect[0]:  # has_width
                width, height = svg_rect[1], svg_rect[2]
            else:
                width, height = _ICON_SIZE, _ICON_SIZE

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
            context = cairo.Context(surface)
            viewport = Rsvg.Rectangle()
            viewport.x = 0
            viewport.y = 0
            viewport.width = float(width)
            viewport.height = float(height)
            handle.render_document(context, viewport)

            pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, int(width), int(height))
            if pixbuf is None:
                logging.warning(
                    "IconEntry set_icon_from_name: failed to render SVG icon '%s'.",
                    name,
                )
                return
            self.set_icon(position, pixbuf)
        else:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    file_name, _ICON_SIZE, _ICON_SIZE
                )
                self.set_icon(position, pixbuf)
            except GLib.Error as e:
                logging.warning(
                    "IconEntry set_icon_from_name: failed to load icon '%s': %s",
                    name,
                    e,
                )

    def set_icon(self, position, pixbuf):
        """Set an icon from a pixbuf.

        Args:
            position: :data:`ICON_ENTRY_PRIMARY` or :data:`ICON_ENTRY_SECONDARY`
            pixbuf: A :class:`GdkPixbuf.Pixbuf` to display as the icon.
        """
        if not isinstance(pixbuf, GdkPixbuf.Pixbuf):
            raise ValueError("Argument must be a pixbuf, not %r." % pixbuf)
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        self.set_icon_from_paintable(position, texture)

    def remove_icon(self, position):
        """Remove the icon at the given position.

        Args:
            position: :data:`ICON_ENTRY_PRIMARY` or :data:`ICON_ENTRY_SECONDARY`
        """
        self.set_icon_from_paintable(position, None)

    def add_clear_button(self):
        """Add a clear button that appears when text is present.

        The clear button is shown as an ``entry-cancel`` icon in the
        secondary position. Clicking it or pressing Escape clears the
        entry text.
        """
        if self._clear_button_added:
            return

        self._clear_button_added = True

        if self.get_text():
            self.show_clear_button()
        else:
            self.hide_clear_button()

        self.connect("icon-press", self._icon_pressed_cb)
        self.connect("changed", self._changed_cb)

    def show_clear_button(self):
        """Show the clear button in the secondary icon position."""
        if not self._clear_shown:
            self.set_icon_from_name(ICON_ENTRY_SECONDARY, "entry-cancel")
            self._clear_shown = True

    def hide_clear_button(self):
        """Hide the clear button from the secondary icon position."""
        if self._clear_shown:
            self.remove_icon(ICON_ENTRY_SECONDARY)
            self._clear_shown = False

    def _keypress_event_cb(self, controller, keyval, keycode, state):
        """Handle Escape key to clear entry text."""
        if Gdk.keyval_name(keyval) == "Escape":
            self.set_text("")
            return True
        return False

    def _icon_pressed_cb(self, entry, icon_pos):
        """Handle icon click to clear text."""
        if icon_pos == ICON_ENTRY_SECONDARY:
            self.set_text("")
            self.hide_clear_button()

    def _changed_cb(self, icon_entry):
        """Toggle clear button visibility based on text content."""
        if not self.get_text():
            self.hide_clear_button()
        else:
            self.show_clear_button()
