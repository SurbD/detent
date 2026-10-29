"""Run: python -m pytest -q   (or: python tests/test_detent.py)   - no Windows or Premiere needed."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from railmath import Rail
from engine import Engine


def test_rail_locks_axis_and_precision():
    r = Rail(axis="y", precision=0.1)
    r.start(100, 50)
    assert r.move(110, 57) == (110, 50)             # horizontal rail: y never changes
    assert r.move(120, 40) == (120, 50)
    for _ in range(10):                              # OS reports last + 1px of hand movement each time
        out = r.move(r.last[0] + 1, 99, precise=True)
    assert out == (121, 50)                          # 10 px of hand = ~1 px of cursor
    assert all(r.move(r.last[0] + 3, y)[1] == 50 for y in (0, 200, 77))

def test_rail_vertical():
    r = Rail(axis="x"); r.start(10, 10)
    assert r.move(30, 25) == (10, 25)

def test_rail_bounds():
    r = Rail(axis="y", bounds=(0, 0, 100, 100)); r.start(95, 10)
    assert r.move(200, 10)[0] == 99


class FakeIO:
    def __init__(self, img, cur):
        self.img, self.cur, self.log = img, list(cur), []
    def cursor(self): return tuple(self.cur)
    def grab(self, x, y, r):
        h, w = self.img.shape[:2]
        l, t = max(0, x - r), max(0, y - r)
        return self.img[t:min(h, y + r), l:min(w, x + r)].copy(), l, t
    def set_cursor(self, x, y): self.cur = [x, y]; self.log.append(("set", x, y))
    def mouse_down(self): self.log.append(("down",))
    def mouse_up(self): self.log.append(("up",))
    def beep(self, ok): pass


def synthetic():
    img = np.full((300, 300, 3), 30, np.uint8)
    B = (246, 130, 59)
    def rect(x, y, w, h): img[y:y + h, x:x + w] = B
    rect(145, 158, 11, 11); rect(79, 222, 8, 5); rect(88, 223, 56, 1); rect(145, 222, 8, 5)
    return img


def wait(cond, t=2.0):
    end = time.time() + t
    while time.time() < end and not cond():
        time.sleep(0.01)

def test_engine_end_to_end():
    io = FakeIO(synthetic(), (90, 215))
    e = Engine(io, axis="y", snap_dist=40, precision=0.1)
    e.hotkey_down(); wait(lambda: e.active)
    assert e.active and ("down",) in io.log
    sx, sy = io.cur
    assert abs(sx - 82) <= 2 and abs(sy - 224) <= 2   # snapped to the real head, not the vertex/icon
    t = e.mouse_move(sx + 12, sy + 9)                 # off-axis hand movement
    assert t == (sx + 12, sy)                         # forced onto the rail
    e.set_precise(True)
    t2 = e.mouse_move(t[0] + 10, t[1] + 4)
    assert t2 == (t[0] + 1, sy)
    e.hotkey_up(); wait(lambda: not e.active)
    assert io.log[-1] == ("up",)
    assert e.mouse_move(5, 5) is None                 # rail off -> mouse untouched
    e.shutdown()

def test_engine_far_from_handle_does_nothing():
    io = FakeIO(synthetic(), (260, 40)); misses = []
    e = Engine(io, snap_dist=40); e.on_miss = lambda: misses.append(1)
    e.hotkey_down(); time.sleep(0.4); e.hotkey_up(); time.sleep(0.2)
    assert not e.active and ("down",) not in io.log
    assert misses == [1]                                  # reported as a miss exactly once -> key can be passed on
    e.shutdown()

class SlowIO(FakeIO):
    def grab(self, x, y, r):
        time.sleep(0.15); return super().grab(x, y, r)

def test_quick_tap_near_a_handle_is_a_miss_not_a_rail():
    io = SlowIO(synthetic(), (90, 215)); misses = []
    e = Engine(io, snap_dist=40); e.on_miss = lambda: misses.append(1)
    e.hotkey_down(); e.hotkey_up()                        # released before detection finished
    time.sleep(0.5)
    assert misses == [1] and not e.active and ("down",) not in io.log
    e.shutdown()

def test_hold_near_handle_still_rails_and_is_not_a_miss():
    io = SlowIO(synthetic(), (90, 215)); misses = []
    e = Engine(io, snap_dist=40); e.on_miss = lambda: misses.append(1)
    e.hotkey_down(); wait(lambda: e.active, 3)
    assert e.active and misses == []
    e.hotkey_up(); wait(lambda: not e.active); e.shutdown()

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
