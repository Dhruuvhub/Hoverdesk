# HoverDesk

HoverDesk is a smart, modern Windows desktop utility built in Python (PyQt6) that automatically manages the visibility of your desktop icons. It tracks system idle time and gracefully hides your desktop icons when you are inactive, bringing them back seamlessly when you return. 

## Features
- **Dual Presentation Modes:**
  - **Normal Mode (Safe):** Uses standard Windows API calls (`ShowWindow`) to instantly show or hide desktop icons.
  - **Fade Mode (Experimental):** Uses smooth alpha-blending transitions to gradually fade out and fade in the desktop icons.
- **Customizable Idle Times:** Configure exactly how long the system needs to be idle before icons disappear (from 1 to 30 seconds).
- **Custom Fade Durations:** When using Fade Mode, control the speed of the alpha blend transition (from 100ms to 1000ms).
- **System Tray Integration:** Runs quietly in the background with a system tray icon, enabling you to minimize it and keep your taskbar clean.
- **Modern UI:** Features a sleek dark theme built using `PyQt6` stylesheets.
- **Singleton Guard:** Uses `QSharedMemory` to ensure only one instance of the app runs at the exact same time, avoiding conflicting states.

## Problems Encountered & Solutions

During the development of this project, we ran into several complex Windows-specific API challenges and resolved them to create a seamless user experience.

### 1. Windows Identity and App Grouping (The "Python Icon" Issue)
**Problem:** The app was constantly grouped under the generic `python.exe` process on the Windows taskbar, and the executable didn't display the custom `icon.ico` on the desktop shortcut or Alt+Tab switcher after being built with PyInstaller.
**Solution:** 
- We enforced a specific Windows Application User Model ID by using `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('hoverdesk.app.1.0')` *before* the `QApplication` instantiation. 
- Integrated the icon consistently by setting it on `app.setWindowIcon()` and `self.setWindowIcon()` directly. 
- Cleared out corrupted PyInstaller build caches (`build/` and `dist/`) to prevent Windows from holding onto the old generic executable cache, and provided the `--icon=icon.ico` flag.

### 2. Fade Animation Flickering and Black Screens
**Problem:** The Experimental Fade Mode relies on Windows `SetLayeredWindowAttributes`. Early versions caused the desktop wallpaper to briefly flash black or severely flicker when the opacity blend reached maximum/minimum values.
**Solution:**
- Transitioned to accurately intercepting the `SysListView32` desktop layer via `WorkerW` / `Progman` loops.
- Stored the `original_ex_style` of the listview, adding the `WS_EX_LAYERED` bitflag *only* during the fade animation.
- Carefully clamped logic in a `QTimer` step handler to gracefully return standard window flags, rather than letting attributes linger when transparent.

### 3. Idle Detection Performance
**Problem:** Polling globally for keyboard or mouse input hooked the Python script too deeply into the system, causing lag or triggering antivirus warnings.
**Solution:** 
- Used the native `ctypes.windll.user32.GetLastInputInfo` which efficiently asks Windows when the last globally registered input happened, allowing for incredibly fast and lightweight idle time calculations inside `HoverEngine`.

## Building the App

To build HoverDesk as a standalone `.exe` without needing Python installed:

1. Ensure requirements are met:
`pip install pyqt6 pywin32 pyinstaller`
2. Run the PyInstaller command:
`pyinstaller --onefile --noconsole --icon=icon.ico hoverdesk.py`
3. HoverDesk will be compiled to `dist/hoverdesk.exe`.
