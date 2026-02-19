"""
Alerts appear in an activity below the toolbox and above the canvas.

:class:`Alert` and the derived :class:`TimeoutAlert`,
:class:`ConfirmationAlert`, :class:`ErrorAlert`, and
:class:`NotifyAlert`, each have a title, a message and optional
buttons.

:class:`Alert` will emit a `response` signal when a button is
clicked.

The :class:`TimeoutAlert` and :class:`NotifyAlert` display a countdown
and will emit a `response` signal when a timeout occurs.

Example:
    Create a simple alert message.

    .. code-block:: python

        from sugar4.graphics.alert import Alert

        # Create a new simple alert
        alert = Alert()

        # Set the title and text body of the alert
        alert.props.title = _('Title of Alert Goes Here')
        alert.props.msg = _('Text message of alert goes here')

        # Add the alert to the activity
        self.add_alert(alert)
        alert.show()

STABLE.
"""

# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2010, Anish Mangal <anishmangal2002@gmail.com>
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

import gettext
import math

from gi.repository import Graphene
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from sugar4.graphics import style
from sugar4.graphics.icon import Icon


def _(msg):
    return gettext.dgettext("sugar-toolkit-gtk4", msg)


class Alert(Gtk.Box):
    """
    Alerts are inside the activity window instead of being a
    separate popup window. They do not hide the canvas.

    Use :func:`~sugar4.graphics.window.Window.add_alert` and
    :func:`~sugar4.graphics.window.Window.remove_alert` to add and
    remove an alert.  These methods are inherited by an
    :class:`~sugar4.activity.activity.Activity` via superclass
    :class:`~sugar4.graphics.window.Window`.

    The alert is placed between the canvas and the toolbox, or above
    the canvas in fullscreen mode.

    Args:
        title (str): the title of the alert
        message (str): the message of the alert
        icon (str): the icon that appears at the far left
    """

    __gtype_name__ = "SugarAlert"

    __gsignals__ = {
        "response": (GObject.SignalFlags.RUN_FIRST, None, ([object])),
    }

    __gproperties__ = {
        "title": (str, None, None, None, GObject.ParamFlags.READWRITE),
        "msg": (str, None, None, None, GObject.ParamFlags.READWRITE),
        "icon": (object, None, None, GObject.ParamFlags.WRITABLE),
    }

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, **kwargs)

        self._title = None
        self._msg = None
        self._icon = None
        self._buttons = {}

        # Set margin and spacing (replaces border_width)
        self.set_margin_top(style.DEFAULT_SPACING)
        self.set_margin_bottom(style.DEFAULT_SPACING)
        self.set_margin_start(style.DEFAULT_SPACING)
        self.set_margin_end(style.DEFAULT_SPACING)
        self.set_spacing(style.DEFAULT_SPACING)

        self._msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._title_label = Gtk.Label()
        self._title_label.set_halign(Gtk.Align.START)
        self._title_label.set_valign(Gtk.Align.CENTER)
        self._title_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        self._msg_box.append(self._title_label)

        self._msg_label = Gtk.Label()
        self._msg_label.set_halign(Gtk.Align.START)
        self._msg_label.set_valign(Gtk.Align.CENTER)
        self._msg_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        self._msg_box.append(self._msg_label)
        self.append(self._msg_box)

        self._buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._buttons_box.set_halign(Gtk.Align.END)
        self._buttons_box.set_spacing(style.DEFAULT_SPACING)
        self._buttons_box.set_hexpand(True)
        self.append(self._buttons_box)

        self.add_css_class("sugar-alert")

    def do_set_property(self, pspec, value):
        """
        Set alert property, GObject internal method.
        Use the `alert.props` object, eg::

            alert.props.title = 'Are you happy?'
        """
        if pspec.name == "title":
            if self._title != value:
                self._title = value
                self._title_label.set_markup("<b>" + self._title + "</b>")
        elif pspec.name == "msg":
            if self._msg != value:
                self._msg = value
                self._msg_label.set_markup(self._msg)
                self._msg_label.set_wrap(True)
        elif pspec.name == "icon":
            if self._icon != value:
                self._icon = value
                self.prepend(self._icon)

    def do_get_property(self, pspec):
        """
        Get alert property, GObject internal method.
        Use the `alert.props` object, eg::

            title = alert.props.title
        """
        if pspec.name == "title":
            return self._title
        elif pspec.name == "msg":
            return self._msg

    def add_entry(self):
        """
        Create an entry and add it to the alert.

        The entry is placed after the title and before the buttons.

        Caller is responsible for capturing the entry text in the
        `response` signal handler or a :class:`Gtk.Entry` signal
        handler.

        Returns:
            :class:`Gtk.Entry`: the entry added to the alert
        """
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        position = 0
        for i, child in enumerate([child for child in self]):
            if child == self._buttons_box:
                position = i
                break
        self.insert_child_after(entry, self._msg_box)
        return entry

    def add_button(self, response_id, label, icon=None, position=-1):
        """
        Create a button and add it to the alert.

        The button is added to the end of the alert.

        When the button is clicked, the `response` signal will be
        emitted, along with a response identifier.

        Args:
            response_id (int): the response identifier, a
                :class:`Gtk.ResponseType` constant or any positive
                integer,
            label (str): a label for the button
            icon (:class:`~sugar4.graphics.icon.Icon` or \
                :class:`Gtk.Image`, optional):
                an icon for the button
            position (int, optional): the position of the button in
                the box of buttons,

        Returns:
            :class:`Gtk.Button`: the button added to the alert

        """
        button = Gtk.Button()
        self._buttons[response_id] = button
        if icon is not None:
            button.set_child(icon)
        button.set_label(label)
        self._buttons_box.append(button)
        button.connect("clicked", self.__button_clicked_cb, response_id)
        return button

    def remove_button(self, response_id):
        """
        Remove a button from the alert.

        The button is selected for removal using the response
        identifier that was passed to :func:`add_button`.

        Args:
            response_id (int): the response identifier

        Returns:
            None

        """
        if response_id in self._buttons:
            self._buttons_box.remove(self._buttons[response_id])
            del self._buttons[response_id]

    def _response(self, response_id):
        """
        Emitting response when we have a result

        A result can be that a user has clicked a button or
        a timeout has occurred, the id identifies the button
        that has been clicked and -1 for a timeout
        """
        self.emit("response", response_id)

    def __button_clicked_cb(self, button, response_id):
        self._response(response_id)


