"""
GLIDEPATH rail prototype
------------------------
Hold the hotkey over a keyframe handle in Premiere's Effect Controls graph:
  1. grabs a screenshot around the cursor
  2. detects the nearest handle and snaps the cursor to it
  3. presses the left mouse button (starts the drag)
  4. locks the Y axis (horizontal rail) until you release the hotkey

Usage:
  python rail.py                 # run, hold F9 to rail
  python rail.py --debug-once    # 3s countdown, saves debug.png showing what was detected
  python rail.py --key f8 --radius 200 --scale 1.5   (scale = Windows display scaling, e.g. 1.5 for 150%)
  python rail.py --axis x        # lock X instead (vertical rail)
"""
import argparse
import threading
import time

import cv2
import mss
import numpy as np
from pynput import keyboard, mouse

import detect
from detect import find_handles, nearest, annotate

mouse_ctl = mouse.Controller()
SNAP_DIST = 40          # px: only snap to a handle this close to the cursor (never jump across the graph)
VERBOSE = False
EXCLUDE_VERTEX = True


def grab(cx, cy, radius):
    """Screenshot a square around (cx, cy) in PHYSICAL pixels. Returns (img_bgr, left, top)."""
    with mss.mss() as sct:
        left, top = int(cx - radius), int(cy - radius)
        shot = sct.grab({"left": left, "top": top, "width": radius * 2, "height": radius * 2})
        return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR), left, top


def locate(radius, scale, exclude_vertex=True):
    """Find nearest handle to the cursor. Returns dict with screen coords (logical, for pynput)."""
    lx, ly = mouse_ctl.position                       # logical coords
    px, py = lx * scale, ly * scale                   # physical pixels for capture
    img, left, top = grab(px, py, radius)
    handles = find_handles(img, exclude_vertex=exclude_vertex)
    pick = nearest(handles, radius, radius, SNAP_DIST * scale)
    return img, handles, pick, left, top


def debug_once(radius, scale):
    print(f"detect.py version: {detect.VERSION}")
    print("Hover over a handle in Premiere... capturing in 3 seconds")
    time.sleep(3)
    img, handles, pick, _, _ = locate(radius, scale, EXCLUDE_VERTEX)
    cv2.imwrite("raw.png", img)   # untouched capture, send this too
    cv2.imwrite("debug.png", annotate(img, handles, radius, radius, pick))
    print(f"{len(handles)} candidates, pick={pick}. Saved debug.png and raw.png")


class Rail:
    def __init__(self, axis, radius, scale):
        self.axis, self.radius, self.scale = axis, radius, scale
        self.active = False
        self.anchor = None

    def start(self):
        if self.active:
            return
        img, handles, pick, left, top = locate(self.radius, self.scale, EXCLUDE_VERTEX)
        if VERBOSE:
            for h in handles:
                d = ((h["x"] - self.radius) ** 2 + (h["y"] - self.radius) ** 2) ** 0.5
                print(f"   candidate {h['kind']:9s} dist={d:5.1f}px  offset=({h['x']-self.radius:+.0f},{h['y']-self.radius:+.0f})")
        if not pick:
            print(f"no handle within {SNAP_DIST}px of the cursor ({len(handles)} candidates in view) - move closer")
            return
        sx = (left + pick["x"]) / self.scale
        sy = (top + pick["y"]) / self.scale
        mouse_ctl.position = (sx, sy)                 # SNAP
        time.sleep(0.02)
        mouse_ctl.press(mouse.Button.left)            # start drag
        self.anchor = (sx, sy)
        self.active = True
        threading.Thread(target=self._lock_loop, daemon=True).start()
        print(f"railing @ {sx:.0f},{sy:.0f}")

    def _lock_loop(self):
        ax, ay = self.anchor
        while self.active:
            x, y = mouse_ctl.position
            if self.axis == "y" and abs(y - ay) > 0:
                mouse_ctl.position = (x, ay)
            elif self.axis == "x" and abs(x - ax) > 0:
                mouse_ctl.position = (ax, y)
            time.sleep(0.001)

    def stop(self):
        if not self.active:
            return
        self.active = False
        time.sleep(0.01)
        mouse_ctl.release(mouse.Button.left)
        print("released")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="f9")
    ap.add_argument("--radius", type=int, default=150)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--axis", choices=["x", "y"], default="y", help="axis to LOCK (y = horizontal rail)")
    ap.add_argument("--snap-dist", type=int, default=40, help="max px between cursor and handle to snap")
    ap.add_argument("--verbose", action="store_true", help="print every candidate + distance on each F9")
    ap.add_argument("--allow-vertex", action="store_true", help="also allow grabbing the keyframe vertex marker")
    ap.add_argument("--debug-once", action="store_true")
    a = ap.parse_args()
    global SNAP_DIST, VERBOSE, EXCLUDE_VERTEX
    SNAP_DIST, VERBOSE, EXCLUDE_VERTEX = a.snap_dist, a.verbose, not a.allow_vertex

    if a.debug_once:
        return debug_once(a.radius, a.scale)

    rail = Rail(a.axis, a.radius, a.scale)
    target = getattr(keyboard.Key, a.key, None) or keyboard.KeyCode.from_char(a.key)

    def on_press(k):
        if k == target:
            rail.start()

    def on_release(k):
        if k == target:
            rail.stop()
        if k == keyboard.Key.esc:
            rail.stop()
            return False

    print(f"detect.py version: {detect.VERSION}")
    print(f"Glidepath rail ready. Hold [{a.key}] over a handle. Esc to quit.")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
        l.join()


if __name__ == "__main__":
    main()
