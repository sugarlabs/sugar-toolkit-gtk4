# Copyright (C) 2009, Aleksey Lim, Simon Schampijer
# Copyright (C) 2012, Walter Bender
# Copyright (C) 2012, One Laptop Per Child
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

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
import gettext

from sugar4.debug import debug_print

from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics.toolbarbox import ToolbarButton
from sugar4.graphics.radiopalette import RadioPalette, RadioMenuButton
from sugar4.graphics.radiotoolbutton import RadioToolButton
from sugar4.graphics.xocolor import XoColor
from sugar4.graphics.icon import Icon
from sugar4.graphics import style
from sugar4.graphics.palettemenu import PaletteMenuBox
from sugar4 import profile

print = debug_print


def _(msg):
    return gettext.dgettext("sugar-toolkit-gtk4", msg)


def _create_activity_icon(metadata, icon_name=None):
    """Create an activity icon with appropriate color."""
    import os

    if metadata is not None and metadata.get("icon-color"):
        color = XoColor(metadata["icon-color"])
    else:
        color = profile.get_color()

    if icon_name is None:
        icon_name = "activity-journal"  # Default fallback icon

    # If icon_name is an absolute SVG path, use file_name
    if icon_name and os.path.isabs(icon_name) and icon_name.endswith(".svg"):
        print(f"[_create_activity_icon] Using SVG file: {icon_name}")
        icon = Icon(file_name=icon_name, xo_color=color)
    else:
        print(f"[_create_activity_icon] Using theme icon: {icon_name}")
        icon = Icon(icon_name=icon_name, xo_color=color)
    return icon


class ActivityButton(ToolButton):
    """Button representing an activity with its icon and metadata."""

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()

        self.props.hide_tooltip_on_click = False
        self.palette_invoker.props.toggle_palette = True
        self.props.tooltip = activity.metadata.get("title", "Activity")

        if hasattr(activity.metadata, "connect"):
            activity.metadata.connect("updated", self.__jobject_updated_cb)

    def __jobject_updated_cb(self, jobject):
        self.props.tooltip = jobject.get("title", "Activity")


class ActivityToolbarButton(ToolbarButton):
    """Toolbar button that contains an activity toolbar."""

    def __init__(self, activity, **kwargs):
        print(f"[ActivityToolbarButton] kwargs: {kwargs}")
        toolbar = ActivityToolbar(activity, orientation_left=True)
        toolbar.connect("enter-key-press", lambda widget: self.emit("clicked"))

        ToolbarButton.__init__(self, page=toolbar, **kwargs)

        icon = _create_activity_icon(activity.metadata, kwargs.get("icon_name"))
        print(f"[ActivityToolbarButton] icon: {icon}")
        self.set_icon_widget(icon)
        icon.show()


class StopButton(ToolButton):
    """Button to stop/close an activity."""

    def __init__(self, activity, icon_name="activity-stop", **kwargs):
        print(f"[StopButton] icon_name: {icon_name}")
        ToolButton.__init__(self, **kwargs)
        # Use custom Icon for stop
        icon = _create_activity_icon(activity.metadata, icon_name=icon_name)
        icon.set_pixel_size(48)
        self.set_icon_widget(icon)
        icon.show()
        print(f"[StopButton] icon_widget type: {type(icon)}")
        if hasattr(icon, "get_icon_name"):
            print(f"[StopButton] icon name: {icon.get_icon_name()}")
        if hasattr(icon, "get_file_name"):
            print(f"[StopButton] file name: {icon.get_file_name()}")
        self.props.tooltip = _("Stop")
        self.props.accelerator = "<Ctrl>Q"
        self.connect("clicked", self.__stop_button_clicked_cb, activity)
        if hasattr(activity, "add_stop_button"):
            activity.add_stop_button(self)

    def __stop_button_clicked_cb(self, button, activity):
        if hasattr(activity, "close"):
            activity.close()


class UndoButton(ToolButton):
    """Standard undo button."""

    def __init__(self, **kwargs):
        ToolButton.__init__(self, "edit-undo", **kwargs)
        self.props.tooltip = _("Undo")
        self.props.accelerator = "<Ctrl>Z"


class RedoButton(ToolButton):
    """Standard redo button."""

    def __init__(self, **kwargs):
        ToolButton.__init__(self, "edit-redo", **kwargs)
        self.props.tooltip = _("Redo")
        self.props.accelerator = "<Ctrl>Y"


class CopyButton(ToolButton):
    """Standard copy button."""

    def __init__(self, **kwargs):
        ToolButton.__init__(self, "edit-copy", **kwargs)
        self.props.tooltip = _("Copy")
        self.props.accelerator = "<Ctrl>C"


class PasteButton(ToolButton):
    """Standard paste button."""

    def __init__(self, **kwargs):
        ToolButton.__init__(self, "edit-paste", **kwargs)
        self.props.tooltip = _("Paste")
        self.props.accelerator = "<Ctrl>V"


