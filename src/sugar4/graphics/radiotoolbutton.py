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
RadioToolButton

Provides a RadioToolButton class, similar to a "push" button.
A group of RadioToolButtons can be set, so that only one can be
selected at a time. When a button is clicked, it depresses and
is shaded darker.

It is also possible to set a tooltip to be dispalyed when the
user scrolls over it with their cursor as well as an accelerator
keyboard shortcut.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")

from gi.repository import Gtk, GObject
import logging

from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics import style

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RadioToolButton(ToolButton):
    """
    A toolbar button that acts as a radio button.

    Radio tool buttons work in groups where only one button can be active
    at a time. When one button is activated, all others in the group are
    automatically deactivated.
    """

    __gtype_name__ = "SugarRadioToolButton"

    __gsignals__ = {"toggled": (GObject.SignalFlags.RUN_FIRST, None, [])}

    def __init__(self, group=None, **kwargs):
        """
        Initialize the radio tool button.

        Args:
            group: Another RadioToolButton to group with, or None for new group
            **kwargs: Additional arguments passed to ToolButton
        """
        super().__init__(**kwargs)

        self._group = []
        self._active = False

        # Set up radio group
        if group is not None:
            self.set_group(group)
        else:
            self._group = [self]

        self.connect("clicked", self._on_clicked)

        # radio button styling
        self.add_css_class("radio-tool-button")

    def _apply_radio_styling(self):
        """Apply radio button styling using centralized theme.
        
        CSS is defined in sugar-gtk4.css (.radio-tool-button class) or
        sugar-artwork themes to avoid duplication.
        """
        # CSS styling is managed by the centralized theme loader

    def _on_clicked(self, button):
        """Handle button click."""
        if not self._active:
            self.set_active(True)

    def get_group(self):
        """Get the list of buttons in this radio group."""
        return self._group[:]

    def set_group(self, group_member):
        """
        Set the radio group by specifying another member.

        Args:
            group_member: Another RadioToolButton to join groups with
        """
        if group_member and isinstance(group_member, RadioToolButton):
            if self in self._group:
                self._group.remove(self)

            self._group = group_member._group
            if self not in self._group:
                self._group.append(self)

            for member in self._group:
                member._group = self._group

    def get_active(self):
        """Get whether this button is active."""
        return self._active

    def set_active(self, active):
        """
        Set the active state of this button.

        Args:
            active: True to activate, False to deactivate
        """
        if active == self._active:
            return

        if active:
            # Deactivate all other buttons in group
            for member in self._group:
                if member != self and member._active:
                    member._set_active_internal(False)

            self._set_active_internal(True)
        else:
            # Only allow deactivation if another button is being activated
            # or if this is the only button in the group
            if len(self._group) == 1:
                self._set_active_internal(False)

    def _set_active_internal(self, active):
        """Internal method to set active state without group management."""
        if active == self._active:
            return

        self._active = active

        if active:
            self.add_css_class("active")
        else:
            self.remove_css_class("active")

        self.emit("toggled")

        self.set_state_flags(
            Gtk.StateFlags.CHECKED if active else Gtk.StateFlags.NORMAL, True
        )

    active = GObject.Property(
        type=bool,
        default=False,
        getter=get_active,
        setter=set_active,
        nick="Active",
        blurb="Whether the radio button is active",
    )
