"""ShelfBridge plugin entry point & metadata."""
import sys
import pathlib

# Make vendored dependencies (keyring, certifi, httpx …) importable.
_vendor = pathlib.Path(__file__).parent / "vendor"
if _vendor.is_dir() and str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))

from calibre.customize import InterfaceActionBase


class ShelfBridgePlugin(InterfaceActionBase):
    name = 'ShelfBridge'
    description = 'Export your Calibre library to reading-tracker services'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'Kayla Ehman'
    version = (0, 1, 0)
    minimum_calibre_version = (6, 0, 0)
    actual_plugin = 'calibre_plugins.shelf_bridge.main:ShelfBridgeAction'
