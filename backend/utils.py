import os
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_asset_path(subpath: str) -> str:
    base = get_base_dir()
    for root in [
        base,
        os.path.join(base, "assets"),
        os.path.join(os.path.dirname(sys.executable), "assets"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "assets"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
    ]:
        p = os.path.normpath(os.path.join(root, subpath))
        if os.path.exists(p):
            return p
    return os.path.normpath(os.path.join(base, "assets", subpath))