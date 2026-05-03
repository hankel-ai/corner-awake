"""
corner_awake.pyw
-----------------
Sits in the system tray and prevents the PC from sleeping whenever the mouse
cursor is dragged into the lower-right corner of the screen (within ~80 px).

Works over RDP (SetThreadExecutionState keeps the session alive).
Audible beeps signal activation / deactivation.

Tray icon:
  Grey  = inactive (normal sleep allowed)
  Green = active   (sleep blocked)

Right-click → Quit to exit.
"""

import threading
import time
import ctypes
import winsound
from ctypes import wintypes

import pystray
from PIL import Image, ImageDraw, ImageFont

# ── Windows API constants ────────────────────────────────────────────────────
ES_CONTINUOUS        = 0x80000000
ES_SYSTEM_REQUIRED   = 0x00000001
ES_DISPLAY_REQUIRED  = 0x00000002

# Pixel distance from screen edge that counts as "in the corner"
CORNER_THRESHOLD = 30

# ── Icon colours ─────────────────────────────────────────────────────────────
COLOR_INACTIVE = (90,  90,  90)
COLOR_ACTIVE   = (30, 200, 90)
COLOR_RING     = (220, 220, 220)
COLOR_TEXT     = (255, 255, 255)

# ── Sound sequences  (freq_hz, duration_ms) ──────────────────────────────────
BEEP_ACTIVATE   = [(880, 120), (1100, 180)]   # rising – sleep blocked
BEEP_DEACTIVATE = [(660, 120), (440, 180)]    # falling – sleep allowed


# ─────────────────────────────────────────────────────────────────────────────

def _play_beeps(sequence):
    """Play a list of (freq, ms) beeps in a daemon thread so the monitor loop
    is not blocked."""
    def _run():
        for freq, ms in sequence:
            try:
                winsound.Beep(freq, ms)
            except Exception:
                pass
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _make_icon(active: bool) -> Image.Image:
    """Render a 64×64 RGBA tray icon.  Green circle = active, grey = inactive.
    Draws a small 'Zzz' when inactive and a lightning bolt symbol when active."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    fill = COLOR_ACTIVE if active else COLOR_INACTIVE

    # Outer glow ring
    d.ellipse([2, 2, 61, 61], fill=(*fill[:3], 60))
    # Main circle
    d.ellipse([6, 6, 57, 57], fill=fill, outline=COLOR_RING, width=2)

    # Symbol text
    try:
        font = ImageFont.truetype("segoeui.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    symbol = "⚡" if active else "Zzz"
    # centre the text
    try:
        bbox = d.textbbox((0, 0), symbol, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        tw, th = d.textsize(symbol, font=font)  # older Pillow

    x = (size - tw) // 2
    y = (size - th) // 2
    d.text((x, y), symbol, fill=COLOR_TEXT, font=font)

    return img


# ─────────────────────────────────────────────────────────────────────────────

class CornerAwakeApp:

    def __init__(self):
        self._in_corner = False
        self._running   = True

        menu = pystray.Menu(
            pystray.MenuItem("Corner Awake  –  inactive", lambda *_: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon(
            name    = "CornerAwake",
            icon    = _make_icon(False),
            title   = "Corner Awake  –  move mouse to lower-right corner to block sleep",
            menu    = menu,
        )

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()

    # ── Windows helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _screen_size():
        u = ctypes.windll.user32
        # SM_CXSCREEN / SM_CYSCREEN – reflects the RDP session resolution
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)

    @staticmethod
    def _cursor_pos():
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def _set_sleep_blocked(blocked: bool):
        flags = ES_CONTINUOUS
        if blocked:
            flags |= ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)

    # ── Monitor loop ──────────────────────────────────────────────────────────

    def _monitor_loop(self):
        while self._running:
            try:
                sw, sh = self._screen_size()
                cx, cy = self._cursor_pos()

                in_corner = (cx >= sw - CORNER_THRESHOLD and
                             cy >= sh - CORNER_THRESHOLD)

                if in_corner and not self._in_corner:
                    self._in_corner = True
                    self._set_sleep_blocked(True)
                    self._icon.icon  = _make_icon(True)
                    self._icon.title = "Corner Awake  –  ⚡ ACTIVE – sleep blocked"
                    # Update the first (label) menu item text
                    self._icon.menu  = pystray.Menu(
                        pystray.MenuItem("⚡ Sleep is BLOCKED", lambda *_: None, enabled=False),
                        pystray.Menu.SEPARATOR,
                        pystray.MenuItem("Quit", self._quit),
                    )
                    _play_beeps(BEEP_ACTIVATE)

                elif not in_corner and self._in_corner:
                    self._in_corner = False
                    self._set_sleep_blocked(False)
                    self._icon.icon  = _make_icon(False)
                    self._icon.title = "Corner Awake  –  inactive"
                    self._icon.menu  = pystray.Menu(
                        pystray.MenuItem("Corner Awake  –  inactive", lambda *_: None, enabled=False),
                        pystray.Menu.SEPARATOR,
                        pystray.MenuItem("Quit", self._quit),
                    )
                    _play_beeps(BEEP_DEACTIVATE)

                # Re-assert every 25 s while active so the OS timer resets
                elif in_corner and self._in_corner:
                    self._set_sleep_blocked(True)

            except Exception:
                pass  # never let the monitor thread die silently

            time.sleep(0.15)   # ~6 checks per second – light on CPU

    # ── Quit ──────────────────────────────────────────────────────────────────

    def _quit(self, icon, _item):
        self._running = False
        self._set_sleep_blocked(False)
        icon.stop()

    def run(self):
        self._icon.run()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    CornerAwakeApp().run()
