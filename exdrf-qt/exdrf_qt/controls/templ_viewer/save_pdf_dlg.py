from typing import TYPE_CHECKING, cast

from PyQt5.QtCore import QMarginsF
from PyQt5.QtGui import QPageLayout, QPageSize
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401


class SavePdfDialog(QFileDialog, QtUseContext):
    def __init__(self, ctx: "QtContext", parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle(self.t("templ.save-pdf.title", "Save PDF As..."))
        self.setAcceptMode(QFileDialog.AcceptSave)
        self.setNameFilter(self.t("templ.save-pdf.filter", "PDF Files (*.pdf)"))
        self.setOption(QFileDialog.DontUseNativeDialog)

        # Create a widget for layout settings
        self.layout_widget = QWidget()
        layout = QVBoxLayout(self.layout_widget)

        # Page Size
        self.page_size_label = QLabel(
            self.t("templ.save-pdf.page-size", "Page Size:")
        )
        layout.addWidget(self.page_size_label)
        self.page_size_combo = QComboBox()

        for size_name, size_id in (
            (
                self.t("templ.save-pdf.page-size.a4", "A4"),
                QPageSize.PageSizeId.A4,
            ),
            (
                self.t("templ.save-pdf.page-size.a3", "A3"),
                QPageSize.PageSizeId.A3,
            ),
            (
                self.t("templ.save-pdf.page-size.a2", "A2"),
                QPageSize.PageSizeId.A2,
            ),
            (
                self.t("templ.save-pdf.page-size.a1", "A1"),
                QPageSize.PageSizeId.A1,
            ),
            (
                self.t("templ.save-pdf.page-size.a0", "A0"),
                QPageSize.PageSizeId.A0,
            ),
            (
                self.t("templ.save-pdf.page-size.b5", "B5"),
                QPageSize.PageSizeId.B5,
            ),
            (
                self.t("templ.save-pdf.page-size.letter", "Letter"),
                QPageSize.PageSizeId.Letter,
            ),
            (
                self.t("templ.save-pdf.page-size.legal", "Legal"),
                QPageSize.PageSizeId.Legal,
            ),
            (
                self.t("templ.save-pdf.page-size.executive", "Executive"),
                QPageSize.PageSizeId.Executive,
            ),
            (
                self.t("templ.save-pdf.page-size.b0", "B0"),
                QPageSize.PageSizeId.B0,
            ),
            (
                self.t("templ.save-pdf.page-size.b1", "B1"),
                QPageSize.PageSizeId.B1,
            ),
            (
                self.t("templ.save-pdf.page-size.b10", "B10"),
                QPageSize.PageSizeId.B10,
            ),
            (
                self.t("templ.save-pdf.page-size.b2", "B2"),
                QPageSize.PageSizeId.B2,
            ),
            (
                self.t("templ.save-pdf.page-size.b3", "B3"),
                QPageSize.PageSizeId.B3,
            ),
            (
                self.t("templ.save-pdf.page-size.b4", "B4"),
                QPageSize.PageSizeId.B4,
            ),
            (
                self.t("templ.save-pdf.page-size.b6", "B6"),
                QPageSize.PageSizeId.B6,
            ),
            (
                self.t("templ.save-pdf.page-size.b7", "B7"),
                QPageSize.PageSizeId.B7,
            ),
            (
                self.t("templ.save-pdf.page-size.b8", "B8"),
                QPageSize.PageSizeId.B8,
            ),
            (
                self.t("templ.save-pdf.page-size.b9", "B9"),
                QPageSize.PageSizeId.B9,
            ),
        ):
            self.page_size_combo.addItem(size_name, size_id)
        layout.addWidget(self.page_size_combo)

        # Orientation
        self.orientation_label = QLabel(
            self.t("templ.save-pdf.orientation", "Orientation:")
        )
        layout.addWidget(self.orientation_label)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem(
            self.t("templ.save-pdf.orientation.portrait", "Portrait"),
            QPageLayout.Orientation.Portrait,
        )
        self.orientation_combo.addItem(
            self.t("templ.save-pdf.orientation.landscape", "Landscape"),
            QPageLayout.Orientation.Landscape,
        )
        layout.addWidget(self.orientation_combo)

        # Margins
        self.left_margin_label = QLabel(
            self.t("templ.save-pdf.left-margin", "Left Margin:")
        )
        layout.addWidget(self.left_margin_label)
        self.left_margin = QDoubleSpinBox()
        self.left_margin.setRange(0, 100)
        self.left_margin.setValue(20)
        layout.addWidget(self.left_margin)

        self.right_margin_label = QLabel(
            self.t("templ.save-pdf.right-margin", "Right Margin:")
        )
        layout.addWidget(self.right_margin_label)
        self.right_margin = QDoubleSpinBox()
        self.right_margin.setRange(0, 100)
        self.right_margin.setValue(10)
        layout.addWidget(self.right_margin)

        self.top_margin_label = QLabel(
            self.t("templ.save-pdf.top-margin", "Top Margin:")
        )
        layout.addWidget(self.top_margin_label)
        self.top_margin = QDoubleSpinBox()
        self.top_margin.setRange(0, 100)
        self.top_margin.setValue(10)
        layout.addWidget(self.top_margin)

        self.bottom_margin_label = QLabel(
            self.t("templ.save-pdf.bottom-margin", "Bottom Margin:")
        )
        layout.addWidget(self.bottom_margin_label)
        self.bottom_margin = QDoubleSpinBox()
        self.bottom_margin.setRange(0, 100)
        self.bottom_margin.setValue(10)
        layout.addWidget(self.bottom_margin)

        # Add a spacer to push the layout widget to the right
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        # Add the layout widget to the dialog
        main_layout = self.layout()
        if main_layout is not None:
            main_layout = cast(QGridLayout, main_layout)
            sidebar_rows = main_layout.rowCount() - 1
            main_layout.addWidget(self.layout_widget, 0, 3, sidebar_rows, 1)

    def get_page_layout(self):
        """Returns the configured QPageLayout."""
        page_size = QPageSize(self.page_size_combo.currentData())
        orientation = self.orientation_combo.currentData()
        margins = QMarginsF(
            self.left_margin.value(),
            self.top_margin.value(),
            self.right_margin.value(),
            self.bottom_margin.value(),
        )
        return QPageLayout(
            page_size, orientation, margins, QPageLayout.Unit.Millimeter
        )