class ConfirmationAlert(Alert):
    """
    An alert with two buttons; Ok and Cancel.

    When a button is clicked, the :class:`ConfirmationAlert` will emit
    a `response` signal with a response identifier.  For the Ok
    button, the response identifier will be
    :class:`Gtk.ResponseType.OK`.  For the Cancel button,
    :class:`Gtk.ResponseType.CANCEL`.

    Args:
        **kwargs: parameters for :class:`~sugar4.graphics.alert.Alert`
    """

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        icon = Icon(icon_name="dialog-cancel")
        self.add_button(Gtk.ResponseType.CANCEL, _("Cancel"), icon)

        icon = Icon(icon_name="dialog-ok")
        self.add_button(Gtk.ResponseType.OK, _("Ok"), icon)


class ErrorAlert(Alert):
    """
    An alert with one button; Ok.

    When the button is clicked, the :class:`ErrorAlert` will
    emit a `response` signal with a response identifier
    :class:`Gtk.ResponseType.OK`.

    Args:
        **kwargs: parameters for :class:`~sugar4.graphics.alert.Alert`
    """

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        icon = Icon(icon_name="dialog-ok")
        self.add_button(Gtk.ResponseType.OK, _("Ok"), icon)


class _TimeoutIcon(Gtk.Widget):
    __gtype_name__ = "SugarTimeoutIcon"

    def __init__(self):
        super().__init__()
        self.set_size_request(48, 48)  # Standard icon size
        self._text = ""

    def do_snapshot(self, snapshot):
        """Render the loading indicator using snapshot-based drawing."""
        width = self.get_width()
        height = self.get_height()

        # Create a cairo context from snapshot
        rect = Graphene.Rect()
        rect.init(0, 0, width, height)
        cr = snapshot.append_cairo(rect)

        # Draw circle background
        x = width * 0.5
        y = height * 0.5
        radius = min(width, height) / 2 - 2
        cr.arc(x, y, radius, 0, 2 * math.pi)

        # Use theme colors
        style_context = self.get_style_context()
        color = style_context.get_color()
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.stroke()

        # Draw text
        if self._text:
            layout = self.create_pango_layout(self._text)
            layout.set_markup(f"<b>{GLib.markup_escape_text(str(self._text))}</b>")
            text_width, text_height = layout.get_pixel_size()
            cr.move_to(x - text_width / 2, y - text_height / 2)
            cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            layout.show_in_cairo_context(cr)

    def set_text(self, text):
        self._text = str(text)
        self.queue_draw()


class _TimeoutAlert(Alert):
    def __init__(self, timeout=5, label=_("Ok"), **kwargs):
        Alert.__init__(self, **kwargs)

        self._timeout = timeout

        self._timeout_text = _TimeoutIcon()
        self._timeout_text.set_text(self._timeout)
        self.add_button(Gtk.ResponseType.OK, label, self._timeout_text)

        self._timeout_sid = GLib.timeout_add(1000, self.__timeout_cb)

    def __timeout_cb(self):
        self._timeout -= 1
        self._timeout_text.set_text(self._timeout)
        if self._timeout == 0:
            Alert._response(self, -1)
            return False
        return True

    def _response(self, *args):
        if hasattr(self, "_timeout_sid"):
            GLib.source_remove(self._timeout_sid)
        Alert._response(self, *args)


class TimeoutAlert(_TimeoutAlert):
    """
    A timed alert with two buttons; Continue and Cancel.  The Continue
    button contains a countdown of seconds remaining.

    When a button is clicked, the :class:`TimeoutAlert` will emit
    a `response` signal with a response identifier.  For the Continue
    button, the response identifier will be
    :class:`Gtk.ResponseType.OK`.  For the Cancel button,
    :class:`Gtk.ResponseType.CANCEL`.

    If the countdown reaches zero before a button is clicked, the
    :class:`TimeoutAlert` will emit a `response` signal with a
    response identifier of -1.

    Args:
        timeout (int, optional): time in seconds, default 5
        **kwargs: parameters for :class:`~sugar4.graphics.alert.Alert`
    """

    def __init__(self, timeout=5, **kwargs):
        _TimeoutAlert.__init__(self, timeout, _("Continue"), **kwargs)

        icon = Icon(icon_name="dialog-cancel")
        self.add_button(Gtk.ResponseType.CANCEL, _("Cancel"), icon)


class NotifyAlert(_TimeoutAlert):
    """
    A timed alert with one button; Ok.  The button contains a
    countdown of seconds remaining.

    When the button is clicked, the :class:`NotifyAlert` will
    emit a `response` signal with a response identifier
    :class:`Gtk.ResponseType.OK`.

    If the countdown reaches zero before the button is clicked, the
    :class:`NotifyAlert` will emit a `response` signal with a
    response identifier of -1.

    Args:
        timeout (int, optional): time in seconds, default 5
        **kwargs: parameters for :class:`~sugar4.graphics.alert.Alert`
    """

    def __init__(self, timeout=5, **kwargs):
        _TimeoutAlert.__init__(self, timeout, _("Ok"), **kwargs)
