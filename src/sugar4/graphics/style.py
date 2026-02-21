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
Style
=================

The style module defines constants for spacing and sizing, as well as
classes for Colors and Fonts. Text rendering is handled by Pango and
colors are inputted by their HTML code (e.g. #FFFFFF)

All the constants are expressed in pixels. They are defined for the XO
screen and are usually adapted to different resolution by applying a
zoom factor.

"""

import logging
import os
from typing import Tuple

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gio, Gtk, Pango

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False

    # Provide fallbacks for when GTK is not available
    class MockPango:
        class EllipsizeMode:
            END = 3

        class FontDescription:
            def __init__(self, desc):
                self.desc = desc

    Pango = MockPango()


FOCUS_LINE_WIDTH = 2
_TAB_CURVATURE = 1
ELLIPSIZE_MODE_DEFAULT = Pango.EllipsizeMode.END


def _compute_zoom_factor() -> float:
    """
    Calculates zoom factor based on size of screen.
    Returns float representing fraction of maximum possible screen size.
    """
    try:
        scaling = int(os.environ.get("SUGAR_SCALING", "100"))
        return scaling / 100.0
    except ValueError:
        logging.error("Invalid SUGAR_SCALING value in environment")
    return 1.0


class Font:
    """
    A font defines the style of how the text should be rendered.

    This implementation provides integration with Pango
    font descriptions and CSS styling.

    Args:
        desc (str): A description of the Font object in Pango format
    """

    def __init__(self, desc: str):
        self._desc = desc
        self._pango_desc = None

    def __str__(self) -> str:
        """Returns description of font."""
        return self._desc

    def __repr__(self) -> str:
        return f"Font('{self._desc}')"

    def get_pango_desc(self):
        """
        Returns Pango description of font.
        Cached for performance.
        """
        if self._pango_desc is None and GTK_AVAILABLE:
            self._pango_desc = Pango.FontDescription(self._desc)
        return self._pango_desc

    def get_css_string(self) -> str:
        """
        Returns a CSS font specification string for modern styling.
        """
        # Convert Pango description to CSS-compatible format
        parts = self._desc.split()
        css_parts = []

        size = None
        weight = "normal"
        style = "normal"
        family = []

        for part in parts:
            if part.lower() in ["bold", "light", "medium", "heavy"]:
                weight = part.lower()
            elif part.lower() in ["italic", "oblique"]:
                style = part.lower()
            elif part.replace(".", "").isdigit():
                size = part
            else:
                family.append(part)

        if family:
            css_parts.append(f"font-family: {' '.join(family)}")
        if size:
            css_parts.append(f"font-size: {size}pt")
        if weight != "normal":
            css_parts.append(f"font-weight: {weight}")
        if style != "normal":
            css_parts.append(f"font-style: {style}")

        return "; ".join(css_parts)


class Color:
    """
    A Color object defines a specific color with RGBA values.

    This implementation provides integration with modern
    color handling and CSS styling.

    Args:
        color (str): String in the form #FFFFFF representing the color
        alpha (float): Transparency of color (0.0 to 1.0)
    """

    def __init__(self, color: str, alpha: float = 1.0):
        self._r, self._g, self._b = self._html_to_rgb(color)
        self._a = max(0.0, min(1.0, alpha))  # Clamp alpha to valid range

    def __str__(self) -> str:
        return f"Color({self.get_html()}, alpha={self._a})"

    def __repr__(self) -> str:
        return f"Color('{self.get_html()}', alpha={self._a})"

    def get_rgba(self) -> Tuple[float, float, float, float]:
        """
        Returns 4-tuple of red, green, blue, and alpha levels in range 0-1.
        """
        return (self._r, self._g, self._b, self._a)

    def get_int(self) -> int:
        """
        Returns color encoded as an int, in the form rgba.
        """
        return (
            int(self._a * 255)
            + (int(self._b * 255) << 8)
            + (int(self._g * 255) << 16)
            + (int(self._r * 255) << 24)
        )

    def get_gdk_rgba(self):
        """
        Returns GDK RGBA color object for GTK4.
        This replaces the deprecated get_gdk_color method.
        """
        if not GTK_AVAILABLE:
            return None
        rgba = Gdk.RGBA()
        rgba.red = self._r
        rgba.green = self._g
        rgba.blue = self._b
        rgba.alpha = self._a
        return rgba

    def get_gdk_color(self):
        """
        Returns GDK standard color (deprecated in GTK4).
        Maintained for compatibility.
        """
        if not GTK_AVAILABLE:
            return None
        logging.warning("get_gdk_color is deprecated in GTK4, use get_gdk_rgba instead")
        return Gdk.Color(
            int(self._r * 65535), int(self._g * 65535), int(self._b * 65535)
        )

    def get_html(self) -> str:
        """
        Returns string in the standard HTML color format (#FFFFFF).
        """
        return "#%02x%02x%02x" % (
            int(self._r * 255),
            int(self._g * 255),
            int(self._b * 255),
        )

    def get_css_rgba(self) -> str:
        """
        Returns CSS rgba() string for GTK4 styling.
        """
        return f"rgba({int(self._r * 255)}, {int(self._g * 255)}, {int(self._b * 255)}, {self._a})"

    def _html_to_rgb(self, html_color: str) -> Tuple[float, float, float]:
        """
        Converts and returns (r, g, b) tuple in float format from
        standard HTML format (#FFFFFF). Colors will be in range 0-1.

        Args:
            html_color (str): HTML string in the format #FFFFFF
        """
        html_color = html_color.strip()
        if html_color[0] == "#":
            html_color = html_color[1:]
        if len(html_color) != 6:
            raise ValueError(f"input #{html_color} is not in #RRGGBB format")

        r, g, b = html_color[:2], html_color[2:4], html_color[4:]
        r, g, b = [int(n, 16) for n in (r, g, b)]
        r, g, b = (r / 255.0, g / 255.0, b / 255.0)

        return (r, g, b)

    def get_svg(self) -> str:
        """
        Returns HTML formatted color, unless the color is completely
        transparent, in which case returns "none".
        """
        if self._a == 0.0:
            return "none"
        else:
            return self.get_html()

    def with_alpha(self, alpha: float) -> "Color":
        """
        Returns a new Color with the specified alpha value.
        """
        return Color(self.get_html(), alpha)


def zoom(units: float) -> int:
    """
    Returns size of units pixels at current zoom level.

    Args:
        units (int or float): Size of item at full size
    """
    return int(ZOOM_FACTOR * units)


def apply_css_to_widget(widget, css: str) -> None:
    """
    Apply CSS styling to a widget.

    Args:
        widget: Widget to style
        css (str): CSS string to apply
    """
    if not GTK_AVAILABLE:
        return

    try:
        from gi.repository import Gtk
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)

        context = widget.get_style_context()
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    except Exception as e:
        logging.warning(f"Failed to apply CSS: {e}")


ZOOM_FACTOR = _compute_zoom_factor()  #: Scale factor, as float (eg. 0.72, 1.0)

DEFAULT_SPACING = zoom(15)  #: Spacing is placed in-between elements
DEFAULT_PADDING = zoom(6)  #: Padding is placed around an element

#: allow elements to tile neatly within boundaries of a grid
#: http://wiki.sugarlabs.org/go/Human_Interface_Guidelines#The_Grid_System
GRID_CELL_SIZE = zoom(75)

LINE_WIDTH = zoom(2)  #: Thickness of a separator line

#: icon that fits within a grid cell
STANDARD_ICON_SIZE = zoom(55)
#: small icon, used in palette menu items
SMALL_ICON_SIZE = zoom(33)
#: larger than standard
MEDIUM_ICON_SIZE = zoom(55 * 1.5)
#: larger than medium, used in journal empty view
LARGE_ICON_SIZE = zoom(55 * 2.0)
#: larger than large, used in activity pulsing launcher icon
XLARGE_ICON_SIZE = zoom(55 * 2.75)

# Font settings
if GTK_AVAILABLE and "org.sugarlabs.font" in Gio.Settings.list_schemas():
    try:
        settings = Gio.Settings("org.sugarlabs.font")
        FONT_SIZE = settings.get_double("default-size")  #: User's preferred font size
        FONT_FACE = settings.get_string("default-face")  #: User's preferred font face
    except Exception:
        FONT_SIZE = 10  #: Default font size
        FONT_FACE = "Sans Serif"  #: Default font face
else:
    #: User's preferred font size
    FONT_SIZE = 10
    #: User's preferred font face
    FONT_FACE = "Sans Serif"

#: Normal font
FONT_NORMAL = Font("%s %f" % (FONT_FACE, FONT_SIZE))
#: Bold font
FONT_BOLD = Font("%s bold %f" % (FONT_FACE, FONT_SIZE))
#: Height in pixels of normal font
FONT_NORMAL_H = zoom(24)
#: Height in pixels of bold font
FONT_BOLD_H = zoom(24)
#: Italic font
FONT_ITALIC = Font(f"{FONT_FACE} italic {FONT_SIZE}")


# old style toolbox design (maintained for compatibility)
TOOLBOX_SEPARATOR_HEIGHT = zoom(9)
TOOLBOX_HORIZONTAL_PADDING = zoom(75)
TOOLBOX_TAB_VBORDER = int((zoom(36) - FONT_NORMAL_H - FOCUS_LINE_WIDTH) / 2)
TOOLBOX_TAB_HBORDER = zoom(15) - FOCUS_LINE_WIDTH - _TAB_CURVATURE
TOOLBOX_TAB_LABEL_WIDTH = zoom(150 - 15 * 2)

COLOR_BLACK = Color("#000000")  #: Black
COLOR_WHITE = Color("#FFFFFF")  #: White
#: Fully transparent color
COLOR_TRANSPARENT = Color("#FFFFFF", alpha=0.0)
#: Default background color of a window
COLOR_PANEL_GREY = Color("#C0C0C0")
#: Background color of selected entry
COLOR_SELECTION_GREY = Color("#A6A6A6")
#: Color of toolbars
COLOR_TOOLBAR_GREY = Color("#282828")
#: Color of buttons
COLOR_BUTTON_GREY = Color("#808080")
#: Fill colour of an inactive button
COLOR_INACTIVE_FILL = Color("#9D9FA1")
#: Stroke colour of an inactive button
COLOR_INACTIVE_STROKE = Color("#757575")
#: Background color of entry
COLOR_TEXT_FIELD_GREY = Color("#E5E5E5")
#: Color of highlighted text
COLOR_HIGHLIGHT = Color("#E7E7E7")

# Additional GTK4-specific colors
COLOR_PRIMARY = Color("#0066CC")  #: Primary accent color
COLOR_SUCCESS = Color("#00AA00")  #: Success state color
COLOR_WARNING = Color("#FF8800")  #: Warning state color
COLOR_ERROR = Color("#CC0000")  #: Error state color

# Palette and UI constants
PALETTE_CURSOR_DISTANCE = zoom(
    10
)  #: Cursor invoked palettes will be placed this far from the cursor
TOOLBAR_ARROW_SIZE = zoom(24)  #: Size of arrow displayed under toolbar buttons
MENU_WIDTH_CHARS = 60  #: Max width of text in a palette menu, in chars

# GTK4-specific constants
BORDER_RADIUS = zoom(8)  #: Default border radius for rounded corners
SHADOW_BLUR = zoom(4)  #: Default shadow blur radius
TRANSITION_DURATION = 200  #: Default transition duration in milliseconds
