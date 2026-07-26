# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
# Copyright (C) 2011, Benjamin Berg <benjamin@sipsolutions.net>
# Copyright (C) 2011, Marco Pesenti Gritti <marco@marcopg.org>
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

import textwrap

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import GLib, Gtk, Gdk, GObject, Pango, Graphene

from sugar4.graphics import style
from sugar4.graphics.icon import Icon
from sugar4.graphics.palettewindow import (
    PaletteWindow,
    _PaletteWindowWidget,
    _PaletteMenuWidget,
)
from sugar4.graphics.palettemenu import PaletteMenuItem
from sugar4.graphics.palettewindow import (
    MouseSpeedDetector,
    Invoker,
    WidgetInvoker,
    CursorInvoker,
    ToolInvoker,
    TreeViewInvoker,
)

assert MouseSpeedDetector
assert Invoker
assert WidgetInvoker
assert CursorInvoker
assert ToolInvoker
assert TreeViewInvoker


class _HeaderItem(Gtk.Widget):
    """A custom widget for palette headers.

    Replaces deprecated MenuItem with a modern widget implementation.
    """

    __gtype_name__ = "SugarPaletteHeader"

    def __init__(self, child_widget):
        super().__init__()

        self._child_widget = None
        self._click_gesture = Gtk.GestureClick.new()
        self._click_gesture.set_button(1)  # Left click
        self.add_controller(self._click_gesture)

        if child_widget:
            self.set_child(child_widget)

    def set_child(self, child_widget):
        if self._child_widget:
            self._child_widget.unparent()

        self._child_widget = child_widget
        if child_widget:
            child_widget.set_parent(self)

    def get_child(self):
        return self._child_widget

    def do_measure(self, orientation, for_size):
        if self._child_widget:
            return self._child_widget.measure(orientation, for_size)
        return 0, 0, -1, -1

    def do_size_allocate(self, width, height, baseline):
        if self._child_widget:
            self._child_widget.allocate(width, height, baseline, None)

    def do_snapshot(self, snapshot):
        """Snapshot implementation for custom drawing."""
        # Draw separator line at bottom
        width = self.get_width()
        height = self.get_height()

        if width > 0 and height > 0:
            # Create a colored rectangle for the separator
            color = Gdk.RGBA()
            color.red = color.green = color.blue = 0.5  # Grey
            color.alpha = 1.0

            line_height = 2
            rect = Gdk.Rectangle()
            rect.x = 0
            rect.y = height - line_height
            rect.width = width
            rect.height = line_height

        snapshot.append_color(
            color, Graphene.Rect().init(rect.x, rect.y, rect.width, rect.height)
        )

        if self._child_widget:
            self.snapshot_child(self._child_widget, snapshot)

    def do_dispose(self):
        if self._child_widget:
            self._child_widget.unparent()
            self._child_widget = None

    # TODO: Dispose here


