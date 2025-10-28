from PyQt5 import QtWidgets, QtCore, QtGui
import sys


class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Make window transparent and click-through
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.rects = []  # list of (box, label)
        self.points = []  # list of (x,y)

    def set_geometry(self, left, top, width, height):
        self.setGeometry(left, top, width, height)

    def update_visuals(self, detections, points):
        self.rects = detections
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor(0, 255, 0, 200))
        pen.setWidth(2)
        painter.setPen(pen)

        # Draw bounding boxes
        for d in self.rects:
            (x1, y1, x2, y2), label = d
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            painter.drawText(x1, y1 - 4, label)

        # Draw click points
        brush = QtGui.QBrush(QtGui.QColor(255, 0, 0, 200))
        painter.setBrush(brush)
        for (x, y) in self.points:
            painter.drawEllipse(QtCore.QPointF(x, y), 6, 6)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = OverlayWindow()
    w.set_geometry(100, 100, 800, 600)
    w.show()
    sys.exit(app.exec_())
