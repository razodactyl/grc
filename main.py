import sys

from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QPushButton, QProgressBar, QLabel, QDesktopWidget

from table_widget import TableWidget
from image_widget import ImageWidget
from image_widget_controls import ImageControlsWidget
from file_list_widget import FileListWidget
from class_list_widget import ClassListWidget


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.title = "Glorified Rectangle Creator"
        self.setWindowTitle(self.title)

        self.data_dir = ""

        self.left = 0
        self.top = 0
        self.width = 1024
        self.height = 768
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.tab_panel = TableWidget(self)

        file_list = FileListWidget()
        self.tab_panel.tab1.layout.addWidget(file_list)

        class_list = ClassListWidget()
        self.tab_panel.tab1.layout.addWidget(class_list)

        self.image_panel = ImageWidget(self)
        self.image_panel_controls = ImageControlsWidget()
        self.tab_panel.tab2.layout.addWidget(self.image_panel)
        self.tab_panel.tab2.layout.addWidget(self.image_panel_controls)

        self.setCentralWidget(self.tab_panel)

        self.center()

        self.show()

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)

    def loadDataDirectory(self):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.data_dir = d
        self.loaded_directory_label.setText(self.data_dir)
        return d

    def openFileNamesDialog(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        files = QFileDialog.getExistingDirectory(self, "Select Directory")
        # files, _ = QFileDialog.getOpenFileNames(self, "QFileDialog.getOpenFileNames()", "",
        #                                         "All Files (*);;Python Files (*.py)", options=options)
        if files:
            print(files)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
