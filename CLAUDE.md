# corner-awake

Tray/menu-bar app: hold cursor in lower-right corner for N seconds, then sleep is blocked until the cursor leaves. One script for Windows and macOS.

## Stack
- Python 3.9+, `pystray`, `Pillow` (on macOS, `pystray` pulls in `pyobjc-framework-Quartz` + Cocoa)
- Single file: `corner_awake.pyw`. Platform branches use `IS_WINDOWS` / `IS_MAC`.

## Run
- Windows: `install_and_run.bat` (first time), then `run.cmd`
- macOS: `bash install_and_run.sh` (creates `.venv` next to the script), then `bash run.sh` (detached via `nohup`)

## Rules
- **Windows behaviour must not change.** Every macOS change goes in an `IS_MAC` branch. Windows code paths stay as they were.
- Verify Windows is unchanged: load `git show <base>:corner_awake.pyw` and the new file with importlib. Compare `_make_icon(True/False).tobytes()` and `_startup_command()` (replace the script path first). Then run `python corner_awake.pyw` for a few seconds to check for errors.
- macOS cannot be tested from the Windows workstation. The user copies the files to the Mac and reports back.

## Platform mapping
| Function | Windows | macOS |
|---|---|---|
| Cursor / screen | `GetCursorPos`, `GetSystemMetrics` (primary monitor) | Quartz `CGEventGetLocation`, `CGDisplayBounds(CGMainDisplayID())`, points, top-left origin |
| Sleep block | `SetThreadExecutionState` | `caffeinate -d -i -w <pid>` child process |
| Beeps | `winsound.Beep` | Same tones rendered to WAV in `tempfile.gettempdir()`, played with `afplay` |
| Start at login | `HKCU\...\Run\CornerAwake` | `~/Library/LaunchAgents/com.cornerawake.plist` (rewritten only when content changes) |
| Icon | Drawn live with `segoeui.ttf` / `seguisym.ttf` | `icon_active.png` / `icon_inactive.png` |
| UI updates from monitor thread | Direct call | `AppHelper.callAfter` (AppKit is not thread-safe) |

## Gotchas
- The icon PNGs are rendered copies of the Windows `_make_icon`. If the icon drawing changes, render them again on Windows:
  `python -I -c "import importlib.util as u; s=u.spec_from_file_location('c','corner_awake.pyw'); m=u.module_from_spec(s); s.loader.exec_module(m); m._make_icon(True).save('icon_active.png'); m._make_icon(False).save('icon_inactive.png')"`
- Segoe UI has no `⚡` glyph (it draws an empty box). The active icon uses `seguisym.ttf` at size 36, centred on the glyph's ink bbox. The inactive "Zzz" icon still uses `segoeui.ttf` at size 22 with the original centring.
- The settings key `start_with_windows` also controls "Start at login" on macOS. It keeps that name so existing `settings.json` files still work.
- macOS shows a Quick Note hot corner in the lower-right by default. It conflicts with this app.
- `.sh` files must keep LF line endings. `.gitattributes` enforces this.
