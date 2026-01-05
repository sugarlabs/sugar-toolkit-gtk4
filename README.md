# sugar-toolkit-gtk4

A modern GTK4 port of the Sugar Toolkit for Python activities.

## Project Status

This project is a ground-up reimplementation of the Sugar Toolkit using GTK4 and modern Python practices. We're maintaining compatibility with Sugar's core concepts while leveraging GTK4's improved APIs.

## Installation

### From Source

```bash
git clone https://github.com/sugarlabs/sugar-toolkit-gtk4.git
cd sugar-toolkit-gtk4
pip install -e .
```

### Development Setup

```bash
make install
```

## Quick Start

```python
from sugar4.activity import SimpleActivity
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

class MyActivity(SimpleActivity):
    def __init__(self):
        super().__init__()

        # Your activity code here
        label = Gtk.Label(label="Hello, Welcome GTK4!")
        self.set_canvas(label)

def main():
    """Run the activity with proper GTK4 application lifecycle."""
    app = Gtk.Application(application_id='org.sugarlabs.TestActivity')

    def on_activate(app):
        activity = MyActivity()
        app.add_window(activity)
        activity.present()

    app.connect('activate', on_activate)
    return app.run()

if __name__ == '__main__':
    main()
```

## Development

### Running Tests

```bash
make test
```

### Running with Coverage

```bash
make test-coverage
```

### Code Formatting

```bash
make format
```

### Building Package

```bash
make build
```

### Running Examples

```bash
make example
```

## Makefile Usage

The project includes a comprehensive Makefile with targets for all development, testing, and packaging workflows. Use `make help` to see all available targets.

### Installation and Setup

```bash
make install          # Install package in development mode
make dev-setup        # Complete development environment setup
```

### Testing and Quality Assurance

```bash
make test             # Run all tests
make test-coverage    # Run tests with HTML coverage report
make format           # Format code with black
make format-check     # Check code formatting without changes
make dev-test         # Run full development test suite
```

### Building and Packaging

```bash
make build            # Build wheel and source distributions
make dist             # Alias for build
make tarball          # Create source tarball
make check            # Verify package integrity with twine
make dev-build        # Clean, build, and check package
```

### Publishing

```bash
make upload-test      # Upload to Test PyPI
make upload           # Upload to production PyPI
```

### Utilities

```bash
make clean            # Remove build artifacts and cache files
make example          # Run the basic activity example
make test-toolkit     # Test toolkit installation (python -m sugar)
make ci-test          # Simulate complete CI pipeline locally
make help             # Show all available targets with descriptions
```

### Development Workflow Examples

**Setting up for development:**

```bash
make dev-setup        # Install everything needed
make test             # Verify setup works
```

**Before committing changes:**

```bash
make dev-test         # Run full test suite with formatting checks
```

**Creating a release:**

```bash
make dev-build        # Clean build and verify package integrity
make tarball          # Create source distribution
make check            # Final verification before upload
```

**Testing the complete CI workflow locally:**

```bash
make ci-test          # Runs the full CI pipeline simulation
```

# Dev Tips

- Run the examples with:
 
```
 GTK_DEBUG=interactive QT_QPA_PLATFORM=xcb GDK_BACKEND=x11 \
SUGAR_BUNDLE_PATH="$(pwd)/examples" \
SUGAR_BUNDLE_ID="org.sugarlabs.SugarTextEditor" \
SUGAR_BUNDLE_NAME="Sugar Text Editor" \
SUGAR_ACTIVITY_ROOT="/tmp/sugar_text_editor" \
python examples/activity_example.py
```
- For Mac OS
```
GTK_DEBUG=interactive \
SUGAR_BUNDLE_PATH="$(pwd)/examples" \
SUGAR_BUNDLE_ID="org.sugarlabs.BasicExample" \
SUGAR_BUNDLE_NAME="Basic Example" \
SUGAR_ACTIVITY_ROOT="/tmp/sugar_basic_example" \
python3 examples/activity_example.py
```

## Requirements

- Python 3.8+
- GTK4
- PyGObject 3.42+
- GObject Introspection

## License

LGPL-2.1-or-later

## GTK4 App Bundling Example

See [`examples/gtk4_bundle_test/`](examples/gtk4_bundle_test/) for a minimal example of bundling a GTK4 Sugar activity using Flatpak.

- Includes a simple activity (`main.py`), Flatpak manifest, and build/run instructions.
- To try it:
  1. Install Flatpak and the GNOME SDK (see the example README).
  2. Build and run the bundle as described in the example.
