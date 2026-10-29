<div align="center">

# 🎚️ Detent

### Shape smoother easing curves in Premiere Pro, without moving your keyframe values.

Hold **Caps Lock** and the easing handle slides along a horizontal rail,<br>so only the curve changes and the value stays exactly where it was.

<br>

[![Download](https://img.shields.io/badge/⬇_Download-Latest_version-2ea44f?style=for-the-badge)](https://github.com/SurbD/detent/releases/latest)

![Platform](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=flat-square&logo=windows&logoColor=white)
![Premiere Pro](https://img.shields.io/badge/Adobe-Premiere_Pro-9999FF?style=flat-square&logo=adobepremierepro&logoColor=white)
![Price](https://img.shields.io/badge/price-free-brightgreen?style=flat-square)
![Offline](https://img.shields.io/badge/works-offline-blue?style=flat-square)

[💬 Feedback](https://github.com/SurbD/detent/issues) · [🐛 Report a bug](https://github.com/SurbD/detent/issues/new) · [🐦 Follow @surbdx](https://x.com/surbdx)

<!-- Add a short demo GIF here: drag it into the GitHub editor, then uncomment the next line
<img src="demo.gif" alt="Detent demo" width="720">
-->

</div>

---

## ✨ How it works

| | Step |
|:-:|---|
| **1** | Open the graph editor in Premiere and select a keyframe with an easing handle. |
| **2** | Put your cursor on the handle and **hold `Caps Lock`**. |
| **3** | Drag. The handle moves along a horizontal rail, so the keyframe's **value never changes**. Only the easing does. |
| **4** | Let go of `Caps Lock` to finish. |

> 🎯 **Need finer control?** Hold **`Shift`** while dragging for precision mode, which slows the cursor down for tiny adjustments.

## 🧠 Built to stay out of your way

- ⌨️ **Caps Lock still works as Caps Lock.** No handle near the cursor, or just a quick tap? Detent hands the key straight back to Premiere, so typing titles in capitals still works.
- 🎬 **Only acts inside Premiere Pro.** In every other app, your keys behave normally.
- 🖱️ **Shift+click multi-select still works.** Shift is only held back while a rail is running.
- ⏸️ **Pause in one keypress.** Press `Ctrl + Alt + D`, or click the tray icon. While paused, every key is yours again.
- 🔒 **Private by design.** Detent works offline and never sends anything anywhere.
- 🚀 **Starts with Windows** (optional), so it's ready when you open Premiere.

## 📥 Install

1. **Download** `Detent-Setup.exe` from the [latest release](https://github.com/SurbD/detent/releases/latest).
2. **Run it.** Leave **Start Detent with Windows** ticked if you want it ready every time you log in.
3. **Find it in the tray** (bottom-right, near the clock). Right-click the icon for settings.

> [!NOTE]
> **Windows may show a "Windows protected your PC" warning.** Detent isn't code-signed yet. Click **More info**, then **Run anyway**. The full source is right here in this repository if you'd like to check it or build it yourself.

> [!IMPORTANT]
> If you run Premiere Pro **as administrator**, run Detent as administrator too. Windows blocks input from a normal app to an elevated one.

## ⚙️ Settings

Right-click the tray icon, then choose **Settings**.

| Setting | Default |
|---|:-:|
| 🎚️ Rail key (hold, then drag) | `Caps Lock` |
| 🎯 Precision key (hold while railing) | `Shift` |
| ⏯️ Pause / resume | `Ctrl + Alt + D` |
| 📏 Detection radius (how close to a handle) | `40 px` |
| 🐢 Precision speed | `10%` |
| 🚀 Start with Windows | On |

Every hotkey has a **Record** button: click it and press the keys you want. Use a combination such as `Ctrl + Q`, or a single modifier. You can also change the rail direction, turn sounds and notifications on or off, and switch off the option that hands the key back to Premiere when no handle is nearby.

## 🆘 Something not working?

Use the tray menu:

- 🧾 **Report a problem** saves a small zip with a screenshot of about 300 × 300 px around your cursor, your settings and your version numbers. Nothing is uploaded automatically. Attach the zip to a [new issue](https://github.com/SurbD/detent/issues/new).
- 💬 **Get help / send feedback** opens a pre-filled issue on this page.

<details>
<summary><b>⚠️ Known limits</b></summary>

<br>

- Caps Lock reaches Premiere about 0.1 seconds late, because Detent checks for a handle first.
- Handle detection has been tested on a limited range of screens. If it misses on yours, tell us, and mention your display scaling.

</details>

<details>
<summary><b>🛠️ Build from source</b></summary>

<br>

Needs Windows and Python 3.

```
pip install -r requirements.txt
python app.py          # run the tray app
```

To build the installer, run `build.bat`. It produces `dist\Detent\Detent.exe`, plus `Output\Detent-Setup.exe` if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed.

Tests run without Windows, except the settings-window test, which needs a display:

```
python tests/test_config.py
python tests/test_hotkeys.py
python tests/test_detent.py
python tests/test_report.py
python tests/test_support.py
python tests/test_ui.py
```

User data lives in `%APPDATA%\Detent` (settings and a log file).

</details>

---

<div align="center">

Made with ❤️ by **[Guyde](https://x.com/surbdx)** · [@surbdx](https://x.com/surbdx)<br>
Free to use. If Detent saves you time, tell a fellow editor.

</div>
