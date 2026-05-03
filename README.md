# Corner Awake 🟢

A tiny Windows system-tray utility that **prevents your PC from sleeping** whenever
your mouse cursor is dragged into the **lower-right corner** of the screen.
Works over RDP sessions.

---

## Quick Start

1. Make sure **Python 3.9+** is installed (https://python.org) with "Add to PATH" checked.
2. Double-click **`install_and_run.bat`** — it installs the two pip dependencies and launches the app.
3. After the first run you can launch `corner_awake.pyw` directly (no console window).

---

## How it works

| Action | What you hear | Tray icon |
|---|---|---|
| Mouse enters lower-right corner (~80 px zone) | Rising beep (880 → 1100 Hz) | 🟢 Green ⚡ |
| Mouse leaves corner | Falling beep (660 → 440 Hz) | ⚫ Grey Zzz |

Sleep is blocked via the Windows **`SetThreadExecutionState`** API
(`ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED`), which also works inside RDP sessions
because it prevents the *session* from idling out, not just the physical display.

Right-click the tray icon → **Quit** to exit cleanly (sleep settings are restored).

---

## Run on Windows Startup

Place a shortcut to `corner_awake.pyw` in your Startup folder:

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

---

## Requirements

- Windows 10/11 (or Windows Server with RDP)
- Python 3.9+
- `pystray` and `Pillow` (installed automatically by `install_and_run.bat`)
