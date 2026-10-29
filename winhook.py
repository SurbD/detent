"""Windows low-level hooks + input injection (ctypes only, no pynput).

* WH_KEYBOARD_LL : sees the hotkey, swallows it so Premiere never gets F9/F8
* WH_MOUSE_LL    : while railing, swallows the REAL mouse move and puts the cursor exactly where the
                   rail says, so Premiere never sees an off-axis position.
"""
import ctypes
import sys
import time
from ctypes import wintypes as wt

if sys.platform != "win32":
    raise ImportError("winhook is Windows-only")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HHOOK = ctypes.c_void_p
ULONG_PTR = ctypes.c_size_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
HC_ACTION = 0
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP, WM_MOUSEMOVE = 0x0100, 0x0101, 0x0104, 0x0105, 0x0200
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x0001, 0x0002
EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E}
PM_REMOVE, QS_ALLINPUT = 1, 0x04FF
MAGIC = 0xD37E57          # tags our own injected input so our hooks ignore it


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wt.POINT), ("mouseData", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = HHOOK
user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [HHOOK]
user32.UnhookWindowsHookEx.restype = wt.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.PeekMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT]
user32.MsgWaitForMultipleObjects.argtypes = [wt.DWORD, ctypes.c_void_p, wt.BOOL, wt.DWORD, wt.DWORD]
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HINSTANCE


user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]
user32.MapVirtualKeyW.restype = wt.UINT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
kernel32.CloseHandle.argtypes = [wt.HANDLE]
_fg_cache = {"t": 0.0, "v": True, "pid": 0, "name": ""}


def async_down(vk):
    return bool(user32.GetAsyncKeyState(int(vk)) & 0x8000)


def foreground_exe():
    """Lower-case file name of the program that owns the focused window ('' if unknown)."""
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    if not pid.value:
        return ""
    if pid.value == _fg_cache["pid"]:
        return _fg_cache["name"]
    h = kernel32.OpenProcess(0x1000, False, pid.value)       # PROCESS_QUERY_LIMITED_INFORMATION
    name = ""
    if h:
        buf = ctypes.create_unicode_buffer(520)
        size = wt.DWORD(520)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            name = buf.value.replace("/", "\\").split("\\")[-1].lower()
        kernel32.CloseHandle(h)
    _fg_cache.update(pid=pid.value, name=name)
    return name


def premiere_in_foreground():
    """True when Premiere Pro has the focus. Cached ~150 ms so key hooks stay fast. Fails OPEN (True)."""
    now = time.monotonic()
    if now - _fg_cache["t"] < 0.15:
        return _fg_cache["v"]
    try:
        name = foreground_exe()
        v = True if not name else ("premiere" in name)
    except Exception:
        v = True
    _fg_cache.update(t=now, v=v)
    return v


def make_dpi_aware():
    """Work in real pixels so screen capture and cursor coordinates always agree (no --scale needed)."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))   # per-monitor v2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            user32.SetProcessDPIAware()


def parse_vk(name):                       # kept for old callers
    from hotkeys import key_vk
    return key_vk(name)


class WinIO:
    """The `io` object the Engine talks to."""

    def cursor(self):
        p = wt.POINT()
        user32.GetCursorPos(ctypes.byref(p))
        return p.x, p.y

    def set_cursor(self, x, y):
        user32.SetCursorPos(int(x), int(y))

    def _click(self, flag):
        inp = INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(0, 0, 0, flag, 0, MAGIC)))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def tap_key(self, vk):
        """Press + release a key as if the user had typed it. Tagged MAGIC so our own hook ignores it."""
        ext = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else 0
        scan = user32.MapVirtualKeyW(vk, 0)
        down = INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(vk, scan, ext, 0, MAGIC)))
        up = INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(vk, scan, ext | KEYEVENTF_KEYUP, 0, MAGIC)))
        for i in (down, up):
            user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))

    def mouse_down(self):
        self._click(MOUSEEVENTF_LEFTDOWN)

    def mouse_up(self):
        self._click(MOUSEEVENTF_LEFTUP)

    def grab(self, x, y, r):
        """BGR screenshot of the area around (x, y), clamped to the virtual screen. -> (img, left, top)"""
        import cv2
        import mss
        import numpy as np
        with mss.mss() as sct:
            m = sct.monitors[0]
            left = max(m["left"], x - r)
            top = max(m["top"], y - r)
            right = min(m["left"] + m["width"], x + r)
            bottom = min(m["top"] + m["height"], y + r)
            shot = sct.grab({"left": left, "top": top, "width": right - left, "height": bottom - top})
            return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR), left, top

    def beep(self, ok):
        import winsound
        winsound.Beep(1200 if ok else 300, 35)


class Hooks:
    """Installs the two low-level hooks and pumps messages. All decisions live in `router` (hotkeys.KeyRouter)."""

    def __init__(self, router):
        self.router = router
        self._mh = self._kh = None
        self._running = False

        def mouse_proc(nCode, wParam, lParam):
            try:
                if nCode == HC_ACTION and wParam == WM_MOUSEMOVE:
                    ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    if ms.dwExtraInfo != MAGIC:
                        target = router.engine.mouse_move(ms.pt.x, ms.pt.y)
                        if target is not None:
                            user32.SetCursorPos(target[0], target[1])
                            return 1                      # swallow the real, possibly off-axis move
            except Exception:
                pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        def key_proc(nCode, wParam, lParam):
            try:
                if nCode == HC_ACTION:
                    kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    if kb.dwExtraInfo != MAGIC:
                        down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                        if router.on_key(kb.vkCode, down):
                            return 1                      # hidden from the app
            except Exception:
                pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._mp, self._kp = HOOKPROC(mouse_proc), HOOKPROC(key_proc)   # keep references alive!

    def run(self):
        hmod = kernel32.GetModuleHandleW(None)
        self._mh = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mp, hmod, 0)
        self._kh = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kp, hmod, 0)
        if not self._mh or not self._kh:
            raise OSError(f"could not install hooks (error {ctypes.get_last_error()})")
        self._running = True
        msg = wt.MSG()
        try:
            while self._running:
                user32.MsgWaitForMultipleObjects(0, None, False, 100, QS_ALLINPUT)
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._unhook()

    def request_stop(self):
        """Safe from any thread: the hook thread notices within ~100 ms and unhooks itself."""
        self._running = False

    def _unhook(self):
        self._running = False
        for h in (self._mh, self._kh):
            if h:
                user32.UnhookWindowsHookEx(h)
        self._mh = self._kh = None
