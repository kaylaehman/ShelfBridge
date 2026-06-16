"""Shim so ``calibre_plugins.shelf_bridge.*`` imports resolve under plain pytest.

Calibre injects a ``calibre_plugins.<name>`` package at runtime and provides the
``calibre.*`` modules. Outside Calibre we stub the minimum surface the pure-logic
modules import at load time, alias ``calibre_plugins.shelf_bridge`` to the repo
root, and stub ``ruflo`` so the agent tests import cleanly without the vendored
package present.
"""
import sys
import types
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _install_calibre_stubs():
    calibre = _ensure_module("calibre")
    utils = _ensure_module("calibre.utils")
    calibre.utils = utils

    # calibre.utils.config.JSONConfig — dict-like with .defaults fallback.
    config = _ensure_module("calibre.utils.config")

    class JSONConfig(dict):
        def __init__(self, rel_path):
            super().__init__()
            self.defaults = {}

        def get(self, key, default=None):
            if key in self:
                return dict.__getitem__(self, key)
            return self.defaults.get(key, default)

        def __getitem__(self, key):
            if key in self:
                return dict.__getitem__(self, key)
            return self.defaults[key]

    config.JSONConfig = JSONConfig
    utils.config = config

    # calibre.utils.logging.default_log
    logging_mod = _ensure_module("calibre.utils.logging")

    class _Log:
        def info(self, *a, **k):
            pass

        warn = info
        warning = info
        error = info
        debug = info

    logging_mod.default_log = _Log()
    utils.logging = logging_mod

    # calibre.db.cache.Cache (type annotation only)
    db_mod = _ensure_module("calibre.db")
    cache_mod = _ensure_module("calibre.db.cache")

    class Cache:  # pragma: no cover - placeholder type
        pass

    cache_mod.Cache = Cache
    db_mod.cache = cache_mod
    calibre.db = db_mod

    # calibre.customize.InterfaceActionBase (root __init__ imports it)
    customize = _ensure_module("calibre.customize")

    class InterfaceActionBase:  # pragma: no cover
        pass

    customize.InterfaceActionBase = InterfaceActionBase
    calibre.customize = customize


def _install_ruflo_stub():
    if "ruflo" in sys.modules:
        return
    ruflo = _ensure_module("ruflo")

    class ToolError(Exception):
        pass

    def ruflo_tool(namespace=None, **kw):
        def decorator(fn):
            fn._ruflo_namespace = namespace
            return fn
        return decorator

    class RufloConfig:  # pragma: no cover - runtime-only
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class RufloAgent:  # pragma: no cover - runtime-only
        def __init__(self, **kw):
            self.__dict__.update(kw)

        def on_step(self, cb):
            pass

        def run(self, task_input):
            class _R:
                def to_dict(self_inner):
                    return {}
            return _R()

    ruflo.ToolError = ToolError
    ruflo.ruflo_tool = ruflo_tool
    ruflo.RufloConfig = RufloConfig
    ruflo.RufloAgent = RufloAgent


def _install_package_alias():
    cp = _ensure_module("calibre_plugins")
    pkg_name = "calibre_plugins.shelf_bridge"
    if pkg_name in sys.modules:
        return
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(REPO_ROOT)]  # submodules importable from repo root
    sys.modules[pkg_name] = pkg
    cp.shelf_bridge = pkg


_install_calibre_stubs()
_install_ruflo_stub()
_install_package_alias()
