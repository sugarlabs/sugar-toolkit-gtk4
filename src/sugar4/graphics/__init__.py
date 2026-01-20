"""
Graphics Module
===============

Visual components, styling, and UI widgets for Sugar activities.
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
except ImportError:
    # gi might not be available during docs build
    pass

# Initialize Sugar theme system
# This loads CSS from sugar-artwork if available, or uses bundled fallback
try:
    from .theme import init_sugar_themes
    init_sugar_themes()
except Exception:
    # Continue even if theme initialization fails
    pass

from .xocolor import XoColor
from .icon import (
    Icon,
    EventIcon,
    CanvasIcon,
    CellRendererIcon,
    get_icon_file_name,
    get_surface,
    get_icon_state,
    SMALL_ICON_SIZE,
    STANDARD_ICON_SIZE,
    LARGE_ICON_SIZE,
)

# from .tray import (HTray, VTray, TrayButton, TrayIcon,
#                    ALIGN_TO_START, ALIGN_TO_END, GRID_CELL_SIZE)
# from .window import Window, UnfullscreenButton


__all__ = [
    "XoColor",
    "Icon",
    "EventIcon",
    "CanvasIcon",
    "CellRendererIcon",
    "get_icon_file_name",
    "get_surface",
    "get_icon_state",
    "SMALL_ICON_SIZE",
    "STANDARD_ICON_SIZE",
    "LARGE_ICON_SIZE",
    # "HTray", "VTray", "TrayButton", "TrayIcon",
    # "ALIGN_TO_START", "ALIGN_TO_END", "GRID_CELL_SIZE",
    # "Window", "UnfullscreenButton"
]
