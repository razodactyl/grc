from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QPushButton, QComboBox, QSizePolicy


class ImageControlsWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.classes = []

        self.init_ui()

    def init_ui(self):
        prevButton = QPushButton("Previous")
        nextButton = QPushButton("Next")

        classSelect = QComboBox(self)
        classSelect.addItem("Test")
        classSelect.activated[str].connect(self.combo_changed)

        prevButton.clicked.connect(self.clicked_prev)
        nextButton.clicked.connect(self.clicked_next)

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        hbox = QHBoxLayout()
        hbox.addWidget(prevButton)
        hbox.addWidget(nextButton)
        hbox.addWidget(classSelect)

        self.setLayout(hbox)

    def clicked_prev(self):
        print("Clicked prev button.")

    def clicked_next(self):
        print("Clicked next button.")

    def combo_changed(self, text):
        print(text)
