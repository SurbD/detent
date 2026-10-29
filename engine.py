"""Detent engine: hotkey -> find handle -> snap -> press -> rail -> release.
OS access goes through an `io` object, so the whole flow is testable without Windows."""
import queue
import threading
import time

from detect import find_handles, nearest
from railmath import Rail


class Engine:
    def __init__(self, io, axis="y", radius=150, snap_dist=40, precision=0.1,
                 verbose=False, sound=False):
        self.io, self.radius, self.snap_dist = io, radius, snap_dist
        self.verbose, self.sound = verbose, sound
        self.rail = Rail(axis=axis, precision=precision)
        self.key_down = False
        self.precise = False
        self.active = False
        self.last_grab = None            # most recent attempt, for 'Report a problem'
        self.on_miss = None              # called when a key press did NOT turn into a rail (router passes the key on)
        self._q = queue.Queue()
        self._stop = False
        self._t = threading.Thread(target=self._worker, daemon=True)
        self._t.start()

    # ---- called from the hook thread: must be FAST, never block ----
    def hotkey_down(self):
        if self.key_down:
            return                      # key auto-repeat
        self.key_down = True
        self._q.put("down")

    def hotkey_up(self):
        self.key_down = False
        self._q.put("up")

    def set_precise(self, on):
        self.precise = bool(on)

    def mouse_move(self, px, py):
        """Return (x, y) to force the cursor there and swallow the real event, or None to let it through."""
        if not self.active:
            return None
        return self.rail.move(px, py, self.precise)

    # ---- worker thread: slow stuff lives here ----
    def _worker(self):
        while not self._stop:
            try:
                cmd = self._q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if cmd == "down":
                    self._begin()
                elif cmd == "up":
                    self._end()
            except Exception as e:      # never let the worker die
                print("detent error:", e)
                self._end()

    def _begin(self):
        x, y = self.io.cursor()
        img, left, top = self.io.grab(x, y, self.radius)
        handles = find_handles(img)
        cx, cy = x - left, y - top
        pick = nearest(handles, cx, cy, self.snap_dist)
        if self.verbose:
            for h in handles:
                d = ((h["x"] - cx) ** 2 + (h["y"] - cy) ** 2) ** 0.5
                print(f"   candidate {h['kind']:9s} dist={d:5.1f}px penalty={h.get('penalty', 0)}")
        self.last_grab = {"img": img, "cx": cx, "cy": cy, "handles": handles, "pick": pick,
                          "snap_dist": self.snap_dist, "when": time.time(), "result": "no handle nearby"}
        if not pick or not self.key_down:           # no handle near the cursor, or it was only a quick tap
            if not pick:
                print(f"no handle within {self.snap_dist}px ({len(handles)} in view)")
                if self.sound:
                    self.io.beep(False)
            if self.on_miss:
                self.on_miss()
            return
        tx, ty = int(round(left + pick["x"])), int(round(top + pick["y"]))
        self.io.set_cursor(tx, ty)
        time.sleep(0.02)
        self.rail.start(tx, ty)
        self.last_grab["result"] = "snapped"
        self.io.mouse_down()
        self.active = True
        if self.sound:
            self.io.beep(True)
        if self.verbose:
            print(f"railing @ {tx},{ty}")
        if not self.key_down:                       # released during setup
            self._end()

    def _end(self):
        if self.active:
            self.active = False
            time.sleep(0.005)
            self.io.mouse_up()
            if self.verbose:
                print("released")

    def shutdown(self):
        self._stop = True
        self._end()
