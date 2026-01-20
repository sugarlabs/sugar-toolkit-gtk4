# Copyright (C) 2007, Red Hat, Inc.
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
Toolbox
==================

A toolbox holds a group of toolbars in a list. One toolbar is displayed
at a time. Toolbars are assigned an index and can be accessed using this index.
Indices are generated in the order the toolbars are added.

"""

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject

from sugar4.graphics import style


class Toolbox(Gtk.Box):
    """
    Class to represent the toolbox of an activity. Groups a
    number of toolbars vertically, which can be accessed using their
    indices. The current toolbar is the only one displayed.

    Emits `current-toolbar-changed` signal when the
    current toolbar is changed. This signal takes the current page index
    as an argument.
    """

    __gtype_name__ = "SugarToolbox"

    __gsignals__ = {
        "current-toolbar-changed": (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._notebook = Gtk.Notebook()
        self._notebook.set_tab_pos(Gtk.PositionType.BOTTOM)
        self._notebook.set_show_border(False)
        self._notebook.set_show_tabs(False)
        self._notebook.set_hexpand(True)
        self._notebook.set_vexpand(True)
        self.append(self._notebook)

        # horizontal separator as we had Gtk.HSeparator before.
        self._separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._separator.set_visible(False)
        self.append(self._separator)

        self._apply_toolbox_styling()

        self._notebook.connect("notify::page", self._notify_page_cb)

    def _apply_toolbox_styling(self):
        """Apply Sugar-style toolbox styling using centralized CSS classes.
        
        CSS classes (defined in sugar-gtk4.css or sugar-artwork themes):
        - toolbox: Applied to the notebook widget
        - toolbox-separator: Applied to the separator widget
        """
        self._notebook.add_css_class("toolbox")
        self._separator.add_css_class("toolbox-separator")

    def _notify_page_cb(self, notebook, pspec):
        """Handle page change notification."""
        current_page = notebook.get_current_page()
        self.emit("current-toolbar-changed", current_page)

    def add_toolbar(self, name: str, toolbar: Gtk.Widget):
        """
        Adds a toolbar to this toolbox. Toolbar will be added
        to the end of this toolbox, and its index will be
        1 greater than the previously added index (index will be
        0 if it is the first toolbar added).

        Args:
            name (str): name of toolbar to be added
            toolbar (Gtk.Widget): Widget to be appended to this toolbox
        """
        label = Gtk.Label(label=name)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)

        # Set minimum width for consistent tab sizing
        label.set_size_request(style.TOOLBOX_TAB_LABEL_WIDTH, -1)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.set_hexpand(True)
        container.set_vexpand(True)
        container.set_margin_start(style.TOOLBOX_HORIZONTAL_PADDING)
        container.set_margin_end(style.TOOLBOX_HORIZONTAL_PADDING)
        container.append(toolbar)

        page_num = self._notebook.append_page(container, label)

        # Show tabs if we have more than one page
        if self._notebook.get_n_pages() > 1:
            self._notebook.set_show_tabs(True)
            self._separator.set_visible(True)

        return page_num

    def remove_toolbar(self, index: int):
        """
        Removes toolbar at the index specified.

        Args:
            index (int): index of the toolbar to be removed
        """
        if index < 0 or index >= self._notebook.get_n_pages():
            raise IndexError(f"Toolbar index {index} out of range")

        self._notebook.remove_page(index)

        if self._notebook.get_n_pages() < 2:
            self._notebook.set_show_tabs(False)
            self._separator.set_visible(False)

    def set_current_toolbar(self, index: int):
        """
        Sets the current toolbar to that of the index specified and
        displays it.

        Args:
            index (int): index of toolbar to be set as current toolbar
        """
        if index < 0 or index >= self._notebook.get_n_pages():
            raise IndexError(f"Toolbar index {index} out of range")

        self._notebook.set_current_page(index)

    def get_current_toolbar(self) -> int:
        """
        Returns current toolbar index.

        Returns:
            int: Index of current toolbar
        """
        return self._notebook.get_current_page()

    def get_toolbar_count(self) -> int:
        """
        Returns the number of toolbars in this toolbox.

        Returns:
            int: Number of toolbars
        """
        return self._notebook.get_n_pages()

    def get_toolbar_at(self, index: int) -> Optional[Gtk.Widget]:
        """
        Get the toolbar widget at the specified index.

        Args:
            index (int): Index of toolbar to retrieve

        Returns:
            Gtk.Widget: Toolbar widget or None if index is invalid
        """
        if index < 0 or index >= self._notebook.get_n_pages():
            return None

        page = self._notebook.get_nth_page(index)
        if page and isinstance(page, Gtk.Box):
            # Return the first child (the actual toolbar)
            child = page.get_first_child()
            return child
        return page

    def set_toolbar_label(self, index: int, label: str):
        """
        Set the label text for a toolbar tab.

        Args:
            index (int): Index of toolbar
            label (str): New label text
        """
        if index < 0 or index >= self._notebook.get_n_pages():
            raise IndexError(f"Toolbar index {index} out of range")

        page = self._notebook.get_nth_page(index)
        tab_label = self._notebook.get_tab_label(page)
        if isinstance(tab_label, Gtk.Label):
            tab_label.set_text(label)

    def get_toolbar_label(self, index: int) -> Optional[str]:
        """
        Get the label text for a toolbar tab.

        Args:
            index (int): Index of toolbar

        Returns:
            str: Label text or None if index is invalid
        """
        if index < 0 or index >= self._notebook.get_n_pages():
            return None

        page = self._notebook.get_nth_page(index)
        tab_label = self._notebook.get_tab_label(page)
        if isinstance(tab_label, Gtk.Label):
            return tab_label.get_text()
        return None

    current_toolbar = property(get_current_toolbar, set_current_toolbar)
