from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QCalendarWidget, QDialog, QPushButton, QVBoxLayout


class CalendarPopup(QDialog):
    def __init__(self, current_date: QDate, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date")
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(
            current_date if current_date.isValid() else QDate.currentDate()
        )
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.calendar)
        layout.addWidget(self.ok_btn)

    def selectedDate(self):
        return self.calendar.selectedDate()
