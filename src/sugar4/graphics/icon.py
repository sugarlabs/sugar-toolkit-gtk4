# Copyright (C) 2006-2007 Red Hat, Inc.
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
Icons
=====

Icons are small pictures that are used to decorate components. In Sugar, icons
are SVG files that are re-coloured with a fill and a stroke colour. Typically,
icons representing the system use a greyscale color palette, whereas icons
representing people take on their selected XoColors.

This module provides modern icon widgets using native gesture handling
and snapshot-based rendering for improved performance and accessibility.

Classes:
    Icon: Basic icon widget for displaying themed icons
    EventIcon: Icon with mouse event handling using gesture controllers
    CanvasIcon: EventIcon with active/prelight states and styleable background
    CellRendererIcon: Icon renderer for use in tree/list views
    get_icon_file_name: Utility function to resolve icon paths
    get_surface: Utility function to get cairo surfaces for icons
    get_icon_state: Utility function to get state-based icon names
"""

import re
import logging
import os
from typing import Optional, Tuple, Dict
from configparser import ConfigParser

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Rsvg", "2.0")

from gi.repository import GLib, GObject, Gtk, Gdk, GdkPixbuf, Rsvg
import cairo

from sugar4.graphics.xocolor import XoColor


# Simple LRU cache implementation
class _LRU:
    def __init__(self, size):
        self.size = size
        self.cache = {}
        self.order = []

    def __contains__(self, key):
        return key in self.cache

    def __getitem__(self, key):
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.size:
            oldest = self.order.pop(0)
            del self.cache[oldest]

        self.cache[key] = value
        self.order.append(key)


_BADGE_SIZE = 0.45
_DEFAULT_ICON_SIZE = 48

# Icon size constants
SMALL_ICON_SIZE = 16
STANDARD_ICON_SIZE = 48
LARGE_ICON_SIZE = 96


class _SVGLoader:
    """Loads and caches SVG icons with entity replacement."""

    def __init__(self):
        self._cache = _LRU(100)

    def load(
        self, file_name: str, entities: Dict[str, str], cache: bool = True
    ) -> Optional[Rsvg.Handle]:
        """Load SVG with entity replacement."""
        if cache and file_name in self._cache:
            icon_data = self._cache[file_name]
        else:
            try:
                with open(file_name, "r", encoding="utf-8") as icon_file:
                    icon_data = icon_file.read()

                if cache:
                    self._cache[file_name] = icon_data
            except (IOError, OSError) as e:
                logging.error("Failed to load icon file %s: %s", file_name, e)
                return None

        # Replace entities
        for entity, value in entities.items():
            if isinstance(value, str):
                xml = f'<!ENTITY {entity} "{value}">'
                icon_data = re.sub(f"<!ENTITY {entity} .*>", xml, icon_data)
            else:
                logging.error("Icon %s, entity %s is invalid.", file_name, entity)

        try:
            return Rsvg.Handle.new_from_data(icon_data.encode("utf-8"))
        except GLib.Error as e:
            logging.error("Failed to create SVG handle for %s: %s", file_name, e)
            return None


class _IconInfo:
    """Information about an icon including attachment points."""

    def __init__(self):
        self.file_name: Optional[str] = None
        self.attach_x: float = 0.0
        self.attach_y: float = 0.0


class _BadgeInfo:
    """Information about badge positioning."""

    def __init__(self):
        self.attach_x: float = 0.0
        self.attach_y: float = 0.0
        self.size: int = 0
        self.icon_padding: int = 0


class _IconBuffer:
    """Manages icon rendering and caching."""

    _surface_cache = _LRU(100)
    _loader = _SVGLoader()

    def __init__(self):
        self.icon_name: Optional[str] = None
        self.file_name: Optional[str] = None
        self.fill_color: Optional[str] = None
        self.stroke_color: Optional[str] = None
        self.background_color: Optional[Gdk.RGBA] = None
        self.badge_name: Optional[str] = None
        self.width: int = _DEFAULT_ICON_SIZE
        self.height: int = _DEFAULT_ICON_SIZE
        self.cache: bool = True
        self.scale: float = 1.0
        self.pixbuf: Optional[GdkPixbuf.Pixbuf] = None
        self.alpha: float = 1.0

    def _get_cache_key(self, sensitive: bool = True) -> tuple:
        """Generate cache key for this icon configuration."""
        bg_color = None
        if self.background_color:
            bg_color = (
                self.background_color.red,
                self.background_color.green,
                self.background_color.blue,
                self.background_color.alpha,
            )

        return (
            self.icon_name,
            self.file_name,
            id(self.pixbuf),
            self.fill_color,
            self.stroke_color,
            self.badge_name,
            self.width,
            self.height,
            bg_color,
            sensitive,
            self.scale,
            self.alpha,
        )

    def _load_svg(self, file_name: str) -> Optional[Rsvg.Handle]:
        """Load SVG with color entities."""
        entities = {}
        if self.fill_color:
            entities["fill_color"] = self.fill_color
        if self.stroke_color:
            entities["stroke_color"] = self.stroke_color

        return self._loader.load(file_name, entities, self.cache)

    def _get_attach_points(self, file_name: str) -> Tuple[float, float]:
        """Get badge attachment points from .icon file."""
        attach_x = attach_y = 0.0

        if not file_name:
            return attach_x, attach_y

        # Try to read from .icon file
        icon_config_file = file_name.replace(".svg", ".icon")
        if icon_config_file != file_name and os.path.exists(icon_config_file):
            try:
                cp = ConfigParser()
                cp.read(icon_config_file)
                attach_points_str = cp.get("Icon Data", "AttachPoints")
                attach_points = attach_points_str.split(",")
                attach_x = float(attach_points[0].strip()) / 1000.0
                attach_y = float(attach_points[1].strip()) / 1000.0
            except Exception as e:
                logging.debug("Could not read icon config %s: %s", icon_config_file, e)

        return attach_x, attach_y

    def _get_icon_info(
        self, file_name: Optional[str], icon_name: Optional[str]
    ) -> _IconInfo:
        """Get icon information from theme or file."""
        icon_info = _IconInfo()

        if file_name:
            icon_info.file_name = file_name
            icon_info.attach_x, icon_info.attach_y = self._get_attach_points(file_name)
        elif icon_name:
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

            # Use IconTheme.lookup_icon for themed icon resolution
            icon_paintable = icon_theme.lookup_icon(
                icon_name,
                None,
                self.width,
                1,
                Gtk.TextDirection.NONE,
                0,
            )

            if icon_paintable:
                file_path = icon_paintable.get_file()
                if file_path:
                    icon_info.file_name = file_path.get_path()
                    icon_info.attach_x, icon_info.attach_y = self._get_attach_points(
                        icon_info.file_name
                    )
            else:
                logging.warning("No icon with name %s found in theme", icon_name)

        return icon_info

    def _get_badge_info(
        self, icon_info: _IconInfo, icon_width: int, icon_height: int
    ) -> _BadgeInfo:
        """Get badge positioning information."""
        info = _BadgeInfo()
        if self.badge_name is None:
            return info

        info.size = int(_BADGE_SIZE * icon_width)
        info.attach_x = int(icon_info.attach_x * icon_width - info.size / 2)
        info.attach_y = int(icon_info.attach_y * icon_height - info.size / 2)

        if info.attach_x < 0 or info.attach_y < 0:
            info.icon_padding = max(-info.attach_x, -info.attach_y)
        elif (
            info.attach_x + info.size > icon_width
            or info.attach_y + info.size > icon_height
        ):
            x_padding = info.attach_x + info.size - icon_width
            y_padding = info.attach_y + info.size - icon_height
            info.icon_padding = max(x_padding, y_padding)

        return info

    def _draw_badge(self, context: cairo.Context, size: int, sensitive: bool):
        """Draw badge icon."""
        if not self.badge_name:
            return

        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        badge_paintable = icon_theme.lookup_icon(
            self.badge_name,
            None,
            size,
            1,
            Gtk.TextDirection.NONE,
            Gtk.IconLookupFlags.NONE,
        )

        if not badge_paintable:
            return

        badge_file = badge_paintable.get_file()
        if not badge_file:
            return

        badge_file_name = badge_file.get_path()
        if not badge_file_name:
            return

        if badge_file_name.endswith(".svg"):
            handle = self._load_svg(badge_file_name)
            if handle:
                # Get SVG dimensions
                svg_rect = handle.get_intrinsic_size_in_pixels()
                if svg_rect[0]:  # has_width
                    icon_width, icon_height = svg_rect[1], svg_rect[2]
                else:
                    icon_width = icon_height = size

                context.scale(float(size) / icon_width, float(size) / icon_height)

                # Create viewport
                viewport = Rsvg.Rectangle()
                viewport.x = 0
                viewport.y = 0
                viewport.width = icon_width
                viewport.height = icon_height

                if sensitive:
                    handle.render_document(context, viewport)
                else:
                    context.push_group()
                    handle.render_document(context, viewport)
                    context.pop_group_to_source()
                    context.paint_with_alpha(0.5)
        else:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(badge_file_name)
                icon_width = pixbuf.get_width()
                icon_height = pixbuf.get_height()

                context.scale(float(size) / icon_width, float(size) / icon_height)
                Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)

                if sensitive:
                    context.paint()
                else:
                    context.paint_with_alpha(0.5)
            except GLib.Error as e:
                logging.error("Failed to load badge pixbuf: %s", e)

    def _get_xo_color(self) -> Optional[XoColor]:
        """Get XoColor from stroke and fill colors."""
        if self.stroke_color and self.fill_color:
            return XoColor(f"{self.stroke_color},{self.fill_color}")
        return None

    def _set_xo_color(self, xo_color: Optional[XoColor]):
        """Set stroke and fill colors from XoColor."""
        if xo_color:
            self.stroke_color = xo_color.get_stroke_color()
            self.fill_color = xo_color.get_fill_color()
        else:
            self.stroke_color = None
            self.fill_color = None

    def get_surface(self, sensitive: bool = True) -> Optional[cairo.ImageSurface]:
        """Get cairo surface for this icon."""
        cache_key = self._get_cache_key(sensitive)
        if cache_key in self._surface_cache:
            return self._surface_cache[cache_key]

        # Handle pixbuf directly
        if self.pixbuf:
            surface = self._create_surface_from_pixbuf(self.pixbuf, sensitive)
            if surface:
                self._surface_cache[cache_key] = surface
            return surface

        # Try to load from file or theme, fallback to document-generic
        for file_name, icon_name in [
            (self.file_name, self.icon_name),
            (None, "document-generic"),
        ]:
            icon_info = self._get_icon_info(file_name, icon_name)
            if not icon_info.file_name:
                continue

            surface = self._create_surface_from_file(icon_info, sensitive)
            if surface:
                self._surface_cache[cache_key] = surface
                return surface

        return None

    def _get_size(
        self, icon_width: int, icon_height: int, padding: int
    ) -> Tuple[int, int]:
        """Get final surface size including padding."""
        if self.width is not None and self.height is not None:
            width = self.width + padding
            height = self.height + padding
        else:
            width = icon_width + padding
            height = icon_height + padding
        return width, height

    def _create_surface_from_pixbuf(
        self, pixbuf: GdkPixbuf.Pixbuf, sensitive: bool
    ) -> Optional[cairo.ImageSurface]:
        """Create surface from pixbuf."""
        width, height = self.width, self.height

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        if self.background_color:
            ctx.set_source_rgba(
                self.background_color.red,
                self.background_color.green,
                self.background_color.blue,
                self.background_color.alpha,
            )
            ctx.paint()

        # Scale pixbuf to fit
        pb_width, pb_height = pixbuf.get_width(), pixbuf.get_height()
        scale_x = width / pb_width
        scale_y = height / pb_height
        scale = min(scale_x, scale_y) * self.scale

        ctx.scale(scale, scale)

        x = (width / scale - pb_width) / 2
        y = (height / scale - pb_height) / 2

        Gdk.cairo_set_source_pixbuf(ctx, pixbuf, x, y)

        if sensitive:
            if self.alpha == 1.0:
                ctx.paint()
            else:
                ctx.paint_with_alpha(self.alpha)
        else:
            ctx.paint_with_alpha(0.5 * self.alpha)

        return surface

    def _create_surface_from_file(
        self, icon_info: _IconInfo, sensitive: bool
    ) -> Optional[cairo.ImageSurface]:
        """Create surface from file."""
        if not icon_info.file_name:
            return None

        if icon_info.file_name.endswith(".svg"):
            return self._create_surface_from_svg(icon_info, sensitive)
        else:
            # Load as pixbuf
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_info.file_name)
                return self._create_surface_from_pixbuf(pixbuf, sensitive)
            except GLib.Error as e:
                logging.error(
                    "Failed to load pixbuf from %s: %s", icon_info.file_name, e
                )
                return None

    def _create_surface_from_svg(
        self, icon_info: _IconInfo, sensitive: bool
    ) -> Optional[cairo.ImageSurface]:
        """Create surface from SVG file."""
        handle = self._load_svg(icon_info.file_name)
        if not handle:
            return None

        # SVG dimensions
        svg_rect = handle.get_intrinsic_size_in_pixels()
        if svg_rect[0]:  # has_width
            icon_width, icon_height = int(svg_rect[1]), int(svg_rect[2])
        else:
            # Fallback dimensions
            icon_width = icon_height = 48

        # badge info and padding
        badge_info = self._get_badge_info(icon_info, icon_width, icon_height)
        padding = badge_info.icon_padding
        width, height = self._get_size(icon_width, icon_height, padding)

        # Create surface
        if self.background_color is None:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        else:
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, int(width), int(height))

        ctx = cairo.Context(surface)

        if self.background_color:
            ctx.set_source_rgba(
                self.background_color.red,
                self.background_color.green,
                self.background_color.blue,
                self.background_color.alpha,
            )
            ctx.paint()

        # Scale context for icon
        ctx.scale(
            float(width) / (icon_width + padding * 2),
            float(height) / (icon_height + padding * 2),
        )
        ctx.save()

        # Translate for padding
        ctx.translate(padding, padding)

        # Create viewport
        viewport = Rsvg.Rectangle()
        viewport.x = 0
        viewport.y = 0
        viewport.width = icon_width
        viewport.height = icon_height

        # Render main icon
        if sensitive:
            if self.alpha == 1.0:
                handle.render_document(ctx, viewport)
            else:
                ctx.push_group()
                handle.render_document(ctx, viewport)
                ctx.pop_group_to_source()
                ctx.paint_with_alpha(self.alpha)
        else:
            ctx.push_group()
            handle.render_document(ctx, viewport)
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(0.5 * self.alpha)

        # Draw badge if present
        if self.badge_name:
            ctx.restore()
            ctx.translate(badge_info.attach_x, badge_info.attach_y)
            self._draw_badge(ctx, badge_info.size, sensitive)

        return surface

    xo_color = property(_get_xo_color, _set_xo_color)


class Icon(Gtk.Widget):
    """
    Basic Sugar icon widget.

    Displays themed icons with Sugar's color customization features.
    Uses modern snapshot-based rendering for improved performance.

    Properties:
        icon_name (str): Icon name from theme
        file_name (str): Path to icon file
        pixel_size (int): Size in pixels
        fill_color (str): Fill color as hex string
        stroke_color (str): Stroke color as hex string
        xo_color (XoColor): Sugar color pair
        badge_name (str): Badge icon name
        alpha (float): Icon transparency (0.0-1.0)
        scale (float): Icon scale factor
        sensitive (bool): Whether icon appears sensitive
    """

    __gtype_name__ = "SugarIcon"

    def __init__(
        self,
        icon_name: Optional[str] = None,
        file_name: Optional[str] = None,
        pixel_size: int = STANDARD_ICON_SIZE,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._buffer = _IconBuffer()
        self._buffer.icon_name = icon_name
        self._buffer.file_name = file_name
        self._buffer.width = pixel_size
        self._buffer.height = pixel_size

        # Set up drawing
        self.set_size_request(pixel_size, pixel_size)

    def do_snapshot(self, snapshot: Gtk.Snapshot):
        """Render icon using snapshot-based drawing."""
        surface = self._buffer.get_surface(self.get_sensitive())
        if surface:
            width = self.get_width()
            height = self.get_height()

            # Center the icon
            x = (width - surface.get_width()) / 2
            y = (height - surface.get_height()) / 2

            snapshot.save()
            snapshot.translate(Graphene.Point().init(x, y))

            # Convert surface to pixbuf then to texture
            pixbuf = Gdk.pixbuf_get_from_surface(
                surface, 0, 0, surface.get_width(), surface.get_height()
            )
            if pixbuf:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                snapshot.append_texture(
                    texture,
                    Graphene.Rect().init(
                        0, 0, surface.get_width(), surface.get_height()
                    ),
                )
            snapshot.restore()

    def do_measure(
        self, orientation: Gtk.Orientation, for_size: int
    ) -> Tuple[int, int, int, int]:
        """Calculate widget size requirements."""
        size = max(self._buffer.width, self._buffer.height)
        return size, size, -1, -1

    # Properties
    def get_icon_name(self) -> Optional[str]:
        return self._buffer.icon_name

    def set_icon_name(self, icon_name: Optional[str]):
        if self._buffer.icon_name != icon_name:
            self._buffer.icon_name = icon_name
            self.queue_draw()

    def get_file_name(self) -> Optional[str]:
        return self._buffer.file_name

    def set_file_name(self, file_name: Optional[str]):
        if self._buffer.file_name != file_name:
            self._buffer.file_name = file_name
            self.queue_draw()

    def get_pixel_size(self) -> int:
        return self._buffer.width

    def set_pixel_size(self, size: int):
        if self._buffer.width != size:
            self._buffer.width = size
            self._buffer.height = size
            self.set_size_request(size, size)
            self.queue_resize()

    def get_fill_color(self) -> Optional[str]:
        return self._buffer.fill_color

    def set_fill_color(self, color: Optional[str]):
        if self._buffer.fill_color != color:
            self._buffer.fill_color = color
            self.queue_draw()

    def get_stroke_color(self) -> Optional[str]:
        return self._buffer.stroke_color

    def set_stroke_color(self, color: Optional[str]):
        if self._buffer.stroke_color != color:
            self._buffer.stroke_color = color
            self.queue_draw()

    def get_xo_color(self) -> Optional[XoColor]:
        return self._buffer._get_xo_color()

    def set_xo_color(self, xo_color: Optional[XoColor]):
        if not hasattr(self, "_buffer") or self._buffer is None:
            self._buffer = _IconBuffer()
        if self._buffer._get_xo_color() != xo_color:
            self._buffer._set_xo_color(xo_color)
            self.queue_draw()

    def get_badge_name(self) -> Optional[str]:
        return self._buffer.badge_name

    def set_badge_name(self, badge_name: Optional[str]):
        if self._buffer.badge_name != badge_name:
            self._buffer.badge_name = badge_name
            self.queue_resize()

    def get_alpha(self) -> float:
        return self._buffer.alpha

    def set_alpha(self, alpha: float):
        if self._buffer.alpha != alpha:
            self._buffer.alpha = alpha
            self.queue_draw()

    def get_scale(self) -> float:
        return self._buffer.scale

    def set_scale(self, scale: float):
        if self._buffer.scale != scale:
            self._buffer.scale = scale
            self.queue_draw()

    def get_badge_size(self) -> int:
        """Get size of badge icon in pixels."""
        return int(_BADGE_SIZE * self.get_pixel_size())

    # GObject properties
    icon_name = GObject.Property(
        type=str, default=None, getter=get_icon_name, setter=set_icon_name
    )
    file_name = GObject.Property(
        type=str, default=None, getter=get_file_name, setter=set_file_name
    )
    pixel_size = GObject.Property(
        type=int,
        default=STANDARD_ICON_SIZE,
        getter=get_pixel_size,
        setter=set_pixel_size,
    )
    fill_color = GObject.Property(
        type=str, default=None, getter=get_fill_color, setter=set_fill_color
    )
    stroke_color = GObject.Property(
        type=str, default=None, getter=get_stroke_color, setter=set_stroke_color
    )
    xo_color = GObject.Property(
        type=object, default=None, getter=get_xo_color, setter=set_xo_color
    )
    badge_name = GObject.Property(
        type=str, default=None, getter=get_badge_name, setter=set_badge_name
    )
    alpha = GObject.Property(
        type=float, default=1.0, getter=get_alpha, setter=set_alpha
    )
    scale = GObject.Property(
        type=float, default=1.0, getter=get_scale, setter=set_scale
    )

    def get_pixbuf(self) -> Optional[GdkPixbuf.Pixbuf]:
        """Get pixbuf for this icon."""
        return self._buffer.pixbuf

    def set_pixbuf(self, pixbuf: Optional[GdkPixbuf.Pixbuf]):
        """Set pixbuf for this icon."""
        if self._buffer.pixbuf != pixbuf:
            self._buffer.pixbuf = pixbuf
            self.queue_draw()

    def get_gtk_image(self) -> Gtk.Image:
        """
        Create a Gtk.Image from this icon for compatibility.

        Returns:
            Gtk.Image: Image widget with icon content
        """
        surface = self._buffer.get_surface(self.get_sensitive())
        if surface:
            # Convert surface to pixbuf then to texture
            pixbuf = Gdk.pixbuf_get_from_surface(
                surface, 0, 0, surface.get_width(), surface.get_height()
            )
            if pixbuf:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                image = Gtk.Image.new_from_paintable(texture)
                return image

        return Gtk.Image.new_from_icon_name("image-missing")


class EventIcon(Icon):
    """
    Icon widget with mouse event handling using gesture controllers.

    Provides click, press, and release events through modern gesture handling
    for better touch and accessibility support.

    Signals:
        clicked: Emitted when icon is clicked
        pressed: Emitted when icon is pressed
        released: Emitted when icon is released
        activate: Emitted when icon is activated
    """

    __gtype_name__ = "SugarEventIcon"

    __gsignals__ = {
        "clicked": (GObject.SignalFlags.RUN_LAST, None, ()),
        "pressed": (GObject.SignalFlags.RUN_LAST, None, (float, float)),
        "released": (GObject.SignalFlags.RUN_LAST, None, (float, float)),
        "activate": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Set up gesture handling
        self._setup_gestures()

    def _setup_gestures(self):
        """Set up gesture controllers for event handling."""
        # Click gesture
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self._on_pressed)
        click_gesture.connect("released", self._on_released)
        self.add_controller(click_gesture)

    def _on_pressed(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float):
        """Handle press events."""
        self.emit("pressed", x, y)

    def _on_released(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float):
        """Handle release events."""
        self.emit("released", x, y)
        if n_press == 1:  # Single click
            # Check if release is within widget bounds
            width = self.get_width()
            height = self.get_height()
            if 0 <= x <= width and 0 <= y <= height:
                self.emit("clicked")
                self.emit("activate")

    def get_background_color(self) -> Optional[Gdk.RGBA]:
        """Get background color."""
        return self._buffer.background_color

    def set_background_color(self, color: Optional[Gdk.RGBA]):
        """Set background color."""
        if self._buffer.background_color != color:
            self._buffer.background_color = color
            self.queue_draw()

    def get_cache(self) -> bool:
        """Get cache setting."""
        return self._buffer.cache

    def set_cache(self, cache: bool):
        """Set cache setting."""
        self._buffer.cache = cache

    # Additional properties for EventIcon
    background_color = GObject.Property(
        type=object,
        default=None,
        getter=get_background_color,
        setter=set_background_color,
    )
    cache = GObject.Property(
        type=bool, default=True, getter=get_cache, setter=set_cache
    )


class CanvasIcon(EventIcon):
    """
    An EventIcon with active and prelight states, and a styleable background.

    This icon responds to mouse hover and press states with visual feedback.
    """

    __gtype_name__ = "SugarCanvasIcon"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._button_down = False

        # Set up hover and focus controllers
        self._setup_state_controllers()

    def _setup_state_controllers(self):
        """Set up state change controllers."""
        # Motion controller for hover effects
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self._on_enter)
        motion_controller.connect("leave", self._on_leave)
        self.add_controller(motion_controller)

        # Override click gesture to handle states
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self._on_canvas_pressed)
        click_gesture.connect("released", self._on_canvas_released)
        self.add_controller(click_gesture)

    def _on_enter(self, controller, x, y):
        """Handle mouse enter."""
        self.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        if self._button_down:
            self.set_state_flags(Gtk.StateFlags.ACTIVE, False)

    def _on_leave(self, controller):
        """Handle mouse leave."""
        # Don't change state if palette is up (would need palette integration)
        self.unset_state_flags(Gtk.StateFlags.PRELIGHT | Gtk.StateFlags.ACTIVE)

    def _on_canvas_pressed(self, gesture, n_press, x, y):
        """Handle canvas press."""
        self._button_down = True
        self.set_state_flags(Gtk.StateFlags.ACTIVE, False)
        self.emit("pressed", x, y)

    def _on_canvas_released(self, gesture, n_press, x, y):
        """Handle canvas release."""
        self.unset_state_flags(Gtk.StateFlags.ACTIVE)
        self._button_down = False
        self.emit("released", x, y)

        if n_press == 1:
            width = self.get_width()
            height = self.get_height()
            if 0 <= x <= width and 0 <= y <= height:
                self.emit("clicked")
                self.emit("activate")

    def do_snapshot(self, snapshot):
        """Override to render background based on state."""
        # Get allocation and style context
        width = self.get_width()
        height = self.get_height()

        # Render background based on state
        style_context = self.get_style_context()
        style_context.save()

        # Add CSS class for styling
        style_context.add_class("canvas-icon")

        # Render background
        snapshot.render_background(style_context, 0, 0, width, height)

        style_context.restore()

        # Call parent to render icon
        super().do_snapshot(snapshot)


# Simplified cell renderer for list/tree view compatibility
class CellRendererIcon:
    """
    Icon renderer for use in list/tree views.

    Modern implementations use different approaches for cell rendering.
    This provides compatibility for legacy code that may need adaptation.

    Note: Consider using modern list/tree widget patterns instead.
    """

    def __init__(self):
        self._buffer = _IconBuffer()
        self._buffer.cache = True
        self._xo_color = None
        self._prelit_fill_color = None
        self._prelit_stroke_color = None

    def set_icon_name(self, icon_name: str):
        self._buffer.icon_name = icon_name

    def set_file_name(self, file_name: str):
        self._buffer.file_name = file_name

    def set_xo_color(self, xo_color: XoColor):
        self._xo_color = xo_color

    def set_fill_color(self, color: str):
        self._buffer.fill_color = color

    def set_stroke_color(self, color: str):
        self._buffer.stroke_color = color

    def set_size(self, size: int):
        self._buffer.width = size
        self._buffer.height = size

    def get_surface(self, sensitive: bool = True) -> Optional[cairo.ImageSurface]:
        """Get rendered surface."""
        if self._xo_color:
            self._buffer.fill_color = self._xo_color.get_fill_color()
            self._buffer.stroke_color = self._xo_color.get_stroke_color()

        return self._buffer.get_surface(sensitive)


# Utility functions
def get_icon_file_name(icon_name: str) -> Optional[str]:
    """
    Resolve icon name to file path using icon theme.

    Uses the system icon theme to find the appropriate icon file
    for the given icon name.

    Args:
        icon_name: Name of icon to resolve

    Returns:
        Path to icon file or None if not found
    """
    icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    icon_paintable = icon_theme.lookup_icon(
        icon_name,
        None,
        STANDARD_ICON_SIZE,
        1,
        Gtk.TextDirection.NONE,
        Gtk.IconLookupFlags.NONE,
    )

    if icon_paintable:
        file_obj = icon_paintable.get_file()
        if file_obj:
            return file_obj.get_path()

    return None


def get_icon_state(base_name: str, perc: float, step: int = 5) -> Optional[str]:
    """
    Get the closest icon name for a given state in percent.

    Args:
        base_name: Base icon name (e.g., 'network-wireless')
        perc: Desired percentage between 0 and 100
        step: Step increment to find possible icons

    Returns:
        Icon name that represents given state, or None if not found
    """
    strength = round(perc / step) * step
    icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

    while 0 <= strength <= 100:
        icon_name = f"{base_name}-{strength:03d}"
        if icon_theme.has_icon(icon_name):
            return icon_name
        strength += step

    return None


def get_surface(
    icon_name: Optional[str] = None,
    file_name: Optional[str] = None,
    fill_color: Optional[str] = None,
    stroke_color: Optional[str] = None,
    pixel_size: int = STANDARD_ICON_SIZE,
    **kwargs,
) -> Optional[cairo.ImageSurface]:
    """
    Get cairo surface for an icon with specified properties.

    Args:
        icon_name: Icon name from theme
        file_name: Path to icon file
        fill_color: Fill color as hex string
        stroke_color: Stroke color as hex string
        pixel_size: Size in pixels
        **kwargs: Additional properties

    Returns:
        Cairo surface or None if icon not found
    """
    buffer = _IconBuffer()
    buffer.icon_name = icon_name
    buffer.file_name = file_name
    buffer.fill_color = fill_color
    buffer.stroke_color = stroke_color
    buffer.width = pixel_size
    buffer.height = pixel_size

    for key, value in kwargs.items():
        if hasattr(buffer, key):
            setattr(buffer, key, value)

    return buffer.get_surface()


# Import Graphene for snapshot-based rendering operations
try:
    gi.require_version("Graphene", "1.0")
    from gi.repository import Graphene
except (ImportError, ValueError):
    logging.warning("Graphene not available, icon rendering may be limited")

    # Provide fallback
    class _GraphenePoint:
        def init(self, x, y):
            self.x, self.y = x, y
            return self

    class _GrapheneRect:
        def init(self, x, y, width, height):
            self.x, self.y, self.width, self.height = x, y, width, height
            return self

    class _GrapheneMock:
        Point = _GraphenePoint
        Rect = _GrapheneRect

    Graphene = _GrapheneMock()

if hasattr(CanvasIcon, "set_css_name"):
    CanvasIcon.set_css_name("canvas-icon")
