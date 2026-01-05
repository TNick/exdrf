from typing import Optional, cast

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication, QMenu, QStyle, QWidget


class StayOpenMenu(QMenu):
    """A menu that stays open until the user clicks outside of it
    or chooses an actionable item.

    Based on https://gist.github.com/mpaperno/cd65ebf255945a6c1272fdf9e3c0746c
    """

    _about_to_hide: bool

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._about_to_hide = False

        self.aboutToHide.connect(self.on_about_to_hide)
        self.aboutToShow.connect(self.on_about_to_show)

        self.installEventFilter(self)

    def on_about_to_hide(self):
        self._about_to_hide = True

    def on_about_to_show(self):
        self._about_to_hide = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore

        while True:
            if obj is not self:
                break
            if self._about_to_hide:
                break

            active_ac = self.activeAction()
            if not active_ac:
                break
            if not active_ac.isEnabled():
                break
            if active_ac.isSeparator():
                break
            if active_ac.menu():
                break
            if not active_ac.isCheckable():
                break

            style = QApplication.style()
            assert style is not None

            if event.type() == QEvent.Type.KeyPress:
                key = cast("QKeyEvent", event).key()
                if not (
                    key == Qt.Key.Key_Return
                    or key == Qt.Key.Key_Enter
                    or (
                        key == Qt.Key.Key_Space
                        and style.styleHint(
                            QStyle.StyleHint.SH_Menu_SpaceActivatesItem,
                            None,
                            self,
                        )
                    )
                ):
                    break
            elif event.type() != QEvent.Type.MouseButtonRelease:
                break

            active_ac.trigger()
            event.accept()
            return True

        return super().eventFilter(obj, event)
