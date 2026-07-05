# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2025 MostlyK
#
# SPDX-License-Identifier: LGPL-2.1-or-later
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
The combobox module provides a combo box; a button like widget which
creates a list popup when clicked.  It's best used outside of a
toolbar when the user needs to choose from a *short* list of items.

Example:

.. literalinclude:: ../examples/combobox.py
"""

from gi.repository import Gdk, Gio, GObject, Gtk, GdkPixbuf


class _ComboBoxItem(GObject.Object):
    """Internal GObject wrapper for items stored in the Gio.ListStore."""

    __gtype_name__ = "SugarComboBoxItem"

    value = GObject.Property(type=object)
    text = GObject.Property(type=str, default="")
    icon_name = GObject.Property(type=str, default="")
    file_name = GObject.Property(type=str, default="")
    is_separator = GObject.Property(type=bool, default=False)


class ComboBox(Gtk.Box):
    """
    This class provides a combo box widget based on :class:`Gtk.DropDown`
    and :class:`Gio.ListStore`.  This lets you make a list of items,
    with a value, label and optionally an icon.
    """

    __gtype_name__ = "SugarComboBox"

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, []),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self._model = Gio.ListStore.new(_ComboBoxItem)
        self._has_icons = False

        self._factory = Gtk.SignalListItemFactory()
        self._factory.connect("setup", self._on_factory_setup)
        self._factory.connect("bind", self._on_factory_bind)

        self._dropdown = Gtk.DropDown(model=self._model, factory=self._factory)
        self._dropdown.set_hexpand(True)
        self._dropdown.set_selected(Gtk.INVALID_LIST_POSITION)
        self._dropdown.connect("notify::selected", self._on_selected_changed)

        self.append(self._dropdown)

    def _on_factory_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        icon = Gtk.Image()
        icon.set_visible(False)
        box.append(icon)
        label = Gtk.Label(xalign=0)
        box.append(label)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_hexpand(True)
        separator.set_visible(False)
        box.append(separator)
        list_item.set_child(box)

    def _on_factory_bind(self, factory, list_item):
        box = list_item.get_child()
        icon = box.get_first_child()
        label = icon.get_next_sibling()
        separator = label.get_next_sibling()
        item = list_item.get_item()

        if item.is_separator:
            icon.set_visible(False)
            label.set_visible(False)
            separator.set_visible(True)
            list_item.set_selectable(False)
        else:
            separator.set_visible(False)
            if item.text:
                label.set_text(item.text)
                label.set_visible(True)
            else:
                label.set_visible(False)

            if self._has_icons and (item.icon_name or item.file_name):
                if item.icon_name:
                    file_name = self._get_real_name_from_theme(
                        item.icon_name, 16 if item.text else 24
                    )
                else:
                    file_name = item.file_name
                try:
                    size = 16 if item.text else 24
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        file_name, size, size
                    )
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    icon.set_from_paintable(texture)
                    icon.set_visible(True)
                except Exception:
                    icon.set_visible(False)
            else:
                icon.set_visible(False)

    def _on_selected_changed(self, dropdown, pspec):
        if dropdown.get_selected() != Gtk.INVALID_LIST_POSITION:
            self.emit("changed")

    def get_value(self):
        """
        The value of the currently selected item; the same as the `value`
        argument that was passed to the `append_item` func.

        Returns:
            object, value of selected item
        """
        row = self.get_active_item()
        if not row:
            return None
        return row[0]

    value = GObject.Property(type=object, getter=get_value, setter=None)

    def _get_real_name_from_theme(self, name, size):
        try:
            try:
                display = self._dropdown.get_display()
            except Exception:
                display = Gdk.Display.get_default()

            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_info = icon_theme.lookup_icon(
                name, None, size, 1, Gtk.TextDirection.NONE, 0
            )
            if not icon_info:
                raise ValueError("Icon %r not found." % name)
            fname = icon_info.get_file().get_path()
            return fname
        except Exception as e:
            raise ValueError("Icon %r not found: %s" % (name, str(e)))

    def append_item(self, value, text, icon_name=None, file_name=None):
        """
        This function adds another item to the bottom of the combo box list.

        If either `icon_name` or `file_name` are supplied and icon column
        will be added to the combo box list.

        Args:
            value (object):  the value that will be returned by `get_value`,
                when this item is selected
            text (str):  the user visible label for the item
            icon_name (str):  the name of the icon in the theme to use for
                this item, optional and conflicting with `file_name`
            file_name (str):  the path to a sugar (svg) icon to use for this
                item, optional and conflicting with `icon_name`
        """
        if icon_name or file_name:
            self._has_icons = True

        item = _ComboBoxItem(
            value=value,
            text=text or "",
            icon_name=icon_name or "",
            file_name=file_name or "",
            is_separator=False,
        )
        self._model.append(item)

    def append_separator(self):
        """
        Add a separator to the bottom of the combo box list.  The separator
        can not be selected.
        """
        item = _ComboBoxItem(is_separator=True)
        self._model.append(item)

    def get_active_item(self):
        """
        Get the row of data for the currently selected item.

        Returns:
            row of data in the format::

                [value, text, icon_name, is_separator]

            or None if nothing is selected.
        """
        index = self._dropdown.get_selected()
        if index == Gtk.INVALID_LIST_POSITION:
            return None
        item = self._model.get_item(index)
        if not item:
            return None
        return [item.value, item.text, item.icon_name, item.is_separator]

    def get_active(self):
        """
        Get the index of the currently selected item.

        Returns:
            int, index of selected item or -1 if none selected.
        """
        index = self._dropdown.get_selected()
        if index == Gtk.INVALID_LIST_POSITION:
            return -1
        return index

    def set_active(self, index):
        """
        Set the active item by index.

        Args:
            index (int):  the index of the item to select, or -1 to deselect.
        """
        if index < 0 or index >= self._model.get_n_items():
            self._dropdown.set_selected(Gtk.INVALID_LIST_POSITION)
        else:
            self._dropdown.set_selected(index)

    def remove_all(self):
        """
        Remove all list items from the combo box.
        """
        self._model.remove_all()
        self._has_icons = False
