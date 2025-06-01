import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

# Initializes and runs the PyQt5 application
# Creates a QApplication instance, instantiates the MainWindow,
# shows the main window, and starts the application's event loop.
# The application exits when the event loop finishes.
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()