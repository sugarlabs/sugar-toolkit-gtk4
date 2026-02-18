# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2025 MostlyK
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

"""
STABLE.
"""

import logging
import cairo
import io

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import dbus

from sugar4.datastore import datastore
from sugar4.activity.activity import PREVIEW_SIZE


J_DBUS_SERVICE = "org.laptop.Journal"
J_DBUS_INTERFACE = "org.laptop.Journal"
J_DBUS_PATH = "/org/laptop/Journal"

FILTER_TYPE_MIME_BY_ACTIVITY = "mime_by_activity"
FILTER_TYPE_GENERIC_MIME = "generic_mime"
FILTER_TYPE_ACTIVITY = "activity"


def get_preview_pixbuf(preview_data, width=-1, height=-1):
    """
    Retrieve a pixbuf with the content of the preview field

    Args:
        preview_data (bytes): preview data from the metadata dictionary. Can't
            be None. Returned from the
            sugar4.datastore.datastore.DSObject.get_metadata() method.

    Keyword Args:
        width (int): the pixbuf width, if is not set,
        the default width will be used
        height (int): the pixbuf height, if is not set,
        the default height will be used

    Returns:
        GdkPixbuf.Pixbuf: the generated Pixbuf
        None: if it could not be created

    Example:
        pixbuf = get_preview_pixbuf(metadata.get('preview', ''))
        has_preview = pixbuf is not None

        if has_preview:
            im = Gtk.Image()
            im.set_from_pixbuf(pixbuf)
            box.append(im)
            im.show()
    """
    if width == -1:
        width = PREVIEW_SIZE[0]

    if height == -1:
        height = PREVIEW_SIZE[1]

    pixbuf = None

    if len(preview_data) > 4:
        try:
            # Handle both base64 encoded and direct PNG data
            if isinstance(preview_data, str):
                import base64

                preview_data = base64.b64decode(preview_data)
            elif isinstance(preview_data, bytes):
                # Check if it's base64 encoded
                if preview_data[1:4] != b"PNG":
                    import base64

                    preview_data = base64.b64decode(preview_data)

            # Create pixbuf from PNG data
            png_file = io.BytesIO(preview_data)

            # Load image and scale to dimensions
            surface = cairo.ImageSurface.create_from_png(png_file)
            png_width = surface.get_width()
            png_height = surface.get_height()

            # Calculate scaling to fit within target dimensions
            scale_w = width / png_width
            scale_h = height / png_height
            scale = min(scale_w, scale_h)

            # Create scaled surface
            scaled_width = int(png_width * scale)
            scaled_height = int(png_height * scale)

            preview_surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, scaled_width, scaled_height
            )
            cr = cairo.Context(preview_surface)
            cr.scale(scale, scale)
            cr.set_source_surface(surface)
            cr.paint()

            # Convert to pixbuf
            pixbuf = Gdk.pixbuf_get_from_surface(
                preview_surface, 0, 0, scaled_width, scaled_height
            )
        except Exception:
            logging.exception("Error while loading the preview")

    return pixbuf


