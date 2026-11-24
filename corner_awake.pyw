"""
corner_awake.pyw
-----------------
Sits in the system tray (Windows) or menu bar (macOS) and prevents the
computer from sleeping whenever the mouse cursor is held in the lower-right
corner of the screen for the configured hold duration (default 1 second).

Windows: SetThreadExecutionState keeps the session alive (works over RDP).
macOS:   a `caffeinate -d -i` child process holds the sleep block.
Audible beeps signal activation / deactivation.

Tray icon:
  Grey  = inactive (normal sleep allowed)
  Green = active   (sleep blocked)

Right-click (Windows) / click (macOS) the icon for Settings (start at login,
hold duration) or Quit.
"""

import json
import math
import os
import plistlib
import struct
import subprocess
import sys
import tempfile
import threading
import time
import ctypes
import wave

IS_WINDOWS = sys.platform == "win32"
IS_MAC     = sys.platform == "darwin"

if IS_WINDOWS:
    import winreg
    import winsound
    from ctypes import wintypes
elif IS_MAC:
    import AppKit
    import Quartz
    from PyObjCTools import AppHelper
else:
    sys.exit("Corner Awake supports Windows and macOS only.")

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

# ── Settings ─────────────────────────────────────────────────────────────────
APP_DIR        = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE  = os.path.join(APP_DIR, "settings.json")
DEFAULTS = {
    "hold_seconds": 1.0,
    "start_with_windows": False,   # also means "start at login" on macOS
}
HOLD_PRESETS = [0.5, 1.0, 2.0, 3.0, 5.0]

# Windows "Run on startup" registry location
RUN_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_REG_NAME = "CornerAwake"

