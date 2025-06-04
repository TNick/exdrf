import logging
from typing import Callable

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication

from exdrf_qt.utils.screen_grabber import FullPageGrabber as BaseGrabber

logger = logging.getLogger(__name__)
ERROR_FAILED_TO_GET_DATA = "Failed to retrieve extended data"


class FullPageGrabber(BaseGrabber):
    """Capture the content of a web page as a full-page screenshot.

    This class is designed to be used as a callback for a QWebEngineView.
    """

    true_callback: Callable[["FullPageGrabber"], None]

    def __init__(
        self, callback: Callable[["FullPageGrabber"], None], *args, **kwargs
    ):
        self.true_callback = callback
        super().__init__(
            callback=self._got_page_size, auto_close=False, *args, **kwargs
        )  # type: ignore

    def _got_page_size(self, _):
        """At this point the view is resized and has the html in place."""
        second_js_code = """
        (function() {
            var doc = document.documentElement;

            // Compute the size of the display.
            var w = Math.max(
                doc.scrollWidth, doc.offsetWidth, doc.clientWidth
            );
            var h = Math.max(
                doc.scrollHeight, doc.offsetHeight, doc.clientHeight
            );

            // Get the full HTML tree with all runtime modifications
            function getFullHTMLTree() {
                // This captures the entire HTML document including all
                // runtime modifications
                let fullHTML = document.documentElement.outerHTML;

                // Alternative: If you want just the body content
                // let fullHTML = document.body.outerHTML;

                // Alternative: Custom tree walker for more control
                function serializeElement(element) {
                    if (element.nodeType === Node.TEXT_NODE) {
                        return element.textContent;
                    }

                    if (element.nodeType !== Node.ELEMENT_NODE) {
                        return '';
                    }

                    let html = '<' + element.tagName.toLowerCase();

                    // Include all attributes (including runtime-added ones)
                    for (let attr of element.attributes) {
                        html += ' ' + attr.name + '="' +
                                attr.value.replace(/"/g, '&quot;') + '"';
                    }

                    // Include computed style if needed
                    // (uncomment if you want inline styles)
                    // let computedStyle = window.getComputedStyle(element);
                    // let styleString = '';
                    // for (let i = 0; i < computedStyle.length; i++) {
                    //     let prop = computedStyle[i];
                    //     styleString += prop + ':' +
                    //                   computedStyle.getPropertyValue(prop) +
                    //                   ';';
                    // }
                    // if (styleString) {
                    //     html += ' style="' + styleString + '"';
                    // }

                    html += '>';

                    // Process child nodes
                    for (let child of element.childNodes) {
                        html += serializeElement(child);
                    }

                    html += '</' + element.tagName.toLowerCase() + '>';
                    return html;
                }

                return fullHTML;
            }

            // Locate selectors.
            let selector = 'p, div, h1, h2, h3, h4, h5, h6, ul, ol, li, dl, ' +
                'dt, dd, table, tr, td, th, thead, tbody, tfoot, span, img, ' +
                'svg, hr, a, b, i, strong, em, u, s, strike, del, font, ' +
                'sup, sub';
            let elements = document.querySelectorAll(selector);
            console.log(
                "Found", elements.length, "relevant elements for d-none check"
            );
            let elementInfoList = [];
            let scrollX = window.scrollX;
            let scrollY = window.scrollY;

            for (let i = 0; i < elements.length; i++) {
                let el = elements[i];
                let id = 'docgen_elem_' + i;
                el.setAttribute('data-docgen-id', id);
                let tagName = el.tagName.toLowerCase();

                let classList = el.classList;
                let isHiddenByDNone = classList.contains('d-none');
                console.log(
                    "Element %s ID %s has d-none: %s",
                    tagName, id, isHiddenByDNone
                );
                let hasCollapse = classList.contains('collapse');
                console.log(
                    "Element %s ID %s has collapse: %s",
                    tagName, id, hasCollapse
                );
                let hasShow = classList.contains('show');
                console.log(
                    "Element %s ID %s has show: %s",
                    tagName, id, hasShow
                );

                let isHiddenByCollapseLogic = false;
                if (hasCollapse && !hasShow) {
                    isHiddenByCollapseLogic = true;
                    console.log(
                        "Element %s ID %s has collapse logic",
                        tagName, id
                    );
                }

                let isEffectivelyHidden =
                    isHiddenByDNone || isHiddenByCollapseLogic;
                console.log(
                    "Element %s ID %s is effectively hidden: %s",
                    tagName, id, isEffectivelyHidden
                );

                let geometry = null;

                if (tagName === 'img' || tagName === 'svg') {
                    let rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        geometry = {
                            docX: rect.left + scrollX,
                            docY: rect.top + scrollY,
                            docWidth: rect.width,
                            docHeight: rect.height
                        };
                    } else {
                         console.log(
                            "Element " + id + " (" + tagName +
                            ") has zero width/height, no geometry stored."
                        );
                    }
                }
                elementInfoList.push({
                    id: id,
                    tagName: tagName,
                    isEffectivelyHidden: isEffectivelyHidden,
                    geometry: geometry
                });
            }

            let scrollWidth = document.documentElement.scrollWidth;
            let scrollHeight = document.documentElement.scrollHeight;
            console.log("Full page dimensions:", scrollWidth, scrollHeight);

            // Capture the full HTML tree with runtime modifications
            let fullHTMLTree = getFullHTMLTree();
            console.log("Full HTML tree captured, length:",
                       fullHTMLTree.length);

            let final_result = {
                elementInfoList: elementInfoList,
                width: w,
                height: h,
                scrollWidth: scrollWidth,
                scrollHeight: scrollHeight,
                fullHTMLTree: fullHTMLTree
            };
            console.log(
                "JS result sample:",
                elementInfoList.length > 0 ? elementInfoList[0] : "No elements"
            );
            return final_result;

        })();
        """
        # Run JS to get the full content size
        page = self.view.page()
        assert page is not None
        page.runJavaScript(second_js_code, self._on_data_loaded)
        QApplication.processEvents()

    def _on_data_loaded(self, js_result):
        """We're informed that the data has been extracted.

        Args:
            js_result: A Python dict like {'width': 1024, 'height': 3000}.
        """
        self.js_result = js_result
        if not js_result:
            self.errors.append(ERROR_FAILED_TO_GET_DATA)
            logger.error(ERROR_FAILED_TO_GET_DATA)

        assert self.pixmap is not None
        assert self.js_result is not None

        if self.debug_mode:
            painter = QPainter(self.pixmap)
            for item in self.js_result["elementInfoList"]:
                geometry = item.get("geometry")
                if geometry is None:
                    continue
                x = int(geometry["docX"])
                y = int(geometry["docY"])
                width = int(geometry["docWidth"])
                height = int(geometry["docHeight"])

                # Create a QRect
                rect = QRect(x, y, width, height)

                # Draw a red rectangle on the pixmap
                painter.setPen(QPen(QColor(255, 0, 0), 2))
                painter.drawRect(rect)

                # Draw the ID in the top left corner of the rectangle
                painter.drawText(rect.topLeft(), item["id"])

        self.true_callback(self)
