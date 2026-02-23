import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('HoverDesk Test')
        self.setGeometry(500, 300, 400, 200)
        layout = QVBoxLayout()
        layout.addWidget(QLabel('UI IS WORKING'))
        btn = QPushButton('Close')
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
