from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QApplication

from exdrf_dev.__version__ import __version__
from exdrf_dev.field_ed_show.main_window import MainWindow


def init_qt_info():
    """CuteLog changes these so we need to change them back."""

    QCoreApplication.setOrganizationName("ExDRF")
    QCoreApplication.setOrganizationDomain("exdrf.dev")
    QCoreApplication.setApplicationName("Field Editor Showcase")
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setAttribute(
        Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True
    )


def main():
    import signal
    import sys

    init_qt_info()

    app = QApplication(sys.argv)
    args = list(app.arguments())
    if len(args) > 1:
        args = args[1:]

    # Create the GUI.
    mw = MainWindow()
    signal.signal(signal.SIGINT, mw.signal_handler)
    mw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
