# Copyright (C) 2013, One Laptop Per Child
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
A progress icon is a progress indicator in the form of an icon.

The icon is drawn twice, once with only a stroke and once with only a fill.
The fill is clipped to the current progress, so the icon appears to fill up
as the operation it represents advances.
"""

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

from sugar4.graphics import style  # noqa: E402
from sugar4.graphics.icon import get_surface  # noqa: E402


class ProgressIcon(Gtk.DrawingArea):
    """
    Display the progress filling the icon.

    This class is compatible with the :class:`sugar4.graphics.icon.Icon`
    class.  Call :meth:`update` with the new progress to update the icon.

    The direction defaults to ``'vertical'``, in which case the icon is
    filled from bottom to top.  If direction is set to ``'horizontal'``,
    it will be filled from right to left or from left to right, depending
    on the system's language RTL setting.

    Args:
        icon_name (str): name of the icon
            [e.g. ``icon_name='emblem-downloads'``]
        pixel_size (int): sets the icon size
            [e.g. ``pixel_size=style.LARGE_ICON_SIZE``]
        stroke_color (str): stroke color means border color
        fill_color (str): the main (inside) color of the progress icon
            [e.g. ``fill_color=style.COLOR_BLUE.get_svg()``]
        direction (str): ``'vertical'`` or ``'horizontal'``
    """

    def __init__(
        self,
        icon_name: str,
        pixel_size: int,
        stroke_color: str,
        fill_color: str,
        direction: str = "vertical",
    ):
        super().__init__()

        self._icon_name = icon_name
        self._direction = direction
        self._progress = 0.0

        self._stroke: Optional[object] = get_surface(
            icon_name=icon_name,
            pixel_size=pixel_size,
            stroke_color=stroke_color,
            fill_color=style.COLOR_TRANSPARENT.get_svg(),
        )

        self._fill: Optional[object] = get_surface(
            icon_name=icon_name,
            pixel_size=pixel_size,
            stroke_color=style.COLOR_TRANSPARENT.get_svg(),
            fill_color=fill_color,
        )

        # GTK4 has no do_get_preferred_width()/do_get_preferred_height() for
        # a Gtk.DrawingArea; the size is requested through the content
        # width and height instead.  get_surface() returns None when the
        # icon cannot be found, so fall back to the size that was asked for
        # rather than failing to size the widget at all.
        if self._stroke is not None:
            self.set_content_width(self._stroke.get_width())
            self.set_content_height(self._stroke.get_height())
        else:
            self.set_content_width(pixel_size)
            self.set_content_height(pixel_size)

        self.set_draw_func(self._draw_cb)

    def _draw_cb(self, area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        if self._stroke is None or self._fill is None:
            return

        # Center the graphic in the allocated space.  In GTK3 this read the
        # allocation off the widget; the draw function is handed the same
        # numbers directly.
        margin_x = (width - self._stroke.get_width()) / 2
        margin_y = (height - self._stroke.get_height()) / 2
        cr.translate(margin_x, margin_y)

        # Paint the fill, clipping it by the progress.
        x_, y_ = 0, 0
        surface_width = self._stroke.get_width()
        surface_height = self._stroke.get_height()
        if self._direction == "vertical":  # vertical direction, bottom to top
            y_ = surface_height
            surface_height *= self._progress * -1
        else:
            rtl_direction = Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
            if rtl_direction:  # horizontal direction, right to left
                x_ = surface_width
                surface_width *= self._progress * -1
            else:  # horizontal direction, left to right
                surface_width *= self._progress

        cr.rectangle(x_, y_, surface_width, surface_height)
        cr.clip()
        cr.set_source_surface(self._fill, 0, 0)
        cr.paint()

        # Paint the stroke over the fill.
        cr.reset_clip()
        cr.set_source_surface(self._stroke, 0, 0)
        cr.paint()

    def update(self, progress: float) -> None:
        """
        Update the progress icon with a new progress value.

        Args:
            progress (float): the new progress, between 0.0 and 1.0
                [e.g. ``update(0.9)``]
        """
        self._progress = progress
        self.queue_draw()