# macOS "start at login" LaunchAgent
LAUNCH_AGENT_LABEL = "com.cornerawake"
LAUNCH_AGENT_PATH  = os.path.expanduser(
    f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist")

# macOS uses pre-rendered copies of the Windows icons so both look identical
# (Segoe UI, used to draw the Windows icon, is not installed on macOS).
ICON_FILES = {
    True:  os.path.join(APP_DIR, "icon_active.png"),
    False: os.path.join(APP_DIR, "icon_inactive.png"),
}


# ─────────────────────────────────────────────────────────────────────────────

def _play_beeps(sequence):
    """Play a list of (freq, ms) beeps without blocking the monitor loop.
    The tones are rendered back to back into one WAV file, so there is no
    gap between them (separate winsound.Beep calls left an audible gap)."""
    try:
        path = _tone_file(sequence)
        if IS_MAC:
            subprocess.Popen(["afplay", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
    except Exception:
        pass


def _write_tone_wav(sequence, path, rate=44100, volume=0.3):
    """Write the (freq, ms) beep sequence as a 16-bit mono sine-wave WAV.
    A 5 ms fade at each tone edge prevents clicks."""
    fade = int(rate * 0.005)
    frames = bytearray()
    for freq, ms in sequence:
        n = int(rate * ms / 1000)
        for i in range(n):
            env = min(1.0, i / fade, (n - 1 - i) / fade)
            sample = volume * env * math.sin(2 * math.pi * freq * i / rate)
            frames += struct.pack("<h", int(32767 * sample))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


_tone_files = {}


def _tone_file(sequence) -> str:
    """Render the beep sequence to a WAV in the temp folder once per run and
    return its path."""
    key = tuple(sequence)
    path = _tone_files.get(key)
    if path is None:
        name = "corner_awake_%s.wav" % "_".join(f"{f}-{ms}" for f, ms in key)
        path = os.path.join(tempfile.gettempdir(), name)
        _write_tone_wav(sequence, path)
        _tone_files[key] = path
    return path


def _make_icon(active: bool) -> Image.Image:
    """Render a 64×64 RGBA tray icon.  Green circle = active, grey = inactive."""
    if IS_MAC:
        try:
            with Image.open(ICON_FILES[active]) as png:
                return png.convert("RGBA")
        except Exception:
            pass  # PNG missing: draw it below with whatever font exists

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    fill = COLOR_ACTIVE if active else COLOR_INACTIVE

    d.ellipse([2, 2, 61, 61], fill=(*fill[:3], 60))
    d.ellipse([6, 6, 57, 57], fill=fill, outline=COLOR_RING, width=2)

    symbol = "⚡" if active else "Zzz"
    # Segoe UI has no ⚡ glyph (it draws an empty box); Segoe UI Symbol does.
    font_file, font_size = ("seguisym.ttf", 36) if active else ("segoeui.ttf", 22)
    try:
        font = ImageFont.truetype(font_file, font_size)
    except Exception:
        font = ImageFont.load_default()

    ox = oy = 0
    try:
        bbox = d.textbbox((0, 0), symbol, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if active:
            ox, oy = bbox[0], bbox[1]   # centre the glyph's ink, not its cell
    except AttributeError:
        tw, th = d.textsize(symbol, font=font)

    x = (size - tw) // 2 - ox
    y = (size - th) // 2 - oy
    d.text((x, y), symbol, fill=COLOR_TEXT, font=font)

    return img


# ── Settings persistence ─────────────────────────────────────────────────────

def _load_settings() -> dict:
    """Load settings.json next to the script.  Create with defaults on first run."""
    if not os.path.exists(SETTINGS_FILE):
        _save_settings(DEFAULTS)
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Backfill any missing keys with defaults
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in data.items() if k in DEFAULTS})
        return merged
    except Exception:
        return dict(DEFAULTS)


def _save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


# ── Start at login (Windows registry / macOS LaunchAgent) ────────────────────

def _startup_command() -> str:
    """Build the command that should run on login: pythonw + this script."""
    pythonw = sys.executable
    # If we're running under python.exe, prefer pythonw.exe so no console flashes
    base = os.path.basename(pythonw).lower()
    if base == "python.exe":
        candidate = os.path.join(os.path.dirname(pythonw), "pythonw.exe")
        if os.path.exists(candidate):
            pythonw = candidate
    script = os.path.abspath(__file__)
    return f'"{pythonw}" "{script}"'


def _launch_agent_plist() -> bytes:
    return plistlib.dumps({
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [sys.executable, os.path.abspath(__file__)],
        "RunAtLoad": True,
        "ProcessType": "Interactive",
    })


def _set_launch_agent(enabled: bool) -> None:
    try:
        if enabled:
            data = _launch_agent_plist()
            # Rewrite only on change: every write re-triggers the macOS
            # "Background Items Added" notification.
            try:
                with open(LAUNCH_AGENT_PATH, "rb") as f:
                    if f.read() == data:
                        return
            except FileNotFoundError:
                pass
            os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
            with open(LAUNCH_AGENT_PATH, "wb") as f:
                f.write(data)
        else:
            try:
                os.remove(LAUNCH_AGENT_PATH)
            except FileNotFoundError:
                pass
    except Exception:
        pass


def _set_run_on_startup(enabled: bool) -> None:
    if IS_MAC:
        _set_launch_agent(enabled)
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, RUN_REG_NAME, 0, winreg.REG_SZ,
                                  _startup_command())
            else:
                try:
                    winreg.DeleteValue(k, RUN_REG_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass


# ── macOS helpers ────────────────────────────────────────────────────────────

_caffeinate_proc = None


def _mac_set_sleep_blocked(blocked: bool) -> None:
    """Hold a `caffeinate -d -i` child while blocked (display + idle sleep,
    the same pair as ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED).
    `-w <our pid>` makes caffeinate exit by itself if this app dies."""
    global _caffeinate_proc
    running = _caffeinate_proc is not None and _caffeinate_proc.poll() is None
    if blocked:
        if not running:
            _caffeinate_proc = subprocess.Popen(
                ["caffeinate", "-d", "-i", "-w", str(os.getpid())],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        if running:
            _caffeinate_proc.terminate()
            try:
                _caffeinate_proc.wait(timeout=2)
            except Exception:
                _caffeinate_proc.kill()
        _caffeinate_proc = None


def _on_ui_thread(fn) -> None:
    """AppKit is not thread-safe: on macOS, icon/menu updates from the monitor
    thread must run on the main thread.  Windows calls straight through."""
    if IS_MAC:
        AppHelper.callAfter(fn)
    else:
        fn()


# ─────────────────────────────────────────────────────────────────────────────

class CornerAwakeApp:

    def __init__(self):
        self._settings   = _load_settings()
        self._active     = False        # sleep currently blocked?
        self._enter_time = None         # when cursor first entered corner
        self._running    = True

        # Reconcile registry with saved preference on startup
        _set_run_on_startup(bool(self._settings.get("start_with_windows")))

        self._icon = pystray.Icon(
            name  = "CornerAwake",
            icon  = _make_icon(False),
            title = self._title_text(),
            menu  = self._build_menu(),
        )

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _status_label(self, _item=None) -> str:
        if self._active:
            return "⚡ Sleep is BLOCKED"
        return f"Corner Awake  –  inactive (hold {self._settings['hold_seconds']:g}s)"

    def _title_text(self) -> str:
        if self._active:
            return "Corner Awake  –  ⚡ ACTIVE – sleep blocked"
        return (f"Corner Awake  –  hold mouse in lower-right corner "
                f"for {self._settings['hold_seconds']:g}s to block sleep")

    def _build_menu(self) -> pystray.Menu:
        # Build hold-duration submenu with radio-style check marks
        hold_items = []
        for preset in HOLD_PRESETS:
            hold_items.append(
                pystray.MenuItem(
                    f"{preset:g} second{'s' if preset != 1 else ''}",
                    self._make_hold_setter(preset),
                    checked=self._make_hold_checker(preset),
                    radio=True,
                )
            )

        settings_menu = pystray.Menu(
            pystray.MenuItem(
                "Start with Windows" if IS_WINDOWS else "Start at login",
                self._toggle_start_with_windows,
                checked=lambda _i: bool(self._settings.get("start_with_windows")),
            ),
            pystray.MenuItem(
                "Hold duration",
                pystray.Menu(*hold_items),
            ),
        )

        return pystray.Menu(
            pystray.MenuItem(self._status_label, lambda *_: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", settings_menu),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

    def _refresh_menu(self):
        try:
            self._icon.title = self._title_text()
            self._icon.update_menu()
        except Exception:
            pass

    # ── Settings actions ──────────────────────────────────────────────────────

    def _toggle_start_with_windows(self, _icon, _item):
        new_val = not bool(self._settings.get("start_with_windows"))
        self._settings["start_with_windows"] = new_val
        _save_settings(self._settings)
        _set_run_on_startup(new_val)
        self._refresh_menu()

    def _make_hold_setter(self, value: float):
        def _set(_icon, _item):
            self._settings["hold_seconds"] = value
            _save_settings(self._settings)
            # Reset any in-progress hold so the new threshold takes effect cleanly
            self._enter_time = None
            self._refresh_menu()
        return _set

    def _make_hold_checker(self, value: float):
        return lambda _i: float(self._settings.get("hold_seconds", 1.0)) == value

    # ── Platform helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _screen_size():
        if IS_MAC:
            # Main display, in points, origin top-left (same as cursor coords)
            b = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
            return b.size.width, b.size.height
        u = ctypes.windll.user32
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)

    @staticmethod
    def _cursor_pos():
        if IS_MAC:
            p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
            return p.x, p.y
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def _set_sleep_blocked(blocked: bool):
        if IS_MAC:
            _mac_set_sleep_blocked(blocked)
            return
        flags = ES_CONTINUOUS
        if blocked:
            flags |= ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)

    # ── Monitor loop ──────────────────────────────────────────────────────────

    def _show_state(self):
        self._icon.icon = _make_icon(self._active)
        self._refresh_menu()

    def _activate(self):
        self._active = True
        self._set_sleep_blocked(True)
        _on_ui_thread(self._show_state)
        _play_beeps(BEEP_ACTIVATE)

    def _deactivate(self):
        self._active = False
        self._set_sleep_blocked(False)
        _on_ui_thread(self._show_state)
        _play_beeps(BEEP_DEACTIVATE)

    def _monitor_loop(self):
        while self._running:
            try:
                sw, sh = self._screen_size()
                cx, cy = self._cursor_pos()

                in_corner = (cx >= sw - CORNER_THRESHOLD and
                             cy >= sh - CORNER_THRESHOLD)

                hold = float(self._settings.get("hold_seconds", 1.0))

                if in_corner:
                    if self._enter_time is None:
                        self._enter_time = time.time()
                    if (not self._active and
                            (time.time() - self._enter_time) >= hold):
                        self._activate()
                    elif self._active:
                        # Re-assert periodically so the OS idle timer resets
                        self._set_sleep_blocked(True)
                else:
                    self._enter_time = None
                    if self._active:
                        self._deactivate()

            except Exception:
                pass  # never let the monitor thread die silently

            time.sleep(0.10)   # 10 checks/sec – snappy hold timing, light on CPU

    # ── Quit ──────────────────────────────────────────────────────────────────

    def _quit(self, icon, _item):
        self._running = False
        self._set_sleep_blocked(False)
        icon.stop()

    def run(self):
        if IS_MAC:
            # Menu-bar-only app: no Dock icon, no app menu
            AppKit.NSApplication.sharedApplication().setActivationPolicy_(
                AppKit.NSApplicationActivationPolicyAccessory)
        self._icon.run()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    CornerAwakeApp().run()
