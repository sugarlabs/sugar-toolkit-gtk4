"""
Sugar Toolkit GTK4 Python
==========================

A modern GTK4 port of the Sugar Toolkit for Python activities.

This package provides the core functionality needed to create Sugar activities
using GTK4, maintaining compatibility with Sugar's educational framework while
leveraging modern GTK4 features.

Modules:
    activity: Core activity classes and functionality
    graphics: Visual components, styling, and UI widgets
    bundle: Activity bundle management
"""

# Set GTK version requirements before any GTK imports
try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("GObject", "2.0")
    gi.require_version("Gio", "2.0")
    gi.require_version("GLib", "2.0")
    gi.require_version("Pango", "1.0")
    gi.require_version("GdkPixbuf", "2.0")
    
    from .activity.activity import Activity, SimpleActivity
    from .graphics import style
    from .graphics.icon import EventIcon, Icon
    from .graphics.menuitem import MenuItem, MenuSeparator
    from .graphics.xocolor import XoColor

    __all__ = [
        "Activity",
        "SimpleActivity",
        "XoColor",
        "Icon",
        "EventIcon",
        "MenuItem",
        "MenuSeparator",
        "style",
    ]
except (ImportError, ValueError):
    # gi might not be available during docs build,
    # or GTK 3.0 is already loaded by a legacy activity importing a utility module.
    __all__ = []

__version__ = "1.1.4"
__author__ = "Sugar Labs Community"
__license__ = "LGPL-2.1-or-later"
