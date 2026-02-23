import sys
import ctypes
import ctypes.wintypes
import win32con
import win32gui
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QSlider, QCheckBox,
    QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSharedMemory, QTimer

from config import load_config, save_config

# --- Phase 3: HoverEngine ---
class HoverEngine:
    def __init__(self):
        self._timer = QTimer()
        self._timer.timeout.connect(self.check_idle)
        self.hwnd = 0
        self.icons_hidden = False
        
        # Dual Mode State
        self.mode = load_config().get("mode", "safe")
        self.fade_duration = load_config().get("fade_duration", 400)
        self.original_ex_style = None
        
        # Fade Animation State
        self.is_fading = False
        self.fade_direction = None
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._anim_step)
        self._current_alpha = 255
        self._fade_target = 0
        self._fade_step = max(1, int((255 - 30) / (self.fade_duration / 15)))
        
    def set_mode(self, new_mode):
        if self.mode == "experimental" and new_mode != "experimental":
            self.restore_window_style()
        self.mode = new_mode

    def start(self):
        if not self._timer.isActive():
            self._timer.start(500)

    def stop(self):
        self._timer.stop()
        self._anim_timer.stop()
        self.restore_window_style()
        self.show_icons_safe()

    def _find_desktop_listview_hwnd(self):
        progman = win32gui.FindWindow("Progman", None)
        if progman:
            defview = win32gui.FindWindowEx(progman, None, "SHELLDLL_DefView", None)
            if defview:
                listview = win32gui.FindWindowEx(defview, None, "SysListView32", None)
                if listview:
                    return listview

        found = {"hwnd": 0}
        def _enum_cb(hwnd, _lparam):
            try:
                class_name = win32gui.GetClassName(hwnd)
            except Exception:
                return True
            if class_name == "WorkerW":
                defview = win32gui.FindWindowEx(hwnd, None, "SHELLDLL_DefView", None)
                if defview:
                    listview = win32gui.FindWindowEx(defview, None, "SysListView32", None)
                    if listview:
                        found["hwnd"] = listview
                        return False
            return True

        win32gui.EnumWindows(_enum_cb, None)
        return found["hwnd"]

    def restore_window_style(self):
        if self.hwnd and self.original_ex_style is not None:
            try:
                win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 255, win32con.LWA_ALPHA)
            except Exception:
                pass
            try:
                win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, self.original_ex_style)
            except Exception:
                pass
            self.original_ex_style = None

    def hide_icons_safe(self):
        if not self.hwnd:
            self.hwnd = self._find_desktop_listview_hwnd()
        if self.hwnd:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
            self.icons_hidden = True

    def show_icons_safe(self):
        if not self.hwnd:
            self.hwnd = self._find_desktop_listview_hwnd()
        if self.hwnd:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            self.icons_hidden = False

    def fade_hide(self):
        if not self.hwnd:
            self.hwnd = self._find_desktop_listview_hwnd()
        if not self.hwnd or self.icons_hidden: return
        if self.fade_direction == "out": return
        
        self.is_fading = True
        self.fade_direction = "out"
        self._anim_timer.stop()
        
        if self.original_ex_style is None:
            self.original_ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, self.original_ex_style | win32con.WS_EX_LAYERED)
        
        self._current_alpha = 255
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, self._current_alpha, win32con.LWA_ALPHA)
        
        self._fade_target = 30
        self._fade_step = max(1, int((255 - 30) / (self.fade_duration / 15)))
        self._anim_timer.start(15)

    def fade_show(self):
        if not self.hwnd:
            self.hwnd = self._find_desktop_listview_hwnd()
        if not self.hwnd or not self.icons_hidden: return
        if self.fade_direction == "in": return
        
        self.is_fading = True
        self.fade_direction = "in"
        self._anim_timer.stop()
        
        if self.original_ex_style is None:
            self.original_ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, self.original_ex_style | win32con.WS_EX_LAYERED)
        
        self._current_alpha = 30
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, self._current_alpha, win32con.LWA_ALPHA)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        
        self._fade_target = 255
        self._fade_step = max(1, int((255 - 30) / (self.fade_duration / 15)))
        self._anim_timer.start(15)

    def _anim_step(self):
        if self._current_alpha > self._fade_target:
            self._current_alpha = max(self._fade_target, self._current_alpha - self._fade_step)
        elif self._current_alpha < self._fade_target:
            self._current_alpha = min(self._fade_target, self._current_alpha + self._fade_step)
            
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, self._current_alpha, win32con.LWA_ALPHA)
        
        if self._current_alpha == self._fade_target:
            self._anim_timer.stop()
            self.is_fading = False
            self.fade_direction = None
            if self._fade_target == 30:
                win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                self.icons_hidden = True
                self.restore_window_style()
            elif self._fade_target == 255:
                self.icons_hidden = False
                self.restore_window_style()

    def check_idle(self):
        if self.is_fading:
            return
            
        cfg = load_config()
        self.set_mode(cfg.get("mode", "safe"))
        self.fade_duration = cfg.get("fade_duration", 400)
        
        if not cfg["enabled"]:
            return

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        
        millis = ctypes.windll.kernel32.GetTickCount64() - lii.dwTime
        idle_seconds = float(millis) / 1000.0

        if idle_seconds > cfg["idle_time"] and not self.icons_hidden:
            if self.mode == "experimental":
                self.fade_hide()
            else:
                self.hide_icons_safe()
        elif idle_seconds < 0.5 and self.icons_hidden:
            if self.mode == "experimental":
                self.fade_show()
            else:
                self.show_icons_safe()