class ShareButton(RadioMenuButton):
    """Button for sharing activities with neighborhood."""

    def __init__(self, activity, **kwargs):
        palette = RadioPalette()

        self.private = RadioToolButton(icon_name="zoom-home")
        palette.append(self.private, _("Private"))

        self.neighborhood = RadioToolButton(
            icon_name="zoom-neighborhood", group=self.private
        )
        self._neighborhood_handle = self.neighborhood.connect(
            "clicked", self.__neighborhood_clicked_cb, activity
        )
        palette.append(self.neighborhood, _("My Neighborhood"))

        if hasattr(activity, "connect"):
            activity.connect("shared", self.__update_share_cb)
            activity.connect("joined", self.__update_share_cb)

        RadioMenuButton.__init__(self, **kwargs)
        self.props.palette = palette

        if hasattr(activity, "max_participants") and activity.max_participants == 1:
            self.props.sensitive = False

    def __neighborhood_clicked_cb(self, button, activity):
        if hasattr(activity, "share"):
            activity.share()

    def __update_share_cb(self, activity):
        self.neighborhood.handler_block(self._neighborhood_handle)
        try:
            if (
                hasattr(activity, "shared_activity")
                and activity.shared_activity is not None
                and hasattr(activity.shared_activity, "props")
                and not activity.shared_activity.props.private
            ):
                self.private.props.sensitive = False
                self.neighborhood.props.sensitive = False
                self.neighborhood.props.active = True
            else:
                self.private.props.sensitive = True
                self.neighborhood.props.sensitive = True
                self.private.props.active = True
        finally:
            self.neighborhood.handler_unblock(self._neighborhood_handle)


class TitleEntry(Gtk.Box):
    """Entry widget for editing activity title."""

    __gsignals__ = {
        "enter-key-press": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, activity, **kwargs):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self.entry = Gtk.Entry(**kwargs)

        # Get display and calculate size
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_monitors()[0]  # Primary monitor
            geometry = monitor.get_geometry()
            width = int(geometry.width / 3)
        else:
            width = 300  # Fallback width

        self.entry.set_size_request(width, -1)
        self.entry.set_text(activity.metadata.get("title", ""))

        # GTK4 uses different event handling
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self.__focus_out_event_cb, activity)
        self.entry.add_controller(focus_controller)

        self.entry.connect("activate", self.__activate_cb, activity)

        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self.__button_press_event_cb)
        self.entry.add_controller(click_gesture)

        self.entry.show()
        self.append(self.entry)

        if hasattr(activity.metadata, "connect"):
            activity.metadata.connect("updated", self.__jobject_updated_cb)
        if hasattr(activity, "connect"):
            activity.connect("closing", self.__closing_cb)

    def __activate_cb(self, entry, activity):
        self.save_title(activity)
        entry.select_region(0, 0)
        self.emit("enter-key-press")
        return False

    def __jobject_updated_cb(self, jobject):
        if self.entry.has_focus():
            return
        title = jobject.get("title", "")
        if self.entry.get_text() == title:
            return
        self.entry.set_text(title)

    def __closing_cb(self, activity):
        self.save_title(activity)
        return False

    def __focus_out_event_cb(self, controller, activity):
        self.entry.select_region(0, 0)
        self.save_title(activity)
        return False

    def __button_press_event_cb(self, gesture, n_press, x, y):
        widget = gesture.get_widget()
        if not widget.has_focus():
            widget.grab_focus()
            widget.select_region(0, -1)
            return True
        return False

    def save_title(self, activity):
        title = self.entry.get_text()
        current_title = activity.metadata.get("title", "")
        if title == current_title:
            return

        activity.metadata["title"] = title
        activity.metadata["title_set_by_user"] = "1"

        if hasattr(activity, "save"):
            activity.save()

        if hasattr(activity, "set_title"):
            activity.set_title(title)

        if hasattr(activity, "get_shared_activity"):
            shared_activity = activity.get_shared_activity()
            if shared_activity is not None and hasattr(shared_activity.props, "name"):
                shared_activity.props.name = title


