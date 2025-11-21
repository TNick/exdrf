from exdrf_qt.controls.pdf_viewer.image_graphics_view import ImageGraphicsView
from exdrf_qt.controls.pdf_viewer.pdf_image_viewer import PdfImageViewer
from exdrf_qt.controls.pdf_viewer.pdf_render_worker import PdfRenderWorker

__all__ = [
    "ImageGraphicsView",
    "PdfRenderWorker",
    "PdfImageViewer",
]


if __name__ == "__main__":
    import os
    import sys

    from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

    from exdrf_qt.context import LocalSettings, QtContext

    app = QApplication(sys.argv)

    # Create a minimal context for standalone usage
    top_widget = QWidget()
    top_widget.mdi_area = None  # type: ignore
    # Note: c_string and schema are DbConn parameters (parent class)
    ctx = QtContext(  # type: ignore[call-arg]
        c_string="",
        stg=LocalSettings(),
        top_widget=top_widget,
        schema=os.environ.get("EXDRF_DB_SCHEMA", "public"),
    )

    viewer = PdfImageViewer(ctx=ctx)
    viewer.resize(1000, 800)

    file_path, _ = QFileDialog.getOpenFileName(
        viewer,
        "Open PDF",
        "",
        "PDF Files (*.pdf);;All Files (*)",
    )

    if not file_path:
        sys.exit(0)

    try:
        viewer.set_pdf(file_path)
        viewer.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(viewer, "Error", str(e))
        sys.exit(1)
