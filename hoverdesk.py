import sys
import ctypes
import ctypes.wintypes
import win32con
import win32gui
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QSlider, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QToolTip
)
from PyQt6.QtGui import QIcon, QCursor
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
        self.setWindowIcon(QIcon('icon.ico'))
        self.setMinimumSize(500, 500)
        self.cfg = load_config()
        
        # Apply Global Stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 8px;
                color: #A0A0A0;
                font-size: 11px;
                font-weight: bold;
                left: 10px;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #404040;
                border: 1px solid #555555;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
            QPushButton#applyBtn {
                background-color: #3DAEE9;
                border: none;
                color: white;
            }
            QPushButton#applyBtn:hover {
                background-color: #4FC3F7;
            }
            QPushButton#applyBtn:pressed {
                background-color: #2980B9;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4A4A4A;
                height: 4px;
                background: #3A3A3A;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3DAEE9;
                border: none;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #4FC3F7;
            }
            QCheckBox {
                background: transparent;
                spacing: 8px;
            }
            QRadioButton {
                background: transparent;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555555;
                border-radius: 10px;
                background: transparent;
            }
            QRadioButton::indicator:hover {
                border-color: #3DAEE9;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #3DAEE9;
                background: #3DAEE9;
            }
            QGroupBox QLabel {
                background: transparent;
            }
            QGroupBox QSlider {
                background: transparent;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF;
                background: transparent;
            }
            QLabel#subtitleLabel {
                font-size: 12px;
                color: #A0A0A0;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        title_label = QLabel("HoverDesk")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle_label = QLabel("Smart Desktop Icon Manager")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addLayout(header_layout)

        # Enable Checkbox
        self.enable_cb = QCheckBox("Enable HoverDesk")
        self.enable_cb.setChecked(self.cfg["enabled"])
        self.enable_cb.toggled.connect(self._on_enable_toggled)
        layout.addWidget(self.enable_cb)

        # Feature Container
        self.features_widget = QWidget()
        features_layout = QVBoxLayout(self.features_widget)
        features_layout.setContentsMargins(0, 0, 0, 0)
        features_layout.setSpacing(10)

        # Mode Section
        self.mode_group = QGroupBox("Mode Settings")
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(15, 20, 15, 15)
        mode_layout.setSpacing(15)

        # Normal Mode block
        safe_container = QWidget()
        safe_container.setStyleSheet("background: transparent;")
        safe_layout = QVBoxLayout(safe_container)
        safe_layout.setContentsMargins(0, 0, 0, 0)
        safe_layout.setSpacing(4)
        self.safe_radio = QRadioButton("Normal Mode (Safe)")
        safe_desc = QLabel("Standard show/hide visibility.")
        safe_desc.setStyleSheet("font-size: 12px; color: #9E9E9E; margin-left: 20px; background: transparent;")
        safe_layout.addWidget(self.safe_radio)
        safe_layout.addWidget(safe_desc)

        # Fade Mode block
        fade_container = QWidget()
        fade_container.setStyleSheet("background: transparent;")
        fade_mode_layout = QVBoxLayout(fade_container)
        fade_mode_layout.setContentsMargins(0, 0, 0, 0)
        fade_mode_layout.setSpacing(4)
        self.fade_radio = QRadioButton("Fade Mode (Experimental)")
        fade_desc = QLabel("Smooth alpha blending transitions.")
        fade_desc.setStyleSheet("font-size: 12px; color: #9E9E9E; margin-left: 20px; background: transparent;")
        fade_mode_layout.addWidget(self.fade_radio)
        fade_mode_layout.addWidget(fade_desc)

        self.mode_btn_group = QButtonGroup()
        self.mode_btn_group.addButton(self.safe_radio)
        self.mode_btn_group.addButton(self.fade_radio)

        mode_layout.addWidget(safe_container)
        mode_layout.addWidget(fade_container)

        self.mode_group.setLayout(mode_layout)
        features_layout.addWidget(self.mode_group)

        # Idle Settings Section
        self.idle_group = QGroupBox("Idle Settings")
        idle_layout = QVBoxLayout()
        idle_layout.setContentsMargins(15, 20, 15, 15)
        idle_layout.setSpacing(10)

        self.idle_label = QLabel(f'Idle Time: {self.cfg["idle_time"]} seconds')
        idle_layout.addWidget(self.idle_label)

        self.idle_slider = QSlider(Qt.Orientation.Horizontal)
        self.idle_slider.setMinimumHeight(24)
        self.idle_slider.setMinimum(1)
        self.idle_slider.setMaximum(30)
        self.idle_slider.setValue(self.cfg["idle_time"])
        self.idle_slider.valueChanged.connect(self._on_slider_change)
        idle_layout.addWidget(self.idle_slider)

        self.idle_group.setLayout(idle_layout)
        features_layout.addWidget(self.idle_group)

        # Fade Settings Section
        self.fade_group = QGroupBox("Fade Settings")
        fade_s_layout = QVBoxLayout()
        fade_s_layout.setContentsMargins(15, 20, 15, 15)
        fade_s_layout.setSpacing(10)

        self.fade_label = QLabel(f'Fade Duration: {self.cfg.get("fade_duration", 400)} ms')
        fade_s_layout.addWidget(self.fade_label)

        self.fade_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_slider.setMinimumHeight(24)
        self.fade_slider.setMinimum(100)
        self.fade_slider.setMaximum(1000)
        self.fade_slider.setSingleStep(50)
        self.fade_slider.setValue(self.cfg.get("fade_duration", 400))
        self.fade_slider.valueChanged.connect(self._on_fade_slider_change)
        fade_s_layout.addWidget(self.fade_slider)

        self.fade_group.setLayout(fade_s_layout)
        features_layout.addWidget(self.fade_group)
        layout.addWidget(self.features_widget)
        layout.addStretch()

        # Connect mode toggle after setup
        self.safe_radio.toggled.connect(self._on_mode_toggled)
        self.fade_radio.toggled.connect(self._on_mode_toggled)

        # Apply defaults at the end
        if self.cfg.get("mode", "safe") == "experimental":
            self.fade_radio.setChecked(True)
            self.fade_group.setVisible(True)
        else:
            self.safe_radio.setChecked(True)
            self.fade_group.setVisible(False)

        # Initial features disabled state
        self._on_enable_toggled(self.cfg["enabled"])

        # Control Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)
        btn_layout.addStretch()
        
        apply_btn = QPushButton('Apply')
        apply_btn.setObjectName("applyBtn")
        apply_btn.setMinimumHeight(40)
        apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(apply_btn)

        hide_btn = QPushButton('Minimize to Tray')
        hide_btn.setMinimumHeight(40)
        hide_btn.clicked.connect(self.hide)
        btn_layout.addWidget(hide_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_enable_toggled(self, checked):
        self.features_widget.setEnabled(checked)

    def _on_slider_change(self, val):
        self.idle_label.setText(f'Idle Time: {val} seconds')

    def _on_fade_slider_change(self, val):
        self.fade_label.setText(f'Fade Duration: {val} ms')

    def _on_mode_toggled(self):
        is_experimental = self.fade_radio.isChecked()
        self.fade_group.setVisible(is_experimental)

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
            
        # Show tooltip
        QToolTip.showText(QCursor.pos(), "Settings Applied Successfully!", self)

    def show_window(self):
        self.cfg = load_config()
        self.enable_cb.setChecked(self.cfg["enabled"])
        
        self.idle_slider.setValue(self.cfg["idle_time"])
        self._on_slider_change(self.cfg["idle_time"])
        
        self.fade_slider.setValue(self.cfg.get("fade_duration", 400))
        self._on_fade_slider_change(self.cfg.get("fade_duration", 400))
        
        if self.cfg.get("mode", "safe") == "experimental":
            self.fade_radio.setChecked(True)
            self.fade_group.setVisible(True)
        else:
            self.safe_radio.setChecked(True)
            self.fade_group.setVisible(False)
        
        self._on_enable_toggled(self.cfg["enabled"])
        
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

if __name__ == '__main__':
    # Set Windows AppUserModelID for proper taskbar grouping and icon
    import ctypes
    try:
        myappid = 'hoverdesk.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # Phase 1: Single Instance Check
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.ico'))
    
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
