from typing import cast

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QApplication

from exdrf_dev.__version__ import __version__
from exdrf_dev.app.main_window import MainWindow


def init_qt_info():
    """CuteLog changes these so we need to change them back."""

    QCoreApplication.setOrganizationName("ExDRF")
    QCoreApplication.setOrganizationDomain("exdrf.dev")
    QCoreApplication.setApplicationName("ExDRF")
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setAttribute(
        Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True
    )


def set_style():
    app = cast(QApplication, QApplication.instance())
    app.setStyleSheet(
        """
        QHeaderView::section {
            background-color: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #A1A1A1, stop: 0.5 #909090,
                stop: 0.6 #838383, stop:1 #A5A5A5
            );
            color: white;
            padding-left: 2px;
            border: 1px solid #6c6c6c;
        }

        QHeaderView::section:checked {
            background-color: red;
        }

        QTreeView {
            alternate-background-color: #e1f5e2;
            show-decoration-selected: 1;
        }

        QTreeView::item {
            border: 1px solid #d9d9d9;
            border-top-color: transparent;
            border-bottom-color: transparent;
            padding: 4px;
        }

        QTreeView::item:hover {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #e7effd, stop: 1 #cbdaf1
            );
            border: 1px solid #bfcde4;
        }

        QTreeView::item:selected {
            border: 1px solid #567dbc;
        }

        QTreeView::item:selected:active{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6ea1f1, stop: 1 #567dbc
            );
        }

        QTreeView::item:selected:!active {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6b9be8, stop: 1 #577fbf
            );
        }

        """
    )


def main():
    import signal
    import sys

    import PyQt5.QtWebEngineWidgets  # noqa: F401

    from exdrf_dev.db.models import Base  # noqa: F401, F403

    init_qt_info()

    app = QApplication(sys.argv)
    args = list(app.arguments())
    if len(args) > 1:
        args = args[1:]

    if len(args) > 0:
        db_string = args[0]
    else:
        db_string = "sqlite:///:memory:"

    # Create the GUI.
    mw = MainWindow(db_string=db_string, Base=Base)
    signal.signal(signal.SIGINT, mw.signal_handler)
    mw.show()
    set_style()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
