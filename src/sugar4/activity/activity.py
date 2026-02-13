# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2007-2009 One Laptop Per Child
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
# Copyright (C) 2025 MostlyK
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Activity
========

A definitive reference for what a Sugar Python activity must do to
participate in the Sugar desktop.

.. note:: This API is STABLE.

The :class:`Activity` class is used to derive all Sugar Python
activities.  This is where your activity starts.

**Derive from the class**

    .. code-block:: python

        from sugar4.activity.activity import Activity

        class MyActivity(Activity):
            def __init__(self, handle):
                Activity.__init__(self, handle)

    An activity must implement a new class derived from
    :class:`Activity`.

    Name the new class `MyActivity`, where `My` is the name of your
    activity.  Use bundle metadata to tell Sugar to instantiate this
    class.  See :class:`~sugar4.bundle` for bundle metadata.

**Create a ToolbarBox**

    In your :func:`__init__` method create a
    :class:`~sugar4.graphics.toolbarbox.ToolbarBox`, with an
    :class:`~sugar4.activity.widgets.ActivityToolbarButton`, a
    :class:`~sugar4.activity.widgets.StopButton`, and then call
    :func:`~sugar4.graphics.window.Window.set_toolbar_box`.

    .. code-block:: python
        :emphasize-lines: 2-4,10-

        from sugar4.activity.activity import Activity
        from sugar4.graphics.toolbarbox import ToolbarBox
        from sugar4.activity.widgets import ActivityToolbarButton
        from sugar4.activity.widgets import StopButton

        class MyActivity(Activity):
            def __init__(self, handle):
                Activity.__init__(self, handle)

                toolbar_box = ToolbarBox()
                activity_button = ActivityToolbarButton(self)
                toolbar_box.toolbar.append(activity_button)

                separator = Gtk.Box()
                separator.set_hexpand(True)
                toolbar_box.toolbar.append(separator)

                stop_button = StopButton(self)
                toolbar_box.toolbar.append(stop_button)

                self.set_toolbar_box(toolbar_box)

**Journal methods**

    In your activity class, code
    :func:`~sugar4.activity.activity.Activity.read_file()` and
    :func:`~sugar4.activity.activity.Activity.write_file()` methods.

    Most activities create and resume journal objects.  For example,
    the Write activity saves the document as a journal object, and
    reads it from the journal object when resumed.

    :func:`~sugar4.activity.activity.Activity.read_file()` and
    :func:`~sugar4.activity.activity.Activity.write_file()` will be
    called by the toolkit to tell your activity that it must load or
    save the data the user is working on.

**Activity toolbars**

    Add any activity toolbars before the last separator in the
    :class:`~sugar4.graphics.toolbarbox.ToolbarBox`, so that the
    :class:`~sugar4.activity.widgets.StopButton` is aligned to the
    right.

    There are a number of standard Toolbars.

    You may need the :class:`~sugar4.activity.widgets.EditToolbar`.
    This has copy and paste buttons.  You may derive your own
    class from
    :class:`~sugar4.activity.widgets.EditToolbar`:

    .. code-block:: python

        from sugar4.activity.widgets import EditToolbar

        class MyEditToolbar(EditToolbar):
            ...

    See :class:`~sugar4.activity.widgets.EditToolbar` for the
    methods you should implement in your class.

    You may need some activity specific buttons and options which
    you can create as toolbars by deriving a class from
    :class:`Gtk.Box`:

    .. code-block:: python

        class MySpecialToolbar(Gtk.Box):
            ...

**Sharing**

    An activity can be shared across the network with other users.  Near
    the end of your :func:`__init__`, test if the activity is shared,
    and connect to signals to detect sharing.

    .. code-block:: python

        if self.shared_activity:
            # we are joining the activity
            self.connect('joined', self._joined_cb)
            if self.get_shared():
                # we have already joined
                self._joined_cb()
        else:
            # we are creating the activity
            self.connect('shared', self._shared_cb)

    Add methods to handle the signals.

Read through the methods of the :class:`Activity` class below, to learn
more about how to make an activity work.

