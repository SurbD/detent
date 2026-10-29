"""Settings + autostart. Pure Python (winreg only touched inside set_autostart)."""
import json
import os
import sys
from dataclasses import asdict, dataclass, fields

APP = "Detent"
VERSION = "1.3.0"


def data_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    p = os.path.join(base, APP)
    os.makedirs(p, exist_ok=True)
    return p


@dataclass
class Config:
    key: str = "capslock"              # hold to rail.  e.g. "capslock", "f9", "ctrl+q", "shift"
    precision_key: str = "shift"       # hold while railing for slow cursor; "none" = off
    toggle_key: str = "ctrl+alt+d"     # pause / resume Detent; "none" = off
    precision: float = 0.10            # cursor speed factor while precision key is held
    axis: str = "y"                    # axis to LOCK: y = horizontal rail
    radius: int = 150
    snap_dist: int = 40
    sound: bool = False
    autostart: bool = True             # start with Windows (on by default)
    only_in_premiere: bool = True      # keys are only touched while Premiere Pro has the focus
    notify: bool = True                # tray pop-up when paused / resumed
    passthrough_on_miss: bool = True   # no handle near the cursor -> give the rail key back to Premiere


def validate(c: Config) -> Config:
    import hotkeys
    d = Config()

    def clean(v, default, allow_none, allow_modifier_only=True):
        if allow_none and str(v).lower() == "none":
            return "none"
        try:
            hk = hotkeys.parse(v)
            if hk.modifier_only and not allow_modifier_only:
                return default
            return hk.spec
        except Exception:
            return default

    c.key = clean(c.key, d.key, False)
    c.precision_key = clean(c.precision_key, d.precision_key, True)
    c.toggle_key = clean(c.toggle_key, d.toggle_key, True, allow_modifier_only=False)
    if c.precision_key == c.key:
        c.precision_key = "none"
    if c.toggle_key in (c.key, c.precision_key):
        c.toggle_key = "none"
    c.axis = c.axis if c.axis in ("x", "y") else "y"
    c.precision = min(max(float(c.precision), 0.02), 0.5)
    c.snap_dist = min(max(int(c.snap_dist), 15), 120)
    c.radius = min(max(int(c.radius), 100), 300)
    for f in ("sound", "autostart", "only_in_premiere", "notify", "passthrough_on_miss"):
        setattr(c, f, bool(getattr(c, f)))
    return c


def load(path=None) -> Config:
    path = path or os.path.join(data_dir(), "config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        known = {f.name for f in fields(Config)}
        return validate(Config(**{k: v for k, v in raw.items() if k in known}))
    except Exception:
        return Config()


def save(c: Config, path=None):
    path = path or os.path.join(data_dir(), "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(validate(c)), f, indent=2)


def pop_installer_autostart():
    """The installer stores the user's "Start with Windows" tick in HKCU\\Software\\Detent.
    Read it once, delete it, and return True/False (None = no new choice from an installer)."""
    if sys.platform != "win32":
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Detent", 0,
                            winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as k:
            value, _ = winreg.QueryValueEx(k, "StartWithWindows")
            winreg.DeleteValue(k, "StartWithWindows")
            return bool(value)
    except OSError:
        return None


def apply_installer_choice(cfg, choice, path=None):
    """Installer choice wins over the saved setting (it is the newest thing the user told us)."""
    if choice is not None and bool(choice) != cfg.autostart:
        cfg.autostart = bool(choice)
        save(cfg, path)
    return cfg


def set_autostart(enabled: bool):
    """Start Detent when Windows starts (HKCU Run key - no admin needed)."""
    if sys.platform != "win32":
        return
    import winreg
    run = r"Software\Microsoft\Windows\CurrentVersion\Run"
    cmd = f'"{sys.executable}"' if getattr(sys, "frozen", False) else \
        f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(sys.argv[0])}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, APP)
            except FileNotFoundError:
                pass
