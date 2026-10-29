"""python tests/test_config.py  - runs anywhere (no Windows, no network)."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C


def tmp(name):
    return os.path.join(tempfile.mkdtemp(), name)

def test_config_roundtrip_and_validation():
    p = tmp("c.json")
    C.save(C.Config(key="f10", precision_key="f10", precision=9, snap_dist=1, axis="z"), p)
    c = C.load(p)
    assert c.key == "f10" and c.precision_key == "none"      # same key twice -> precision off
    assert c.precision == 0.5 and c.snap_dist == 15 and c.axis == "y"
    open(p, "w").write("{broken")
    assert C.load(p) == C.Config()                              # corrupt file -> defaults

def test_autostart_on_by_default_and_can_be_turned_off():
    assert C.Config().autostart is True
    assert C.load(tmp("missing.json")).autostart is True        # first run -> starts with Windows
    p = tmp("c.json"); C.save(C.Config(autostart=False), p)
    assert C.load(p).autostart is False                         # user's choice is kept

def test_no_licensing_left():
    root = os.path.join(os.path.dirname(__file__), "..")
    assert not os.path.exists(os.path.join(root, "licensing.py"))
    src = open(os.path.join(root, "app.py"), encoding="utf-8").read()
    for word in ("licensing", "LicenseWindow", "trial", "lemonsqueezy"):
        assert word.lower() not in src.lower(), word

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
