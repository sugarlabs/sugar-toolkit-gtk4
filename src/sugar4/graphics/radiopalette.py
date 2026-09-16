# Copyright (C) 2009, Aleksey Lim
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
RadioPalette
=========================

Radio palette provides a way to create radio button groups within palettes,
allowing users to select one option from multiple choices.

This implementation modernizes the radio palette system while maintaining
compatibility with Sugar's palette interface patterns.

Example:

    Create a radio palette with multiple tool options.

    .. code-block:: python

        from gi.repository import Gtk
        from sugar4.graphics.radiopalette import RadioToolsButton, RadioPalette
        from sugar4.graphics.toolbutton import ToolButton

        # Create the main radio button
        radio_button = RadioToolsButton(
            icon_name='tool-brush',
            tooltip='Drawing Tools'
        )

        # Create the palette
        palette = RadioPalette(primary_text='Drawing Tools')
        radio_button.set_palette(palette)

        # Add tool options
        brush_btn = ToolButton(icon_name='tool-brush')
        palette.append(brush_btn, 'Brush')

        pen_btn = ToolButton(icon_name='tool-pen')
        palette.append(pen_btn, 'Pen')

"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GObject", "2.0")

from gi.repository import Gtk
import logging

from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics.palette import Palette
from sugar4.debug import debug_print

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print = debug_print


class RadioMenuButton(ToolButton):
    """
    A toolbar button that shows a radio palette when clicked.
    """

    def __init__(self, **kwargs):
        print(f"RadioMenuButton.__init__ called with kwargs: {kwargs}")

        # Don't create a default palette by removing tooltip
        # This prevents ToolButton from auto-creating a regular Palette
        tooltip = kwargs.pop("tooltip", None)

        super().__init__(**kwargs)
        self.selected_button = None

        invoker = self.get_palette_invoker()
        print(f"Got palette invoker: {invoker}")
        if invoker:
            invoker.set_toggle_palette(True)
            print("Set toggle_palette to True")

        self.set_hide_tooltip_on_click(False)

        self.connect("notify::palette", self._on_palette_changed)

        # Set tooltip after everything is set up
        if tooltip:
            self.set_tooltip_text(tooltip)

        if self.get_palette():
            print("Palette already exists, calling _on_palette_changed")
            self._on_palette_changed(self, None)

    def _on_palette_changed(self, widget, pspec):
        print("RadioMenuButton._on_palette_changed called")
        palette = self.get_palette()
        print(f"Current palette: {palette}")
        if not isinstance(palette, RadioPalette):
            print("Palette is not a RadioPalette instance")
            return
        print("Calling palette.update_button()")
        palette.update_button()

    def get_selected_button(self):
        return self.selected_button

    def set_selected_button(self, button):
        self.selected_button = button


