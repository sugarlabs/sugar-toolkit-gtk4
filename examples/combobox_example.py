"""
Example demonstrating the Sugar ComboBox widget.

This example shows how to use the ComboBox component from the Sugar Toolkit,
including adding items with text and icons, handling selection changes,
and using separators.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from sugar4.graphics.combobox import ComboBox


class ComboBoxExample(Gtk.ApplicationWindow):
    """Example window demonstrating ComboBox usage."""

    def __init__(self, app):
        super().__init__(application=app, title="Sugar ComboBox Example")
        self.set_default_size(400, 300)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.set_child(vbox)

        title = Gtk.Label(label="<b>Sugar ComboBox Examples</b>")
        title.set_use_markup(True)
        vbox.append(title)

        # Example 1: Simple text combo
        self.create_simple_combo_example(vbox)

        # Example 2: Combo with icons
        self.create_icon_combo_example(vbox)

        # Example 3: Combo with separators
        self.create_separator_combo_example(vbox)

        # Example 4: Complex values combo
        self.create_complex_combo_example(vbox)

        self.status_label = Gtk.Label(label="Select items to see their values")
        self.status_label.set_selectable(True)
        vbox.append(self.status_label)

    def create_simple_combo_example(self, parent):
        """Create simple text-only combobox example."""
        frame = Gtk.Frame(label="Simple Text ComboBox")
        frame.set_margin_top(10)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(10)
        hbox.set_margin_bottom(10)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        frame.set_child(hbox)

        label = Gtk.Label(label="Fruit:")
        hbox.append(label)

        self.simple_combo = ComboBox()
        self.simple_combo.append_item("apple", "Apple")
        self.simple_combo.append_item("banana", "Banana")
        self.simple_combo.append_item("orange", "Orange")
        self.simple_combo.append_item("grape", "Grape")

        self.simple_combo.connect("changed", self.on_simple_changed)
        hbox.append(self.simple_combo)

        parent.append(frame)

    def create_icon_combo_example(self, parent):
        """Create combobox with icons example."""
        frame = Gtk.Frame(label="ComboBox with Icons")
        frame.set_margin_top(10)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(10)
        hbox.set_margin_bottom(10)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        frame.set_child(hbox)

        label = Gtk.Label(label="Action:")
        hbox.append(label)

        # Create combo with icons
        self.icon_combo = ComboBox()
        try:
            self.icon_combo.append_item(
                "new", "New Document", icon_name="document-new"
            )
            self.icon_combo.append_item(
                "open", "Open Document", icon_name="document-open"
            )
            self.icon_combo.append_item(
                "save", "Save Document", icon_name="document-save"
            )
            self.icon_combo.append_item("copy", "Copy", icon_name="edit-copy")
            self.icon_combo.append_item("paste", "Paste", icon_name="edit-paste")
        except (ValueError, AttributeError):
            # Fallback if icons don't exist or properties not available
            self.icon_combo.append_item("new", "New Document")
            self.icon_combo.append_item("open", "Open Document")
            self.icon_combo.append_item("save", "Save Document")
            self.icon_combo.append_item("copy", "Copy")
            self.icon_combo.append_item("paste", "Paste")

        self.icon_combo.connect("changed", self.on_icon_changed)
        hbox.append(self.icon_combo)

        parent.append(frame)

    def create_separator_combo_example(self, parent):
        """Create combobox with separators example."""
        frame = Gtk.Frame(label="ComboBox with Separators")
        frame.set_margin_top(10)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_top(10)
        hbox.set_margin_bottom(10)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        frame.set_child(hbox)

        label = Gtk.Label(label="Category:")
        hbox.append(label)

        self.separator_combo = ComboBox()

        # Fruits
        self.separator_combo.append_item("apple", "Apple")
        self.separator_combo.append_item("banana", "Banana")
        self.separator_combo.append_separator()

        # Vegetables
        self.separator_combo.append_item("carrot", "Carrot")
        self.separator_combo.append_item("broccoli", "Broccoli")
        self.separator_combo.append_separator()

        # Grains
        self.separator_combo.append_item("rice", "Rice")
        self.separator_combo.append_item("wheat", "Wheat")

        self.separator_combo.connect("changed", self.on_separator_changed)
        hbox.append(self.separator_combo)

        parent.append(frame)

    def create_complex_combo_example(self, parent):
        """Create combobox with complex values example."""
        frame = Gtk.Frame(label="ComboBox with Complex Values")
        frame.set_margin_top(10)

        vbox_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_inner.set_margin_top(10)
        vbox_inner.set_margin_bottom(10)
        vbox_inner.set_margin_start(10)
        vbox_inner.set_margin_end(10)
        frame.set_child(vbox_inner)

        description = Gtk.Label(
            label="Each item stores a dictionary with multiple properties:"
        )
        description.set_wrap(True)
        vbox_inner.append(description)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox_inner.append(hbox)

        label = Gtk.Label(label="Person:")
        hbox.append(label)

        self.complex_combo = ComboBox()

        people = [
            {"name": "Alice", "age": 30, "role": "Developer"},
            {"name": "Bob", "age": 25, "role": "Designer"},
            {"name": "Charlie", "age": 35, "role": "Manager"},
            {"name": "Diana", "age": 28, "role": "Tester"},
        ]

        for person in people:
            display_text = f"{person['name']} ({person['role']})"
            self.complex_combo.append_item(person, display_text)

        self.complex_combo.connect("changed", self.on_complex_changed)
        hbox.append(self.complex_combo)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox_inner.append(button_box)

        clear_button = Gtk.Button(label="Clear All")
        clear_button.connect("clicked", self.on_clear_clicked)
        button_box.append(clear_button)

        add_button = Gtk.Button(label="Add Random Person")
        add_button.connect("clicked", self.on_add_clicked)
        button_box.append(add_button)

        parent.append(frame)

    def on_simple_changed(self, combo):
        """Handle simple combo selection change."""
        value = combo.get_value()
        if value:
            self.status_label.set_text(f"Simple combo selected: {value}")

    def on_icon_changed(self, combo):
        """Handle icon combo selection change."""
        value = combo.get_value()
        if value:
            item = combo.get_active_item()
            text = item[1] if item else "Unknown"
            self.status_label.set_text(f"Icon combo selected: {value} ({text})")

    def on_separator_changed(self, combo):
        """Handle separator combo selection change."""
        value = combo.get_value()
        if value:
            self.status_label.set_text(f"Category selected: {value}")

    def on_complex_changed(self, combo):
        """Handle complex combo selection change."""
        value = combo.get_value()
        if value and isinstance(value, dict):
            status_text = (
                f"Person: {value['name']}, Age: {value['age']}, "
                f"Role: {value['role']}"
            )
            self.status_label.set_text(status_text)

    def on_clear_clicked(self, button):
        """Clear all items from complex combo."""
        self.complex_combo.remove_all()
        self.status_label.set_text("Complex combo cleared")

    def on_add_clicked(self, button):
        """Add a random person to complex combo."""
        import random

        names = ["Eve", "Frank", "Grace", "Henry", "Iris"]
        roles = ["Analyst", "Writer", "Artist", "Teacher"]

        person = {
            "name": random.choice(names),
            "age": random.randint(22, 40),
            "role": random.choice(roles),
        }

        display_text = f"{person['name']} ({person['role']})"
        self.complex_combo.append_item(person, display_text)
        self.status_label.set_text(f"Added: {display_text}")


class ComboBoxApp(Gtk.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(application_id="org.sugarlabs.ComboBoxExample")

    def do_activate(self):
        """Activate the application."""
        window = ComboBoxExample(self)
        window.present()


def main():
    """Main function."""
    app = ComboBoxApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
