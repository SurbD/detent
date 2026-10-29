"""UI smoke test for the settings window + hotkey recorder, driven with synthetic key events.
Runs on Windows as-is; on Linux use:  xvfb-run -a python3 tests/test_ui.py   (skips if Tk is unavailable)."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk(); root.withdraw()
except Exception as e:
    print("skip (no Tk/display):", e); sys.exit(0)
import config as C, hotkeys

# app.py needs Windows-only modules at import time, so load just the two UI classes from its source
src = open(os.path.join(os.path.dirname(__file__), "..", "app.py"), encoding="utf-8").read()
code = src[src.index("class HotkeyField"):src.index("class App:")]
asked = []
ns = {"tk": tk, "ttk": ttk, "hotkeys": hotkeys, "C": C,
      "messagebox": types.SimpleNamespace(askyesno=lambda *a, **k: asked.append(a) or True)}
exec(code, ns)
HotkeyField, SettingsWindow = ns["HotkeyField"], ns["SettingsWindow"]

class RT:
    def __init__(self): self.log = []
    def suspend(self, on): self.log.append(on)

class FakeApp:
    def __init__(self): self.root, self.cfg, self.rt, self.saved = root, C.Config(), RT(), None
    def report_problem(self): pass
    def update_config(self, c): self.saved = c

def press(w, *keys):
    for k in keys:
        w.event_generate("<KeyPress>", keysym=k); w.update()

def release(w, *keys):
    for k in keys:
        w.event_generate("<KeyRelease>", keysym=k); w.update()

def field(spec="capslock", **kw):
    app = FakeApp(); top = tk.Toplevel(root)
    f = HotkeyField(top, app, "t", spec, **kw); f.pack(); top.update()
    return app, top, f

def test_record_capslock():
    app, top, f = field("f9")
    f.toggle_record(); assert f.recording and app.rt.log == [True]
    press(top, "Caps_Lock"); assert f.spec == "capslock" and not f.recording and app.rt.log == [True, False]
    assert f.cap.cget("text") == "Caps Lock"

def test_record_combo():
    app, top, f = field("capslock")
    f.toggle_record(); press(top, "Control_L", "Alt_L", "d")
    assert f.spec == "ctrl+alt+d" and f.cap.cget("text") == "Ctrl + Alt + D"

def test_record_function_key_and_escape():
    app, top, f = field("capslock")
    f.toggle_record(); press(top, "F9"); assert f.spec == "f9"
    f.toggle_record(); press(top, "Escape"); assert f.spec == "f9" and not f.recording     # cancel keeps old value

def test_single_modifier():
    app, top, f = field("capslock")
    f.kind.set("single"); f._kind_changed(); assert f.spec is None                       # type switch clears an incompatible key
    f.toggle_record(); press(top, "d")
    assert f.recording and "modifier" in f.note.cget("text").lower()                      # letter rejected in single mode
    press(top, "Shift_L"); release(top, "Shift_L")
    assert f.spec == "shift" and not f.recording

def test_single_modifier_two_keys_rejected():
    app, top, f = field("shift")
    f.toggle_record(); press(top, "Shift_L", "Control_L"); release(top, "Shift_L", "Control_L")
    assert f.recording and "just one" in f.note.cget("text").lower()
    f.stop_record()

def test_settings_window_roundtrip():
    app = FakeApp(); w = SettingsWindow(app); w.update()
    assert w.f_rail.spec == "capslock" and w.f_prec.spec == "shift" and w.f_tog.spec == "ctrl+alt+d"
    w.f_rail.toggle_record(); press(w, "F9")
    w.v_snap.set(55); w.v_prec.set(20); w.v_pass.set(False)
    w.save()
    c = app.saved
    assert c and (c.key, c.precision_key, c.toggle_key, c.snap_dist, c.precision) == ("f9", "shift", "ctrl+alt+d", 55, 0.2)
    assert c.passthrough_on_miss is False
    assert app.rt.log[-1] is False                                                       # recording always un-suspends

def test_settings_rejects_duplicates_and_warns_on_modifier():
    app = FakeApp(); w = SettingsWindow(app); w.update()
    w.f_prec.spec = "capslock"; w.save()
    assert app.saved is None and "different" in w.msg.cget("text")
    w.f_prec.spec = "ctrl"; w.f_rail.spec = "shift"; asked.clear(); w.save()            # modifier-only rail -> warning shown
    assert asked and app.saved.key == "shift"

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
