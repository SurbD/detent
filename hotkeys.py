"""Hotkey specs, matching and routing. Pure Python - no OS calls - so it is fully unit-testable.

Spec strings: "capslock", "f9", "ctrl+alt+d" (Modifier + Key) or "shift" (Single Modifier).
"""
from dataclasses import dataclass
from typing import Optional

MODS = {"shift": (0xA0, 0xA1, 0x10), "ctrl": (0xA2, 0xA3, 0x11),
        "alt": (0xA4, 0xA5, 0x12), "win": (0x5B, 0x5C)}
MOD_ORDER = ["ctrl", "alt", "shift", "win"]
ALIASES = {"control": "ctrl", "cmd": "win", "super": "win", "windows": "win", "option": "alt",
           "menu": "alt", "caps": "capslock", "caps_lock": "capslock", "grave": "backtick", "`": "backtick",
           "pgup": "pageup", "prior": "pageup", "pgdn": "pagedown", "next": "pagedown", "del": "delete"}
NAMED = {"capslock": 0x14, "tab": 0x09, "space": 0x20, "backtick": 0xC0, "insert": 0x2D,
         "delete": 0x2E, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22}
PRETTY = {"capslock": "Caps Lock", "backtick": "`", "pageup": "Page Up", "pagedown": "Page Down",
          "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}


def key_vk(name):
    n = ALIASES.get(name, name)
    if n.startswith("f") and n[1:].isdigit() and 1 <= int(n[1:]) <= 24:
        return 0x70 + int(n[1:]) - 1
    if n in NAMED:
        return NAMED[n]
    if len(n) == 1 and n.isalnum():
        return ord(n.upper())
    raise ValueError(f"unknown key '{name}'")


@dataclass(frozen=True)
class Hotkey:
    mods: tuple
    key: str                       # key name, or the modifier name when modifier_only
    vk: Optional[int]
    modifier_only: bool

    @property
    def spec(self):
        return "+".join(list(self.mods) + [self.key])

    @property
    def trigger_vks(self):
        return set(MODS[self.key]) if self.modifier_only else {self.vk}


def parse(spec):
    parts = [ALIASES.get(p.strip().lower(), p.strip().lower()) for p in str(spec).split("+") if p.strip()]
    if not parts:
        raise ValueError("empty hotkey")
    *mods, last = parts
    for m in mods:
        if m not in MODS:
            raise ValueError(f"'{m}' is not a modifier")
    if last in MODS:
        if mods:
            raise ValueError("use Modifier + Key, or a single modifier")
        return Hotkey((), last, None, True)
    mods = tuple(m for m in MOD_ORDER if m in set(mods))
    return Hotkey(mods, last, key_vk(last), False)


def normalize(spec):
    return parse(spec).spec


def display(spec):
    hk = parse(spec)
    return " + ".join(PRETTY.get(p, p.upper()) for p in list(hk.mods) + [hk.key])


class HeldKeys:
    def __init__(self):
        self.s = set()

    def down(self, vk):
        self.s.add(vk)

    def up(self, vk):
        self.s.discard(vk)

    def mod_held(self, name):
        return any(v in self.s for v in MODS[name])

    def heal(self, async_down, current):
        """Forget keys the OS says are no longer down (e.g. released while another window had focus)."""
        if async_down:
            for v in list(self.s):
                if v != current and not async_down(v):
                    self.s.discard(v)


class Matcher:
    """Turns raw key events into 'press' / 'repeat' / 'release' for one hotkey."""

    def __init__(self, hk):
        self.hk = hk
        self.active = False

    def feed(self, vk, down, keys):
        hk = self.hk
        is_trigger = vk in hk.trigger_vks
        if down:
            if self.active:
                return "repeat" if is_trigger else None
            if is_trigger and all(keys.mod_held(m) for m in hk.mods):
                self.active = True
                return "press"
            return None
        if not self.active:
            return None
        if is_trigger and not (hk.modifier_only and keys.mod_held(hk.key)):
            self.active = False
            return "release"
        for m in hk.mods:                                   # a required modifier was let go first
            if vk in MODS[m] and not keys.mod_held(m):
                self.active = False
                return "release"
        return None


class KeyRouter:
    """Decides, for every key event: act on it? swallow it (hide it from the app)?

    Rules
      * only inside Premiere (focus_check) unless only_in_premiere=False
      * the toggle hotkey works even while paused
      * Single-Modifier hotkeys are never swallowed (Shift+click etc. keep working)
      * the precision key, when it is a modifier, is hidden from Premiere only while a rail is running
      * a key-up is swallowed only if its key-down was swallowed - so no key can get 'stuck'
    """

    def __init__(self, engine, rail, precision=None, toggle=None, focus_check=None,
                 on_toggle=None, only_in_premiere=True, async_down=None, forward=None, passthrough=True):
        self.engine = engine
        self.keys = HeldKeys()
        self.rail = Matcher(parse(rail))
        self.prec = Matcher(parse(precision)) if precision and precision != "none" else None
        self.toggle = Matcher(parse(toggle)) if toggle and toggle != "none" else None
        self.focus_check = focus_check or (lambda: True)
        self.on_toggle = on_toggle
        self.only_in_premiere = only_in_premiere
        self.async_down = async_down
        self.enabled = True
        self.suspended = False          # True while the settings window is recording a hotkey
        self.swallowed = set()
        self.forward = forward          # callable(vk): re-sends a key press the app should still get
        if passthrough and forward:
            engine.on_miss = self._on_miss

    def _on_miss(self):
        """The rail key was pressed but there was no handle to grab (or it was a quick tap):
        give the key back to Premiere so e.g. Caps Lock still works. Modifier keys were never hidden."""
        hk = self.rail.hk
        if self.enabled and not hk.modifier_only and self.forward:
            self.forward(hk.vk)

    def set_enabled(self, on):
        if not on:
            if self.rail.active:
                self.rail.active = False
                self.engine.hotkey_up()
            if self.prec and self.prec.active:
                self.prec.active = False
                self.engine.set_precise(False)
        self.enabled = on

    def on_key(self, vk, down):
        """Return True to swallow the event."""
        if down:
            self.keys.heal(self.async_down, vk)
            self.keys.down(vk)
        else:
            self.keys.up(vk)

        if not down:                                        # releases are always processed
            self._dispatch(vk, False)
            if vk in self.swallowed:
                self.swallowed.discard(vk)
                return True
            return False

        gate = (not self.suspended) and (not self.only_in_premiere or self.focus_check())
        if not gate:
            return vk in self.swallowed                     # keep an already-swallowed key's repeats consistent
        swallow = self._dispatch(vk, True)
        if swallow:
            self.swallowed.add(vk)
        return swallow or vk in self.swallowed

    def _dispatch(self, vk, down):
        swallow = False
        if self.toggle:
            r = self.toggle.feed(vk, down, self.keys)
            if r == "press" and self.on_toggle:
                self.on_toggle()
            if down and r in ("press", "repeat") and not self.toggle.hk.modifier_only:
                swallow = True
        if self.enabled:
            r = self.rail.feed(vk, down, self.keys)
            if r == "press":
                self.engine.hotkey_down()
            elif r == "release":
                self.engine.hotkey_up()
            if down and r in ("press", "repeat") and not self.rail.hk.modifier_only:
                swallow = True
            if self.prec:
                r = self.prec.feed(vk, down, self.keys)
                if r == "press":
                    self.engine.set_precise(True)
                elif r == "release":
                    self.engine.set_precise(False)
                if down and r in ("press", "repeat") and (not self.prec.hk.modifier_only or self.engine.active):
                    swallow = True
        return swallow