Hint: A good and simple activity to learn from is the Read activity.
You may copy it and use it as a template.
"""

import gettext
import io
import json
import logging
import os
import signal
import time
from errno import EEXIST
from hashlib import sha1

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gdk, Gio, GLib, GObject, Graphene, Gtk

try:
    import cairo

    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False
    logging.warning("Cairo not available, preview generation disabled")

import dbus

from sugar4 import env, util
from sugar4.bundle.activitybundle import get_bundle_instance
from sugar4.bundle.helpers import bundle_from_dir
from sugar4.datastore import datastore
from sugar4.graphics import style
from sugar4.graphics.alert import Alert
from sugar4.graphics.icon import Icon
from sugar4.graphics.window import Window
from sugar4.profile import get_color, get_save_as


def _(msg):
    return gettext.dgettext("sugar-toolkit-gtk4", msg)


SCOPE_PRIVATE = "private"
SCOPE_INVITE_ONLY = "invite"  # shouldn't be shown in UI, it's implicit
SCOPE_NEIGHBORHOOD = "public"

J_DBUS_SERVICE = "org.laptop.Journal"
J_DBUS_PATH = "/org/laptop/Journal"
J_DBUS_INTERFACE = "org.laptop.Journal"

N_BUS_NAME = "org.freedesktop.Notifications"
N_OBJ_PATH = "/org/freedesktop/Notifications"
N_IFACE_NAME = "org.freedesktop.Notifications"

PREVIEW_SIZE = style.zoom(300), style.zoom(225)
"""
Size of a preview image for journal object metadata.
"""


class _ActivitySession(GObject.GObject):
    """
    Manages activity session lifecycle.

    This replaces the legacy X session management with modern application lifecycle handling.
    """

    __gsignals__ = {
        "quit-requested": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "quit": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._activities = []
        self._will_quit = []
        self._main_loop = None

    def register(self, activity):
        self._activities.append(activity)

    def unregister(self, activity):
        if activity in self._activities:
            self._activities.remove(activity)

        if len(self._activities) == 0:
            logging.debug("Quitting the activity process.")
            # In GTK4, we need to quit the application properly
            if self._main_loop and self._main_loop.is_running():
                self._main_loop.quit()
            else:
                # Fallback to GLib main loop
                GLib.MainLoop().quit()

    def will_quit(self, activity, will_quit):
        if will_quit:
            self._will_quit.append(activity)

            # We can quit only when all the instances agreed to
            for act in self._activities:
                if act not in self._will_quit:
                    return

            self.emit("quit")
        else:
            self._will_quit = []

    def set_main_loop(self, main_loop):
        self._main_loop = main_loop


class Activity(Window):
    """
    Initialise an Activity.

    Args:
        handle (:class:`~sugar4.activity.activityhandle.ActivityHandle`):
            instance providing the activity id and access to the presence
            service which *may* provide sharing for this application

        create_jobject (boolean):
            DEPRECATED: define if it should create a journal object if
            we are not resuming. The parameter is ignored, and always
            will be created a object in the Journal.

    **Signals:**
        * **shared** - the activity has been shared on a network in
            order that other users may join,

        * **joined** - the activity has joined with other instances of
            the activity to create a shared network activity.

        * **closing** - the activity is about to close

    Side effects:

        * sets the display DPI setting (resolution) to the Sugar
          screen resolution.

        * connects our "close-request" signal to our close handling.

        * creates a base Gtk.ApplicationWindow within this window.

        * creates activity service handling for this application.

    When your activity implements :func:`__init__`, it must call the
    :class:`Activity` class :func:`__init__` before any
    :class:`Activity` specific code.
    """

    __gtype_name__ = "SugarActivity"

    __gsignals__ = {
        "shared": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "joined": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # For internal use only, use can_close() if you want to perform extra
        # checks before actually closing
        "closing": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, handle, create_jobject=True, application=None):
        self._busy_count = 0
        self._stop_buttons = []
        self._in_main = False
        self._iconify = False
        self._active = False
        self._active_time = None
        self._spent_time = 0
        self._activity_id = handle.activity_id if handle else None
        self.shared_activity = None
        self._join_id = None
        self._updating_jobject = False
        self._closing = False
        self._quit_requested = False
        self._deleting = False
        self._max_participants = None
        self._invites_queue = []
        self._jobject = None
        self._jobject_old = None
        self._is_resumed = False
        self._read_file_called = False
        self._owns_file = False
        self._bus = None

        # Set up signal handling early
        if hasattr(GLib, "unix_signal_add"):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.close)

        # Stuff that needs to be done early
        icons_path = os.path.join(get_bundle_path(), "icons")
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(icons_path)

        sugar_theme = "sugar-72"
        if "SUGAR_SCALING" in os.environ:
            if os.environ["SUGAR_SCALING"] == "100":
                sugar_theme = "sugar-100"

        # styling and theming
        display = Gdk.Display.get_default()
        if display:
            settings = Gtk.Settings.get_for_display(display)
            settings.set_property("gtk-theme-name", sugar_theme)
            settings.set_property("gtk-icon-theme-name", "sugar")
            settings.set_property(
                "gtk-font-name", "%s %f" % (style.FONT_FACE, style.FONT_SIZE)
            )

        # Initialize parent Window
        Window.__init__(self, application=application)

        if "SUGAR_ACTIVITY_ROOT" in os.environ:
            # If this activity runs inside Sugar, we want it to take all the
            # screen. In GTK4, we use different approach for fullscreen
            self.connect("notify::default-width", self.__window_size_changed_cb)
            self.connect("notify::default-height", self.__window_size_changed_cb)
            self._adapt_window_to_screen()

        # Process titles will only show 15 characters
        # but they get truncated anyway so if more characters
        # are supported in the future we will get a better view
        # of the processes
        if handle:
            proc_title = "%s <%s>" % (get_bundle_name(), handle.activity_id)
            util.set_proc_title(proc_title)

        self.connect("close-request", self.__close_request_cb)

        self._session = _get_session()
        self._session.register(self)
        self._session.connect("quit-requested", self.__session_quit_requested_cb)
        self._session.connect("quit", self.__session_quit_cb)

        # GTK4: Accelerator groups are handled differently
        # We'll use application accelerators instead
        self.sugar_accel_group = None
        if application:
            self.sugar_accel_group = application

        share_scope = SCOPE_PRIVATE

        if handle and handle.object_id:
            self._is_resumed = True
            try:
                self._jobject = datastore.get(handle.object_id)

                if "share-scope" in self._jobject.metadata:
                    share_scope = self._jobject.metadata["share-scope"]

                if "launch-times" in self._jobject.metadata:
                    self._jobject.metadata["launch-times"] += ", %d" % int(time.time())
                else:
                    self._jobject.metadata["launch-times"] = str(int(time.time()))

                if "spent-times" in self._jobject.metadata:
                    self._jobject.metadata["spent-times"] += ", 0"
                else:
                    self._jobject.metadata["spent-times"] = "0"

            except Exception as e:
                logging.warning(
                    "Could not load journal object %s: %s", handle.object_id, e
                )
                logging.info("Creating new journal object in standalone mode")
                self._is_resumed = False
                self._jobject = self._initialize_journal_object()
        else:
            self._is_resumed = False
            self._jobject = self._initialize_journal_object()
            if hasattr(self._jobject, "metadata") and self._jobject.metadata:
                self.set_title(self._jobject.metadata["title"])

        self._original_title = self._jobject.metadata["title"]

        # Sharing setup
        # TODO
        if handle and handle.invited:
            # For GTK4/Flatpak, we'll implement sharing differently
            logging.warning("Activity sharing not yet implemented in GTK4 port")
            self._set_up_sharing(None, share_scope)
        else:
            # No presence service in GTK4 port yet
            self._set_up_sharing(None, share_scope)

        if self.shared_activity is not None:
            self._jobject.metadata["title"] = self.shared_activity.props.name
            self._jobject.metadata["icon-color"] = self.shared_activity.props.color
        else:
            self._jobject.metadata.connect("updated", self.__jobject_updated_cb)
        self.set_title(self._jobject.metadata["title"])

        bundle = get_bundle_instance(get_bundle_path())
        if bundle and bundle.get_icon():
            self.set_icon_name(bundle.get_icon())

        if self._is_resumed and get_save_as():
            # preserve original and use a copy for editing
            self._jobject_old = self._jobject
            self._jobject = datastore.copy(self._jobject, "/")

        # Set the original title again after any operations
        self._original_title = self._jobject.metadata["title"]

    def add_stop_button(self, button):
        """
        Register an extra stop button.  Normally not required.  Use only
        when an activity has more than the default stop button.

        Args:
            button (:class:`Gtk.Button`): a stop button
        """
        self._stop_buttons.append(button)

    def iconify(self):
        """Iconify the activity window."""
        if not self._in_main:
            self._iconify = True  # i.e. do after Window.show()
        else:
            self.minimize()

    def show(self):
        """
        Show the activity window.

        In GTK4, ApplicationWindow uses present() instead of show().
        This method provides compatibility with the activityinstance API.
        """
        self.present()

    def run_main_loop(self):
        """
        Run the main loop for the activity.

        Note: In modern applications, this is typically handled by the application framework,
        but we keep this for compatibility with legacy code.
        """
        if self._iconify:
            self.minimize()
        self._in_main = True

        # Use GLib main loop instead of deprecated Gtk.main()
        main_loop = GLib.MainLoop()
        self._session.set_main_loop(main_loop)
        main_loop.run()

    def _initialize_journal_object(self):
        """Initialize a new journal object for the activity."""
        title = _("%s Activity") % get_bundle_name()
        icon_color = get_color().to_string()

        try:
            jobject = datastore.create()
            jobject.metadata["title"] = title
            jobject.metadata["title_set_by_user"] = "0"
            jobject.metadata["activity"] = self.get_bundle_id()
            jobject.metadata["activity_id"] = self.get_id()
            jobject.metadata["keep"] = "0"
            jobject.metadata["preview"] = ""
            jobject.metadata["share-scope"] = SCOPE_PRIVATE
            jobject.metadata["icon-color"] = icon_color
            jobject.metadata["launch-times"] = str(int(time.time()))
            jobject.metadata["spent-times"] = "0"
            jobject.file_path = ""

            # Try to write to datastore
            # NOTE: Bug on GTK3 Toolkit:
            # FIXME: We should be able to get an ID synchronously from the DS,
            # then call async the actual create.
            # http://bugs.sugarlabs.org/ticket/2169

            datastore.write(jobject)
            return jobject

        except Exception as e:
            # This is to test Activity seperately in env without sugar4.
            logging.warning(
                "Datastore not available (not running in Sugar environment): %s", e
            )
            logging.info(
                "Activity will run in standalone mode without journal integration"
            )

            # Create a minimal mock journal object for standalone operation
            from sugar4.datastore.datastore import DSMetadata

            class MockJobject:
                """Mock journal object that doesn't require datastore"""

                def __init__(self):
                    self.object_id = None  # No real journal object
                    self.file_path = ""
                    self._metadata = DSMetadata()
                    self._destroyed = False

                @property
                def metadata(self):
                    return self._metadata

                def destroy(self):
                    self._destroyed = True

            jobject = MockJobject()
            jobject.metadata["title"] = title
            jobject.metadata["title_set_by_user"] = "0"
            jobject.metadata["activity"] = self.get_bundle_id()
            jobject.metadata["activity_id"] = self.get_id()
            jobject.metadata["keep"] = "0"
            jobject.metadata["preview"] = ""
            jobject.metadata["share-scope"] = SCOPE_PRIVATE
            jobject.metadata["icon-color"] = icon_color
            jobject.metadata["launch-times"] = str(int(time.time()))
            jobject.metadata["spent-times"] = "0"

            return jobject

    def __jobject_updated_cb(self, jobject):
        """Handle journal object updates."""
        if self.get_title() == jobject["title"]:
            return
        self.set_title(jobject["title"])

    def _set_up_sharing(self, mesh_instance, share_scope):
        """
        Set up activity sharing.

        Note: Simplified for GTK4 port - full sharing implementation
        will use modern collaboration APIs.
        """
        # handle activity share/join
        logging.debug(
            "*** Act %s, mesh instance %r, scope %s"
            % (self._activity_id, mesh_instance, share_scope)
        )

        # For now, sharing is not implemented in GTK4 port
        if mesh_instance is not None:
            logging.warning("Activity sharing not yet implemented in GTK4 port")
        elif share_scope != SCOPE_PRIVATE:
            logging.warning("Activity sharing not yet implemented in GTK4 port")

    def get_active(self):
        """
        Get whether the activity is active.  An activity may be made
        inactive by the shell as a result of another activity being
        active.  An active activity accumulates usage metrics.

        Returns:
            boolean: if the activity is active.
        """
        return self._active

    def _update_spent_time(self):
        """Update the time spent in the activity."""
        if self._active is True and self._active_time is None:
            self._active_time = time.time()
        elif self._active is False and self._active_time is not None:
            self._spent_time += time.time() - self._active_time
            self._active_time = None
        elif self._active is True and self._active_time is not None:
            current = time.time()
            self._spent_time += current - self._active_time
            self._active_time = current

    def set_active(self, active):
        """
        Set whether the activity is active.  An activity may declare
        itself active or inactive, as can the shell.  An active activity
        accumulates usage metrics.

        Args:
            active (boolean): if the activity is active.
        """
        if self._active != active:
            self._active = active
            self._update_spent_time()
            if not self._active and self._jobject:
                self.save()

    active = GObject.Property(
        type=bool, default=False, getter=get_active, setter=set_active
    )
    """
        Whether an activity is active.
    """

    def get_max_participants(self):
        """
        Get the maximum number of users that can share a instance
        of this activity.  Should be configured in the activity.info
        file.  When not configured, it will be zero.

        Returns:
            int: the maximum number of participants

        See also
        :func:`~sugar4.bundle.activitybundle.ActivityBundle.get_max_participants`
        in :class:`~sugar4.bundle.activitybundle.ActivityBundle`.
        """
        # If max_participants has not been set in the activity, get it
        # from the bundle.
        if self._max_participants is None:
            bundle = get_bundle_instance(get_bundle_path())
            self._max_participants = bundle.get_max_participants()
        return self._max_participants

    def set_max_participants(self, participants):
        """
        Set the maximum number of users that can share a instance of
        this activity.  An activity may use this method instead of or
        as well as configuring the activity.info file.  When both are
        used, this method takes precedence over the activity.info
        file.

        Args:
            participants (int): the maximum number of participants
        """
        self._max_participants = participants

    max_participants = GObject.Property(
        type=int, default=0, getter=get_max_participants, setter=set_max_participants
    )

    def get_id(self):
        """
        Get the activity id, a likely-unique identifier for the
        instance of an activity, randomly assigned when a new instance
        is started, or read from the journal object metadata when a
        saved instance is resumed.

        Returns:
            str: the activity id

        See also
        :meth:`~sugar4.activity.activityfactory.create_activity_id`
        and :meth:`~sugar4.util.unique_id`.
        """
        return self._activity_id

    def get_bundle_id(self):
        """
        Returns:
            str: the bundle_id from the activity.info file
        """
        return os.environ["SUGAR_BUNDLE_ID"]

    def get_canvas(self):
        """
        Get the :attr:`canvas`.

        Returns:
            :class:`Gtk.Widget`: the widget used as canvas
        """
        return Window.get_canvas(self)

    def set_canvas(self, canvas):
        """
        Set the :attr:`canvas`.

        Args:
            canvas (:class:`Gtk.Widget`): the widget used as canvas
        """
        Window.set_canvas(self, canvas)
        if not self._read_file_called and canvas:
            canvas.connect("map", self.__canvas_map_cb)

    canvas = property(get_canvas, set_canvas)
    """
    The :class:`Gtk.Widget` used as canvas, or work area of your
    activity.  A common canvas is :class:`Gtk.ScrolledWindow`.
    """

    def __window_size_changed_cb(self, *args):
        """Handle window size changes."""
        self._adapt_window_to_screen()

    def _adapt_window_to_screen(self):
        """
        Adapt window to screen size.

        Uses modern display management APIs to determine optimal sizing.
        """
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_monitors().get_item(0)
            if monitor:
                geometry = monitor.get_geometry()
                self.set_default_size(geometry.width, geometry.height)

    def __session_quit_requested_cb(self, session):
        """Handle session quit request."""
        self._quit_requested = True

        if self._prepare_close() and not self._updating_jobject:
            session.will_quit(self, True)

    def __session_quit_cb(self, client):
        """Handle session quit."""
        self._complete_close()

    def __canvas_map_cb(self, canvas):
        """Handle canvas map signal."""
        logging.debug("Activity.__canvas_map_cb")
        if self._jobject and self._jobject.file_path and not self._read_file_called:
            self.read_file(self._jobject.file_path)
            self._read_file_called = True
        canvas.disconnect_by_func(self.__canvas_map_cb)

    def __jobject_create_cb(self):
        """Handle journal object creation."""
        pass

    def __jobject_error_cb(self, err):
        """Handle journal object errors."""
        logging.debug("Error creating activity datastore object: %s" % err)

    def get_activity_root(self):
        """
        Deprecated. This part of the API has been moved
        out of this class to the module itself
        """
        return get_activity_root()

    def read_file(self, file_path):
        """
        Subclasses implement this method if they support resuming objects from
        the journal. 'file_path' is the file to read from.

        You should immediately open the file from the file_path,
        because the file_name will be deleted immediately after
        returning from :meth:`read_file`.

        Once the file has been opened, you do not have to read it immediately:
        After you have opened it, the file will only be really gone when you
        close it.

        Although not required, this is also a good time to read all meta-data:
        the file itself cannot be changed externally, but the title,
        description and other metadata['tags'] may change. So if it is
        important for you to notice changes, this is the time to record the
        originals.

        Args:
            file_path (str): the file path to read
        """
        raise NotImplementedError

    def write_file(self, file_path):
        """
        Subclasses implement this method if they support saving data to objects
        in the journal. 'file_path' is the file to write to.

        If the user did make changes, you should create the file_path and save
        all document data to it.

        Additionally, you should also write any metadata needed to resume your
        activity. For example, the Read activity saves the current page and
        zoom level, so it can display the page.

        Note: Currently, the file_path *WILL* be different from the
        one you received in :meth:`read_file`. Even if you kept the
        file_path from :meth:`read_file` open until now, you must
        still write the entire file to this file_path.

        Args:
            file_path (str): complete path of the file to write
        """
        raise NotImplementedError

    def notify_user(self, summary, body):
        """
        Display a notification with the given summary and body.
        The notification will go under the activities icon in the frame.

        Note: In GTK4/Flatpak, this uses the portal notification system.
        """
        try:
            # Use GApplication notification system in GTK4
            if self.get_application():
                notification = Gio.Notification.new(summary)
                notification.set_body(body)

                # Get bundle for icon
                bundle = get_bundle_instance(get_bundle_path())
                if bundle and bundle.get_icon():
                    icon = Gio.ThemedIcon.new(bundle.get_icon())
                    notification.set_icon(icon)

                self.get_application().send_notification(self.get_id(), notification)
            else:
                logging.warning("Cannot send notification: no application instance")
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")

    def __save_cb(self):
        """Handle successful save."""
        logging.debug("Activity.__save_cb")
        self._updating_jobject = False
        if self._quit_requested:
            self._session.will_quit(self, True)
        elif self._closing:
            self._complete_close()

    def __save_error_cb(self, err):
        """Handle save error."""
        logging.debug("Activity.__save_error_cb")
        self._updating_jobject = False
        if self._quit_requested:
            self._session.will_quit(self, False)
        if self._closing:
            self._show_keep_failed_dialog()
            self._closing = False
        raise RuntimeError("Error saving activity object to datastore: %s" % err)

    def _cleanup_jobject(self):
        """Clean up journal object."""
        if self._jobject:
            if self._owns_file and os.path.isfile(self._jobject.file_path):
                logging.debug("_cleanup_jobject: removing %r" % self._jobject.file_path)
                os.remove(self._jobject.file_path)
            self._owns_file = False
            self._jobject.destroy()
            self._jobject = None

    def get_preview(self):
        """
        Get a preview image from the :attr:`canvas`, for use as
        metadata for the journal object.  This should be what the user
        is seeing at the time.

        Returns:
            bytes: image data in PNG format

        Activities may override this method, and return a string with
        image data in PNG format with a width and height of
        :attr:`~sugar4.activity.activity.PREVIEW_SIZE` pixels.

        The method captures the canvas widget using GTK4's
        WidgetPaintable API, then scales the result to the preview
        size.
        """
        if not HAS_CAIRO:
            logging.warning("Cairo not available, cannot generate preview")
            return None

        if self.canvas is None:
            return None

        try:
            canvas_width = self.canvas.get_width()
            canvas_height = self.canvas.get_height()
            if canvas_width <= 0 or canvas_height <= 0:
                return None

            native = self.canvas.get_native()
            if native is None:
                return None

            renderer = native.get_renderer()
            if renderer is None:
                return None

            # GTK4: WidgetPaintable captures any widget's current
            # rendered state, including all children.
            paintable = Gtk.WidgetPaintable.new(self.canvas)
            snapshot = Gtk.Snapshot()
            paintable.snapshot(snapshot, canvas_width, canvas_height)
            node = snapshot.to_node()
            if node is None:
                return None

            viewport = Graphene.Rect()
            viewport.init(0, 0, canvas_width, canvas_height)
            texture = renderer.render_texture(node, viewport)

            # Convert the full-resolution texture to a Cairo surface
            # via PNG so we can scale it down to PREVIEW_SIZE.
            png_data = texture.save_to_png_bytes()
            screenshot_surface = cairo.ImageSurface.create_from_png(
                io.BytesIO(png_data.get_data())
            )

            preview_width, preview_height = PREVIEW_SIZE
            preview_surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, preview_width, preview_height
            )
            preview_cr = cairo.Context(preview_surface)

            scale_w = preview_width * 1.0 / canvas_width
            scale_h = preview_height * 1.0 / canvas_height
            scale = min(scale_w, scale_h)

            translate_x = int((preview_width - (canvas_width * scale)) / 2)
            translate_y = int((preview_height - (canvas_height * scale)) / 2)

            preview_cr.translate(translate_x, translate_y)
            preview_cr.scale(scale, scale)

            preview_cr.set_source_rgba(1, 1, 1, 1)
            preview_cr.set_operator(cairo.OPERATOR_SOURCE)
            preview_cr.paint()
            preview_cr.set_source_surface(screenshot_surface)
            preview_cr.paint()

            preview_str = io.BytesIO()
            preview_surface.write_to_png(preview_str)
            return preview_str.getvalue()

        except Exception as e:
            logging.error(f"Error generating preview: {e}")
            return None

    def _get_buddies(self):
        """Get buddies information for sharing."""
        if self.shared_activity is not None:
            buddies = {}
            for buddy in self.shared_activity.get_joined_buddies():
                if not buddy.props.owner:
                    buddy_id = sha1((buddy.props.key).encode("utf-8")).hexdigest()
                    buddies[buddy_id] = [buddy.props.nick, buddy.props.color]
            return buddies
        else:
            return {}

    def save(self):
        """
        Save to the journal.

        This may be called by the :meth:`close` method.

        Activities should not override this method. This method is part of the
        public API of an activity, and should behave in standard ways. Use your
        own implementation of write_file() to save your activity specific data.
        """
        if self._jobject is None:
            logging.debug("Cannot save, no journal object.")
            return

        logging.debug("Activity.save: %r" % getattr(self._jobject, "object_id", "mock"))

        if self._updating_jobject:
            logging.info("Activity.save: still processing a previous request.")
            return

        buddies_dict = self._get_buddies()
        if buddies_dict:
            self.metadata["buddies_id"] = json.dumps(list(buddies_dict.keys()))
            self.metadata["buddies"] = json.dumps(self._get_buddies())

        # update spent time before saving
        self._update_spent_time()

        def set_last_value(values_list, new_value):
            if ", " not in values_list:
                return "%d" % new_value
            else:
                partial_list = ", ".join(values_list.split(", ")[:-1])
                return partial_list + ", %d" % new_value

        self.metadata["spent-times"] = set_last_value(
            self.metadata["spent-times"], self._spent_time
        )

        preview = self.get_preview()
        if preview is not None:
            # In GTK4, we handle binary data differently
            self.metadata["preview"] = preview

        if not self.metadata.get("activity_id", ""):
            self.metadata["activity_id"] = self.get_id()

        file_path = os.path.join(get_activity_root(), "instance", "%i" % time.time())
        try:
            self.write_file(file_path)
        except NotImplementedError:
            logging.debug("Activity.write_file is not implemented.")
        else:
            if os.path.exists(file_path):
                self._owns_file = True
                self._jobject.file_path = file_path

        # Check if we have a real datastore object or a mock
        if hasattr(self._jobject, "object_id") and self._jobject.object_id is not None:
            # Real journal object - try to write to datastore
            try:
                if self._jobject.object_id is None:
                    datastore.write(self._jobject, transfer_ownership=True)
                else:
                    self._updating_jobject = True
                    datastore.write(
                        self._jobject,
                        transfer_ownership=True,
                        reply_handler=self.__save_cb,
                        error_handler=self.__save_error_cb,
                    )
            except Exception as e:
                logging.warning("Failed to save to datastore: %s", e)
                logging.info(
                    "Running in standalone mode - file saved to: %s", file_path
                )
                self._updating_jobject = False
        else:
            # Mock journal object - just log that we saved the file
            logging.info("Standalone mode: Activity data saved to %s", file_path)

    def copy(self):
        """
        Make a copy of the journal object.

        Activities may use this to 'Keep in Journal' the current state
        of the activity.  A new journal object will be created for the
        running activity.

        Activities should not override this method. Instead, like
        :meth:`save` do any copy work that needs to be done in
        :meth:`write_file`.
        """
        logging.debug("Activity.copy: %r" % self._jobject.object_id)
        self.save()
        self._jobject.object_id = None

    def __privacy_changed_cb(self, shared_activity, param_spec):
        """Handle privacy changes in shared activity."""
        logging.debug("__privacy_changed_cb %r" % shared_activity.props.private)
        if shared_activity.props.private:
            self._jobject.metadata["share-scope"] = SCOPE_INVITE_ONLY
        else:
            self._jobject.metadata["share-scope"] = SCOPE_NEIGHBORHOOD

    def __joined_cb(self, activity, success, err):
        """Callback when join has finished"""
        logging.debug("Activity.__joined_cb %r" % success)
        self.shared_activity.disconnect(self._join_id)
        self._join_id = None
        if not success:
            logging.debug("Failed to join activity: %s" % err)
            return

        # Power management for GTK4
        # power_manager = power.get_power_manager()
        # if power_manager.suspend_breaks_collaboration():
        #     power_manager.inhibit_suspend()

        self.present()
        self.emit("joined")
        self.__privacy_changed_cb(self.shared_activity, None)

    def get_shared_activity(self):
        """
        Get the shared activity of type
        :class:`sugar4.presence.activity.Activity`, or None if the
        activity is not shared, or is shared and not yet joined.

        Returns:
            :class:`sugar4.presence.activity.Activity`: instance of
                the shared activity or None
        """
        return self.shared_activity

    def get_shared(self):
        """
        Get whether the activity is shared.

        Returns:
            bool: the activity is shared.
        """
        if not self.shared_activity:
            return False
        return self.shared_activity.props.joined

    def __share_cb(self, ps, success, activity, err):
        """Handle sharing callback."""
        if not success:
            logging.debug("Share of activity %s failed: %s." % (self._activity_id, err))
            return

        logging.debug(
            "Share of activity %s successful, PS activity is %r."
            % (self._activity_id, activity)
        )

        activity.props.name = self._jobject.metadata["title"]

        # Power management for GTK4
        # power_manager = power.get_power_manager()
        # if power_manager.suspend_breaks_collaboration():
        #     power_manager.inhibit_suspend()

        self.shared_activity = activity
        self.shared_activity.connect("notify::private", self.__privacy_changed_cb)
        self.emit("shared")
        self.__privacy_changed_cb(self.shared_activity, None)

        self._send_invites()

    def _invite_response_cb(self, error):
        """Handle invite response."""
        if error:
            logging.error("Invite failed: %s", error)

    def _send_invites(self):
        """Send pending invites."""
        while self._invites_queue:
            account_path, contact_id = self._invites_queue.pop()
            # Presence service handling simplified for GTK4
            logging.warning("Invite functionality not yet implemented in GTK4 port")

    def invite(self, account_path, contact_id):
        """
        Invite a buddy to join this activity.

        Args:
            account_path: account path
            contact_id: contact ID

        **Side Effects:**
            Calls :meth:`share` to privately share the activity if it wasn't
            shared before.
        """
        self._invites_queue.append((account_path, contact_id))

        if self.shared_activity is None or not self.shared_activity.props.joined:
            self.share(True)
        else:
            self._send_invites()

    def share(self, private=False):
        """
        Request that the activity be shared on the network.

        Args:
            private (bool): True to share by invitation only,
                False to advertise as shared to everyone.

        Once the activity is shared, its privacy can be changed by
        setting the :attr:`private` property of the
        :attr:`sugar4.presence.activity.Activity` class.
        """
        raise NotImplementedError(
            "Activity sharing not yet implemented in GTK4 port. "
            "Use Flatpak and modern collaboration APIs for sharing."
        )

    def _show_keep_failed_dialog(self):
        """
        A keep error means the activity write_file method raised an
        exception before writing the file, or the datastore cannot be
        written to.
        """
        alert = Alert()
        alert.props.title = _("Keep error")
        alert.props.msg = _("Keep error: all changes will be lost")

        cancel_icon = Icon(icon_name="dialog-cancel")
        alert.add_button(Gtk.ResponseType.CANCEL, _("Don't stop"), cancel_icon)

        stop_icon = Icon(icon_name="dialog-ok")
        alert.add_button(Gtk.ResponseType.OK, _("Stop anyway"), stop_icon)

        self.add_alert(alert)
        alert.connect("response", self.__keep_failed_dialog_response_cb)

        self.present()

    def __keep_failed_dialog_response_cb(self, alert, response_id):
        """Handle keep failed dialog response."""
        self.remove_alert(alert)
        if response_id == Gtk.ResponseType.OK:
            self.close(skip_save=True)
            if self._quit_requested:
                self._session.will_quit(self, True)
        elif self._quit_requested:
            self._session.will_quit(self, False)

    def can_close(self):
        """
        Return whether :func:`close` is permitted.

        An activity may override this function to code extra checks
        before closing.

        Returns:
            bool: whether :func:`close` is permitted by activity,
            default True.
        """
        return True

    def _show_stop_dialog(self):
        """Show the stop dialog."""
        for button in self._stop_buttons:
            button.set_sensitive(False)
        alert = Alert()
        alert.props.title = _("Stop")
        alert.props.msg = _("Stop: name your journal entry")

        title = self._jobject.metadata["title"]
        alert.entry = alert.add_entry()
        alert.entry.set_text(title)

        label, tip = self._get_save_label_tip(title)
        button = alert.add_button(
            Gtk.ResponseType.OK, label, Icon(icon_name="dialog-ok")
        )

        if self.sugar_accel_group and hasattr(
            self.sugar_accel_group, "set_accels_for_action"
        ):
            self.sugar_accel_group.set_accels_for_action("win.save", ["Return"])

        button.set_tooltip_text(tip)
        alert.ok = button

        label, tip = self._get_erase_label_tip()
        button = alert.add_button(
            Gtk.ResponseType.ACCEPT, label, Icon(icon_name="list-remove")
        )
        button.set_tooltip_text(tip)

        button = alert.add_button(
            Gtk.ResponseType.CANCEL, _("Cancel"), Icon(icon_name="dialog-cancel")
        )

        # GTK4: Accelerators are handled differently
        if self.sugar_accel_group and hasattr(
            self.sugar_accel_group, "set_accels_for_action"
        ):
            self.sugar_accel_group.set_accels_for_action("win.cancel", ["Escape"])

        button.set_tooltip_text(_("Cancel stop and continue the activity"))

        alert.connect("response", self.__stop_dialog_response_cb)
        alert.entry.connect("changed", self.__stop_dialog_changed_cb, alert)
        self.add_alert(alert)

    def __stop_dialog_response_cb(self, alert, response_id):
        """Handle stop dialog response."""
        if response_id == Gtk.ResponseType.OK:
            title = alert.entry.get_text()
            if self._is_resumed and title == self._original_title:
                datastore.delete(self._jobject_old.get_object_id())
            self._jobject.metadata["title"] = title
            self._do_close(False)

        if response_id == Gtk.ResponseType.ACCEPT:
            datastore.delete(self._jobject.get_object_id())
            self._do_close(True)

        if response_id == Gtk.ResponseType.CANCEL:
            for button in self._stop_buttons:
                button.set_sensitive(True)

        self.remove_alert(alert)

    def __stop_dialog_changed_cb(self, entry, alert):
        """Handle stop dialog entry changes."""
        label, tip = self._get_save_label_tip(entry.get_text())

        alert.ok.set_label(label)
        alert.ok.set_tooltip_text(tip)

    def _get_save_label_tip(self, title):
        """Get save button label and tooltip."""
        label = _("Save new")
        tip = _("Save a new journal entry")
        if self._is_resumed and title == self._original_title:
            label = _("Save")
            tip = _("Save into the old journal entry")

        return label, tip

    def _get_erase_label_tip(self):
        """Get erase button label and tooltip."""
        if self._is_resumed:
            label = _("Erase changes")
            tip = _(
                "Erase what you have done, and leave your old journal entry unchanged"
            )
        else:
            label = _("Erase")
            tip = _("Erase what you have done, and avoid making a journal entry")

        return label, tip

    def _prepare_close(self, skip_save=False):
        """Prepare for closing the activity."""
        if not skip_save:
            try:
                self.save()
            except BaseException:
                logging.exception("Error saving activity object to datastore")
                self._show_keep_failed_dialog()
                return False

        self._closing = True
        return True

    def _complete_close(self):
        """Complete the close process."""
        self.destroy()

        if self.shared_activity:
            self.shared_activity.leave()

        self._cleanup_jobject()

        # D-Bus service cleanup
        if self._bus:
            logging.debug("Cleaning up D-Bus service")

        self._session.unregister(self)

        # Power management for GTK4
        # power.get_power_manager().shutdown()

    def _do_close(self, skip_save):
        """Internal close method."""
        self.busy()
        self.emit("closing")
        if not self._closing:
            if not self._prepare_close(skip_save):
                return

        if not self._updating_jobject:
            self._complete_close()

    def close(self, skip_save=False):
        """
        Save to the journal and stop the activity.

        Activities should not override this method, but should
        implement :meth:`write_file` to do any state saving
        instead. If the activity wants to control whether it can close,
        it should override :meth:`can_close`.

        Args:
            skip_save (bool): avoid last-chance save; but does not prevent
                a journal object, as an object is created when the activity
                starts.  Use this when an activity calls :meth:`save` just
                prior to :meth:`close`.
        """
        if not self.can_close():
            return

        if get_save_as():
            if self._jobject.metadata["title"] != self._original_title:
                self._do_close(skip_save)
            else:
                self._show_stop_dialog()
        else:
            self._do_close(skip_save)

    def __close_request_cb(self, window):
        """Handle close request signal (GTK4 version)."""
        self.close()
        return True

    def get_metadata(self):
        """
        Get the journal object metadata.

        Returns:
            dict: the journal object metadata, or None if there is no object.

        Activities can set metadata in write_file() using:

        .. code-block:: python

            self.metadata['MyKey'] = 'Something'

        and retrieve metadata in read_file() using:

        .. code-block:: python

            self.metadata.get('MyKey', 'aDefaultValue')

        Make sure your activity works properly if one or more of the
        metadata items is missing. Never assume they will all be
        present.
        """
        if self._jobject:
            return self._jobject.metadata
        else:
            return None

    metadata = property(get_metadata, None)

    def handle_view_source(self):
        """
        An activity may override this method to show additional
        information in the View Source window. Examples can be seen in
        Browse and TurtleArt.

        Raises:
            :exc:`NotImplementedError`
        """
        raise NotImplementedError

    def get_document_path(self, async_cb, async_err_cb):
        """
        Not implemented.
        """
        async_err_cb(NotImplementedError())

    def busy(self):
        """
        Show that the activity is busy.  If used, must be called once
        before a lengthy operation, and :meth:`unbusy` must be called
        after the operation completes.

        .. code-block:: python

            self.busy()
            self.long_operation()
            self.unbusy()
        """
        if self._busy_count == 0:
            # GTK4: Different cursor handling
            cursor = Gdk.Cursor.new_from_name("wait", None)
            self.set_cursor(cursor)
        self._busy_count += 1

    def unbusy(self):
        """
        Show that the activity is not busy.  An equal number of calls
        to :meth:`unbusy` are required to balance the calls to
        :meth:`busy`.

        Returns:
            int: a count of further calls to :meth:`unbusy` expected
        """
        self._busy_count -= 1
        if self._busy_count == 0:
            self.set_cursor(None)
        return self._busy_count


