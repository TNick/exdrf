import os

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QApplication

from exdrf_dev.__version__ import __version__
from exdrf_dev.select_model_show.main_window import MainWindow


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
    else:
        raise ValueError("No connection string provided.")

    c_string = args[0]
    if "memory" in c_string:
        raise ValueError("Memory connection string is not supported.")

    # We want to start with a fresh database, so we need to remove the old one.
    if c_string.startswith("sqlite:///"):
        c_string = c_string.replace("sqlite:///", "")

    # if os.path.exists(c_string):
    #     bkp_up = os.path.join(
    #         os.path.dirname(c_string), "backup_" + os.path.basename(c_string)
    #     )
    #     if not os.path.exists(bkp_up):
    #         shutil.copyfile(c_string, bkp_up)
    #     os.remove(c_string)
    populate = not os.path.exists(c_string)

    c_string = "sqlite:///" + c_string

    # Create the GUI.
    mw = MainWindow(c_string=c_string, populate=populate)
    signal.signal(signal.SIGINT, mw.signal_handler)
    mw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
