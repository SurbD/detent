"""Pure rail maths (no OS calls) so it can be unit-tested anywhere."""


class Rail:
    """Axis-locked, optionally slowed, cursor motion.

    axis="y": lock Y  -> horizontal rail (default; ease-in/out handles)
    axis="x": lock X  -> vertical rail

    The OS tells us where it *would* put the cursor (px, py). Because we always park the real
    cursor at `last`, (px - last) is the user's true hand movement this event.
    """

    def __init__(self, axis="y", precision=0.1, bounds=None):
        self.axis = axis
        self.precision = precision
        self.bounds = bounds              # (left, top, right, bottom) in px, or None
        self.ax = self.ay = 0
        self.vx = self.vy = 0.0
        self.last = (0, 0)

    def start(self, x, y):
        self.ax, self.ay = int(x), int(y)
        self.vx, self.vy = float(x), float(y)
        self.last = (int(x), int(y))

    def move(self, px, py, precise=False):
        f = self.precision if precise else 1.0
        dx, dy = px - self.last[0], py - self.last[1]
        if self.axis == "y":
            self.vx += dx * f
            self.vy = float(self.ay)
        else:
            self.vy += dy * f
            self.vx = float(self.ax)
        if self.bounds:
            l, t, r, b = self.bounds
            self.vx = min(max(self.vx, l), r - 1)
            self.vy = min(max(self.vy, t), b - 1)
        nx, ny = int(round(self.vx)), int(round(self.vy))
        self.last = (nx, ny)
        return nx, ny
