"""
CSS Theme Loader for Sugar Toolkit GTK4

This module provides centralized CSS theme loading from sugar-artwork
and fallback CSS definitions for Sugar toolkit components.

SPDX-License-Identifier: LGPL-2.1-or-later
"""

import os
import gi
from typing import Optional

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

import logging

logger = logging.getLogger(__name__)


class SugarThemeLoader:
    """
    Loads CSS themes from sugar-artwork or uses fallback definitions.
    
    This class manages the loading and application of Sugar-specific CSS
    styling, preferring sugar-artwork themes when available.
    """

    _instance = None
    _css_provider = None
    _fallback_css_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of SugarThemeLoader."""
        return cls()

    def __init__(self):
        """Initialize the theme loader."""
        self.css_provider = Gtk.CssProvider()
        self._sugar_artwork_path = None
        self._find_sugar_artwork()

    def _find_sugar_artwork(self) -> Optional[str]:
        """
        Find the sugar-artwork installation path.
        
        Returns:
            Path to sugar-artwork CSS files, or None if not found.
        """
        # Common installation paths for sugar-artwork
        possible_paths = [
            "/usr/share/sugar/artwork",
            "/usr/local/share/sugar/artwork",
            "/opt/sugar/artwork",
            os.path.expanduser("~/.local/share/sugar/artwork"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found sugar-artwork at: {path}")
                self._sugar_artwork_path = path
                return path

        logger.debug("sugar-artwork not found in common paths")
        return None

    def load_theme(self, theme_name: str = "default") -> bool:
        """
        Load a theme from sugar-artwork.
        
        Args:
            theme_name: Name of the theme to load (without extension).
                       Defaults to "default".
        
        Returns:
            True if theme was loaded successfully, False otherwise.
        """
        if self._sugar_artwork_path is None:
            logger.warning("sugar-artwork not found, using fallback CSS")
            return self.load_fallback_css()

        css_path = os.path.join(
            self._sugar_artwork_path, f"themes/{theme_name}.css"
        )

        if not os.path.exists(css_path):
            logger.warning(
                f"Theme file not found: {css_path}, trying alternate paths"
            )
            # Try alternate path structure
            css_path = os.path.join(
                self._sugar_artwork_path, f"{theme_name}.css"
            )

        if not os.path.exists(css_path):
            logger.warning(f"Theme file not found at any location, using fallback")
            return self.load_fallback_css()

        try:
            self.css_provider.load_from_path(css_path)
            self._apply_css_provider()
            logger.info(f"Loaded theme from sugar-artwork: {css_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load theme from {css_path}: {e}")
            return self.load_fallback_css()

    def load_fallback_css(self) -> bool:
        """
        Load fallback CSS from sugar-toolkit-gtk4.
        
        Returns:
            True if fallback CSS was loaded successfully, False otherwise.
        """
        if self._fallback_css_loaded:
            return True

        # Get the path to the fallback CSS file
        current_dir = os.path.dirname(__file__)
        css_path = os.path.join(current_dir, "sugar-gtk4.css")

        if not os.path.exists(css_path):
            logger.error(f"Fallback CSS file not found: {css_path}")
            return False

        try:
            self.css_provider.load_from_path(css_path)
            self._apply_css_provider()
            self._fallback_css_loaded = True
            logger.info(f"Loaded fallback CSS from: {css_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load fallback CSS from {css_path}: {e}")
            return False

    def load_css_string(self, css: str) -> bool:
        """
        Load CSS from a string.
        
        Args:
            css: CSS string to load.
        
        Returns:
            True if CSS was loaded successfully, False otherwise.
        """
        try:
            self.css_provider.load_from_data(css.encode())
            self._apply_css_provider()
            return True
        except Exception as e:
            logger.error(f"Failed to load CSS from string: {e}")
            return False

    def _apply_css_provider(self):
        """Apply the CSS provider to the default display."""
        try:
            display = Gtk.SettingsList().get_default_display()
            if display:
                Gtk.StyleContext.add_provider_for_display(display, self.css_provider, 600)
            else:
                logger.warning("Could not get default display for CSS provider")
        except Exception as e:
            logger.error(f"Failed to apply CSS provider: {e}")

    @staticmethod
    def apply_css_to_widget(widget, css: str, priority: int = 600):
        """
        Apply CSS directly to a specific widget.
        
        Args:
            widget: The GTK widget to apply CSS to.
            css: CSS string to apply.
            priority: CSS priority level (default 600).
        """
        if widget is None:
            return

        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(css.encode())
            widget.get_style_context().add_provider(css_provider, priority)
        except Exception as e:
            logger.error(f"Failed to apply CSS to widget: {e}")


# Initialize the global theme loader
_theme_loader = None


def get_theme_loader() -> SugarThemeLoader:
    """Get the global SugarThemeLoader instance."""
    global _theme_loader
    if _theme_loader is None:
        _theme_loader = SugarThemeLoader()
    return _theme_loader


def init_sugar_themes():
    """Initialize Sugar themes on module load."""
    loader = get_theme_loader()
    # Try to load theme from sugar-artwork, fall back to bundled CSS
    if not loader.load_theme():
        logger.info("Using fallback CSS from sugar-toolkit-gtk4")
