# Detent

**Free Windows helper for Adobe Premiere Pro.** Detent lets you adjust easing handles in the keyframe graph editor without changing the keyframe's value. Hold Caps Lock and the handle moves along a horizontal rail, so you can shape smoother curves with more control.

<!-- Add a short demo GIF here: drag the line below into the GitHub editor
![Detent demo](demo.gif)
-->

**[⬇ Download the latest version](https://github.com/SurbD/detent/releases/latest)**  ·  [Report a problem or request a feature](https://github.com/SurbD/detent/issues)

---

## How it works

1. Open the graph editor in Premiere and select a keyframe with an easing handle.
2. Put your cursor on the handle and **hold Caps Lock**.
3. Drag. The handle slides along a horizontal rail, so the keyframe's value stays exactly where it was and only the easing changes.
4. Let go of Caps Lock to finish.

Hold **Shift** while dragging for precision mode, which slows the cursor down for fine adjustments.

## Good to know

- **Caps Lock still works as Caps Lock.** If there's no handle near the cursor, or you only tap the key, Detent hands it back to Premiere. Typing a title in capitals still works, with no need to pause Detent.
- **It only acts inside Premiere Pro.** In every other app your keys behave normally.
- **Shift+click multi-select still works.** Shift is only held back while a rail is running.
- **Pause and resume** with `Ctrl + Alt + D`, or click the tray icon. While paused, every key works normally.
- **Nothing leaves your computer.** Detent works offline and never sends data anywhere.

## Install

1. Download `Detent-Setup.exe` from the [latest release](https://github.com/SurbD/detent/releases/latest).
2. Run it. Leave **Start Detent with Windows** ticked if you want it ready every time you log in.
3. Detent appears as a small icon in the system tray (bottom-right, near the clock). Right-click it for Settings.

> **Windows may show a "Windows protected your PC" warning.** Detent isn't code-signed yet. Click **More info**, then **Run anyway**. The full source is in this repository if you want to check or build it yourself.

> If you run Premiere Pro **as administrator**, run Detent as administrator too. Windows blocks input from a normal app to an elevated one.

## Settings

Right-click the tray icon, then **Settings**.

| Setting | Default |
|---|---|
| Rail key (hold, then drag) | `Caps Lock` |
| Precision key (hold while railing) | `Shift` |
| Pause / resume | `Ctrl + Alt + D` |
| Detection radius (how close the cursor must be to a handle) | 40 px |
| Precision speed | 10% |
| Start with Windows | On |

Each hotkey has a **Record** button: click it and press the keys you want. You can use a combination such as `Ctrl + Q`, or a single modifier. You can also change the rail direction, turn the sounds and notifications on or off, and turn off the option that hands the key back to Premiere when no handle is nearby.

## Something not working?

Use the tray menu:

- **Report a problem** saves a small zip with a screenshot of about 300 × 300 px around your cursor, your settings and your version numbers. Nothing is uploaded automatically. Attach the zip to a [new issue](https://github.com/SurbD/detent/issues/new).
- **Get help / send feedback** opens a pre-filled issue on this page.

Known limits: Caps Lock reaches Premiere about 0.1 seconds late, because Detent checks for a handle first. Handle detection has been tested on a limited range of screens, so tell us if it misses on yours, and mention your display scaling.

## Build from source

Needs Windows and Python 3.

```
pip install -r requirements.txt
python app.py          # run the tray app
```

To build the installer, run `build.bat`. It produces `dist\Detent\Detent.exe`, and `Output\Detent-Setup.exe` if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed.

Tests (no Windows needed, except the settings-window test, which needs a display):

```
python tests/test_config.py
python tests/test_hotkeys.py
python tests/test_detent.py
python tests/test_report.py
python tests/test_support.py
python tests/test_ui.py
```

User data lives in `%APPDATA%\Detent` (settings and a log file).

---

Made by [Guyde](https://github.com/SurbD). Free to use.
