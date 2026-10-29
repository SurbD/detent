"""
DETENT - hold a key to lock Premiere Pro keyframe handles onto a rail (Windows).

    python detent.py                       # hold F9 over a handle and drag
    python detent.py --precision-key f8    # also hold F8 for 10% slow-motion cursor
    python detent.py --axis x              # vertical rail instead
    python detent.py --verbose             # print candidates / distances
    python detent.py --debug-once          # 3s countdown, saves raw.png + debug.png
"""
import argparse
import time

import cv2

import detect
from detect import find_handles, nearest, annotate
from engine import Engine
from hotkeys import KeyRouter
import hotkeys
import winhook


def debug_once(io, radius, snap):
    print(f"detect.py version: {detect.VERSION}\nHover over a handle in Premiere... capturing in 3 seconds")
    time.sleep(3)
    x, y = io.cursor()
    img, left, top = io.grab(x, y, radius)
    cx, cy = x - left, y - top
    hs = find_handles(img)
    pick = nearest(hs, cx, cy, snap)
    cv2.imwrite("raw.png", img)
    cv2.imwrite("debug.png", annotate(img, hs, cx, cy, pick))
    print(f"{len(hs)} candidates, pick={pick}. Saved raw.png + debug.png")


def main():
    ap = argparse.ArgumentParser(description="Detent - rail-lock for Premiere keyframe handles (developer CLI)")
    ap.add_argument("--key", default="capslock", help='hold to rail: "capslock", "f9", "ctrl+q", "shift"')
    ap.add_argument("--precision-key", default="shift", help="hold while railing for slow cursor; 'none' to disable")
    ap.add_argument("--toggle-key", default="ctrl+alt+d", help="pause / resume; 'none' to disable")
    ap.add_argument("--precision", type=float, default=0.1, help="cursor speed factor in precision mode")
    ap.add_argument("--axis", choices=["x", "y"], default="y", help="axis to LOCK (y = horizontal rail)")
    ap.add_argument("--radius", type=int, default=150, help="capture radius in px")
    ap.add_argument("--snap-dist", type=int, default=40, help="detection radius: max px between cursor and handle")
    ap.add_argument("--anywhere", action="store_true", help="react in every app, not just Premiere")
    ap.add_argument("--no-passthrough", action="store_true", help="never give the key back to Premiere when no handle is near")
    ap.add_argument("--sound", action="store_true", help="beep on snap / miss")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--debug-once", action="store_true")
    a = ap.parse_args()

    winhook.make_dpi_aware()
    io = winhook.WinIO()
    if a.debug_once:
        return debug_once(io, a.radius, a.snap_dist)

    eng = Engine(io, axis=a.axis, radius=a.radius, snap_dist=a.snap_dist,
                 precision=a.precision, verbose=a.verbose, sound=a.sound)
    def on_toggle():
        router.set_enabled(not router.enabled)
        print("on" if router.enabled else "paused")

    router = KeyRouter(eng, a.key, a.precision_key, a.toggle_key, focus_check=winhook.premiere_in_foreground,
                       on_toggle=on_toggle, only_in_premiere=not a.anywhere, async_down=winhook.async_down,
                       forward=io.tap_key, passthrough=not a.no_passthrough)
    hooks = winhook.Hooks(router)
    print(f"Detent ready  (detect {detect.VERSION})")
    print(f"  rail: {hotkeys.display(a.key)}   precision: {a.precision_key}   pause/resume: {a.toggle_key}")
    print("  Ctrl+C to quit.")
    try:
        hooks.run()
    except KeyboardInterrupt:
        pass
    finally:
        eng.shutdown()
        print("bye")


if __name__ == "__main__":
    main()
