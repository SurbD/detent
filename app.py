"""
DETENT - tray app (Windows). This is the end-user entry point; detent.py is the developer CLI.

 tray icon  ->  Enabled / Settings / Report a problem / Get help / Quit
 settings   ->  hotkeys, precision speed, snap distance, axis, sound, start with Windows
 free (no activation needed); starts with Windows by default
"""
import ctypes
import logging
import os
import queue
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

import pystray
from PIL import Image, ImageDraw

import config as C
import hotkeys
import report
import support
import winhook
from engine import Engine
from hotkeys import KeyRouter


def setup_logging():
    path = os.path.join(C.data_dir(), "detent.log")
    logging.basicConfig(filename=path, level=logging.INFO, format="%(asctime)s %(message)s")
    if getattr(sys, "frozen", False):            # windowed exe has no console: send prints to the log
        sys.stdout = sys.stderr = open(path, "a", buffering=1, encoding="utf-8")


def already_running():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW(None, False, "Local\\DetentSingleInstance")
    return ctypes.get_last_error() == 183          # ERROR_ALREADY_EXISTS


def make_icon(on=True):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 62, 62), 14, fill=(22, 23, 26, 255))
    col = (91, 156, 255, 255) if on else (120, 124, 136, 255)
    d.line((14, 32, 50, 32), fill=col, width=5)           # the rail
    d.ellipse((38, 24, 54, 40), outline=col, width=5)     # the handle
    d.rectangle((10, 28, 18, 36), fill=(231, 232, 236, 255))   # the keyframe
    return img


class Runtime:
    """Owns engine + router + hook thread so settings changes can restart them cleanly."""

    def __init__(self):
        self.eng = self.router = self.hooks = self.thread = None

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, cfg, on_toggle):
        self.stop()
        io = winhook.WinIO()
        self.eng = Engine(io, axis=cfg.axis, radius=cfg.radius, snap_dist=cfg.snap_dist,
                          precision=cfg.precision, sound=cfg.sound)
        self.router = KeyRouter(self.eng, cfg.key, cfg.precision_key, cfg.toggle_key,
                                focus_check=winhook.premiere_in_foreground, on_toggle=on_toggle,
                                only_in_premiere=cfg.only_in_premiere, async_down=winhook.async_down,
                                forward=io.tap_key, passthrough=cfg.passthrough_on_miss)
        self.hooks = winhook.Hooks(self.router)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            self.hooks.run()
        except Exception:
            logging.exception("hook thread crashed")

    def set_enabled(self, on):
        if self.router:
            self.router.set_enabled(on)

    def suspend(self, on):
        """While the settings window records a hotkey, Detent must not react to (or hide) the keys."""
        if self.router:
            self.router.suspended = on

    def stop(self):
        if self.hooks:
            self.hooks.request_stop()
        if self.thread:
            self.thread.join(timeout=1.5)
        if self.eng:
            self.eng.shutdown()                   # releases the mouse button if a drag was in progress
        self.eng = self.router = self.hooks = self.thread = None


