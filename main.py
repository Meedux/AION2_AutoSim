
"""Main GUI application for AION.
Uses a local YOLO weight (models/aion.pt) to run realtime detections
and draw a click-through overlay on the selected game window.
"""
import sys
import ctypes
from PySide6 import QtWidgets, QtCore
from loguru import logger
from utils import list_windows, get_window_rect
from overlay import OverlayWindow
from detection import DetectionController
from input_controller import focus_window


def is_admin():
    """Check if the program is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Restart the program with administrator privileges."""
    try:
        if sys.argv[0].endswith('.py'):
            # Running as Python script
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                ' '.join([f'"{arg}"' for arg in sys.argv]), 
                None, 
                1
            )
        else:
            # Running as executable
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                ' '.join([f'"{arg}"' for arg in sys.argv[1:]]), 
                None, 
                1
            )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to elevate privileges: {e}")
        return False
    return True


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AION Autoplay")
        self.resize(900, 640)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # top controls
        form = QtWidgets.QFormLayout()
        self.win_combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_windows)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.win_combo)
        h.addWidget(self.refresh_btn)
        form.addRow("Game window:", h)

        # Using local model weights placed at models/aion.pt
        info = QtWidgets.QLabel("Using local model weights: models/aion.pt (Ultralytics YOLO)")
        info.setWordWrap(True)
        form.addRow("Settings:", info)

        # Simulate mode checkbox
        self.simulate_cb = QtWidgets.QCheckBox("Simulate mode (log only, no real inputs)")
        self.simulate_cb.setChecked(False)
        self.simulate_cb.hide()  # Hide simulate mode - user wants real implementation
        form.addRow("Mode:", self.simulate_cb)

        layout.addLayout(form)

        # Start/Stop and Emergency Stop
        btns = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.emergency_stop_btn = QtWidgets.QPushButton("EMERGENCY STOP")
        self.emergency_stop_btn.setStyleSheet("QPushButton { background-color: red; color: white; font-weight: bold; }")
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        btns.addWidget(self.emergency_stop_btn)
        layout.addLayout(btns)

        # Log terminal
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, stretch=1)
        # track desired automation state (applies to controller when created)
        # Default automation ON as requested
        self._automation_enabled = True
        self._overlay = OverlayWindow()
        # ensure overlay matches the desired automation default immediately
        try:
            self._overlay.set_automation_enabled(self._automation_enabled)
        except Exception:
            pass
        self._controller = None
        # start a global hotkey listener for Pause/Break to toggle automation
        self._hotkey_thread = None
        self._start_hotkey_listener()
        self._pos_timer = QtCore.QTimer(self)
        self._pos_timer.setInterval(300)  # ms
        self._pos_timer.timeout.connect(self._reposition_overlay)

        self._refresh_windows()

    def log(self, text: str):
        # append thread-safely
        QtCore.QMetaObject.invokeMethod(self.log_view, "appendPlainText", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, text))

    def _refresh_windows(self):
        self.win_combo.clear()
        wins = list_windows()
        for title, hwnd in wins:
            self.win_combo.addItem(f"{title} (hwnd={hwnd})", hwnd)

    def start(self):
        idx = self.win_combo.currentIndex()
        if idx < 0:
            self.log("No window selected")
            return
        hwnd = self.win_combo.currentData()
        rect = get_window_rect(hwnd)
        if not rect:
            self.log("Unable to get window rect")
            return
        left, top, w, h = rect
        # show overlay aligned to window
        self._overlay.setGeometry(left, top, w, h)
        self._overlay.show()
        self._overlay.make_clickthrough()

        # create controller (local model)
        self._controller = DetectionController(hwnd=hwnd, overlay_update=self._overlay.update_overlay, log_fn=self.log, fps=6)
        # apply stored automation preference
        try:
            self._controller.action_planner.set_enabled(self._automation_enabled)
        except Exception:
            pass
        self._controller.start()
        # Focus the game window immediately when starting
        focus_window(hwnd)
        # start periodic overlay repositioning to follow the target window
        self._pos_timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log("Started detection")

    def stop(self):
        if self._controller:
            self._controller.stop()
            self._controller = None
        self._overlay.hide()
        self._pos_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log("Stopped")

    def emergency_stop(self):
        # Immediately disable automation and stop controller
        self._automation_enabled = False
        try:
            self._overlay.set_automation_enabled(False)
        except Exception:
            pass
        if self._controller:
            try:
                self._controller.action_planner.set_enabled(False)
            except Exception:
                pass
        self.log("EMERGENCY STOP: Automation disabled")

    def _reposition_overlay(self):
        # Keep overlay aligned to the target window while running
        idx = self.win_combo.currentIndex()
        if idx < 0:
            return
        hwnd = self.win_combo.currentData()
        rect = get_window_rect(hwnd)
        if rect:
            left, top, w, h = rect
            self._overlay.setGeometry(left, top, w, h)

    def toggle_automation(self):
        # toggle desired automation state and apply to controller if present
        self._automation_enabled = not self._automation_enabled
        enabled = self._automation_enabled
        # update overlay indicator
        try:
            self._overlay.set_automation_enabled(enabled)
        except Exception:
            pass
        # apply to running controller
        if self._controller:
            try:
                self._controller.action_planner.set_enabled(enabled)
            except Exception:
                pass

    def _start_hotkey_listener(self):
        # Start background thread that registers a global Delete hotkey and
        # invokes toggle_automation when pressed.
        import threading, ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        WM_HOTKEY = 0x0312
        VK_DELETE = 0x2E

        def _hotkey_thread_fn():
            HOTKEY_ID = 1
            # Try RegisterHotKey first (simple, preferred)
            if user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_DELETE):
                # registration succeeded
                try:
                    self.log("Hotkey registered: Delete (RegisterHotKey)")
                except Exception:
                    pass
                msg = wintypes.MSG()
                try:
                    while True:
                        b = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                        if b == 0:
                            break
                        if msg.message == WM_HOTKEY:
                            try:
                                QtCore.QMetaObject.invokeMethod(self, "toggle_automation", QtCore.Qt.QueuedConnection)
                            except Exception:
                                pass
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                finally:
                    try:
                        user32.UnregisterHotKey(None, HOTKEY_ID)
                    except Exception:
                        pass
                return

            # If RegisterHotKey failed, fall back to a low-level keyboard hook
            try:
                self.log("RegisterHotKey failed; falling back to low-level keyboard hook")
            except Exception:
                pass

            # WH_KEYBOARD_LL hook to catch Delete presses
            WH_KEYBOARD_LL = 13
            WM_KEYDOWN = 0x0100

            kernel32 = ctypes.windll.kernel32

            # define KBDLLHOOKSTRUCT
            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [("vkCode", wintypes.DWORD),
                            ("scanCode", wintypes.DWORD),
                            ("flags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", wintypes.ULONG_PTR)]

            LowLevelKeyboardProc = ctypes.WINFUNCTYPE(wintypes.LRESULT, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)

            @LowLevelKeyboardProc
            def _ll_keyboard_proc(nCode, wParam, lParam):
                try:
                    if nCode >= 0 and wParam == WM_KEYDOWN:
                        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                        if kb.vkCode == VK_DELETE:
                            try:
                                QtCore.QMetaObject.invokeMethod(self, "toggle_automation", QtCore.Qt.QueuedConnection)
                            except Exception:
                                pass
                except Exception:
                    pass
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            # install hook
            hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _ll_keyboard_proc, kernel32.GetModuleHandleW(None), 0)
            if not hook_id:
                try:
                    self.log("Failed to install low-level keyboard hook for Delete key")
                except Exception:
                    pass
                return

            # message loop to keep the hook alive
            msg = wintypes.MSG()
            try:
                while True:
                    b = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if b == 0:
                        break
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                try:
                    user32.UnhookWindowsHookEx(hook_id)
                except Exception:
                    pass

        t = threading.Thread(target=_hotkey_thread_fn, daemon=True)
        t.start()
        self._hotkey_thread = t

    def closeEvent(self, event):
        # ensure controller stopped and leave
        try:
            if self._controller:
                self._controller.stop()
        except Exception:
            pass
        return super().closeEvent(event)


def run_app():
    """Main application entry point."""
    app = QtWidgets.QApplication(sys.argv)
    
    # AutoHotkey handles everything automatically - no driver installation needed!
    logger.info("✓ AutoHotkey ready for input control")
    
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    logger.info("Starting AION automation with AutoHotkey input control...")
    run_app()
