"""python tests/test_hotkeys.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hotkeys import parse, display, normalize, KeyRouter, MODS

CAPS, SHIFT, CTRL, ALT, D, Q, F9 = 0x14, 0xA0, 0xA2, 0xA4, ord("D"), ord("Q"), 0x78

class Eng:
    def __init__(self): self.log, self.active, self.on_miss = [], False, None
    def hotkey_down(self): self.log.append("rail_on"); self.active = True
    def hotkey_up(self): self.log.append("rail_off"); self.active = False
    def set_precise(self, on): self.log.append(f"precise_{on}")

def make(rail="capslock", prec="shift", tog="ctrl+alt+d", focus=None, **kw):
    e, t = Eng(), []
    r = KeyRouter(e, rail, prec, tog, focus_check=focus or (lambda: True), on_toggle=lambda: t.append(1), **kw)
    return e, r, t

def test_parse_and_display():
    assert parse("Ctrl+Alt+D").spec == "ctrl+alt+d" and normalize("alt+CTRL+d") == "ctrl+alt+d"
    assert parse("shift").modifier_only and not parse("f9").modifier_only
    assert display("ctrl+alt+d") == "Ctrl + Alt + D" and display("capslock") == "Caps Lock"
    for bad in ("", "ctrl+shift", "banana", "ctrl+banana"):
        try: parse(bad); assert False, bad
        except ValueError: pass

def test_capslock_rail_swallowed_only_in_premiere():
    focus = {"on": True}
    e, r, _ = make(focus=lambda: focus["on"])
    assert r.on_key(CAPS, True) is True and e.log == ["rail_on"]       # swallowed -> no caps toggle in Premiere
    assert r.on_key(CAPS, True) is True and e.log == ["rail_on"]       # auto-repeat swallowed, no double start
    assert r.on_key(CAPS, False) is True and e.log == ["rail_on", "rail_off"]
    focus["on"] = False                                                 # another app: caps works normally
    e.log.clear()
    assert r.on_key(CAPS, True) is False and r.on_key(CAPS, False) is False and e.log == []

def test_focus_lost_while_holding_still_releases():
    focus = {"on": True}
    e, r, _ = make(focus=lambda: focus["on"])
    r.on_key(CAPS, True); focus["on"] = False                           # alt-tab away mid-rail
    assert r.on_key(CAPS, False) is True and e.log[-1] == "rail_off"    # still released; its key-up still hidden

def test_shift_precision_passes_through_unless_railing():
    e, r, _ = make()
    assert r.on_key(SHIFT, True) is False and e.log == ["precise_True"]  # no rail: Shift untouched (shift+click works)
    assert r.on_key(SHIFT, False) is False and e.log[-1] == "precise_False"
    r.on_key(CAPS, True)                                                 # rail running
    assert r.on_key(SHIFT, True) is True                                 # now hidden from Premiere
    assert r.on_key(SHIFT, False) is True                                # and its release too: never stuck
    r.on_key(SHIFT, True); r.on_key(CAPS, False)                         # (rail ended; shift still down...)
    assert r.on_key(SHIFT, False) is True                                # its down WAS swallowed, so up is swallowed

def test_shift_down_before_rail_then_release_not_swallowed():
    e, r, _ = make()
    assert r.on_key(SHIFT, True) is False                                # passed through
    r.on_key(CAPS, True)                                                 # rail starts while shift is held
    assert r.on_key(SHIFT, False) is False                               # up must pass too (Premiere saw the down)

def test_single_modifier_rail_never_swallowed():
    e, r, _ = make(rail="shift", prec="capslock")
    assert r.on_key(SHIFT, True) is False and e.log == ["rail_on"]
    assert r.on_key(SHIFT, False) is False and e.log[-1] == "rail_off"

def test_combo_rail_and_early_modifier_release():
    e, r, _ = make(rail="ctrl+q", prec="none", tog="none")
    assert r.on_key(CTRL, True) is False
    assert r.on_key(Q, True) is True and e.log == ["rail_on"]
    assert r.on_key(CTRL, False) is False and e.log[-1] == "rail_off"    # modifier let go first ends the rail
    assert r.on_key(Q, False) is True and e.log.count("rail_off") == 1   # q-up hidden, no double release
    assert r.on_key(Q, True) is False                                    # q alone does nothing

def test_toggle_pause_and_resume():
    e, r, t = make()
    for k in (CTRL, ALT): r.on_key(k, True)
    assert r.on_key(D, True) is True and t == [1]                        # toggle fired, 'D' hidden
    r.on_key(D, False); r.on_key(CTRL, False); r.on_key(ALT, False)
    r.set_enabled(False)                                                 # app pauses
    e.log.clear()
    assert r.on_key(CAPS, True) is False and e.log == []                 # paused: caps passes straight through
    r.on_key(CAPS, False)
    for k in (CTRL, ALT): r.on_key(k, True)
    r.on_key(D, True); assert t == [1, 1]                                # toggle still alive while paused (quick turn-on)

def test_pausing_mid_rail_releases():
    e, r, _ = make()
    r.on_key(CAPS, True); r.set_enabled(False)
    assert e.log[-1] == "rail_off"

def test_suspended_for_recording():
    e, r, _ = make(only_in_premiere=False)
    r.suspended = True
    assert r.on_key(CAPS, True) is False and e.log == []

def test_stale_modifier_is_healed():
    e, r, _ = make(rail="ctrl+q", prec="none", tog="none")
    r.async_down = lambda vk: False                                      # OS says nothing is physically down
    r.keys.down(CTRL)                                                    # stale: we missed the ctrl-up
    assert r.on_key(Q, True) is False and e.log == []                    # so ctrl+q does NOT fire

def test_miss_gives_the_key_back():
    sent, e = [], Eng()
    r = KeyRouter(e, "capslock", "shift", "none", forward=sent.append)
    assert r.on_key(CAPS, True) is True                  # hidden at first (we don't know yet if there's a handle)
    e.on_miss()                                          # engine: nothing to grab here
    assert sent == [CAPS]                                # ...so Premiere gets a Caps Lock tap after all
    r.on_key(CAPS, False)

def test_miss_combo_and_modifier_and_disabled_and_off():
    sent, e = [], Eng()
    r = KeyRouter(e, "ctrl+q", "none", "none", forward=sent.append)
    r.on_key(CTRL, True); r.on_key(Q, True); e.on_miss(); assert sent == [Q]
    sent.clear(); e2 = Eng(); KeyRouter(e2, "shift", "none", "none", forward=sent.append); e2.on_miss(); assert sent == []   # modifiers were never hidden
    e3 = Eng(); r3 = KeyRouter(e3, "capslock", "none", "none", forward=sent.append); r3.set_enabled(False); e3.on_miss(); assert sent == []
    e4 = Eng(); KeyRouter(e4, "capslock", "none", "none", forward=sent.append, passthrough=False); assert e4.on_miss is None

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