class HotkeyField(ttk.Frame):
    """Keyrails-style hotkey editor: type (Modifier + Key / Single Modifier), keycap, Record button."""
    TK = {"Shift_L": "shift", "Shift_R": "shift", "Control_L": "ctrl", "Control_R": "ctrl",
          "Alt_L": "alt", "Alt_R": "alt", "Super_L": "win", "Super_R": "win", "Win_L": "win", "Win_R": "win",
          "Caps_Lock": "capslock", "Tab": "tab", "space": "space", "grave": "backtick", "Insert": "insert",
          "Delete": "delete", "Home": "home", "End": "end", "Prior": "pageup", "Next": "pagedown",
          "Escape": "escape"}

    def __init__(self, parent, app, title, spec, allow_none=False, allow_single=True, hint=""):
        super().__init__(parent, padding=(0, 6))
        self.app, self.allow_none = app, allow_none
        self.spec = None if spec == "none" else spec
        self.recording = False
        ttk.Label(self, text=title, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        single = bool(self.spec) and hotkeys.parse(self.spec).modifier_only
        self.kind = tk.StringVar(value="single" if single else "combo")
        if allow_single:
            r = ttk.Frame(self)
            r.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
            ttk.Label(r, text="Hotkey type").pack(side="left", padx=(0, 8))
            ttk.Radiobutton(r, text="Modifier + Key", value="combo", variable=self.kind, command=self._kind_changed).pack(side="left")
            ttk.Radiobutton(r, text="Single Modifier", value="single", variable=self.kind, command=self._kind_changed).pack(side="left", padx=8)
        self.cap = ttk.Label(self, width=26, anchor="center", relief="sunken", padding=6)
        self.cap.grid(row=2, column=0, sticky="w", pady=6)
        self.btn = ttk.Button(self, text="Record", command=self.toggle_record)
        self.btn.grid(row=2, column=1, padx=8)
        if allow_none:
            ttk.Button(self, text="Clear", command=self.clear).grid(row=2, column=2)
        self.note = ttk.Label(self, text=hint, foreground="#666", wraplength=420, justify="left")
        self.note.grid(row=3, column=0, columnspan=3, sticky="w")
        self.hint = hint
        self._show()

    def _show(self):
        self.cap.config(text=hotkeys.display(self.spec) if self.spec else "Not set")

    def _kind_changed(self):
        if self.spec and (hotkeys.parse(self.spec).modifier_only != (self.kind.get() == "single")):
            self.spec = None
            self._show()

    def clear(self):
        self.stop_record()
        self.spec = None
        self._show()

    def _keyname(self, e):
        k = e.keysym
        if k in self.TK:
            return self.TK[k]
        if k.upper().startswith("F") and k[1:].isdigit():
            return k.lower()
        if len(k) == 1 and k.isalnum():
            return k.lower()
        return None

    def toggle_record(self):
        if self.recording:
            return self.stop_record()
        self.recording, self.held, self.seen = True, set(), set()
        self.btn.config(text="Press keys…  (Esc = cancel)")
        self.cap.config(text="…")
        self.app.rt.suspend(True)
        top = self.winfo_toplevel()
        top.focus_force()
        self._b1 = top.bind("<KeyPress>", self._down, add="+")
        self._b2 = top.bind("<KeyRelease>", self._up, add="+")

    def stop_record(self):
        if not self.recording:
            return
        self.recording = False
        top = self.winfo_toplevel()
        top.unbind("<KeyPress>", self._b1)
        top.unbind("<KeyRelease>", self._b2)
        self.app.rt.suspend(False)
        self.btn.config(text="Record")
        self.note.config(text=self.hint)
        self._show()

    def _finish(self, spec):
        self.spec = hotkeys.normalize(spec)
        self.stop_record()

    def _down(self, e):
        n = self._keyname(e)
        if n is None:
            return "break"
        if n == "escape":
            self.stop_record()
        elif n in hotkeys.MODS:
            self.held.add(n)
            self.seen.add(n)
        elif self.kind.get() == "single":
            self.note.config(text="Single Modifier needs a modifier key: Shift, Ctrl, Alt or Win.")
        else:
            mods = [m for m in hotkeys.MOD_ORDER if m in self.held]
            self._finish("+".join(mods + [n]))
        return "break"

    def _up(self, e):
        n = self._keyname(e)
        if n in hotkeys.MODS:
            self.held.discard(n)
            if not self.held:
                if self.kind.get() == "single":
                    if len(self.seen) == 1:
                        self._finish(next(iter(self.seen)))
                    else:
                        self.note.config(text="Pick just one modifier.")
                self.seen = set()
        return "break"


class SettingsWindow(tk.Toplevel):
    AXES = {"Horizontal rail (recommended)": "y", "Vertical rail": "x"}

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        c = app.cfg
        self.title("Detent settings")
        self.resizable(False, False)
        outer = ttk.Frame(self, padding=14)
        outer.grid()
        nb = ttk.Notebook(outer)
        nb.grid(sticky="nsew")

        hk = ttk.Frame(nb, padding=12)
        nb.add(hk, text="Hotkeys")
        self.f_rail = HotkeyField(hk, app, "Rail  (hold, then drag)", c.key, allow_none=False,
                                  hint="Hold this over a keyframe handle, then drag.")
        self.f_prec = HotkeyField(hk, app, "Precision  (hold while railing)", c.precision_key, allow_none=True,
                                  hint="Slows the cursor down for fine adjustments.")
        self.f_tog = HotkeyField(hk, app, "Pause / resume Detent", c.toggle_key, allow_none=True, allow_single=False,
                                 hint="Press once to pause, again to turn it back on. Works while paused.")
        for f in (self.f_rail, self.f_prec, self.f_tog):
            f.pack(fill="x")
        row = ttk.Frame(hk)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Precision speed").pack(side="left")
        self.v_prec = tk.IntVar(value=round(c.precision * 100))
        ttk.Scale(row, from_=2, to=50, variable=self.v_prec, length=180,
                  command=lambda v: self.l_prec.config(text=f"{int(float(v))}%")).pack(side="left", padx=10)
        self.l_prec = ttk.Label(row, text=f"{self.v_prec.get()}%", width=5)
        self.l_prec.pack(side="left")

        gen = ttk.Frame(nb, padding=12)
        nb.add(gen, text="General")
        ttk.Label(gen, text="Detection radius", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        r = ttk.Frame(gen)
        r.pack(fill="x")
        self.v_snap = tk.IntVar(value=c.snap_dist)
        ttk.Scale(r, from_=15, to=120, variable=self.v_snap, length=260,
                  command=lambda v: self.l_snap.config(text=f"{int(float(v))} px")).pack(side="left")
        self.l_snap = ttk.Label(r, text=f"{c.snap_dist} px", width=7)
        self.l_snap.pack(side="left", padx=8)
        ttk.Label(gen, text="Area searched around the cursor when the rail key is pressed.",
                  foreground="#666").pack(anchor="w", pady=(0, 12))
        ttk.Label(gen, text="Rail direction", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.v_axis = tk.StringVar(value=next(k for k, v in self.AXES.items() if v == c.axis))
        ttk.Combobox(gen, textvariable=self.v_axis, values=list(self.AXES), state="readonly", width=30).pack(anchor="w", pady=(2, 12))
        self.v_only = tk.BooleanVar(value=c.only_in_premiere)
        self.v_sound = tk.BooleanVar(value=c.sound)
        self.v_notify = tk.BooleanVar(value=c.notify)
        self.v_pass = tk.BooleanVar(value=c.passthrough_on_miss)
        self.v_auto = tk.BooleanVar(value=c.autostart)
        ttk.Checkbutton(gen, text="Only react while Premiere Pro is the active window", variable=self.v_only).pack(anchor="w")
        ttk.Checkbutton(gen, text="No handle near the cursor? Give the key back to Premiere (e.g. Caps Lock still works)",
                        variable=self.v_pass).pack(anchor="w")
        ttk.Checkbutton(gen, text="Beep when it grabs a handle / pauses / resumes", variable=self.v_sound).pack(anchor="w")
        ttk.Checkbutton(gen, text="Show a notification when paused / resumed", variable=self.v_notify).pack(anchor="w")
        ttk.Checkbutton(gen, text="Start Detent with Windows", variable=self.v_auto).pack(anchor="w")

        self.msg = ttk.Label(outer, foreground="#b00020", wraplength=460)
        self.msg.grid(sticky="w", pady=(8, 0))
        b = ttk.Frame(outer)
        b.grid(sticky="ew", pady=(10, 0))
        ttk.Button(b, text="Report a problem…", command=app.report_problem).pack(side="left")
        ttk.Button(b, text="Send feedback…", command=app.open_feedback).pack(side="left", padx=(8, 0))
        ttk.Button(b, text="Cancel", command=self._close).pack(side="right", padx=(8, 0))
        ttk.Button(b, text="Save", command=self.save).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self):
        for f in (self.f_rail, self.f_prec, self.f_tog):
            f.stop_record()
        self.destroy()

    def save(self):
        key, prec, tog = self.f_rail.spec, self.f_prec.spec or "none", self.f_tog.spec or "none"
        if not key:
            self.msg.config(text="Set a rail hotkey (click Record).")
            return
        used = [x for x in (key, prec, tog) if x != "none"]
        if len(used) != len(set(used)):
            self.msg.config(text="Each hotkey must be different.")
            return
        if hotkeys.parse(key).modifier_only:
            if not messagebox.askyesno("Detent", "Shift, Ctrl and Alt are used all the time in Premiere (for example "
                                       "Shift+click to multi-select).\n\nIf you use one as the rail key, Detent may "
                                       "grab a handle when you click near one with it held.\n\nUse it anyway?", parent=self):
                return
        c = C.Config(key=key, precision_key=prec, toggle_key=tog, precision=self.v_prec.get() / 100.0,
                     axis=self.AXES[self.v_axis.get()], radius=self.app.cfg.radius, snap_dist=int(self.v_snap.get()),
                     sound=self.v_sound.get(), autostart=self.v_auto.get(),
                     only_in_premiere=self.v_only.get(), notify=self.v_notify.get(),
                     passthrough_on_miss=self.v_pass.get())
        self._close()
        self.app.update_config(c)


class App:
    def __init__(self):
        self.cfg = C.load()
        try:
            C.apply_installer_choice(self.cfg, C.pop_installer_autostart())
        except Exception:
            logging.exception("installer autostart choice")
        self.rt = Runtime()
        self.paused = False
        self.q = queue.Queue()
        self.win = {}
        self.root = tk.Tk()
        self.root.withdraw()
        self.icon = pystray.Icon("Detent", make_icon(True), "Detent", menu=self._menu())
        self.icon.run_detached()
        self.apply_state()
        self._sync_autostart()
        self.root.after(100, self._poll)

    def _menu(self):
        Item = pystray.MenuItem
        return pystray.Menu(
            Item(f"Detent {C.VERSION}", None, enabled=False),
            Item("Enabled", self._toggle, checked=lambda i: not self.paused, default=True),   # click the tray icon = pause/resume
            Item("Settings…", lambda i: self.q.put("settings")),
            Item("Report a problem…", lambda i: self.q.put("report")),
            Item("Get help / send feedback…", lambda i: self.q.put("feedback")),
            Item("Open log folder", lambda i: os.startfile(C.data_dir())),
            Item("Quit", lambda i: self.q.put("quit")))

    def _toggle(self, icon=None, item=None):
        self.q.put("toggle")

    def _sync_autostart(self):
        """Make the Windows startup entry match the setting (on by default). Also refreshes the
        exe path if Detent was moved or reinstalled somewhere else."""
        try:
            C.set_autostart(self.cfg.autostart)
        except Exception:
            logging.exception("autostart")

    def apply_state(self):
        if not self.rt.running:
            try:
                self.rt.start(self.cfg, on_toggle=lambda: self.q.put("toggle"))
            except Exception:
                logging.exception("could not start")
        if self.rt.running:
            self.rt.set_enabled(not self.paused)          # paused: hooks stay alive only to hear the toggle key
        on = self.rt.running and not self.paused
        self.icon.icon = make_icon(on)
        self.icon.title = f"Detent - {'paused' if self.paused else ('on' if on else 'not running - see log')}"
        self.icon.update_menu()

    def toggle_pause(self):
        self.paused = not self.paused
        self.apply_state()
        text = "Detent paused" if self.paused else "Detent on"
        if self.cfg.notify:
            try:
                self.icon.notify(text, "Detent")
            except Exception:
                pass
        if self.cfg.sound:
            try:
                import winsound
                winsound.Beep(450 if self.paused else 1000, 60)
            except Exception:
                pass

    def report_problem(self):
        last = self.rt.eng.last_grab if self.rt.eng else None
        if not last:
            messagebox.showinfo("Detent", "Nothing to report yet.\n\nHold your rail key over a handle once "
                                "(the one that misbehaves), then choose Report a problem again.")
            return
        try:
            path = report.build(last, self.cfg)
        except Exception as e:
            messagebox.showerror("Detent", f"Couldn’t create the report: {e}")
            return
        import subprocess
        subprocess.Popen(["explorer", "/select,", path])
        msg = ("Report saved and shown in a folder window.\n\nIt holds a small screenshot (about 300 x 300 px "
               "around your cursor), the settings and version info. Nothing was sent anywhere.")
        if support.is_configured():
            if messagebox.askyesno("Detent", msg + "\n\nOpen the Detent issues page now? Describe what happened "
                                   "and drag the .zip file into the comment box.", parent=None):
                self.open_feedback(kind="bug")
        else:
            messagebox.showinfo("Detent", msg)

    def open_feedback(self, kind="feedback"):
        if not support.is_configured():
            messagebox.showinfo("Detent", "The feedback page isn't set up in this build yet.")
            return
        try:
            webbrowser.open(support.new_issue_url(kind))
        except Exception:
            logging.exception("open feedback page")

    def update_config(self, c):
        self.cfg = c
        C.save(c)
        self._sync_autostart()
        self.rt.stop()
        self.apply_state()

    def _show(self, name, cls):
        w = self.win.get(name)
        if w is not None and w.winfo_exists():
            w.lift()
            return
        self.win[name] = cls(self)

    def _poll(self):
        try:
            while True:
                cmd = self.q.get_nowait()
                if cmd == "settings":
                    self._show("settings", SettingsWindow)
                elif cmd == "apply":
                    self.apply_state()
                elif cmd == "toggle":
                    self.toggle_pause()
                elif cmd == "report":
                    self.report_problem()
                elif cmd == "feedback":
                    self.open_feedback()
                elif cmd == "quit":
                    self.rt.stop()
                    self.icon.stop()
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


def main():
    setup_logging()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # real pixels, before any window exists
    except Exception:
        pass
    winhook.make_dpi_aware()
    if already_running():
        return
    App().root.mainloop()


if __name__ == "__main__":
    main()
