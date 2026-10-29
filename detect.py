"""Handle detection for Premiere's Effect Controls graph (blue handle glyphs).

Premiere draws, for a selected keyframe:
   [keyframe icon (hourglass) in the icon row]   <- x marks the keyframe's time
   ... handle head ---- thin stem ---- keyframe vertex marker (same x as the icon)
We want the HEAD, never the vertex (dragging the vertex moves the keyframe itself).
So: heads = small blobs attached to a stem end, minus anything lined up with a keyframe icon.
"""
import cv2
import numpy as np

VERSION = "v7-capsule-playhead"   # printed by rail.py so we can confirm which file is running
HSV_LO = (100, 110, 110)
HSV_HI = (125, 255, 255)
GRAY_LO = (0, 0, 170)      # unselected keyframe icons are white/gray, not blue
GRAY_HI = (180, 50, 255)
ICON_X_TOL = 4
MIN_STEM = 14       # px: shortest handle line we accept (short eases at low zoom are ~15px)      # px: a stem end this close (in x) to a keyframe icon is the vertex, not a handle


def _blobs(mask):
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
    return [(stats[i], cents[i]) for i in range(1, n)]


def _hourglass_icons(mask):
    """Hourglass signature: wide top row, wide bottom row, pinched middle."""
    out = []
    for st, c in _blobs(mask):
        x, y, w, h, area = [int(v) for v in st]
        if not (8 <= w <= 16 and 8 <= h <= 16):
            continue
        rows = (mask[y:y + h, x:x + w] > 0).sum(1)
        q = max(2, h // 4)
        top, bot = rows[:q].max(), rows[-q:].max()
        mid = rows[h // 2 - 1:h // 2 + 2].min()
        if top >= 0.75 * w and bot >= 0.75 * w and mid <= 0.45 * w:
            out.append((float(c[0]), float(c[1])))
    return out


def _refine_head(mask, ex, ey, side):
    """Centre of the head glyph just beyond a stem end: centroid of blue pixels around it,
    ignoring the stem row and any tall vertical line (playhead)."""
    H, W = mask.shape
    cx0 = int(round(ex + side * 3))
    x0, x1 = max(0, cx0 - 5), min(W, cx0 + 6)
    y0, y1 = max(0, int(round(ey)) - 5), min(H, int(round(ey)) + 6)
    sub = (mask[y0:y1, x0:x1] > 0).copy()
    sub[int(round(ey)) - y0, :] = False
    sub[:, sub.sum(0) >= 9] = False
    ys, xs = np.nonzero(sub)
    if len(xs) < 6:
        return None
    px = x0 + xs.mean()
    py = y0 + ys.mean()
    return px, (py if abs(py - ey) <= 2 else ey)


def find_handles(img_bgr, hsv_lo=HSV_LO, hsv_hi=HSV_HI, exclude_vertex=True):
    """Return list of dicts {x, y, kind, penalty}: draggable handle heads (image pixel coords).
    `penalty` (px) is added to the distance in nearest() for ends that might be the keyframe vertex."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(hsv_lo), np.array(hsv_hi))
    H, W = mask.shape

    # 1) LONG STEMS: horizontal runs only (cuts them loose from the playhead / other vertical lines)
    hmask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((1, 9), np.uint8))
    stems, stem_boxes = [], []          # stems: list of (ends, is_capsule)
    for st, c in _blobs(hmask):
        x, y, w, h, area = [int(v) for v in st]
        if w >= MIN_STEM and h <= 12:
            ys, xs = np.where(hmask[y:y + h, x:x + w] > 0)
            ends = []
            for ex in (xs.min(), xs.max()):
                col = ys[np.abs(xs - ex) <= 2]
                ends.append((float(x + ex), float(y + col.mean()), -1 if ex == xs.min() else 1))
            stems.append((ends, False))
            stem_boxes.append((x, y, x + w, y + h))

    # 2) ICONS, small head blobs, and SHORT "capsules" (head+stem+vertex fused, ~10-40px long)
    smalls, icons, capsules = [], [], []
    for st, c in _blobs(mask):
        x, y, w, h, area = [int(v) for v in st]
        if 9 <= h <= 16 and w >= 4 and area >= 25 and w <= 16:          # hourglass, even if cut off
            icons.append((x + w / 2.0, w / 2.0))
        elif 3 <= w <= 11 and 3 <= h <= 11 and area >= 8:
            smalls.append((float(c[0]), float(c[1])))
        if 10 <= w <= 40 and 3 <= h <= 6 and area >= 12:                 # short handle: ring --- bracket
            if not any(x < bx1 and x + w > bx0 and y < by1 and y + h > by0 for bx0, by0, bx1, by1 in stem_boxes):
                cy = y + h / 2.0
                capsules.append(([(x + 2.5, cy, -1), (x + w - 2.5, cy, 1)], True))
    stems += capsules

    gray_mask = cv2.inRange(hsv, np.array(GRAY_LO), np.array(GRAY_HI))
    for cx, _cy in _hourglass_icons(gray_mask):                         # white hourglass = unselected key
        icons.append((cx, 5.0))

    playheads = [x for x in range(W) if mask[:, x].sum() / 255.0 >= 0.6 * H]

    def on_playhead(px):
        return any(abs(px - p) <= 2 for p in playheads)

    def is_vertex(px):
        return any(abs(px - cx) <= max(ICON_X_TOL, hw + 1) for cx, hw in icons)

    found = []
    for ends, is_capsule in stems:
        strong = [is_vertex(e[0]) for e in ends]
        if all(strong):
            strong = [False, False]
        ph = [on_playhead(e[0]) for e in ends]
        for i, (ex, ey, side) in enumerate(ends):
            kind, penalty = "stem-end", 0
            if strong[i]:                                   # lined up with a keyframe icon = the keyframe itself
                if exclude_vertex:
                    continue
                kind = "vertex"
            elif not any(strong) and ph[i] and not all(ph):
                penalty = 14                                # probably hidden under the playhead = vertex, but unsure
            if is_capsule or penalty:
                px, py = ex, ey                             # use the stem tip as-is (no glyph to measure)
                if penalty and playheads:                   # head ring hidden under the playhead: centre on it
                    px = min(playheads, key=lambda p: abs(p - ex))
            else:
                best = None
                for sx, sy in smalls:
                    if abs(sy - ey) <= 4 and 0 <= (sx - ex) * side <= 12:
                        dd = abs(sx - ex)
                        if best is None or dd < best[0]:
                            best = (dd, sx, sy)
                if best:
                    px, py, kind = best[1], best[2], ("head" if kind == "stem-end" else kind)
                else:
                    r = _refine_head(mask, ex, ey, side)
                    if r is None:
                        continue                            # no head glyph here (e.g. text underline)
                    px, py = r
            if px <= 2 or px >= W - 3 or py <= 2 or py >= H - 3:
                continue                                    # cut off by the capture edge
            found.append({"x": px, "y": py, "kind": kind, "penalty": penalty})
    return found


def nearest(handles, cx, cy, max_dist):
    best, best_d = None, max_dist
    for h in handles:
        d = ((h["x"] - cx) ** 2 + (h["y"] - cy) ** 2) ** 0.5
        d_adj = d - (4 if h["kind"] == "head" else 0) + h.get("penalty", 0)
        if d_adj < best_d:
            best, best_d = h, d_adj
    return best


def annotate(img_bgr, handles, cx=None, cy=None, pick=None):
    out = img_bgr.copy()
    for h in handles:
        col = {"head": (0, 200, 0), "vertex": (255, 0, 255)}.get(h["kind"], (0, 165, 255))
        cv2.circle(out, (int(h["x"]), int(h["y"])), 9, col, 1)
    if pick:
        cv2.circle(out, (int(pick["x"]), int(pick["y"])), 13, (0, 0, 255), 2)
    if cx is not None:
        cv2.drawMarker(out, (int(cx), int(cy)), (255, 0, 255), cv2.MARKER_CROSS, 14, 1)
    return out