class Palette(PaletteWindow):
    """Floating palette implementation.

    This class dynamically switches between one of two encapsulated child
    widget types: a _PaletteWindowWidget or a _PaletteMenuWidget.

    The window widget, created by default, acts as the container for any
    type of widget the user may wish to add. It can optionally display primary
    text, secondary text, and an icon at the top of the palette.

    If the user attempts to access the 'menu' property, the window widget is
    destroyed and the palette is dynamically switched to use a menu widget.
    This maintains the same look and feel as a normal palette,
    allowing submenus and so on.
    """

    __gsignals__ = {
        "activate": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    __gtype_name__ = "SugarPalette"

    def __init__(
        self, label=None, accel_path=None, text_maxlen=style.MENU_WIDTH_CHARS, **kwargs
    ):
        # DEPRECATED: label is passed with the primary-text property,
        # accel_path is set via the invoker property

        self._primary_text = None
        self._secondary_text = None
        self._icon = None
        self._icon_visible = True

        # header container
        self._primary_event_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._primary_event_box.set_spacing(style.DEFAULT_SPACING)

        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", self.__button_release_event_cb)
        self._primary_event_box.add_controller(click_gesture)

        # icon container
        self._icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._icon_box.set_size_request(style.GRID_CELL_SIZE, -1)
        self._primary_event_box.append(self._icon_box)

        # labels container
        labels_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        labels_box.set_margin_start(style.DEFAULT_SPACING)
        labels_box.set_margin_end(style.DEFAULT_SPACING)
        labels_box.set_margin_top(style.DEFAULT_SPACING)
        labels_box.set_margin_bottom(style.DEFAULT_SPACING)
        labels_box.set_hexpand(True)
        self._primary_event_box.append(labels_box)

        # Primary label
        self._label = Gtk.Label()
        self._label.set_halign(Gtk.Align.START)
        self._label.set_valign(Gtk.Align.CENTER)

        if text_maxlen > 0:
            self._label.set_max_width_chars(text_maxlen)
            self._label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        labels_box.append(self._label)

        # Secondary label
        self._secondary_label = Gtk.Label()
        self._secondary_label.set_halign(Gtk.Align.START)
        self._secondary_label.set_valign(Gtk.Align.CENTER)
        labels_box.append(self._secondary_label)

        # secondary content container
        self._secondary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._secondary_box.append(self._separator)

        super().__init__(**kwargs)

        self._full_request = [0, 0]
        self._content = None

        if label is not None:
            self.props.primary_text = label

        self._add_content()

        self.action_bar = PaletteActionBar()
        self._secondary_box.append(self.action_bar)

        self.connect("notify::invoker", self.__notify_invoker_cb)

        # Default to a normal window palette
        self._content_widget = None
        self.set_content(None)

    def _setup_widget(self):
        super()._setup_widget()
        self._widget.connect("destroy", self.__destroy_cb)

    def __destroy_cb(self, palette):
        self.popdown(immediate=True)
        # Break the reference cycle to help with garbage collection
        self._widget = None

    def __notify_invoker_cb(self, palette, pspec):
        invoker = self.props.invoker
        if (
            invoker is not None
            and hasattr(invoker, "props")
            and hasattr(invoker.props, "widget")
        ):
            self._update_accel_widget()
            if hasattr(invoker, "connect"):
                invoker.connect("notify::widget", self.__invoker_widget_changed_cb)

    def __invoker_widget_changed_cb(self, invoker, spec):
        self._update_accel_widget()

    def get_full_size_request(self):
        return self._full_request

    def get_content_widget(self):
        """Get the content widget."""
        return self._content_widget

    def popup(self, immediate=False):
        if self._invoker is not None:
            self._update_full_request()

        super().popup(immediate)

    def popdown(self, immediate=False, state=None):
        """Hide the palette.

        Args:
            immediate (bool): if True, hide instantly. If False, use animation.
            state: deprecated parameter, ignored.
        """
        if immediate and self._widget:
            if hasattr(self._widget, "get_preferred_size"):
                self._widget.get_preferred_size()
        super().popdown(immediate)

    def on_enter(self):
        super().on_enter()

    def _add_content(self):
        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._secondary_box.append(self._content)

    def _update_accel_widget(self):
        if (
            self.props.invoker is not None
            and hasattr(self.props.invoker, "props")
            and hasattr(self.props.invoker.props, "widget")
        ):
            # GTK4: Set accelerator widget if the label supports it
            if hasattr(self._label, "set_accel_widget"):
                self._label.set_accel_widget(self.props.invoker.props.widget)

    def set_primary_text(self, label, accel_path=None):
        self._primary_text = label
        if label is not None:
            label = GLib.markup_escape_text(label)
            self._label.set_markup(f"<b>{label}</b>")
            self._label.set_visible(True)
        else:
            self._label.set_visible(False)

    def get_primary_text(self):
        return self._primary_text

    primary_text = GObject.Property(
        type=str, getter=get_primary_text, setter=set_primary_text
    )

    def __button_release_event_cb(self, gesture, n_press, x, y):
        if self.props.invoker is not None and hasattr(
            self.props.invoker, "primary_text_clicked"
        ):
            self.props.invoker.primary_text_clicked()

    def set_secondary_text(self, label):
        if label is None:
            self._secondary_label.set_visible(False)
        else:
            NO_OF_LINES = 3
            ELLIPSIS_LENGTH = 6

            label = label.replace("\n", " ")
            label = label.replace("\r", " ")

            if hasattr(self._secondary_label, "set_lines"):
                self._secondary_label.set_max_width_chars(style.MENU_WIDTH_CHARS)
                self._secondary_label.set_wrap(True)
                self._secondary_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
                self._secondary_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                self._secondary_label.set_lines(NO_OF_LINES)
                self._secondary_label.set_justify(Gtk.Justification.FILL)
            else:
                # Fallback for older GTK versions
                body_width = NO_OF_LINES * style.MENU_WIDTH_CHARS
                body_width -= ELLIPSIS_LENGTH
                if len(label) > body_width:
                    label = " ".join(label[:body_width].split()[:-1]) + "..."
                label = textwrap.fill(label, width=style.MENU_WIDTH_CHARS)

            self._secondary_text = label
            self._secondary_label.set_text(label)
            self._secondary_label.set_visible(True)

    def get_secondary_text(self):
        return self._secondary_text

    secondary_text = GObject.Property(
        type=str, getter=get_secondary_text, setter=set_secondary_text
    )

    def _show_icon(self):
        self._icon_box.set_visible(True)

    def _hide_icon(self):
        self._icon_box.set_visible(False)

    def set_icon(self, icon):
        if icon is None:
            self._icon = None
            self._hide_icon()
        else:
            child = self._icon_box.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self._icon_box.remove(child)
                child = next_child

            event_box = Gtk.Box()
            click_gesture = Gtk.GestureClick()
            click_gesture.connect("released", self.__icon_button_release_event_cb)
            event_box.add_controller(click_gesture)

            self._icon_box.append(event_box)

            self._icon = icon
            self._icon.props.pixel_size = style.STANDARD_ICON_SIZE
            event_box.append(self._icon)
            self._show_icon()

    def get_icon(self):
        return self._icon

    icon = GObject.Property(type=object, getter=get_icon, setter=set_icon)

    def __icon_button_release_event_cb(self, gesture, n_press, x, y):
        self.emit("activate")

    def set_icon_visible(self, visible):
        self._icon_visible = visible

        if visible and self._icon is not None:
            self._show_icon()
        else:
            self._hide_icon()

    def get_icon_visible(self):
        return self._icon_visible

    icon_visible = GObject.Property(
        type=bool, default=True, getter=get_icon_visible, setter=set_icon_visible
    )

    def set_content(self, widget):
        assert self._widget is None or isinstance(self._widget, _PaletteWindowWidget)

        if self._widget is None:
            self._widget = _PaletteWindowWidget(self)
            self._setup_widget()

            self._palette_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self._palette_box.append(self._primary_event_box)
            self._palette_box.append(self._secondary_box)

            self._widget.set_child(self._palette_box)

            height = style.GRID_CELL_SIZE - 2 * 4  # Approximate border width
            self._primary_event_box.set_size_request(-1, height)

        # Remove existing content
        if self._content is not None:
            child = self._content.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self._content.remove(child)
                child = next_child

        if widget is not None:
            # Set up button release handling
            click_gesture = Gtk.GestureClick()
            click_gesture.connect("released", self.__widget_button_release_cb)
            widget.add_controller(click_gesture)

            if self._content is not None:
                self._content.append(widget)
                self._content.set_visible(True)
        else:
            if self._content is not None:
                self._content.set_visible(False)

        self._content_widget = widget

        self._update_accept_focus()
        self._update_separators()

    def __widget_button_release_cb(self, gesture, n_press, x, y):
        # Check if the event widget is a PaletteMenuItem
        widget = gesture.get_widget()
        while widget:
            if isinstance(widget, PaletteMenuItem):
                self.popdown(immediate=True)
                return False
            widget = widget.get_parent()
        return False

    def get_label_width(self):
        # GTK4: Get preferred width
        min_width, nat_width = self._label.get_preferred_size()
        accel_width = 0
        if hasattr(self._label, "get_accel_width"):
            accel_width = self._label.get_accel_width()
        return nat_width.width + accel_width

    def _update_separators(self):
        # Check if there are content children
        if self._content is not None:
            visible = self._content.get_first_child() is not None
            self._separator.set_visible(visible)

    def _update_accept_focus(self):
        if self._widget and self._content is not None:
            accept_focus = self._content.get_first_child() is not None
            self._widget.set_accept_focus(accept_focus)

    def _update_full_request(self):
        if self._widget is not None:
            if hasattr(self._widget, "get_preferred_size"):
                min_size, nat_size = self._widget.get_preferred_size()
                self._full_request = [nat_size.width, nat_size.height]
            else:
                self._full_request = [
                    style.GRID_CELL_SIZE * 3,
                    style.GRID_CELL_SIZE * 2,
                ]

    def get_menu(self):
        assert self._content_widget is None

        if self._widget is None or not isinstance(self._widget, _PaletteMenuWidget):

            if self._widget is not None:
                # Remove containers before destroying widget
                if hasattr(self, "_palette_box"):
                    child = self._palette_box.get_first_child()
                    while child:
                        next_child = child.get_next_sibling()
                        self._palette_box.remove(child)
                        child = next_child

                self._teardown_widget()
                self._widget.destroy()

            self._widget = _PaletteMenuWidget()

            self._label_menuitem = _HeaderItem(self._primary_event_box)
            self._widget.append(self._label_menuitem)

            self._setup_widget()

        return self._widget

    menu = GObject.Property(type=object, getter=get_menu)

    def _invoker_right_click_cb(self, invoker):
        self.popup(immediate=True)


class PaletteActionBar(Gtk.Box):

    def __init__(self):
        # initializing with Horizontal box as this was a HButtonBox before
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_spacing(style.DEFAULT_SPACING)
        self.set_homogeneous(True)
        self.add_css_class("palette-action-bar")

    def add_action(self, label, icon_name=None):
        button = Gtk.Button(label=label)

        if icon_name:
            icon = Icon(icon_name=icon_name, pixel_size=style.SMALL_ICON_SIZE)
            # GTK4: Use set_child instead of set_image
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            box.append(icon)
            box.append(Gtk.Label(label=label))
            button.set_child(box)

        self.append(button)
        return button
