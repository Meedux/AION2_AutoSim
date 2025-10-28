import sys
import os
import time
import threading
from PyQt5 import QtWidgets, QtCore, QtGui
from loguru import logger

from utils import enum_windows, get_window_rect, bring_window_to_front
from detection import Detector
from overlay import OverlayWindow

import pyautogui

# Strong per-widget dark style to override native white backgrounds
DARK_INPUT_STYLE = """
background-color: #1e1e1e; color: #eaeaea; border: 1px solid #333; padding: 4px;
QComboBox QAbstractItemView { background-color: #1e1e1e; color: #eaeaea; selection-background-color: #3a7bd5; }
QPushButton { background-color: #2a2a2a; border: 1px solid #333; }
"""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AION2 AutoSim - Combat Macro')
        self.resize(900, 700)
        self._central = QtWidgets.QWidget()
        self.setCentralWidget(self._central)
        layout = QtWidgets.QVBoxLayout(self._central)

        # Top controls
        controls = QtWidgets.QHBoxLayout()
        self.win_combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton('Refresh Windows')
        self.select_btn = QtWidgets.QPushButton('Select Window')
        # enforce dark style on top controls
        self.win_combo.setStyleSheet(DARK_INPUT_STYLE)
        self.refresh_btn.setStyleSheet(DARK_INPUT_STYLE)
        self.select_btn.setStyleSheet(DARK_INPUT_STYLE)
        controls.addWidget(self.win_combo)
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.select_btn)

        layout.addLayout(controls)

        # Model and target
        h2 = QtWidgets.QHBoxLayout()
        self.model_path_edit = QtWidgets.QLineEdit()
        self.model_browse = QtWidgets.QPushButton('Browse Model')
        self.target_edit = QtWidgets.QLineEdit('Highland Sparkle')
        self.conf_spin = QtWidgets.QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 0.99)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.4)
        h2.addWidget(QtWidgets.QLabel('Model:'))
        h2.addWidget(self.model_path_edit)
        h2.addWidget(self.model_browse)
        h2.addWidget(QtWidgets.QLabel('Target label:'))
        h2.addWidget(self.target_edit)
        h2.addWidget(QtWidgets.QLabel('Conf:'))
        h2.addWidget(self.conf_spin)
        # enforce dark style on model/target inputs
        self.model_path_edit.setStyleSheet(DARK_INPUT_STYLE)
        self.model_browse.setStyleSheet(DARK_INPUT_STYLE)
        self.target_edit.setStyleSheet(DARK_INPUT_STYLE)
        self.conf_spin.setStyleSheet(DARK_INPUT_STYLE)
        layout.addLayout(h2)

        # Start/stop
        h3 = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton('Start')
        self.stop_btn = QtWidgets.QPushButton('Stop')
        self.overlay_chk = QtWidgets.QCheckBox('Show overlay')
        self.start_btn.setStyleSheet(DARK_INPUT_STYLE)
        self.stop_btn.setStyleSheet(DARK_INPUT_STYLE)
        h3.addWidget(self.start_btn)
        h3.addWidget(self.stop_btn)
        h3.addWidget(self.overlay_chk)
        layout.addLayout(h3)

        # Terminal/log
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        # Connections
        self.refresh_btn.clicked.connect(self.refresh_windows)
        self.model_browse.clicked.connect(self.browse_model)
        self.select_btn.clicked.connect(self.select_window)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.overlay_chk.stateChanged.connect(self.toggle_overlay)

        self.selected_hwnd = None
        self.capture_rect = None
        self.detector = None
        self.overlay = None
        self._click_history = []

        logger.add(self._log_sink)

        self.refresh_windows()

    def _log_sink(self, message):
        # loguru sink writes message object; append text to GUI
        try:
            txt = message.strip('\n')
        except Exception:
            txt = str(message)
        QtCore.QMetaObject.invokeMethod(self.log_view, 'appendPlainText', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, txt))

    def refresh_windows(self):
        self.win_combo.clear()
        wins = enum_windows()
        for hwnd, title in wins:
            self.win_combo.addItem(f'{title} (0x{hwnd:08x})', userData=hwnd)

    def browse_model(self):
        # First, check ./models for any bundled .pt files and pick the first one
        models_dir = os.path.join(os.getcwd(), 'models')
        if os.path.isdir(models_dir):
            for f in os.listdir(models_dir):
                if f.lower().endswith('.pt'):
                    full = os.path.join(models_dir, f)
                    logger.info(f'Using model from ./models: {full}')
                    self.model_path_edit.setText(full)
                    return

        # If no model found, run the helper PowerShell script to download one, then re-check.
        script = os.path.join(os.getcwd(), 'scripts', 'download_default_model.ps1')
        if os.path.exists(script):
            logger.info('No model in ./models; running download helper...')

            def _run_script():
                try:
                    # Use PowerShell to run the script with bypass execution policy
                    import subprocess
                    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script]
                    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
                    logger.info(proc.stdout)
                    if proc.returncode != 0:
                        logger.error(f'Download script failed: {proc.returncode} {proc.stderr}')
                    # Re-check models folder
                    if os.path.isdir(models_dir):
                        for f in os.listdir(models_dir):
                            if f.lower().endswith('.pt'):
                                full = os.path.join(models_dir, f)
                                logger.info(f'Found downloaded model: {full}')
                                QtCore.QMetaObject.invokeMethod(self.model_path_edit, 'setText', QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, full))
                                return
                    # If still not found, open file dialog for manual selection
                    QtCore.QMetaObject.invokeMethod(self, '_open_model_file_dialog', QtCore.Qt.QueuedConnection)
                except Exception as e:
                    logger.exception('Failed running download helper: {}', e)

            t = threading.Thread(target=_run_script, daemon=True)
            t.start()
            return

        # Fallback: open file dialog if no script is available
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select model weights (YOLO .pt)', os.getcwd(), 'PyTorch files (*.pt);;All Files (*)')
        if path:
            self.model_path_edit.setText(path)

    @QtCore.pyqtSlot()
    def _open_model_file_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select model weights (YOLO .pt)', os.getcwd(), 'PyTorch files (*.pt);;All Files (*)')
        if path:
            self.model_path_edit.setText(path)

    def select_window(self):
        idx = self.win_combo.currentIndex()
        if idx < 0:
            return
        hwnd = self.win_combo.itemData(idx)
        self.selected_hwnd = hwnd
        bring_window_to_front(hwnd)
        rect = get_window_rect(hwnd)
        self.capture_rect = rect
        logger.info(f'Selected window hwnd=0x{hwnd:08x}, rect={rect}')
        if self.overlay and self.overlay.isVisible():
            left, top, right, bottom = rect
            self.overlay.set_geometry(left, top, right - left, bottom - top)

    def start(self):
        if not self.capture_rect:
            logger.warning('No window selected')
            return
        model_path = self.model_path_edit.text().strip()
        if not model_path or not os.path.exists(model_path):
            logger.warning('Model path invalid; please provide trained YOLO weights (.pt)')
            return
        target = self.target_edit.text().strip()
        conf = float(self.conf_spin.value())

        self.detector = Detector(model_path=model_path, target_label=target, conf_thr=conf)
        self.detector.start(self.capture_rect, self._on_detect)
        logger.info('Detection started')

    def get_default_model(self):
        # Removed automatic download to avoid runtime import of heavy native libraries (torch)
        # Instead, check for a model file in ./models and prefer that.
        models_dir = os.path.join(os.getcwd(), 'models')
        if os.path.isdir(models_dir):
            for f in os.listdir(models_dir):
                if f.lower().endswith('.pt'):
                    full = os.path.join(models_dir, f)
                    logger.info(f'Found bundled model: {full}')
                    self.model_path_edit.setText(full)
                    return
        logger.warning('No bundled model found in ./models. Please place your .pt weights in that folder or run the provided download script (scripts/download_default_model.ps1).')

    def stop(self):
        if self.detector:
            self.detector.stop()
            self.detector = None
            logger.info('Detection stopped')

    def toggle_overlay(self, state):
        if state:
            if not self.overlay:
                self.overlay = OverlayWindow()
            if self.capture_rect:
                left, top, right, bottom = self.capture_rect
                self.overlay.set_geometry(left, top, right - left, bottom - top)
            self.overlay.show()
        else:
            if self.overlay:
                self.overlay.hide()

    def _on_detect(self, target, screen_point, img, detections):
        # Called from detector thread; marshal to main thread
        QtCore.QMetaObject.invokeMethod(self, '_handle_detect', QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(object, target), QtCore.Q_ARG(object, screen_point), QtCore.Q_ARG(object, detections))

    @QtCore.pyqtSlot(object, object, object)
    def _handle_detect(self, target, screen_point, detections):
        x, y = screen_point
        # Log and click
        logger.info(f'Detected target {target["label"]} conf={target["conf"]:.2f} at {x},{y} - clicking')
        # Overlay update
        if self.overlay and self.overlay.isVisible():
            # Map detections to overlay coords (they are in capture window coords)
            viz = []
            for d in detections:
                bx = d['box']
                label = d['label']
                viz.append((bx, label))
            pts = [(screen_point[0] - self.capture_rect[0], screen_point[1] - self.capture_rect[1])]
            self.overlay.update_visuals(viz, pts)

        # Perform double click
        try:
            # Ensure game window is foreground
            if self.selected_hwnd:
                bring_window_to_front(self.selected_hwnd)
                time.sleep(0.02)
            pyautogui.FAILSAFE = False
            pyautogui.doubleClick(x, y)
            self._click_history.append(((x, y), time.time()))
        except Exception as e:
            logger.exception('Click failed: {}', e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    # Apply dark palette
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
    palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(18, 18, 18))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(44, 44, 44))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 45))
    palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    app.setPalette(palette)

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
