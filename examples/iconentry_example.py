#!/usr/bin/env python3
"""
Simple example demonstrating the Sugar IconEntry widget.

Shows a search entry with a primary icon and clear button, plus
a secondary entry with custom icon management.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from sugar4.graphics.iconentry import (
    ICON_ENTRY_PRIMARY,
    ICON_ENTRY_SECONDARY,
    IconEntry,
)


class IconEntryExample(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Sugar IconEntry Example")
        self.set_default_size(500, 300)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        self.set_child(vbox)

        title = Gtk.Label(label="<b>IconEntry Demo</b>")
        title.set_use_markup(True)
        vbox.append(title)

        search_frame = Gtk.Frame(label="Search Entry (Primary Icon + Clear)")
        search_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        search_box.set_margin_top(6)
        search_box.set_margin_bottom(6)
        search_box.set_margin_start(6)
        search_box.set_margin_end(6)

        self.search_entry = IconEntry()
        self.search_entry.set_icon_from_name(ICON_ENTRY_PRIMARY, "edit-find-symbolic")
        self.search_entry.add_clear_button()
        self.search_entry.set_placeholder_text("Type to search...")
        self.search_entry.connect("changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activate)
        search_box.append(self.search_entry)

        self.search_status = Gtk.Label(label="Type something to search")
        search_box.append(self.search_status)

        search_frame.set_child(search_box)
        vbox.append(search_frame)

        manual_frame = Gtk.Frame(label="Manual Icon Control")
        manual_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        manual_box.set_margin_top(6)
        manual_box.set_margin_bottom(6)
        manual_box.set_margin_start(6)
        manual_box.set_margin_end(6)

        self.manual_entry = IconEntry()
        self.manual_entry.set_placeholder_text("Use buttons below to add/remove icons")
        manual_box.append(self.manual_entry)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        add_primary = Gtk.Button(label="Set Primary Icon")
        add_primary.connect("clicked", self._on_add_primary)
        button_box.append(add_primary)

        add_secondary = Gtk.Button(label="Set Secondary Icon")
        add_secondary.connect("clicked", self._on_add_secondary)
        button_box.append(add_secondary)

        remove_all = Gtk.Button(label="Remove All Icons")
        remove_all.connect("clicked", self._on_remove_all)
        button_box.append(remove_all)

        manual_box.append(button_box)

        self.manual_status = Gtk.Label(label="No icons set")
        manual_box.append(self.manual_status)

        manual_frame.set_child(manual_box)
        vbox.append(manual_frame)

        info = Gtk.Label(label="Tip: Press Escape in any IconEntry to clear its text")
        info.add_css_class("dim-label")
        vbox.append(info)

    def _on_search_changed(self, entry):
        text = entry.get_text()
        if text:
            self.search_status.set_text(f"Searching for: {text}")
        else:
            self.search_status.set_text("Type something to search")

    def _on_search_activate(self, entry):
        text = entry.get_text()
        self.search_status.set_text(f"Search submitted: {text}")

    def _on_add_primary(self, button):
        self.manual_entry.set_icon_from_name(ICON_ENTRY_PRIMARY, "edit-find-symbolic")
        self.manual_status.set_text("Primary icon set")

    def _on_add_secondary(self, button):
        self.manual_entry.set_icon_from_name(
            ICON_ENTRY_SECONDARY, "window-close-symbolic"
        )
        self.manual_status.set_text("Secondary icon set")

    def _on_remove_all(self, button):
        self.manual_entry.remove_icon(ICON_ENTRY_PRIMARY)
        self.manual_entry.remove_icon(ICON_ENTRY_SECONDARY)
        self.manual_status.set_text("All icons removed")


class IconEntryApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.sugarlabs.IconEntryExample")

    def do_activate(self):
        window = IconEntryExample(self)
        window.present()


def main():
    app = IconEntryApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
