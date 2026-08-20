import sys

from PySide6.QtWidgets import QApplication

from camera_lab.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Mini Camera Lab")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
