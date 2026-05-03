# Corner Awake

A tiny Windows system-tray utility that **prevents your PC from sleeping** while
your mouse cursor is **held in the lower-right corner** of the screen for the
configured hold duration (default **1 second**). Works over RDP sessions.

---

## Quick Start

1. Install **Python 3.9+** from <https://python.org> with "Add Python to PATH" checked.
2. Double-click **`install_and_run.bat`** — it installs the two pip dependencies (`pystray`, `Pillow`) and launches the app.
3. After that, use **`run.cmd`** (or `corner_awake.pyw` directly) to start it without re-installing.

A grey circle appears in the system tray. Right-click it for **Settings** or **Quit**.

---

## How it works

| Action | What happens |
|---|---|
| Mouse enters lower-right corner (~30 px zone) | Hold timer starts (no sound yet) |
| Mouse leaves before the hold completes | Nothing — timer resets silently |
| Mouse stays in corner for the configured duration | Rising beep (880 → 1100 Hz), icon turns green, sleep is blocked |
| Mouse leaves the corner | Falling beep (660 → 440 Hz), icon turns grey, sleep allowed |

Sleep is blocked via the Windows **`SetThreadExecutionState`** API
(`ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED`).

**RDP support:** Run Corner Awake on the **client** machine (the one you're
sitting at). When you move the client's cursor into its lower-right corner, the
client's sleep/idle timer is blocked — keeping the RDP session alive even if
the remote host has its own idle policy. The API call prevents the *local
session* from idling out, which is what causes RDP disconnects on the client
side.

---

## Settings

Right-click the tray icon → **Settings**.

- **Start with Windows** — toggles a `HKCU\...\Run\CornerAwake` registry entry that launches the app at login under `pythonw.exe`.
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
| `settings.json` | User preferences (auto-created, gitignored) |

---

## Requirements

- Windows 10/11 (or Windows Server with RDP)
- Python 3.9+
- `pystray` and `Pillow` (installed by `install_and_run.bat`)
