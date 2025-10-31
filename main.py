
"""Main GUI application for AION.
Uses a local YOLO weight (models/aion.pt) to run realtime detections
and draw a click-through overlay on the selected game window.
"""
import sys
from PySide6 import QtWidgets, QtCore
from loguru import logger
from utils import list_windows, get_window_rect
from overlay import OverlayWindow
from detection import DetectionController


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AION - Local YOLO Live Detector")
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

        layout.addLayout(form)

        # Start/Stop
        btns = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        layout.addLayout(btns)

        # Log terminal
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, stretch=1)
        self._overlay = OverlayWindow()
        self._controller = None
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
        self._controller.start()
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


def run_app():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