class ObjectChooser(object):
    """
    UI interface for object choosers.

    Object choosers can be used by activities to allow the
    user to select objects from the file system or from
    some other similar source.

    Keyword Args:
        parent (:class:`Gtk.Widget`): the widget calling ObjectChooser

        what_filter (str): an activity bundle_id or a generic mime type as
            defined in :mod:`sugar4.mime` used to determine which objects
            will be presented in the object chooser

        filter_type (str): should be one of [None, FILTER_TYPE_GENERIC_MIME,
            FILTER_TYPE_ACTIVITY, FILTER_TYPE_MIME_BY_ACTIVITY]

            If filter_type is None, the default behavior of the
            what_filter is applied (for backward compatibility),
            this option is DEPRECATED.

            If filter_type is FILTER_TYPE_GENERIC_MIME, the
            what_filter should be a generic mime type defined in
            mime.py; the object chooser will filter based in the
            'mime_type' metadata field.

            If filter_type is FILTER_TYPE_ACTIVITY, the what_filter
            should by an activity bundle_id; the object chooser
            will filter based in the 'activity' metadata field.

            If filter_type is FILTER_TYPE_MIME_BY_ACTIVITY, the
            what_filter should be an activity bundle_id; the object
            chooser will filter based on the 'mime_type' metadata
            field and the mime types defined by the activity in the
            activity.info file.

        show_preview (bool): if True will show the preview image associated with
            the object in the Journal. This option is only available if
            filter_type is selected.

    Examples:
        chooser = ObjectChooser(self._activity, what_filter='Image')

        chooser = ObjectChooser(parent=self,
                                what_filter=self.get_bundle_id(),
                                filter_type=FILTER_TYPE_ACTIVITY)
    """

    def __init__(
        self, parent=None, what_filter=None, filter_type=None, show_preview=False
    ):
        if parent is None:
            parent_xid = 0
        elif hasattr(parent, "get_surface"):
            # GTK4 uses surfaces instead of XID
            try:
                surface = parent.get_surface()
                if surface and hasattr(surface, "get_handle"):
                    parent_xid = surface.get_handle()
                else:
                    parent_xid = 0
            except (AttributeError, TypeError):
                parent_xid = 0
        elif hasattr(parent, "get_window") and hasattr(parent.get_window(), "get_xid"):
            # Fallback for GTK3 compatibility
            parent_xid = parent.get_window().get_xid()
        else:
            parent_xid = parent if isinstance(parent, int) else 0

        self._parent_xid = parent_xid
        self._show_preview = show_preview
        self._main_loop = None
        self._object_id = None
        self._bus = None
        self._chooser_id = None
        self._response_code = Gtk.ResponseType.NONE
        self._what_filter = what_filter

        if filter_type is not None:
            # verify is one of the available types
            if filter_type not in [
                FILTER_TYPE_MIME_BY_ACTIVITY,
                FILTER_TYPE_GENERIC_MIME,
                FILTER_TYPE_ACTIVITY,
            ]:
                raise ValueError("filter_type not implemented")

        self._filter_type = filter_type

    def run(self):
        """
        Runs the object chooser and displays it.

        Returns:
            Gtk.ResponseType constant, the response received
            from displaying the object chooser.
        """
        self._object_id = None

        self._main_loop = GObject.MainLoop()

        # Use DBusGMainLoop for dbus.SessionBus mainloop integration (GTK4 compatible)
        from dbus.mainloop.glib import DBusGMainLoop

        dbus_loop = DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SessionBus(mainloop=dbus_loop)
        self._bus.add_signal_receiver(
            self.__name_owner_changed_cb,
            signal_name="NameOwnerChanged",
            dbus_interface="org.freedesktop.DBus",
            arg0=J_DBUS_SERVICE,
        )

        obj = self._bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
        journal = dbus.Interface(obj, J_DBUS_INTERFACE)
        journal.connect_to_signal("ObjectChooserResponse", self.__chooser_response_cb)
        journal.connect_to_signal("ObjectChooserCancelled", self.__chooser_cancelled_cb)

        if self._what_filter is None:
            what_filter = ""
        else:
            what_filter = self._what_filter

        try:
            if self._filter_type is None:
                self._chooser_id = journal.ChooseObject(self._parent_xid, what_filter)
            else:
                self._chooser_id = journal.ChooseObjectWithFilter(
                    self._parent_xid, what_filter, self._filter_type, self._show_preview
                )

            self._main_loop.run()
        except Exception as e:
            logging.error("Error running object chooser: %s", e)
            self._response_code = Gtk.ResponseType.CANCEL
        finally:
            self._main_loop = None

        return self._response_code

    def get_parent_xid(self):
        """Get the parent window XID."""
        return self._parent_xid

    def get_what_filter(self):
        """Get the what filter string."""
        return self._what_filter

    def get_filter_type(self):
        """Get the filter type."""
        return self._filter_type

    def get_show_preview(self):
        """Get the show preview flag."""
        return self._show_preview

    def get_response_code(self):
        """Get the response code from the chooser."""
        return self._response_code

    def get_object_id(self):
        """Get the selected object ID."""
        return self._object_id

    def get_selected_object(self):
        """
        Gets the object selected using the object chooser.

        Returns:
            object: the object selected
        """
        if self._object_id is None:
            return None
        else:
            return datastore.get(self._object_id)

    def destroy(self):
        """
        Destroys and cleans up (disposes) the object chooser.
        """
        self._cleanup()

    def _cleanup(self):
        if self._main_loop is not None and self._main_loop.is_running():
            self._main_loop.quit()
            self._main_loop = None
        self._bus = None

    def __chooser_response_cb(self, chooser_id, object_id):
        if chooser_id != self._chooser_id:
            return
        logging.debug("ObjectChooser.__chooser_response_cb: %r", object_id)
        self._response_code = Gtk.ResponseType.ACCEPT
        self._object_id = object_id
        self._cleanup()

    def __chooser_cancelled_cb(self, chooser_id):
        if chooser_id != self._chooser_id:
            return
        logging.debug("ObjectChooser.__chooser_cancelled_cb: %r", chooser_id)
        self._response_code = Gtk.ResponseType.CANCEL
        self._cleanup()

    def __name_owner_changed_cb(self, name, old, new):
        logging.debug("ObjectChooser.__name_owner_changed_cb")
        # Journal service disappeared from the bus
        self._response_code = Gtk.ResponseType.CANCEL
        self._cleanup()
