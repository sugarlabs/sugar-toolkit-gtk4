# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2008, Benjamin Berg <benjamin@sipsolutions.net>
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
# Boston, MA 02111-1307, USA

import gettext
import logging
import struct

from gi.repository import Gdk, Gio, GObject, Gtk

from sugar4.graphics import style
from sugar4.graphics.icon import Icon
from sugar4.graphics.palette import Palette
from sugar4.graphics.palettewindow import WidgetInvoker
from sugar4.graphics.toolbutton import ToolButton


def _(msg):
    return gettext.dgettext("sugar-toolkit-gtk4", msg)


def get_svg_color_string(color):
    """Convert Gdk.RGBA to SVG hex color string."""
    return "#%.2X%.2X%.2X" % (
        int(color.red * 255),
        int(color.green * 255),
        int(color.blue * 255),
    )


class _ColorButton(Gtk.Button):
    """
    This is a ColorButton for Sugar. It is similar to the Gtk.ColorButton,
    but does not have any alpha support.
    Instead of a color selector dialog it will pop up a Sugar palette.

    As a preview an sugar4.graphics.Icon is used. The fill color will be set to
    the current color, and the stroke color is set to the font color.
    """

    __gtype_name__ = "SugarColorButton"
    __gsignals__ = {"color-set": (GObject.SignalFlags.RUN_FIRST, None, tuple())}

    def __init__(self, **kwargs):
        self._title = _("Choose a color")
        # GTK4: Gdk.Color → Gdk.RGBA
        self._color = Gdk.RGBA()
        self._color.red = 0.0
        self._color.green = 0.0
        self._color.blue = 0.0
        self._color.alpha = 1.0
        self._has_palette = True
        self._has_invoker = True
        self._palette = None
        self._accept_drag = True

        self._preview = Icon(
            icon_name="color-preview", pixel_size=style.STANDARD_ICON_SIZE
        )

        GObject.GObject.__init__(self, **kwargs)

        # FIXME Drag and drop is not working, SL #3796
        # GTK4: Drag and drop API changed significantly
        # For now, disable drag and drop
        """
        if self._accept_drag:
            # GTK4 drag and drop setup would go here
            pass
        """

        # GTK4: set_image → set_child
        self._preview.fill_color = get_svg_color_string(self._color)
        self._preview.stroke_color = self._get_fg_style_color_str()
        self.set_child(self._preview)

        if self._has_palette and self._has_invoker:
            self._invoker = WidgetInvoker(self)
            # FIXME: This is a hack.
            self._invoker.has_rectangle_gap = lambda: False
            self._invoker.palette = self._palette

    def create_palette(self):
        """
        Create a new palette with selected color and title.
        (Here the title is 'Choose a color' and the bgcolor
        is black.)
        """
        if self._has_palette:
            self._palette = _ColorPalette(color=self._color, primary_text=self._title)
            self._palette.connect("color-set", self.__palette_color_set_cb)
            self._palette.connect("notify::color", self.__palette_color_changed)

        return self._palette

    def __palette_color_set_cb(self, palette):
        self.emit("color-set")

    def __palette_color_changed(self, palette, pspec):
        self.color = self._palette.color

    def _get_fg_style_color_str(self):
        context = self.get_style_context()
        # GTK4: get_color with StateType -> get_color with state
        fg_color = context.get_color()
        # the color components are stored as float values between 0.0 and 1.0
        return "#%.2X%.2X%.2X" % (
            int(fg_color.red * 255),
            int(fg_color.green * 255),
            int(fg_color.blue * 255),
        )

    def set_color(self, color):
        assert isinstance(color, Gdk.RGBA)

        if (
            abs(self._color.red - color.red) < 0.001
            and abs(self._color.green - color.green) < 0.001
            and abs(self._color.blue - color.blue) < 0.001
        ):
            return

        self._color = Gdk.RGBA()
        self._color.red = color.red
        self._color.green = color.green
        self._color.blue = color.blue
        self._color.alpha = color.alpha
        self._preview.fill_color = get_svg_color_string(self._color)
        if self._palette:
            self._palette.props.color = self._color
        self.notify("color")

    def get_color(self):
        return self._color

    color = GObject.Property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        """
        Sets the icon for the tool button from a named themed icon.
        If it is none then no icon will be shown.

        Args:
            icon_name(string): The name for a themed icon.
            It can be set as 'None' too.

        Example:
            set_icon_name('view-radial')
        """
        self._preview.props.icon_name = icon_name

    def get_icon_name(self):
        """
        The get_icon_name() method returns the value of the icon_name
        property that contains the name of a themed icon or None.
        """
        return self._preview.props.icon_name

    icon_name = GObject.Property(type=str, getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, pixel_size):
        self._preview.props.pixel_size = pixel_size

    def get_icon_size(self):
        return self._preview.props.pixel_size

    icon_size = GObject.Property(type=int, getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        self._title = title
        if self._palette:
            self._palette.primary_text = self._title

    def get_title(self):
        return self._title

    title = GObject.Property(type=str, getter=get_title, setter=set_title)

    def _set_has_invoker(self, has_invoker):
        self._has_invoker = has_invoker

    def _get_has_invoker(self):
        return self._has_invoker

    has_invoker = GObject.Property(
        type=bool,
        default=True,
        flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
        getter=_get_has_invoker,
        setter=_set_has_invoker,
    )

    def _set_has_palette(self, has_palette):
        self._has_palette = has_palette

    def _get_has_palette(self):
        return self._has_palette

    has_palette = GObject.Property(
        type=bool,
        default=True,
        flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
        getter=_get_has_palette,
        setter=_set_has_palette,
    )

    def _set_accept_drag(self, accept_drag):
        self._accept_drag = accept_drag

    def _get_accept_drag(self):
        return self._accept_drag

    accept_drag = GObject.Property(
        type=bool,
        default=True,
        flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
        getter=_get_accept_drag,
        setter=_set_accept_drag,
    )


class _ColorPalette(Palette):
    """This is a color picker palette. It will usually be used indirectly
    trough a sugar4.graphics.ColorButton.
    """

    _RED = 0
    _GREEN = 1
    _BLUE = 2

    __gtype_name__ = "SugarColorPalette"

    # The color-set signal is emitted when the user is finished selecting
    # a color.
    __gsignals__ = {"color-set": (GObject.SignalFlags.RUN_FIRST, None, tuple())}

    def __init__(self, **kwargs):
        self._color = Gdk.RGBA()
        self._color.red = 0.0
        self._color.green = 0.0
        self._color.blue = 0.0
        self._color.alpha = 1.0
        self._previous_color = Gdk.RGBA()
        self._previous_color.red = 0.0
        self._previous_color.green = 0.0
        self._previous_color.blue = 0.0
        self._previous_color.alpha = 1.0
        self._scales = None

        Palette.__init__(self, **kwargs)

        self.connect("popup", self.__popup_cb)
        self.connect("popdown", self.__popdown_cb)

        self._picker_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # GTK4: Gtk.Alignment removed, use margins instead
        alignment = Gtk.Box()
        alignment.set_margin_start(style.DEFAULT_SPACING)
        alignment.set_margin_end(style.DEFAULT_SPACING)
        alignment.append(self._picker_hbox)
        self.set_content(alignment)

        # GTK4: Gtk.Table → Gtk.Grid
        self._swatch_tray = Gtk.Grid()

        self._picker_hbox.append(self._swatch_tray)
        # GTK4: Gtk.VSeparator → Gtk.Separator with orientation
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self._picker_hbox.append(separator)
        self._picker_hbox.set_margin_start(style.DEFAULT_SPACING)
        self._picker_hbox.set_margin_end(style.DEFAULT_SPACING)

        # GTK4: Gtk.Table → Gtk.Grid
        self._chooser_table = Gtk.Grid()
        self._chooser_table.set_column_spacing(style.DEFAULT_PADDING)

        self._scales = []
        self._scales.append(self._create_color_scale(_("Red"), self._RED, 0))
        self._scales.append(self._create_color_scale(_("Green"), self._GREEN, 1))
        self._scales.append(self._create_color_scale(_("Blue"), self._BLUE, 2))

        self._picker_hbox.append(self._chooser_table)

    def _create_color_scale(self, text, color, row):
        label = Gtk.Label(label=text)
        label.set_xalign(1.0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        scale.set_size_request(style.zoom(250), -1)
        scale.set_draw_value(False)
        scale.set_range(0, 1.0)
        scale.set_increments(0.1, 0.2)

        if color == self._RED:
            scale.set_value(self._color.red)
        elif color == self._GREEN:
            scale.set_value(self._color.green)
        elif color == self._BLUE:
            scale.set_value(self._color.blue)

        scale.connect("value-changed", self.__scale_value_changed_cb, color)
        # GTK4: Grid uses attach(child, column, row, width, height)
        self._chooser_table.attach(label, 0, row, 1, 1)
        self._chooser_table.attach(scale, 1, row, 1, 1)

        return scale

    def _build_swatches(self):
        # Clear existing children
        child = self._swatch_tray.get_first_child()
        while child:
            next_child = self._swatch_tray.get_next_sibling(child)
            self._swatch_tray.remove(child)
            child = next_child

        # Use a hardcoded list of colors for now.
        colors = [
            "#ed2529",
            "#69bc47",
            "#3c54a3",
            "#f57f25",
            "#0b6b3a",
            "#00a0c6",
            "#f6eb1a",
            "#b93f94",
            "#5b4a9c",
            "#000000",
            "#919496",
            "#ffffff",
        ]

        # We want 3 rows of colors.
        rows = 3
        i = 0
        for color_hex in colors:
            color = Gdk.RGBA()
            color.parse(color_hex)
            button = _ColorButton(
                has_palette=False,
                color=color,
                accept_drag=False,
                icon_size=style.STANDARD_ICON_SIZE,
            )
            # GTK4: ReliefStyle removed, buttons are flat by default
            self._swatch_tray.attach(button, i % rows, i // rows, 1, 1)
            button.connect("clicked", self.__swatch_button_clicked_cb)
            i += 1

    def __popup_cb(self, palette):
        self._previous_color = Gdk.RGBA()
        self._previous_color.red = self._color.red
        self._previous_color.green = self._color.green
        self._previous_color.blue = self._color.blue
        self._previous_color.alpha = self._color.alpha

    def __popdown_cb(self, palette):
        self.emit("color-set")

    def __scale_value_changed_cb(self, widget, color):
        new_color = Gdk.RGBA()
        new_color.red = self._color.red
        new_color.green = self._color.green
        new_color.blue = self._color.blue
        new_color.alpha = self._color.alpha

        if color == self._RED:
            new_color.red = widget.get_value()
        elif color == self._GREEN:
            new_color.green = widget.get_value()
        elif color == self._BLUE:
            new_color.blue = widget.get_value()
        self.color = new_color

    def __swatch_button_clicked_cb(self, button):
        self.props.color = button.get_color()

    def set_color(self, color):
        assert isinstance(color, Gdk.RGBA)

        if (
            abs(self._color.red - color.red) < 0.001
            and abs(self._color.green - color.green) < 0.001
            and abs(self._color.blue - color.blue) < 0.001
        ):
            return

        self._color = Gdk.RGBA()
        self._color.red = color.red
        self._color.green = color.green
        self._color.blue = color.blue
        self._color.alpha = color.alpha

        if self._scales:
            self._scales[self._RED].set_value(self._color.red)
            self._scales[self._GREEN].set_value(self._color.green)
            self._scales[self._BLUE].set_value(self._color.blue)

        self.notify("color")

    def get_color(self):
        return self._color

    color = GObject.Property(type=object, getter=get_color, setter=set_color)


def _add_accelerator(tool_button):
    """Add accelerator when widget is properly added to app window."""
    if not hasattr(tool_button, '_accelerator') or not tool_button._accelerator:
        return

    root = tool_button.get_root()
    if not root:
        return

    app = getattr(root, 'get_application', lambda: None)()
    if not app:
        return

    # Remove previous action if exists
    if hasattr(tool_button, '_accel_action_name'):
        try:
            app.remove_action(tool_button._accel_action_name)
        except Exception:
            pass

    action_name = f"color-tool-{id(tool_button)}"
    action = Gio.SimpleAction.new(action_name, None)
    action.connect("activate", lambda a, p: tool_button.emit("clicked"))
    app.add_action(action)
    app.set_accels_for_action(f"app.{action_name}",
                              [tool_button._accelerator])

    tool_button._accel_action = action
    tool_button._accel_action_name = action_name


def setup_accelerator(tool_button):
    _add_accelerator(tool_button)
    tool_button.connect("notify::root", lambda *a: _add_accelerator(tool_button))


class ColorToolButton(Gtk.Box):
    """Color tool button for GTK4 toolbar."""

    __gtype_name__ = "SugarColorToolButton"
    __gsignals__ = {"color-set": (GObject.SignalFlags.RUN_FIRST, None, tuple())}

    def __init__(self, icon_name="color-preview", **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = WidgetInvoker()
        self._palette = None

        GObject.GObject.__init__(self, **kwargs)

        # GTK4: Create the button and add it to the box
        self._color_button = _ColorButton(icon_name=icon_name, has_invoker=False)
        self.append(self._color_button)

        self._color_button.icon_size = style.STANDARD_ICON_SIZE

        self._palette_invoker.attach_widget(self)
        self._palette_invoker.props.toggle_palette = True
        self._palette_invoker.props.lock_palette = True

        # This widget just proxies the following properties to the colorbutton
        self._color_button.connect("notify::color", self.__notify_change)
        self._color_button.connect("notify::icon-name", self.__notify_change)
        self._color_button.connect("notify::icon-size", self.__notify_change)
        self._color_button.connect("notify::title", self.__notify_change)
        self._color_button.connect("color-set", self.__color_set_cb)

    def set_accelerator(self, accelerator):
        """
        Sets keyboard shortcut that activates this button.

        Args:
            accelerator(string): accelerator to be set. Should be in
            form <modifier>Letter

        Example:
            set_accelerator(self, 'accel')
        """
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        """
        Returns the above accelerator string.
        """
        return self._accelerator

    accelerator = GObject.Property(
        type=str, setter=set_accelerator, getter=get_accelerator
    )

    def create_palette(self):
        """
        The create_palette function is called when the palette needs to be
        invoked.

        Returns:

            sugar4.graphics.palette.Palette, or None to indicate that you
            do not want a palette shown
        """
        self._palette = self._color_button.create_palette()
        return self._palette

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker
    )

    def set_expanded(self, expanded):
        box = self.toolbar_box
        if not box:
            return

        if not expanded:
            self._palette_invoker.notify_popdown()
            return

        if box.expanded_button is not None:
            if box.expanded_button != self:
                box.expanded_button.set_expanded(False)
        box.expanded_button = self

    def get_toolbar_box(self):
        parent = self.get_parent()
        if not hasattr(parent, "owner"):
            return None
        return parent.owner

    toolbar_box = property(get_toolbar_box)

    def set_color(self, color):
        """
        Sets the color of the colorbutton
        """
        self._color_button.props.color = color

    def get_color(self):
        """
        Gets the above set color string.
        """
        return self._color_button.props.color

    color = GObject.Property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        """
        Sets the icon for the tool button from a named themed icon.

        Args:
            icon_name(string): The name for a themed icon.
            It can be set as 'None' too.

        Example:
            set_icon_name('view-radial')
        """
        self._color_button.props.icon_name = icon_name

    def get_icon_name(self):
        """
        The get_icon_name() method returns the value of the icon_name
        property that contains the name of a themed icon or None.
        """
        return self._color_button.props.icon_name

    icon_name = GObject.Property(type=str, getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, icon_size):
        """
        Sets the size of icons in the colorbutton.
        """
        self._color_button.props.icon_size = icon_size

    def get_icon_size(self):
        """
        Gets the size of icons in the colorbutton.
        """
        return self._color_button.props.icon_size

    icon_size = GObject.Property(type=int, getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        """
        The set_title() method sets the "title" property to the value of
        title. The "title" property contains the string that is used to
        set the colorbutton title.
        """
        self._color_button.props.title = title

    def get_title(self):
        """
        Return the above title string.
        """
        return self._color_button.props.title

    title = GObject.Property(type=str, getter=get_title, setter=set_title)

    def __notify_change(self, widget, pspec):
        self.notify(pspec.name)

    def __color_set_cb(self, widget):
        self.emit("color-set")
