"""ShelfBridge plugin entry point & metadata."""
import sys
import pathlib

# When the plugin runs from an unzipped checkout (e.g. tests), a sibling
# ``vendor/`` is a real directory we can add to sys.path directly. When it runs
# as an installed Calibre zip, that path is virtual — so :meth:`initialize`
# extracts the vendored deps to a cache dir instead.
_vendor = pathlib.Path(__file__).parent / "vendor"
if _vendor.is_dir() and str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))

from calibre.customize import InterfaceActionBase


def _extract_vendor_from_zip(zip_path):
    """Extract bundled vendor/ from the plugin zip to a cache dir, add to path.

    Calibre loads plugins from the zip in memory, so an in-zip ``vendor/`` can't
    be placed on ``sys.path`` directly. We extract it once to a stable temp dir.
    Returns the cache dir, or None if there is nothing to extract.
    """
    import os
    import zipfile
    import tempfile

    cache = os.path.join(tempfile.gettempdir(), "shelf_bridge_vendor")
    try:
        with zipfile.ZipFile(zip_path) as z:
            members = [n for n in z.namelist()
                       if n.startswith("vendor/") and not n.endswith("/")]
            if not members:
                return None
            for m in members:
                target = os.path.join(cache, *m.split("/")[1:])  # strip 'vendor/'
                os.makedirs(os.path.dirname(target), exist_ok=True)
                if not os.path.exists(target):
                    with z.open(m) as src, open(target, "wb") as dst:
                        dst.write(src.read())
    except Exception:
        return None
    if cache not in sys.path:
        sys.path.insert(0, cache)
    return cache


class ShelfBridgePlugin(InterfaceActionBase):
    name = 'ShelfBridge'
    description = 'Export your Calibre library to reading-tracker services'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'Kayla Ehman'
    version = (0, 1, 1)
    minimum_calibre_version = (6, 0, 0)
    actual_plugin = 'calibre_plugins.shelf_bridge.main:ShelfBridgeAction'

    def initialize(self):
        # Make vendored deps (keyring, certifi, httpx …) importable when running
        # as an installed zip. Best-effort: the credential store falls back to
        # plain prefs if extraction fails.
        if getattr(self, "plugin_path", None):
            _extract_vendor_from_zip(self.plugin_path)
        try:
            super().initialize()
        except Exception:
            pass
