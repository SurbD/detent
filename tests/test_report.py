"""python tests/test_report.py"""
import os, sys, tempfile, zipfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C, report

def test_report_zip_contents():
    img = np.full((120, 160, 3), 30, np.uint8)
    last = {"img": img, "cx": 80, "cy": 60, "handles": [{"x": 70.0, "y": 60.0, "kind": "stem-end", "penalty": 0}],
            "pick": {"x": 70.0, "y": 60.0, "kind": "stem-end", "penalty": 0}, "snap_dist": 40,
            "when": 0, "result": "snapped"}
    path = report.build(last, C.Config(), tempfile.mkdtemp())
    with zipfile.ZipFile(path) as z:
        assert sorted(z.namelist()) == ["debug.png", "info.txt", "raw.png"]
        info = z.read("info.txt").decode()
        assert "Result: snapped" in info and "detect v" in info and "capslock" in info
        assert z.read("raw.png")[:4] == b"\x89PNG" and "license_key" not in info.lower()

def test_nothing_to_report():
    try: report.build(None, C.Config(), tempfile.mkdtemp()); assert False
    except ValueError: pass

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
