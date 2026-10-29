"""'Report a problem': packs the last grab attempt into one small zip the user can send you.
Nothing is uploaded automatically. The zip holds a ~300x300 px screenshot around the cursor,
an annotated copy, the settings, and version info."""
import json
import os
import platform
import time
import zipfile
from dataclasses import asdict

import cv2

import config as C
import detect


def _png(img):
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes() if ok else b""


def build(last, cfg, out_dir=None):
    """Write the report zip and return its path. `last` is Engine.last_grab."""
    if not last:
        raise ValueError("nothing to report yet")
    out_dir = out_dir or C.data_dir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, time.strftime("detent-report-%Y%m%d-%H%M%S.zip"))
    img, cx, cy = last["img"], last["cx"], last["cy"]
    pick = last["pick"]
    lines = [
        f"Detent {C.VERSION}   detect {detect.VERSION}",
        f"Windows: {platform.platform()}   Python {platform.python_version()}",
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last['when']))}",
        f"Result: {last['result']}   (detection radius {last['snap_dist']}px)",
        f"Capture size: {img.shape[1]}x{img.shape[0]}   cursor in capture: ({cx:.0f},{cy:.0f})",
        f"Picked: {pick}",
        "Candidates:",
    ] + [f"  {h['kind']:9s} x={h['x']:.1f} y={h['y']:.1f} penalty={h.get('penalty', 0)}" for h in last["handles"]] + [
        "", "Settings:", json.dumps(asdict(cfg), indent=2)]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("raw.png", _png(img))
        z.writestr("debug.png", _png(detect.annotate(img, last["handles"], cx, cy, pick)))
        z.writestr("info.txt", "\n".join(lines))
    return path
