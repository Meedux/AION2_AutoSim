"""Overlay window using PySide6. Draws boxes and labels on a transparent, click-through window.

This module exposes OverlayWindow which can be updated with a list of detections.
"""
from typing import List, Tuple
import ctypes
import sys
from loguru import logger
from PySide6 import QtCore, QtGui, QtWidgets
import win32con
import win32gui


class OverlayWindow(QtWidgets.QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
		# Make the widget ignore mouse events so it is click-through
		self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
		self.detections: List[dict] = []
		self.target_size = (0, 0)

	def make_clickthrough(self):
		hwnd = int(self.winId())
		ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
		ex_style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
		win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

	def update_overlay(self, detections: List[dict], target_size: Tuple[int, int]):
		self.detections = detections
		self.target_size = target_size
		self.update()

	def paintEvent(self, event: QtGui.QPaintEvent):
		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		pen = QtGui.QPen(QtGui.QColor(255, 0, 0, 200))
		pen.setWidth(2)
		painter.setPen(pen)
		font = QtGui.QFont("Segoe UI", 10)
		painter.setFont(font)

		w, h = self.target_size
		for d in self.detections:
			# Expect detection with x,y,width,height in pixel coords relative to target_size
			try:
				x = int(d["x"])
				y = int(d["y"])
				ww = int(d["width"])
				hh = int(d["height"])
				cls = str(d.get("class", ""))
				conf = d.get("confidence", 0)
			except Exception:
				continue
			rect = QtCore.QRect(x, y, ww, hh)
			painter.drawRect(rect)
			text = f"{cls} {conf:.2f}" if isinstance(conf, (float, int)) else f"{cls}"
			text_bg = QtGui.QColor(0, 0, 0, 160)
			metrics = painter.fontMetrics()
			tw = metrics.horizontalAdvance(text) + 6
			th = metrics.height() + 2
			painter.fillRect(x, max(0, y - th), tw, th, text_bg)
			painter.setPen(QtGui.QColor(255, 255, 255))
			painter.drawText(x + 3, max(0, y - 3), text)

