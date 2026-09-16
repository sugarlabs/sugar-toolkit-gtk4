"""Sugar GTK4 Icon Example - Complete Feature Demo."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk

from sugar4.activity import SimpleActivity
from sugar4.graphics.icon import Icon, EventIcon, CanvasIcon
from sugar4.graphics.xocolor import XoColor
from sugar4.graphics.palette import Palette
from sugar4.graphics.palettemenu import PaletteMenuBox, PaletteMenuItem


class PaletteIcon(CanvasIcon):
    """A CanvasIcon that pops up a palette via create_palette."""

    def __init__(self, primary_text, **kwargs):
        super().__init__(**kwargs)
        self._primary_text = primary_text
        self.palette_invoker.props.toggle_palette = True

    def create_palette(self):
        palette = Palette(self._primary_text)
        menu_box = PaletteMenuBox()
        palette.set_content(menu_box)
        for label in ("Open", "Copy", "Remove"):
            item = PaletteMenuItem(label)
            menu_box.append_item(item)
            item.set_visible(True)
        menu_box.set_visible(True)
        self.connect_to_palette_pop_events(palette)
        return palette


class IconExampleActivity(SimpleActivity):
    """Example activity demonstrating all Sugar GTK4 icon features."""

    def __init__(self):
        super().__init__()
        self.set_title("Sugar GTK4 Icon Example ")
        self._create_content()

    def _create_content(self):
        """Create the main content showing all icon types and features."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)

        # Scrolled window for all content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(main_box)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        # Add CSS provider for CanvasIcon hover/active states
        css_provider = Gtk.CssProvider()
        css_data = """
        .canvas-icon {
            background-color: transparent;
            border-radius: 8px;
            padding: 4px;
            transition: background-color 200ms ease;
        }
        .canvas-icon:hover {
            background-color: rgba(0, 0, 0, 0.15);
        }
        .canvas-icon:active {
            background-color: rgba(0, 0, 0, 0.25);
        }
        """
        try:
            css_provider.load_from_string(css_data)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        except Exception as e:
            print(f"Warning: Could not load CSS provider: {e}")

        # Title
        title = Gtk.Label()
        title.set_markup("<big><b>Sugar GTK4 Icon Examples - Complete</b></big>")
        title.set_hexpand(True)
        main_box.append(title)

        # Add sections
        self._add_basic_icons(main_box)
        self._add_colored_icons(main_box)
        self._add_badge_icons(main_box)
        self._add_event_icons(main_box)
        self._add_canvas_icons(main_box)
        self._add_palette_icons(main_box)
        self._add_size_and_alpha_examples(main_box)

        self.set_canvas(scrolled)
        self.set_default_size(900, 700)

    def _add_basic_icons(self, container):
        """Add basic icon examples."""
        frame = Gtk.Frame(label="Basic Icons")
        frame.set_hexpand(True)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_hexpand(True)
        box.set_halign(Gtk.Align.CENTER)

        # System icons
        for icon_name in [
            "document-new",
            "document-open",
            "document-save",
            "edit-copy",
            "edit-paste",
        ]:
            icon = Icon(icon_name=icon_name, pixel_size=48)
            box.append(icon)

        frame.set_child(box)
        container.append(frame)

    def _add_colored_icons(self, container):
        """Add colored icon examples."""
        frame = Gtk.Frame(label="Colored Icons")
        frame.set_hexpand(True)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_hexpand(True)

        # XO Color examples using xotest.svg
        hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox1.set_hexpand(True)
        hbox1.set_halign(Gtk.Align.CENTER)
        label1 = Gtk.Label(label="XO Colors (xotest.svg):")
        label1.set_size_request(150, -1)
        hbox1.append(label1)

        xotest_svg = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "sugar4",
            "graphics",
            "icons",
            "test.svg",
        )
        for i in range(3):
            xo_color = XoColor.get_random_color()
            icon = Icon(file_name=xotest_svg, pixel_size=48)
            icon.set_xo_color(xo_color)
            hbox1.append(icon)

        vbox.append(hbox1)

        # Manual color examples (still using xotest.svg)
        hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox2.set_hexpand(True)
        hbox2.set_halign(Gtk.Align.CENTER)
        label2 = Gtk.Label(label="Manual Colors (xotest.svg):")
        label2.set_size_request(150, -1)
        hbox2.append(label2)

        for fill, stroke in [
            ("#FF0000", "#800000"),
            ("#00FF00", "#008000"),
            ("#0000FF", "#000080"),
        ]:
            icon = Icon(file_name=xotest_svg, pixel_size=48)
            icon.set_fill_color(fill)
            icon.set_stroke_color(stroke)
            hbox2.append(icon)

        vbox.append(hbox2)
        frame.set_child(vbox)
        container.append(frame)

    def _add_badge_icons(self, container):
        """Add badge icon examples."""
        frame = Gtk.Frame(label="Badge Icons")
        frame.set_hexpand(True)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_hexpand(True)

        # Info label
        info_label = Gtk.Label(label="Icons with badges (small overlay icons):")
        vbox.append(info_label)

        # Badge examples
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        hbox.set_hexpand(True)
        hbox.set_halign(Gtk.Align.CENTER)
        badges = [
            ("folder", "emblem-favorite"),
            ("document-new", "emblem-important"),
            ("network-wireless", "dialog-information"),
        ]
        for main_icon, badge_icon in badges:
            vbox_item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            vbox_item.set_halign(Gtk.Align.CENTER)
            icon = Icon(icon_name=main_icon, pixel_size=64)
            icon.set_badge_name(badge_icon)
            icon.set_fill_color("#00AA00")
            icon.set_stroke_color("#004400")
            vbox_item.append(icon)
            label = Gtk.Label(label=f"{main_icon}\n+ {badge_icon}")
            label.set_justify(Gtk.Justification.CENTER)
            vbox_item.append(label)
            hbox.append(vbox_item)

        vbox.append(hbox)
        frame.set_child(vbox)
        container.append(frame)

    def _add_event_icons(self, container):
        """Add event icon examples."""
        frame = Gtk.Frame(label="Interactive Icons (EventIcon)")
        frame.set_hexpand(True)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_hexpand(True)

        # Info label
        info_label = Gtk.Label(label="Click these icons to see events:")
        vbox.append(info_label)

        # Status label
        self.event_info = Gtk.Label(label="No events yet")
        vbox.append(self.event_info)

        # Event icons
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_hexpand(True)
        hbox.set_halign(Gtk.Align.CENTER)

        for i, icon_name in enumerate(
            ["media-playback-start", "media-playback-pause", "media-playback-stop"]
        ):
            event_icon = EventIcon(icon_name=icon_name, pixel_size=64)
            event_icon.connect("clicked", self._on_icon_clicked, icon_name)
            event_icon.connect("pressed", self._on_icon_pressed, icon_name)
            event_icon.connect("released", self._on_icon_released, icon_name)
            event_icon.connect("activate", self._on_icon_activated, icon_name)
            hbox.append(event_icon)

        vbox.append(hbox)
        frame.set_child(vbox)
        container.append(frame)

    def _add_canvas_icons(self, container):
        """Add canvas icon examples with hover effects."""
        frame = Gtk.Frame(label="Canvas Icons (Hover Effects)")
        frame.set_hexpand(True)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_hexpand(True)

        info_label = Gtk.Label(label="Hover and click these icons for visual feedback:")
        vbox.append(info_label)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        hbox.set_hexpand(True)
        hbox.set_halign(Gtk.Align.CENTER)

        icons = [
            ("system-search", "#FF8800", "#AA4400"),
            ("edit-delete", "#FF0000", "#880000"),
            ("dialog-information", "#0088FF", "#004488"),
        ]
        for icon_name, fill, stroke in icons:
            # Create a wrapper box for the canvas icon to ensure proper CSS application
            wrapper = Gtk.Box()
            wrapper.add_css_class("canvas-icon")

            canvas_icon = CanvasIcon(icon_name=icon_name, pixel_size=64)
            canvas_icon.set_fill_color(fill)
            canvas_icon.set_stroke_color(stroke)

            wrapper.append(canvas_icon)
            hbox.append(wrapper)

        vbox.append(hbox)
        frame.set_child(vbox)
        container.append(frame)

    def _add_palette_icons(self, container):
        """Add icons that pop up a palette on click or right click."""
        frame = Gtk.Frame(label="Icons with Palettes")
        frame.set_hexpand(True)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_hexpand(True)

        info_label = Gtk.Label(
            label="Click or right-click these icons to pop up a palette:")
        vbox.append(info_label)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        hbox.set_hexpand(True)
        hbox.set_halign(Gtk.Align.CENTER)

        for icon_name, label in [
            ("folder", "Documents"),
            ("network-wireless", "Network"),
            ("system-users", "Friends"),
        ]:
            icon = PaletteIcon(label, icon_name=icon_name, pixel_size=64)
            hbox.append(icon)

        vbox.append(hbox)
        frame.set_child(vbox)
        container.append(frame)

    def _add_size_and_alpha_examples(self, container):
        """Add different size and transparency examples."""
        frame = Gtk.Frame(label="Different Sizes and Transparency")
        frame.set_hexpand(True)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        hbox.set_margin_top(10)
        hbox.set_margin_bottom(10)
        hbox.set_hexpand(True)
        hbox.set_halign(Gtk.Align.CENTER)

        sizes = [16, 24, 32, 48, 64, 96]
        for size in sizes:
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            vbox.set_halign(Gtk.Align.CENTER)
            icon = Icon(icon_name="applications-graphics", pixel_size=size)
            vbox.append(icon)
            label = Gtk.Label(label=f"{size}px")
            vbox.append(label)
            hbox.append(vbox)

        # Transparency example
        vbox_alpha = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_alpha.set_halign(Gtk.Align.CENTER)
        label_alpha = Gtk.Label(label="Alpha (transparency):")
        vbox_alpha.append(label_alpha)
        for alpha in [1.0, 0.7, 0.4]:
            icon = Icon(icon_name="applications-graphics", pixel_size=48)
            icon.set_alpha(alpha)
            vbox_alpha.append(icon)
        hbox.append(vbox_alpha)

        frame.set_child(hbox)
        container.append(frame)

    def _on_icon_clicked(self, icon, icon_name):
        """Handle icon click events."""
        self.event_info.set_text(f"Clicked: {icon_name}")

    def _on_icon_pressed(self, icon, x, y, icon_name):
        """Handle icon press events."""
        self.event_info.set_text(f"Pressed: {icon_name} at ({x:.1f}, {y:.1f})")

    def _on_icon_released(self, icon, x, y, icon_name):
        """Handle icon release events."""
        self.event_info.set_text(f"Released: {icon_name} at ({x:.1f}, {y:.1f})")

    def _on_icon_activated(self, icon, icon_name):
        """Handle icon activate events."""
        self.event_info.set_text(f"Activated: {icon_name}")


def main():
    """Run the icon example activity."""
    app = Gtk.Application(application_id="org.sugarlabs.IconExample")

    def on_activate(app):
        activity = IconExampleActivity()
        app.add_window(activity)
        activity.present()

    app.connect("activate", on_activate)
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
