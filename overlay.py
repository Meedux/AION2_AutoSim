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
        self.detections = []  # list of detection dicts
        self.points = []  # list of (x,y) in overlay coords

    def set_geometry(self, left, top, width, height):
        self.setGeometry(left, top, width, height)

    def update_visuals(self, detections, points):
        # detections: list of dicts with keys 'label','box', optionally 'hp_pct','mp_pct','circle'
        self.detections = detections
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw detections
        for d in self.detections:
            label = d.get('label', '')
            box = d.get('box', None)

            if label == 'map' and 'circle' in d:
                cx, cy, r = d['circle']
                # circle coordinates are relative to capture; draw as circle
                pen_map = QtGui.QPen(QtGui.QColor(0, 200, 0, 180))
                pen_map.setWidth(3)
                painter.setPen(pen_map)
                painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 200, 0, 40)))
                painter.drawEllipse(QtCore.QPointF(cx, cy), r, r)
                painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 200)))
                painter.drawText(cx - 10, cy - r - 6, 'map')
                continue

            if box is not None:
                x1, y1, x2, y2 = box
                # draw bounding box
                pen = QtGui.QPen(QtGui.QColor(0, 255, 0, 200))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(QtGui.QBrush())
                painter.drawRect(x1, y1, x2 - x1, y2 - y1)
                painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200, 200)))
                painter.drawText(x1, y1 - 6, label)

                # Draw HP bar if available (red)
                hp = d.get('hp_pct', None)
                if hp is not None:
                    bar_w = max(40, x2 - x1)
                    bar_h = 8
                    bx = x1
                    by = y1 - 18
                    # background
                    painter.setPen(QtGui.QPen(QtGui.QColor(60, 60, 60, 180)))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(40, 40, 40, 180)))
                    painter.drawRect(bx, by, bar_w, bar_h)
                    # fill
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(220, 20, 20, 200)))
                    painter.setPen(QtGui.QPen(QtGui.QColor(180, 20, 20, 200)))
                    painter.drawRect(bx, by, int(bar_w * max(0.0, min(1.0, hp))), bar_h)
                    # text on top
                    painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 230)))
                    painter.drawText(bx + 4, by + bar_h - 1, f"HP {int(hp*100)}%")

                # Draw MP bar if available (blue)
                mp = d.get('mp_pct', None)
                if mp is not None:
                    bar_w = max(40, x2 - x1)
                    bar_h = 8
                    bx = x1
                    by = y1 - 28
                    # background
                    painter.setPen(QtGui.QPen(QtGui.QColor(60, 60, 60, 180)))
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(40, 40, 40, 180)))
                    painter.drawRect(bx, by, bar_w, bar_h)
                    # fill
                    painter.setBrush(QtGui.QBrush(QtGui.QColor(40, 120, 220, 200)))
                    painter.setPen(QtGui.QPen(QtGui.QColor(30, 100, 200, 200)))
                    painter.drawRect(bx, by, int(bar_w * max(0.0, min(1.0, mp))), bar_h)
                    # text on top
                    painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 230)))
                    painter.drawText(bx + 4, by + bar_h - 1, f"MP {int(mp*100)}%")

        # Draw click points as red boxes
        pen_red = QtGui.QPen(QtGui.QColor(255, 0, 0, 200))
        pen_red.setWidth(2)
        painter.setPen(pen_red)
        painter.setBrush(QtGui.QBrush())  # No fill
        for (x, y) in self.points:
            size = 20
            painter.drawRect(x - size//2, y - size//2, size, size)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = OverlayWindow()
    w.set_geometry(100, 100, 800, 600)
    w.show()
    sys.exit(app.exec_())