class RadioToolsButton(RadioMenuButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def do_clicked(self):
        if not self.selected_button:
            logger.warning("RadioToolsButton clicked but no button selected")
            return
        self.selected_button.emit("clicked")


class RadioPalette(Palette):
    """
    A palette containing radio button options.
    """

    def __init__(self, **kwargs):
        print(f"RadioPalette.__init__ called with kwargs: {kwargs}")
        super().__init__(**kwargs)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.button_box.set_spacing(6)
        self.button_box.set_homogeneous(True)

        self.set_content(self.button_box)
        print("RadioPalette created successfully")

    def append(self, button, label):
        """
        Add a button option to the radio palette.

        Args:
            button: The ToolButton to add to the radio group
            label: The label text for this option
        """
        print(f"RadioPalette.append called with button: {button}, label: {label}")

        if not isinstance(button, ToolButton):
            raise TypeError("Button must be a ToolButton instance")

        if button.get_palette() is not None:
            raise RuntimeError("Radio palette buttons should not have sub-palettes")

        button.palette_label = label

        button.connect("clicked", self._on_button_clicked)

        self.button_box.append(button)

        children_count = 0
        child = self.button_box.get_first_child()
        while child:
            children_count += 1
            child = child.get_next_sibling()

        print(f"RadioPalette now has {children_count} buttons")

        if children_count == 1:
            print(
                "First button added, setting as selected but not calling _on_button_clicked yet"
            )
            # Don't call _on_button_clicked immediately - wait for the palette to be attached to a button
            if hasattr(button, "set_active"):
                button.set_active(True)
            button.palette_label = label  # Ensure label is set

    def update_button(self):
        print("RadioPalette.update_button called")
        print(f"Current invoker: {self.get_invoker()}")

        # Find the first button or any active button
        selected_button = None
        child = self.button_box.get_first_child()
        while child:
            if hasattr(child, "get_active") and child.get_active():
                print(f"Found active button: {child}")
                selected_button = child
                break
            child = child.get_next_sibling()

        # If no active button found, use the first button
        if not selected_button:
            selected_button = self.button_box.get_first_child()
            if selected_button:
                print(f"No active button found, using first button: {selected_button}")
                if hasattr(selected_button, "set_active"):
                    selected_button.set_active(True)

        if selected_button:
            # Update the RadioMenuButton to reflect the selected tool
            invoker = self.get_invoker()
            if invoker and hasattr(invoker, "_widget"):
                radio_button = invoker._widget  # This should be our RadioMenuButton
                print(f"Updating radio button: {radio_button}")

                if hasattr(selected_button, "palette_label"):
                    print(f"Setting primary text to: {selected_button.palette_label}")
                    self.set_primary_text(selected_button.palette_label)

                if isinstance(radio_button, RadioMenuButton):
                    icon_name = selected_button.get_icon_name()
                    if icon_name:
                        print(f"Setting icon to: {icon_name}")
                        radio_button.set_icon_name(icon_name)

                    radio_button.set_selected_button(selected_button)

    def _on_button_clicked(self, button):
        print(f"RadioPalette._on_button_clicked called with button: {button}")

        child = self.button_box.get_first_child()
        while child:
            if hasattr(child, "set_active"):
                child.set_active(child == button)
            child = child.get_next_sibling()

        if hasattr(button, "palette_label"):
            print(f"Setting primary text to: {button.palette_label}")
            self.set_primary_text(button.palette_label)

        print("Calling popdown")
        self.popdown(immediate=True)

        # Update the RadioMenuButton
        invoker = self.get_invoker()
        print(f"Got invoker: {invoker}")
        if invoker and hasattr(invoker, "_widget"):
            radio_button = invoker._widget
            print(f"Radio button from invoker: {radio_button}")
            if isinstance(radio_button, RadioMenuButton):
                if hasattr(button, "palette_label"):
                    # Don't set label on the radio button, just the tooltip
                    pass

                icon_name = button.get_icon_name()
                if icon_name:
                    print(f"Setting radio button icon to: {icon_name}")
                    radio_button.set_icon_name(icon_name)

                radio_button.set_selected_button(button)
                print(f"Set selected button to: {button}")

    def popdown(self, immediate=True):
        print(f"RadioPalette.popdown called with immediate={immediate}")
        # Call the parent class's popdown method
        super().popdown(immediate=immediate)
        print(f"RadioPalette.popdown: is_up={self.is_up()}, widget={self._widget}")

    def popup(self, immediate=True):
        print(f"RadioPalette.popup called with immediate={immediate}")
        # Call the parent class's popup method
        super().popup(immediate=immediate)
        print(f"RadioPalette.popup: is_up={self.is_up()}, widget={self._widget}")

    def get_buttons(self):
        buttons = []
        child = self.button_box.get_first_child()
        while child:
            if isinstance(child, ToolButton):
                buttons.append(child)
            child = child.get_next_sibling()
        return buttons

    def get_selected_button(self):
        child = self.button_box.get_first_child()
        while child:
            if hasattr(child, "get_active") and child.get_active():
                return child
            child = child.get_next_sibling()
        return None
