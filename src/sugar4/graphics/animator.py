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
Animator
====================

The animator module provides a simple framework to create animations.

Example:
    Animate the size of a window::

        from gi.repository import Gtk
        from sugar4.graphics.animator import Animator, Animation

        # Construct a window to animate
        w = Gtk.Window()
        w.connect('destroy', lambda w: app.quit())

        # Start the animation when the window is shown
        w.connect('realize', lambda self: animator.start())
        w.present()

        # Construct a 5 second animator
        animator = Animator(5, widget=w)

        class SizeAnimation(Animation):
            def __init__(self):
                # Tell the animation to give us values between 20 and
                # 420 during the animation
                Animation.__init__(self, 20, 420)

            def next_frame(self, frame):
                size = int(frame)
                w.set_default_size(size, size)

        # Add the animation to the animator
        animation = SizeAnimation()
        animator.add(animation)

        # The animation runs inside a GLib main loop
        app.run()

STABLE.
"""

import time
import math
import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, GLib
import logging

EASE_OUT_EXPO = 0
EASE_IN_EXPO = 1


class Animator(GObject.GObject):
    """
    The animator class manages the timing for calling the animations.

    The animations can be added using the `add` function and then started
    with the `start` function. If multiple animations are added, then they
    will be played back at the same time and rate as each other.

    The `completed` signal is emitted upon the completion of the animation
    and also when the `stop` function is called.

    Args:
        duration (float): the duration of the animation in seconds
        fps (int, optional): the number of animation callbacks to make
            per second (frames per second). This is used as fallback when
            frame clock is not available.
        easing (int): the desired easing mode, either `EASE_OUT_EXPO`
            or `EASE_IN_EXPO`
        widget (:class:`Gtk.Widget`): one of the widgets that the animation
            is acting on. If supplied, the animation will run on the frame
            clock of the widget for smoother animation.

    .. note::

        When creating an animation, take into account the limited cpu power
        on some devices, such as the XO. Setting the fps too high can
        use significant cpu usage.
    """

    __gsignals__ = {
        "completed": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, duration, fps=20, easing=EASE_OUT_EXPO, widget=None):
        GObject.GObject.__init__(self)

        self._animations = []
        self._duration = duration
        self._interval = 1.0 / fps
        self._easing = easing
        self._widget = widget
        self._timeout_sid = 0
        self._tick_callback_id = 0
        self._start_time = None
        self._completed = False
        self._in_tick_cb = False

    def add(self, animation):
        """
        Add an animation to this animator.

        Args:
            animation (:class:`sugar4.graphics.animator.Animation`):
                the animation instance to add
        """
        self._animations.append(animation)

    def remove_all(self):
        """
        Remove all animations and stop this animator.
        """
        self.stop()
        self._animations = []

    def start(self):
        """
        Start the animation running. This will stop and restart the
        animation if the animation is currently running.
        """
        if self._timeout_sid or self._tick_callback_id:
            self.stop()

        self._start_time = time.time()
        self._completed = False

        if self._widget and hasattr(self._widget, "add_tick_callback"):
            try:
                self._tick_callback_id = self._widget.add_tick_callback(
                    self._tick_cb, None
                )
            except Exception as e:
                logging.warning(
                    "Failed to use frame clock, falling back to timeout: %s", e
                )
                self._use_timeout_fallback()
        else:
            self._use_timeout_fallback()

    def _use_timeout_fallback(self):
        interval_ms = int(self._interval * 1000)
        self._timeout_sid = GLib.timeout_add(interval_ms, self._timeout_cb)

    def stop(self):
        """
        Stop the animation and emit the `completed` signal.
        """
        if self._tick_callback_id and self._widget:
            if not getattr(self, '_in_tick_cb', False):
                try:
                    self._widget.remove_tick_callback(self._tick_callback_id)
                except Exception as e:
                    logging.warning("Error removing tick callback: %s", e)
            self._tick_callback_id = 0

        if self._timeout_sid:
            GLib.source_remove(self._timeout_sid)
            self._timeout_sid = 0

        for animation in self._animations:
            animation.do_stop()

        if not self._completed:
            self._completed = True
            self.emit("completed")

    def _tick_cb(self, widget, frame_clock, user_data):
        """Frame clock callback for smooth animation timing."""
        if self._start_time is None:
            self._start_time = time.time()
            
        self._in_tick_cb = True
        try:
            res = self._next_frame_cb()
        finally:
            self._in_tick_cb = False
            
        if res == GLib.SOURCE_REMOVE:
            self._tick_callback_id = 0
            
        return res

    def _timeout_cb(self):
        """GLib timeout callback."""
        return self._next_frame_cb()

    def _next_frame_cb(self):
        """Process the next animation frame."""
        if self._completed:
            return GLib.SOURCE_REMOVE

        current_time = min(self._duration, time.time() - self._start_time)
        current_time = max(current_time, 0.0)

        for animation in self._animations:
            animation.do_frame(current_time, self._duration, self._easing)

        if current_time >= self._duration:
            self.stop()
            return GLib.SOURCE_REMOVE
        else:
            return GLib.SOURCE_CONTINUE


class Animation(object):
    """
    The animation class is a base class for creating an animation.
    It should be subclassed. Subclasses should specify a `next_frame`
    function to set the required properties based on the animation
    progress. The range of the `frame` value passed to the `next_frame`
    function is defined by the `start` and `end` values.

    Args:
        start (float): the first `frame` value for the `next_frame` method
        end (float): the last `frame` value for the `next_frame` method

    .. code-block:: python

        class MyAnimation(Animation):
            def __init__(self, thing):
                # Tell the animation to give us values between 0.0 and
                # 1.0 during the animation
                Animation.__init__(self, 0.0, 1.0)
                self._thing = thing

            def next_frame(self, frame):
                # Use the `frame` value to set properties
                self._thing.set_green_value(frame)
    """

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def do_frame(self, t, duration, easing):
        """
        This method is called by the animator class every frame. This
        method calculates the `frame` value to then call `next_frame`.

        Args:
            t (float): the current time elapsed of the animation in seconds
            duration (float): the length of the animation in seconds
            easing (int): the easing mode passed to the animator
        """
        start = self.start
        change = self.end - self.start

        if t == duration:
            frame = self.end
        else:
            if easing == EASE_OUT_EXPO:
                frame = change * (-pow(2, -10 * t / duration) + 1) + start
            elif easing == EASE_IN_EXPO:
                frame = change * pow(2, 10 * (t / duration - 1)) + start
            else:
                frame = change * (t / duration) + start

        self.next_frame(frame)

    def next_frame(self, frame):
        """
        This method is called every frame and should be overridden by
        subclasses.

        Args:
            frame (float): a value between `start` and `end` representing
                the current progress in the animation
        """
        pass

    def do_stop(self):
        """
        This method is called whenever the animation is stopped, either
        due to the animation ending or being stopped by the animation.
        `next_frame` will not be called after do_stop, unless the animation
        is restarted.

        .. versionadded:: 0.109.0.3

        This should be used in subclasses if they bind any signals.  Eg.
        if they bind the draw signal for a widget:

        .. code-block:: python

            class SignalAnimation(Animation):

                def __init__(self, widget):
                    Animation.__init__(self, 0, 1)
                    self._draw_hid = None
                    self._widget = widget

                def next_frame(self, frame):
                    self._frame = frame
                    if self._draw_hid is None:
                        self._draw_hid = self._widget.connect_after(
                            'draw', self.__draw_cb)
                    self._widget.queue_draw()

                def __draw_cb(self, widget, cr):
                    cr.save()
                    # Do the draw
                    cr.restore()

                def do_stop(self):
                    self._widget.disconnect(self._draw_hid)
                    self._widget.queue_draw()

        """
        pass


class FadeAnimation(Animation):
    """
    A convenience animation class for fading widgets in/out.

    Args:
        widget (Gtk.Widget): The widget to animate
        start_opacity (float): Starting opacity (0.0 to 1.0)
        end_opacity (float): Ending opacity (0.0 to 1.0)
    """

    def __init__(self, widget, start_opacity=0.0, end_opacity=1.0):
        super().__init__(start_opacity, end_opacity)
        self._widget = widget

    def next_frame(self, frame):
        """Update widget opacity."""
        if self._widget:
            self._widget.set_opacity(frame)


class ScaleAnimation(Animation):
    """
    A convenience animation class for scaling widgets via opacity.

    GTK4 Python bindings do not expose Gsk.Transform on Gtk.Widget
    directly. This class uses opacity as a visual scale proxy.

    Args:
        widget (Gtk.Widget): The widget to animate
        start_scale (float): Starting opacity (0.0 to 1.0)
        end_scale (float): Ending opacity (0.0 to 1.0)
    """

    def __init__(self, widget, start_scale=0.0, end_scale=1.0):
        super().__init__(start_scale, end_scale)
        self._widget = widget

    def next_frame(self, frame):
        """Update widget opacity as scale proxy."""
        if self._widget:
            self._widget.set_opacity(max(0.0, min(1.0, frame)))


class MoveAnimation(Animation):
    """
    A convenience animation class for moving widgets.

    Uses widget margin properties as a proxy for position, which is the
    standard GTK4 Python API approach. Direct transform manipulation is
    not exposed on Gtk.Widget in Python bindings.

    Args:
        widget (Gtk.Widget): The widget to animate
        start_pos (tuple): Starting position (x, y) as margin offsets
        end_pos (tuple): Ending position (x, y) as margin offsets
    """

    def __init__(self, widget, start_pos, end_pos):
        super().__init__(0.0, 1.0)
        self._widget = widget
        self._start_pos = start_pos
        self._end_pos = end_pos

    def next_frame(self, frame):
        """Update widget margin position."""
        if self._widget:
            x = int(self._start_pos[0] + (self._end_pos[0] - self._start_pos[0]) * frame)
            y = int(self._start_pos[1] + (self._end_pos[1] - self._start_pos[1]) * frame)
            self._widget.set_margin_start(max(0, x))
            self._widget.set_margin_top(max(0, y))


class ColorAnimation(Animation):
    """
    A convenience animation class for animating colors.

    Args:
        start_color (tuple): Starting RGBA color (r, g, b, a)
        end_color (tuple): Ending RGBA color (r, g, b, a)
        callback (function): Function to call with interpolated color
    """

    def __init__(self, start_color, end_color, callback):
        super().__init__(0.0, 1.0)
        self._start_color = start_color
        self._end_color = end_color
        self._callback = callback

    def next_frame(self, frame):
        """Interpolate color and call callback."""
        if self._callback:
            r = (
                self._start_color[0]
                + (self._end_color[0] - self._start_color[0]) * frame
            )
            g = (
                self._start_color[1]
                + (self._end_color[1] - self._start_color[1]) * frame
            )
            b = (
                self._start_color[2]
                + (self._end_color[2] - self._start_color[2]) * frame
            )
            a = (
                self._start_color[3]
                + (self._end_color[3] - self._start_color[3]) * frame
            )
            self._callback((r, g, b, a))
