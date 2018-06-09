import numpy as np

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker, QWaitCondition, QPoint
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QImage, QPixmap, QPainter, QBrush, QColor

from collections import namedtuple

State = namedtuple('State', 'mouse_pos drag_start_pos drag_end_pos dragging bounding_boxes selected_class')


class BoundingBox(object):
    def __init__(self, x=0, y=0, w=0, h=0, selected=False):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.selected = selected


def make_default_state():
    return State(
        mouse_pos=[0,0],
        drag_start_pos=[0,0],
        drag_end_pos=[0,0],
        dragging=False,
        bounding_boxes=[],
        selected_class=0
    )


class RenderThread(QThread):
    renderedImage = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super(RenderThread, self).__init__(parent)

        self.mutex = QMutex()

        self.state = make_default_state()

        self.condition = QWaitCondition()

        self.restart = False
        self.abort = False

    def __del__(self):
        self.mutex.lock()
        self.abort = True
        self.condition.wakeOne()
        self.mutex.unlock()

        self.wait()

    def render(self, state=None):
        locker = QMutexLocker(self.mutex)

        # update renderable state
        if state:
            print("Update render state")
            print("state =>", state)
            self.state = state

        if not self.isRunning():
            self.start(QThread.LowPriority)
        else:
            self.restart = True
            self.condition.wakeOne()

    def run(self):

        im_np = np.ones((800, 800, 3), dtype=np.uint8)
        im_np = np.transpose(im_np, (1, 0, 2)).copy()
        image = QImage(im_np, im_np.shape[1], im_np.shape[0], QImage.Format_RGB888)
        base = QImage("/Users/jonathan/Documents/Scan 1.jpeg")
        base = base.scaled(image.size(), Qt.KeepAspectRatio)

        while True:
            self.mutex.lock()

            state = self.state

            self.mutex.unlock()

            # im_np = np.ones((1000, 1000, 3), dtype=np.uint8)
            # im_np = np.transpose(im_np, (1,0,2)).copy()
            # image = QImage(im_np, im_np.shape[1], im_np.shape[0], QImage.Format_RGB888)

            painter = QPainter()

            painter.begin(image)

            brush = QBrush(QColor("#FF00FF"))
            painter.setBrush(brush)
            painter.setPen(Qt.white)

            painter.fillRect(image.rect(), Qt.blue)

            painter.drawImage(0, 0, base)

            if state.dragging:
                painter.setOpacity(0.2)
                painter.drawRect(
                    state.drag_start_pos[0],
                    state.drag_start_pos[1],
                    state.mouse_pos[0] - state.drag_start_pos[0],
                    state.mouse_pos[1] - state.drag_start_pos[1]
                )

            for box in state.bounding_boxes:
                if box.selected:
                    painter.setOpacity(0.5)
                    painter.drawRect(
                        box.x,
                        box.y,
                        10,
                        10

                    )
                else:
                    painter.setOpacity(0.2)
                painter.drawRect(
                    box.x,
                    box.y,
                    box.w,
                    box.h
                )

            # painter.drawLine(0, state.mouse_pos[1], image.width(), state.mouse_pos[1])
            # painter.drawLine(state.mouse_pos[0], 0, state.mouse_pos[0], image.height())

            painter.end()

            if not self.restart:
                self.renderedImage.emit(image)

            self.mutex.lock()
            if not self.restart:
                self.condition.wait(self.mutex)
            self.restart = False
            self.mutex.unlock()


class ImageWidget(QLabel):
    def __init__(self, parent):
        super(QLabel, self).__init__(parent)

        self.thread = RenderThread()
        self.base_image = QPixmap()
        self.pixmap = QPixmap()
        self.thread.renderedImage.connect(self.updatePixmap)
        # self.pixmap = None
        # im_np = np.ones((1800, 2880, 3), dtype=np.uint8)
        # im_np = np.transpose(im_np, (1,0,2)).copy()
        # qimage = QImage(im_np, im_np.shape[1], im_np.shape[0], QImage.Format_RGB888)
        # self.pixmap = QPixmap(qimage)
        # self.pixmap = self.pixmap.scaled(640, 480, Qt.KeepAspectRatio)
        # self.setPixmap(self.pixmap)
        # self.pixmap.fill(Qt.white)
        self.setCursor(Qt.CrossCursor)
        self.thread.render()
        # https://stackoverflow.com/questions/7829829/pyqt4-mousemove-event-without-mousepress
        self.setMouseTracking(True)

        self.state = make_default_state()

    def loadImage(self, path):
        self.base_image = QPixmap(path)

    def is_point_in_box(self, x, y, box):
        return x > box.x and x < (box.x+box.w) and y > box.y and y < (box.y+box.h)

    def get_box_area(self, box):
        return box.w * box.h

    def mouseMoveEvent(self, event):
        mouse_x = event.pos().x()
        mouse_y = event.pos().y()

        # boxes = self.state.bounding_boxes
        # for box in boxes:
        #     box.selected = self.is_point_in_box(mouse_x, mouse_y, box)
        #     self.thread.render(self.state)

        self.state = self.state._replace(mouse_pos=[event.pos().x(), event.pos().y()])
        self.thread.render(self.state)

    def mousePressEvent(self, event):
        mouse_x = event.pos().x()
        mouse_y = event.pos().y()

        boxes = self.state.bounding_boxes
        for box in boxes:
            box.selected = self.is_point_in_box(mouse_x, mouse_y, box)
            self.thread.render(self.state)

        self.state = self.state._replace(bounding_boxes=boxes)

        if event.buttons() & Qt.LeftButton:
            self.state = self.state._replace(
                drag_start_pos=[mouse_x, mouse_y],
                dragging=True,
            )

    def mouseReleaseEvent(self, event):
        # if event.buttons() & Qt.LeftButton:
        if self.state.dragging:
            self.state = self.state._replace(
                drag_end_pos=[event.pos().x(), event.pos().y()],
                dragging=False
            )

            bounding_boxes = self.state.bounding_boxes

            x = self.state.drag_start_pos[0]
            y = self.state.drag_start_pos[1]
            w = self.state.drag_end_pos[0] - x
            h = self.state.drag_end_pos[1] - y

            box = BoundingBox(x=x, y=y, w=w, h=h, selected=True)

            if self.get_box_area(box) > 100:
                bounding_boxes.append(box)

            self.state = self.state._replace(
                bounding_boxes=bounding_boxes
            )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        if self.pixmap.isNull():
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "No image loaded...")
            return

        painter.drawPixmap(QPoint(), self.pixmap)

    def updatePixmap(self, image):
        self.pixmap = QPixmap.fromImage(image)
        self.update()
