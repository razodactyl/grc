import numpy as np

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker, QWaitCondition, QPoint
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QPainter, QBrush, QColor

from collections import namedtuple

State = namedtuple('State', 'mouse_pos drag_start_pos drag_end_pos dragging bounding_boxes selected_class')
def make_default_state():
    return State(
        mouse_pos=[0,0],
        drag_start_pos=[0,0],
        drag_end_pos=[0,0],
        dragging=False,
        bounding_boxes=[],
        selected_class=0
    )


class BoundingBox(object):
    def __init__(self, x=0, y=0, w=0, h=0, selected=False):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.selected = selected

    def xy_in_bounds(self, x, y):
        return self.x < x < (self.x + self.w) and self.y < y < (self.y + self.h)

    def get_area(self):
        return self.w * self.h

    def draw(self, painter):
        if self.selected:
            painter.setOpacity(0.5)
        else:
            painter.setOpacity(0.2)
        painter.drawRect(
            self.x,
            self.y,
            self.w,
            self.h
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

        self.base_image = None
        self.canvas = self.make_canvas(800, 600)

    def __del__(self):
        self.mutex.lock()
        self.abort = True
        self.condition.wakeOne()
        self.mutex.unlock()

        self.wait()

    def make_canvas(self, width, height):
        im_np = np.ones((width, height, 3), dtype=np.uint8)
        im_np = np.transpose(im_np, (1, 0, 2)).copy()
        canvas = QImage(im_np, im_np.shape[1], im_np.shape[0], QImage.Format_RGB888)
        return canvas

    def load_image(self, path):
        image = QImage(path)
        self.mutex.lock()
        self.base_image = image

        self.canvas = self.make_canvas(self.base_image.width(), self.base_image.height())

        self.mutex.unlock()

    def render(self, state=None):
        locker = QMutexLocker(self.mutex)

        # update renderable state
        if state:
            # print("Update render state")
            # print("state =>", state)
            self.state = state

        if not self.isRunning():
            self.start(QThread.LowPriority)
        else:
            self.restart = True
            self.condition.wakeOne()

    def run(self):
        while True:
            self.mutex.lock()
            state = self.state

            # if self.base_image:
            #     image = self.base_image
            # else:
            #     # base = QImage("/Users/jonathan/Documents/Scan 1.jpeg")
            #     # base = base.scaled(image.size(), Qt.KeepAspectRatio)

            self.mutex.unlock()

            painter = QPainter()

            painter.begin(self.canvas)

            brush = QBrush(QColor("#FF00FF"))
            painter.setBrush(brush)
            painter.setPen(Qt.white)

            # painter.fillRect(image.rect(), Qt.black)
            # painter.drawImage(image.rect(), image)

            if state.dragging:
                painter.setOpacity(0.2)
                painter.drawRect(
                    state.drag_start_pos[0],
                    state.drag_start_pos[1],
                    state.mouse_pos[0] - state.drag_start_pos[0],
                    state.mouse_pos[1] - state.drag_start_pos[1]
                )

            for box in state.bounding_boxes:
                box.draw(painter)

            painter.end()

            if not self.restart:
                self.renderedImage.emit(self.canvas)

            self.mutex.lock()
            if not self.restart:
                self.condition.wait(self.mutex)
            self.restart = False
            self.mutex.unlock()


class ImageWidget(QLabel):
    def __init__(self, parent):
        super(QLabel, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        self.thread = RenderThread()
        self.pixmap = QPixmap()
        self.thread.renderedImage.connect(self.updatePixmap)

        self.thread.render()
        # https://stackoverflow.com/questions/7829829/pyqt4-mousemove-event-without-mousepress

        self.state = make_default_state()

        self.thread.load_image("/Users/jonathan/Desktop/scanned on 20180605/Scan.jpeg")

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

        # event.buttons() => bitmask of ALL buttons - i.e we can perform multi click etc.
        if event.buttons() & Qt.LeftButton:
            boxes = self.state.bounding_boxes

            for box in boxes:
                box.selected = box.xy_in_bounds(mouse_x, mouse_y)
                self.thread.render(self.state)

            self.state = self.state._replace(bounding_boxes=boxes)

            self.state = self.state._replace(
                drag_start_pos=[mouse_x, mouse_y],
                dragging=True,
            )

    def mouseReleaseEvent(self, event):
        # event.button() (lack of 's') => button that caused the event.
        if event.button() == Qt.LeftButton:
            if self.state.dragging:
                self.state = self.state._replace(
                    drag_end_pos=[event.pos().x(), event.pos().y()],
                    dragging=False
                )

                bounding_boxes = self.state.bounding_boxes

                x1 = self.state.drag_start_pos[0]
                x2 = self.state.drag_end_pos[0]
                y1 = self.state.drag_start_pos[1]
                y2 = self.state.drag_end_pos[1]

                # Normalize coordinates (remove difference between start corner and end corner):
                # top left, bottom right => x,y,w,h

                min_x = min(x1, x2)
                min_y = min(y1, y2)
                max_x = max(x1, x2)
                max_y = max(y1, y2)

                x = min_x
                y = min_y
                w = max_x - min_x
                h = max_y - min_y

                box = BoundingBox(x=x, y=y, w=w, h=h, selected=True)

                if box.get_area() > 20:
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