# --- Phase 4: UI Integration ---
class MainWindow(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle('HoverDesk')
        self.setGeometry(600, 300, 420, 320)
        self.cfg = load_config()
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel('HoverDesk Settings Panel'))

        # Enable checkbox
        self.enable_cb = QCheckBox("Enable HoverDesk")
        self.enable_cb.setChecked(self.cfg["enabled"])
        layout.addWidget(self.enable_cb)

        # Idle time slider
        idle_layout = QHBoxLayout()
        self.idle_label = QLabel(f'Idle Time: {self.cfg["idle_time"]}s')
        idle_layout.addWidget(self.idle_label)
        
        self.idle_slider = QSlider(Qt.Orientation.Horizontal)
        self.idle_slider.setMinimum(1)
        self.idle_slider.setMaximum(30)
        self.idle_slider.setValue(self.cfg["idle_time"])
        self.idle_slider.valueChanged.connect(self._on_slider_change)
        idle_layout.addWidget(self.idle_slider)
        
        layout.addLayout(idle_layout)

        # Mode Selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        
        self.safe_radio = QRadioButton("Normal Mode (Safe)")
        self.fade_radio = QRadioButton("Fade Mode (Experimental)")
        
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.safe_radio)
        self.mode_group.addButton(self.fade_radio)
        
        mode_layout.addWidget(self.safe_radio)
        mode_layout.addWidget(self.fade_radio)
        layout.addLayout(mode_layout)

        # Fade Duration Config (Hidden by default unless in experimental mode)
        self.fade_widget = QWidget()
        fade_layout = QHBoxLayout(self.fade_widget)
        fade_layout.setContentsMargins(0, 0, 0, 0)
        self.fade_label = QLabel(f'Fade Duration: {self.cfg.get("fade_duration", 400)}ms')
        fade_layout.addWidget(self.fade_label)
        
        self.fade_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_slider.setMinimum(100)
        self.fade_slider.setMaximum(1000)
        self.fade_slider.setSingleStep(50)
        self.fade_slider.setValue(self.cfg.get("fade_duration", 400))
        self.fade_slider.valueChanged.connect(self._on_fade_slider_change)
        fade_layout.addWidget(self.fade_slider)
        
        layout.addWidget(self.fade_widget)
        
        # Connect mode toggle
        self.safe_radio.toggled.connect(self._on_mode_toggled)
        self.fade_radio.toggled.connect(self._on_mode_toggled)

        # Apply defaults at the end
        if self.cfg.get("mode", "safe") == "experimental":
            self.fade_radio.setChecked(True)
        else:
            self.safe_radio.setChecked(True)

        # Buttons
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton('Apply')
        apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(apply_btn)

        hide_btn = QPushButton('Hide to Tray')
        hide_btn.clicked.connect(self.hide)
        btn_layout.addWidget(hide_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_slider_change(self, val):
        self.idle_label.setText(f'Idle Time: {val}s')

    def _on_fade_slider_change(self, val):
        self.fade_label.setText(f'Fade Duration: {val}ms')

    def _on_mode_toggled(self):
        self.fade_widget.setVisible(self.fade_radio.isChecked())

    def _on_apply(self):
        self.cfg["enabled"] = self.enable_cb.isChecked()
        self.cfg["idle_time"] = self.idle_slider.value()
        self.cfg["fade_duration"] = self.fade_slider.value()
        self.cfg["mode"] = "experimental" if self.fade_radio.isChecked() else "safe"
        save_config(self.cfg)
        
        self.engine.set_mode(self.cfg["mode"])
        if self.cfg["enabled"]:
            self.engine.start()
        else:
            self.engine.stop()

    def show_window(self):
        self.cfg = load_config()
        self.enable_cb.setChecked(self.cfg["enabled"])
        
        self.idle_slider.setValue(self.cfg["idle_time"])
        self._on_slider_change(self.cfg["idle_time"])
        
        self.fade_slider.setValue(self.cfg.get("fade_duration", 400))
        self._on_fade_slider_change(self.cfg.get("fade_duration", 400))
        
        if self.cfg.get("mode", "safe") == "experimental":
            self.fade_radio.setChecked(True)
        else:
            self.safe_radio.setChecked(True)
        
        self._on_mode_toggled()
        
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

if __name__ == '__main__':
    # Phase 1: Single Instance Check
    app = QApplication(sys.argv)
    
    lock = QSharedMemory("HoverDeskSingleton")
    if lock.attach():
        print("Instance already running. Exiting immediately.")
        sys.exit(0)
    lock.create(1)
    
    # Store lock so it's not garbage collected
    app._single_instance_lock = lock

    engine = HoverEngine()
    
    # Start engine automatically on boot if enabled
    initial_cfg = load_config()
    if initial_cfg["enabled"]:
        engine.start()

    window = MainWindow(engine)
    tray = QSystemTrayIcon(QIcon('icon.ico'))
    tray.setToolTip('HoverDesk')
    
    menu = QMenu()
    menu.addAction('Show', window.show_window)
    menu.addSeparator()
    
    def on_exit():
        engine.stop()
        app.quit()
        
    menu.addAction('Exit', on_exit)
    tray.setContextMenu(menu)
    tray.show()
    
    window.show()
    sys.exit(app.exec())