class DescriptionItem(ToolButton):
    """Button for editing activity description."""

    def __init__(self, activity, icon=None, **kwargs):
        print(f"[DescriptionItem] kwargs: {kwargs}")
        ToolButton.__init__(self, **kwargs)
        import os

        # Accept either icon name or file path
        # TODO: Improve icon handling
        if icon is None:
            # Default to theme icon name
            icon_name = "edit-description"
            file_name = None
        elif os.path.isabs(icon):
            icon_name = None
            file_name = icon
        elif icon.endswith(".svg"):
            from sugar4.activity.activity import get_bundle_path
            file_name = os.path.join(get_bundle_path(), icon)
            icon_name = None
        else:
            icon_name = icon
            file_name = None
            
        icon_widget = Icon(icon_name=icon_name, file_name=file_name)
        icon_widget.set_pixel_size(48)
        self.set_icon_widget(icon_widget)
        icon_widget.show()
        print(f"[DescriptionItem] icon_widget type: {type(icon_widget)}")
        print(f"[DescriptionItem] icon_name: {icon_name}")
        print(f"[DescriptionItem] file_name: {file_name}")
        self.set_tooltip(_("Description"))
        self.palette_invoker.props.toggle_palette = True
        self.palette_invoker.props.lock_palette = True
        self.props.hide_tooltip_on_click = False
        self._palette = self.get_palette()

        description_box = PaletteMenuBox()
        sw = Gtk.ScrolledWindow()

        # Get display and calculate size
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_monitors()[0]  # Primary monitor
            geometry = monitor.get_geometry()
            width = int(geometry.width / 2)
        else:
            width = 400  # Fallback width

        sw.set_size_request(width, 2 * style.GRID_CELL_SIZE)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self._text_view = Gtk.TextView()
        self._text_view.set_cursor_visible(True)
        self._text_view.set_left_margin(style.DEFAULT_PADDING)
        self._text_view.set_right_margin(style.DEFAULT_PADDING)
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        text_buffer = Gtk.TextBuffer()
        description = activity.metadata.get("description", "")
        if description:
            text_buffer.set_text(description)
        self._text_view.set_buffer(text_buffer)

        # GTK4 focus handling
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self.__description_changed_cb, activity)
        self._text_view.add_controller(focus_controller)

        sw.set_child(self._text_view)
        description_box.append_item(sw, vertical_padding=0)
        self._palette.set_content(description_box)
        description_box.show()

        if hasattr(activity.metadata, "connect"):
            activity.metadata.connect("updated", self.__jobject_updated_cb)

    def set_expanded(self, expanded):
        box = self.toolbar_box
        if not box:
            return

        if not expanded:
            self.palette_invoker.notify_popdown()
            return

        if hasattr(box, "expanded_button") and box.expanded_button is not None:
            box.expanded_button.queue_draw()
            if box.expanded_button != self:
                box.expanded_button.set_expanded(False)
        if hasattr(box, "expanded_button"):
            box.expanded_button = self

    def get_toolbar_box(self):
        parent = self.get_parent()
        if not hasattr(parent, "owner"):
            return None
        return parent.owner

    toolbar_box = property(get_toolbar_box)

    def _get_text_from_buffer(self):
        buf = self._text_view.get_buffer()
        start_iter = buf.get_start_iter()
        end_iter = buf.get_end_iter()
        return buf.get_text(start_iter, end_iter, False)

    def __jobject_updated_cb(self, jobject):
        if self._text_view.has_focus():
            return
        description = jobject.get("description", "")
        if not description:
            return
        if self._get_text_from_buffer() == description:
            return
        buf = self._text_view.get_buffer()
        buf.set_text(description)

    def __description_changed_cb(self, controller, activity):
        description = self._get_text_from_buffer()
        current_description = activity.metadata.get("description", "")
        if description == current_description:
            return

        activity.metadata["description"] = description
        if hasattr(activity, "save"):
            activity.save()
        return False


class ActivityToolbar(Gtk.Box):
    """The Activity toolbar with the Journal entry title and sharing button."""

    __gsignals__ = {
        "enter-key-press": (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, activity, orientation_left=False):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_css_class("toolbar")

        self._activity = activity

        if hasattr(activity, "metadata") and activity.metadata:
            title_button = TitleEntry(activity)
            title_button.connect(
                "enter-key-press", lambda widget: self.emit("enter-key-press")
            )
            title_button.show()
            self.append(title_button)
            self.title = title_button.entry

        if not orientation_left:
            # Add expandable space
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            self.append(spacer)

        if hasattr(activity, "metadata") and activity.metadata:
            description_item = DescriptionItem(activity)
            description_item.show()
            self.append(description_item)

        self.share = ShareButton(activity)
        self.share.show()
        self.append(self.share)


class EditToolbar(Gtk.Box):
    """Provides the standard edit toolbar for Activities.

    Members:
        undo  -- the undo button
        redo  -- the redo button
        copy  -- the copy button
        paste -- the paste button
        separator -- A separator between undo/redo and copy/paste

    This class only provides the 'edit' buttons in a standard layout,
    your activity will need to either hide buttons which make no sense for your
    Activity, or you need to connect the button events to your own callbacks:

        ## Example from Read.activity:
        # Create the edit toolbar:
        self._edit_toolbar = EditToolbar()
        # Hide undo and redo, they're not needed
        self._edit_toolbar.undo.props.visible = False
        self._edit_toolbar.redo.props.visible = False
        # Hide the separator too:
        self._edit_toolbar.separator.props.visible = False

        # As long as nothing is selected, copy needs to be insensitive:
        self._edit_toolbar.copy.set_sensitive(False)
        # When the user clicks the button, call _edit_toolbar_copy_cb()
        self._edit_toolbar.copy.connect('clicked', self._edit_toolbar_copy_cb)

        # Add the edit toolbar:
        toolbox.add_toolbar(_('Edit'), self._edit_toolbar)
        # And make it visible:
        self._edit_toolbar.show()
    """

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_css_class("toolbar")

        self.undo = UndoButton()
        self.append(self.undo)
        self.undo.show()

        self.redo = RedoButton()
        self.append(self.redo)
        self.redo.show()

        self.separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(self.separator)
        self.separator.show()

        self.copy = CopyButton()
        self.append(self.copy)
        self.copy.show()

        self.paste = PasteButton()
        self.append(self.paste)
        self.paste.show()
