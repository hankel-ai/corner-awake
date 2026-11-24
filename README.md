# Corner Awake

A tiny system-tray (Windows) / menu-bar (macOS) utility that **prevents your
computer from sleeping** while your mouse cursor is **held in the lower-right
corner** of the screen for the configured hold duration (default **1 second**).
Works over RDP sessions. One script, `corner_awake.pyw`, runs on both systems.

---

## Quick Start (Windows)

1. Install **Python 3.9+** from <https://python.org> with "Add Python to PATH" checked.
2. Double-click **`install_and_run.bat`** — it installs the two pip dependencies (`pystray`, `Pillow`) and launches the app.
3. After that, use **`run.cmd`** (or `corner_awake.pyw` directly) to start it without re-installing.

A grey circle appears in the system tray. Right-click it for **Settings** or **Quit**.

## Quick Start (macOS)

1. Copy the folder to the Mac. Python 3.9+ is required (`python3 --version`).
2. In Terminal, run `bash install_and_run.sh`. It creates a private `.venv`
   next to the script, installs `pystray` and `Pillow` (plus `pyobjc`, which
   `pystray` pulls in on macOS), and launches the app.
3. After that, run `bash run.sh` to start it. The app keeps running after you
   close Terminal.
4. Turn off the default **Quick Note** hot corner, which also uses the
   lower-right corner: System Settings > Desktop & Dock > Hot Corners.

The same grey circle appears in the menu bar. Click it for **Settings** or **Quit**.

---

## How it works

| Action | What happens |
|---|---|
| Mouse enters lower-right corner (~30 px zone) | Hold timer starts (no sound yet) |
| Mouse leaves before the hold completes | Nothing — timer resets silently |
| Mouse stays in corner for the configured duration | Rising beep (880 → 1100 Hz), icon turns green, sleep is blocked |
| Mouse leaves the corner | Falling beep (660 → 440 Hz), icon turns grey, sleep allowed |

Sleep is blocked via the Windows **`SetThreadExecutionState`** API
(`ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED`). On macOS, the app runs
`caffeinate -d -i -w <app pid>` while active (display + idle sleep blocked).
`caffeinate` exits by itself if the app dies, so sleep is never left blocked.
macOS plays the same beep tones from a generated WAV file through `afplay`.

**RDP support:** Run Corner Awake on the **client** machine (the one you're
sitting at). When you move the client's cursor into its lower-right corner, the
client's sleep/idle timer is blocked — keeping the RDP session alive even if
the remote host has its own idle policy. The API call prevents the *local
session* from idling out, which is what causes RDP disconnects on the client
side.

---

## Settings

Right-click the tray icon → **Settings**.

- **Start with Windows** (macOS: **Start at login**) — on Windows, toggles a `HKCU\...\Run\CornerAwake` registry entry that launches the app at login under `pythonw.exe`. On macOS, writes or removes
  `~/Library/LaunchAgents/com.cornerawake.plist`. macOS shows a
  "Background Items Added" notice the first time.
- **Hold duration** — choose how long the cursor must sit in the corner before activation: 0.5 s, 1 s, 2 s, 3 s, or 5 s.

Settings are stored in **`settings.json`** next to the script and are created
on first run with defaults if the file is missing. The file is gitignored so
each install keeps its own preferences.

```json
{
  "hold_seconds": 1.0,
  "start_with_windows": false
}
```

---

## Files

| File | Purpose |
|---|---|
| `corner_awake.pyw` | The app (runs windowless under `pythonw.exe`) |
| `install_and_run.bat` | First-time setup: installs pip deps + launches |
| `run.cmd` | Launch only — assumes deps already installed |
| `install_and_run.sh` | macOS first-time setup: creates `.venv`, installs deps, launches |
| `run.sh` | macOS launch only |
| `icon_active.png`, `icon_inactive.png` | Tray icons for macOS, rendered from the Windows icon code (Segoe UI is not on macOS) |
| `settings.json` | User preferences (auto-created, gitignored) |

---

## Requirements

- Windows 10/11 (or Windows Server with RDP), or macOS
- Python 3.9+
- `pystray` and `Pillow` (installed by `install_and_run.bat` / `install_and_run.sh`)