class SimpleActivity(Activity):
    """
    A simple activity implementation for quick prototyping.

    This provides a basic activity with a toolbar and content area.
    """

    def __init__(self, handle=None, application=None):
        super().__init__(handle=handle, application=application)
        self._create_toolbar()
        self._create_content_area()

    def _create_toolbar(self):
        """Create the toolbar."""
        from sugar4.activity.widgets import ActivityToolbarButton, StopButton
        from sugar4.graphics.toolbarbox import ToolbarBox

        toolbar_box = ToolbarBox()

        # Activity button
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.append(activity_button)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar_box.toolbar.append(spacer)

        # Stop button
        stop_button = StopButton(self)
        toolbar_box.toolbar.append(stop_button)

        self.set_toolbar_box(toolbar_box)

    def _create_content_area(self):
        """Create a simple content area."""
        label = Gtk.Label(label="Simple Sugar GTK4 Activity")
        label.set_margin_top(50)
        label.set_margin_bottom(50)
        label.set_margin_start(50)
        label.set_margin_end(50)
        self.set_canvas(label)


# Global session manager
_session = None


def _get_session():
    """Get the global session manager."""
    global _session
    if _session is None:
        _session = _ActivitySession()
    return _session


def get_bundle_name():
    """
    Returns:
        str: the bundle name for the current process' bundle
    """
    return os.environ["SUGAR_BUNDLE_NAME"]


