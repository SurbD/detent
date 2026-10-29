# Detent 1.3.0 (Windows) — free

Also in 1.3.0:
- Folder build (`--onedir`) instead of one big exe, so Detent opens quickly at Windows login. Output: dist\Detent\Detent.exe.
- Installer has a "Start Detent with Windows (recommended)" checkbox, ticked by default. Detent picks up that choice on its next launch.
- "Get help / send feedback…" in the tray menu and Settings opens a pre-filled GitHub issue. After "Report a problem", Detent offers to open the issues page so the zip can be attached.
- Feedback goes to https://github.com/SurbD/detent/issues (ISSUES_URL in support.py).

1.3.0: Detent is now free. The 7-day trial, license keys and the License window are gone; it runs fully from the first launch. "Start Detent with Windows" is now on by default (Settings > General to turn it off).

1.2.0: the rail key now only does its job when there is a handle near the cursor. Otherwise (or on a quick tap) the key is handed back to Premiere, so Caps Lock keeps working as Caps Lock. Setting: "No handle near the cursor? Give the key back to Premiere" (on by default).
Trade-off: in Premiere the key reaches the app ~0.1 s late, because Detent first checks for a handle.

1.1.1: fixed the Record button crash ("'str' object is not callable"). Added tests/test_ui.py, which drives the settings window with synthetic key presses.

## What's new in 1.1
- Settings: Keyrails-style hotkey editor (Modifier + Key / Single Modifier, Record button) for rail, precision and pause/resume
- Defaults: hold Caps Lock = rail, hold Shift = precision, Ctrl+Alt+D = pause / resume (click the tray icon works too)
- Keys are only touched while Premiere Pro is the active window - Caps Lock etc. work normally everywhere else
- Single-Modifier hotkeys (Shift/Ctrl/Alt) are never hidden from Premiere; the precision modifier is hidden only while a rail runs
- Detection radius slider; "Report a problem" (tray menu + Settings) saves a small zip you can send to support

## Try the tray app from source
    pip install -r requirements.txt
    python app.py                 # tray icon appears; right-click for Enabled / Settings / Quit
(`python detent.py` is still the developer CLI with --verbose / --debug-once.)

## Build the installer
    build.bat                     # -> dist\Detent\Detent.exe  (and Output\Detent-Setup.exe if Inno Setup 6 is installed)
Inno Setup: https://jrsoftware.org/isinfo.php

## Where things live
%APPDATA%\Detent\config.json   settings
%APPDATA%\Detent\detent.log    log (tray menu -> Open log folder)

## Tests (no Windows / network needed)
    python tests/test_detent.py
    python tests/test_config.py
    python tests/test_hotkeys.py
    python tests/test_report.py
    python tests/test_support.py
    python tests/test_ui.py        # settings window + Record button (needs a display; skips if none)

## Known limits
- Unsigned exe -> SmartScreen / antivirus warnings. Buy a code-signing certificate before a public launch.
- Premiere running as administrator needs Detent run as administrator too (Windows blocks cross-privilege input).
