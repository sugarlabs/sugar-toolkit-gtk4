"""
Tests for Window (GTK4)
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from sugar4.graphics.window import Window


@pytest.fixture
def gtk_app():
    app = Gtk.Application()
    yield app
    app.quit()


def test_window_creation(gtk_app):
    """Test that a Window can be created and basic properties work."""
    win = Window(application=gtk_app)
    assert isinstance(win, Window)
    assert win.get_enable_fullscreen_mode() is True
    assert win.is_fullscreen() is False


def test_window_canvas_set_get(gtk_app):
    """Test setting and getting the canvas widget."""
    win = Window(application=gtk_app)
    canvas = Gtk.Label(label="Canvas Widget")
    win.set_canvas(canvas)
    assert win.get_canvas() is canvas
    # Property access
    win.canvas = canvas
    assert win.canvas is canvas


def test_window_toolbar_set_get(gtk_app):
    """Test setting and getting the toolbar box."""
    win = Window(application=gtk_app)
    toolbar = Gtk.Box()
    win.set_toolbar_box(toolbar)
    assert win.get_toolbar_box() is toolbar
    # Property access
    win.toolbar_box = toolbar
    assert win.toolbar_box is toolbar


def test_window_fullscreen_toggle(gtk_app):
    """Test fullscreen and unfullscreen logic."""
    win = Window(application=gtk_app)
    win.fullscreen()
    assert win.is_fullscreen() is True
    win.unfullscreen()
    assert win.is_fullscreen() is False


def test_window_alert_add_remove(gtk_app):
    """Test adding and removing alerts."""
    win = Window(application=gtk_app)
    alert = Gtk.Label(label="Alert")
    win.add_alert(alert)
    assert alert in win.get_alerts()
    win.remove_alert(alert)
    assert alert not in win.get_alerts()


def test_window_enable_fullscreen_mode_property(gtk_app):
    """Test enable_fullscreen_mode property getter/setter."""
    win = Window(application=gtk_app)
    win.set_enable_fullscreen_mode(False)
    assert win.get_enable_fullscreen_mode() is False
    win.set_enable_fullscreen_mode(True)
    assert win.get_enable_fullscreen_mode() is True