def get_bundle_path():
    """
    Returns:
        str: the bundle path for the current process' bundle
    """
    return os.environ["SUGAR_BUNDLE_PATH"]


def get_activity_root():
    """
    Returns:
        str: a path for saving Activity specific preferences, etc.

    Returns a path to the location in the filesystem where the
    activity can store activity related data that doesn't pertain to
    the current execution of the activity and thus cannot go into the
    DataStore.

    Currently, this will return something like
    ~/.sugar/default/MyActivityName/

    Activities should ONLY save settings, user preferences and other
    data which isn't specific to a journal item here. If (meta-)data
    is in anyway specific to a journal entry, it MUST be stored in the
    DataStore.
    """
    if os.environ.get("SUGAR_ACTIVITY_ROOT"):
        return os.environ["SUGAR_ACTIVITY_ROOT"]
    else:
        activity_root = env.get_profile_path(os.environ["SUGAR_BUNDLE_ID"])
        try:
            os.mkdir(activity_root)
        except OSError as e:
            if e.errno != EEXIST:
                raise e
        return activity_root


def show_object_in_journal(object_id):
    """
    Raise the journal activity and show a journal object.

    Args:
        object_id (object): journal object

    Note: In GTK4/Flatpak environment, this functionality will need
    to be implemented using the document portal.
    """
    raise NotImplementedError(
        "Journal integration not yet implemented in GTK4 port. "
        "Use Flatpak document portal for file management."
    )


def launch_bundle(bundle_id="", object_id=""):
    """
    Launch an activity for a journal object, or an activity.

    Args:
        bundle_id (str): activity bundle id, optional
        object_id (object): journal object
    """
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    bundle_launcher = dbus.Interface(obj, J_DBUS_INTERFACE)
    return bundle_launcher.LaunchBundle(bundle_id, object_id)


def get_bundle(bundle_id="", object_id=""):
    """
    Get the bundle id of an activity that can open a journal object.

    Args:
        bundle_id (str): activity bundle id, optional
        object_id (object): journal object
    """
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    journal = dbus.Interface(obj, J_DBUS_INTERFACE)
    bundle_path = journal.GetBundlePath(bundle_id, object_id)
    if bundle_path:
        return bundle_from_dir(bundle_path)
    else:
        return None
