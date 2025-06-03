import io
import json  # For JS communication
import logging
import re
from copy import deepcopy  # Added for cloning OXML elements
from typing import TYPE_CHECKING, Any, Union

from bs4 import BeautifulSoup, FeatureNotFound, Tag
from bs4.element import NavigableString  # Corrected import

# Imports for HtmlToDocxConverter
from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.text import WD_UNDERLINE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.shared import Inches, Pt, RGBColor
from lxml.etree import _Element
from minify_html import minify
from PyQt5.QtCore import QBuffer, QByteArray, QEvent, QIODevice, Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QImage
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QApplication  # For processEvents

from exdrf_qt.context_use import QtUseContext

if TYPE_CHECKING:
    from exdrf_qt.context import QtContext  # noqa: F401

OxmlElementType = Union[BaseOxmlElement, _Element]
logger = logging.getLogger(__name__)

# Define constants for styling
# MODIFIED: Store colors as (R, G, B) tuples for opacity processing
# And create RGBColor objects on demand.
BORDER_COLOR_SUCCESS_RGB = (0x19, 0x87, 0x54)  # Bootstrap's success green
TABLE_STRIPED_BG_COLOR_RGB = (0xF2, 0xF2, 0xF2)  # Light gray for striping
DEFAULT_BORDER_COLOR_RGB = (0x00, 0x00, 0x00)  # Black
DEFAULT_BORDER_WIDTH_PT = 0.75  # Approx 1px, use in Pt() later


class WebView(QWebEngineView, QtUseContext):
    """A custom web view that can handle internal navigation requests."""

    def __init__(self, ctx: "QtContext", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.devtools_view = None
        self.installEventFilter(self)

    def eventFilter(self, obj, event):  # type: ignore
        """Handle mouse press events."""
        if event.type() == QEvent.Type.MouseButtonPress:
            history = self.history()
            if history is None:
                return super().eventFilter(obj, event)

            # Handle the 'Back' button
            if event.button() == Qt.MouseButton.BackButton:
                if history.canGoBack():
                    history.back()
                event.accept()
                return True  # Return True as event is handled

            # Handle the 'Forward' button
            if event.button() == Qt.MouseButton.ForwardButton:
                if history.canGoForward():
                    history.forward()
                event.accept()
                return True  # Return True as event is handled

        # Otherwise, handle as usual
        return super().eventFilter(obj, event)

    def show_devtools(self):
        if not self.devtools_view:
            # DevTools view
            self.devtools_view = QWebEngineView()
            self.devtools_view.setWindowTitle("DevTools")
            page = self.page()
            assert page is not None
            page.setDevToolsPage(self.devtools_view.page())
            self.devtools_view.closeEvent = (
                lambda event: self._on_devtools_close(event)  # type: ignore
            )
        self.devtools_view.show()
        self.devtools_view.raise_()

    def closeEvent(self, event):  # type: ignore
        if self.devtools_view:
            self.devtools_view.close()
            self.devtools_view = None
        super().closeEvent(event)

    def _on_devtools_close(self, event):  # type: ignore
        self.devtools_view = None
        event.accept()


class HtmlToDocxConverter:
    output_path: str
    view: QWebEngineView
    doc: DocumentObject
    image_cache: dict[str, bytes]
    full_page_qimage: QImage | None
    elements_map: dict[str, dict[str, Any]]
    page_width: int
    page_height: int

    def __init__(self, view: QWebEngineView):  # view is now mandatory
        self.view = view
        self.doc = Document()
        self.image_cache: dict[str, bytes] = {}
        self.full_page_qimage: QImage | None = None
        # MODIFIED: Initialize new elements_map
        # element_id: {"tagName": str, "is_hidden": bool, "geometry": Optional[dict]}
        self.elements_map: dict[str, dict[str, Any]] = {}

    def export_to_docx(self, output_path: str):
        self.output_path = output_path
        self.prepare_assets()

    def prepare_assets(self):
        # MODIFIED: Corrected string literal definition for JS code
        js_get_geometries = """
        (function() {
            console.log(
                "Preparing assets: identifying elements and their visibility"
            );
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

                let isHidden = el.classList.contains('d-none');
                let geometry = null;
                let tagName = el.tagName.toLowerCase();

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
                    isHiddenByDNone: isHidden,
                    geometry: geometry
                });
            }

            let scrollWidth = document.documentElement.scrollWidth;
            let scrollHeight = document.documentElement.scrollHeight;
            console.log("Full page dimensions:", scrollWidth, scrollHeight);

            let final_result = {
                elementInfoList: elementInfoList,
                pageDimensions: { width: scrollWidth, height: scrollHeight }
            };
            console.log(
                "JS result sample:",
                elementInfoList.length > 0 ? elementInfoList[0] : "No elements"
            );
            return JSON.stringify(final_result);
        })();
        """  # MODIFIED: Corrected string literal definition for JS code
        self._run_js_async(js_get_geometries, self.assets_prepared)

    def assets_prepared(self, js_result_str):
        if not js_result_str:
            logger.error("Failed to get element information from JavaScript.")
            return

        try:
            js_data = json.loads(js_result_str)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse JS result: {e}. Result was: {js_result_str}"
            )
            return

        # MODIFIED: Process elementInfoList into self.elements_map
        raw_element_info = js_data.get("elementInfoList", [])
        page_dims = js_data.get("pageDimensions")

        self.elements_map = {}
        for item in raw_element_info:
            self.elements_map[item["id"]] = {
                "tagName": item["tagName"],
                "is_hidden": item["isHiddenByDNone"],
                "geometry": item.get("geometry"),  # Will be None if not present
            }

        # Debug: Log a sample from the processed map
        if self.elements_map:
            sample_id = next(iter(self.elements_map))
            logger.debug(f"Py map {sample_id}: {self.elements_map[sample_id]}")

        if not page_dims or not self.view:
            logger.error(
                "Could not get page dimensions or view not available "
                "for screenshot."
            )
            return

        self.page_width = int(page_dims["width"])
        self.page_height = int(page_dims["height"])

        # Ensure minimum size for grab
        self.page_width = max(
            self.page_width, self.view.minimumSizeHint().width(), 100
        )
        self.page_height = max(
            self.page_height, self.view.minimumSizeHint().height(), 100
        )

        self._run_js_async("window.scrollTo(0,0);", self.window_scrolled)

    def window_scrolled(self, js_result_str):
        original_size = self.view.size()
        QApplication.processEvents()

        self.view.resize(self.page_width, self.page_height)
        QApplication.processEvents()  # Allow resize and layout
        # A more robust wait might be needed here, e.g., QTimer

        pixmap = self.view.grab()
        self.full_page_qimage = pixmap.toImage()
        assert self.full_page_qimage is not None

        self.view.resize(original_size)  # Restore original size
        QApplication.processEvents()

        if self.full_page_qimage.isNull():
            logger.error("Failed to grab full page screenshot.")
            self.full_page_qimage = None
        else:
            logger.info(
                "Full page screenshot captured: %sx%s",
                self.full_page_qimage.width(),
                self.full_page_qimage.height(),
            )

        page = self.view.page()
        assert page is not None
        page.toHtml(self.got_current_html_with_ids)

    def got_current_html_with_ids(self, html_content: str):
        self.doc = Document()
        self.image_cache = {}  # Reset image cache for this run
        html_content = minify(
            html_content,
            allow_noncompliant_unquoted_attribute_values=False,
            allow_optimal_entities=False,
            allow_removing_spaces_between_attributes=True,
            keep_closing_tags=True,
            keep_comments=False,
            keep_html_and_head_opening_tags=True,
            keep_input_type_text_attr=False,
            keep_ssi_comments=False,
            minify_css=True,
            minify_doctype=False,
            minify_js=True,
            preserve_brace_template_syntax=False,
            preserve_chevron_percent_template_syntax=False,
            remove_bangs=False,
            remove_processing_instructions=False,
        )
        try:
            soup = BeautifulSoup(html_content, "lxml")
        except FeatureNotFound:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            logger.error("BeautifulSoup parsing error: %s", e)
            return

        # MODIFIED: Strip all <script> tags
        for script_tag in soup.find_all("script"):
            script_tag.decompose()

        body = soup.find("body")
        process_root = body if body else soup

        for element in process_root.children:  # type: ignore
            if isinstance(element, (Tag, NavigableString)):
                self._process_block_element(element, self.doc, [])

        try:
            self.doc.save(self.output_path)
            logger.info("DOCX file successfully saved to %s", self.output_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_path))
        except Exception as e:
            logger.error(
                "Error saving DOCX file to %s: %s", self.output_path, e
            )

    def _run_js_async(self, js_code: str, callback) -> Any:
        page = self.view.page()
        assert page is not None
        page.runJavaScript(js_code, callback)

    def _add_element_as_image(self, element_id: str, parent_docx_object):
        # MODIFIED: Use self.elements_map to get geometry
        if not self.full_page_qimage:
            logger.error(
                "Missing full page screenshot for element %s", element_id
            )
            return

        element_data = self.elements_map.get(element_id)
        if not element_data:
            logger.error("No map data found for element %s", element_id)
            return

        geometry_data = element_data.get("geometry")
        if not geometry_data:
            logger.error(
                "Missing geometry for image/svg element %s", element_id
            )
            return

        if element_id in self.image_cache:
            img_bytes = self.image_cache[element_id]
        else:
            # MODIFIED: Use geometry_data directly for coordinates and dimensions
            x = int(geometry_data["docX"])
            y = int(geometry_data["docY"])
            width = int(geometry_data["docWidth"])
            height = int(geometry_data["docHeight"])

            if width <= 0 or height <= 0:
                logger.error(
                    "Invalid dimensions for element %s: w=%s, h=%s",
                    element_id,
                    width,
                    height,
                )
                return

            cropped_qimage = self.full_page_qimage.copy(x, y, width, height)
            if cropped_qimage.isNull():
                logger.error("Failed to crop image for element %s", element_id)
                return

            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            cropped_qimage.save(buffer, "PNG")
            img_bytes = bytes(byte_array.data())
            self.image_cache[element_id] = img_bytes

        if img_bytes:
            img_stream = io.BytesIO(img_bytes)
            # MODIFIED: Use geometry_data directly for width/height
            w_px = geometry_data["docWidth"]
            h_px = geometry_data["docHeight"]

            para_for_img = None
            if hasattr(parent_docx_object, "add_paragraph") and not isinstance(
                parent_docx_object, DocumentObject
            ):
                # If parent is a cell or similar that can add paragraphs
                para_for_img = parent_docx_object.add_paragraph()
            elif hasattr(
                parent_docx_object, "add_run"
            ):  # Parent is already a paragraph
                para_for_img = parent_docx_object
            else:  # Document object or fallback
                para_for_img = self.doc.add_paragraph()

            try:
                dpi = 96.0
                w_inch = Inches(w_px / dpi) if w_px > 0 else None
                h_inch = Inches(h_px / dpi) if h_px > 0 else None

                run_for_picture = para_for_img.add_run()  # type: ignore
                if w_inch and h_inch:
                    run_for_picture.add_picture(
                        img_stream, width=w_inch, height=h_inch
                    )
                elif w_inch:
                    run_for_picture.add_picture(img_stream, width=w_inch)
                elif h_inch:
                    run_for_picture.add_picture(img_stream, height=h_inch)
                else:  # Add with original pixel size
                    run_for_picture.add_picture(img_stream)
            except Exception as e:
                logger.error(
                    "Error adding cropped image %s to DOCX: %s",
                    element_id,
                    e,
                )

    # --- Color and Style Parsers (largely unchanged but may need review) ---
    def _hex_to_rgb(self, hex_color: str) -> RGBColor | None:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        if len(hex_color) == 6:
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return RGBColor(r, g, b)
            except ValueError:
                return None
        return None

    def _get_color(self, css_color_string: str) -> RGBColor | None:
        css_color_string = css_color_string.lower().strip()
        named_colors = {
            "black": RGBColor(0, 0, 0),
            "white": RGBColor(255, 255, 255),
            "red": RGBColor(255, 0, 0),
            "green": RGBColor(0, 128, 0),
            "blue": RGBColor(0, 0, 255),
            "yellow": RGBColor(255, 255, 0),
            "transparent": None,
        }
        if css_color_string in named_colors:
            return named_colors[css_color_string]
        if css_color_string.startswith("#"):
            return self._hex_to_rgb(css_color_string)
        elif css_color_string.startswith("rgb("):
            try:
                match = re.match(
                    r"rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)", css_color_string
                )
                if match:
                    r, g, b = map(int, match.groups())
                    return RGBColor(r, g, b)
            except Exception:
                return None
        return None

    def _parse_styles(self, element: Tag) -> tuple[dict[str, Any], list[str]]:
        styles: dict[str, Any] = {}
        style_attr = element.get("style")
        if style_attr and isinstance(style_attr, str):
            for style_declaration in style_attr.split(";"):
                style_declaration = style_declaration.strip()
                if ":" in style_declaration:
                    prop, val = style_declaration.split(":", 1)
                    prop = prop.strip().lower()
                    val = val.strip()
                    if prop == "--bs-border-opacity":
                        try:
                            styles["border_opacity"] = float(val)
                        except ValueError:
                            logger.warning(f"Invalid opacity: {val}")
                    else:
                        styles[prop] = val

        final_class_list: list[str] = []
        class_attr = element.get("class")
        if isinstance(class_attr, str):
            final_class_list = class_attr.split()
        elif isinstance(class_attr, list):
            final_class_list = [
                str(c) for c in class_attr if isinstance(c, str)
            ]

        return styles, final_class_list

    # --- Content Processors (adapted for new image handling) ---
    def _apply_formatting_to_run(self, run, element_tag: Tag):
        tag_name = element_tag.name.lower()
        styles, _ = self._parse_styles(element_tag)

        if tag_name in ["b", "strong"] or styles.get("font-weight") == "bold":
            run.bold = True
        if tag_name in ["i", "em"] or styles.get("font-style") == "italic":
            run.italic = True

        text_decoration = styles.get("text-decoration", "")
        if tag_name == "u" or "underline" in text_decoration:
            run.underline = True
        if (
            tag_name in ["s", "strike", "del"]
            or "line-through" in text_decoration
        ):
            run.strike = True

        color_str = styles.get("color")
        if color_str:
            color = self._get_color(color_str)
            if color:
                run.font.color.rgb = color

        font_family_str = styles.get("font-family")
        if font_family_str:
            primary_font = (
                font_family_str.split(",")[0]
                .strip()
                .replace("'", "")
                .replace('"', "")
            )
            if primary_font:
                run.font.name = primary_font

        font_size_str = styles.get("font-size")
        if font_size_str:
            try:
                val_str = re.sub(r"[^\\d\\.]", "", font_size_str)
                if val_str:
                    val = float(val_str)
                    if "pt" in font_size_str:
                        run.font.size = Pt(val)
                    elif "px" in font_size_str:
                        run.font.size = Pt(val * 0.75)
            except ValueError:
                pass

        if tag_name == "a":
            if not run.font.color.rgb:
                run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
            if not run.underline:
                run.underline = WD_UNDERLINE.SINGLE

    def _process_inline_content(
        self,
        html_node,
        docx_parent_paragraph,
        active_format_tags: list[Tag],
        first: bool = False,
        is_dt_content: bool = False,
        current_paragraph_classes: list[str] | None = None,
    ):
        if isinstance(html_node, NavigableString):
            text = str(html_node)
            if len(text) > 0:
                prefix = " " if text[0].isspace() and not first else ""
                suffix = " " if text[-1].isspace() else ""
                text = prefix + text.strip() + suffix

                run = docx_parent_paragraph.add_run(text)
                if is_dt_content:
                    run.bold = True
                for fmt_tag in active_format_tags:
                    self._apply_formatting_to_run(run, fmt_tag)

        elif isinstance(html_node, Tag):
            # Check if element should be skipped based on d-none
            # MODIFIED: Safely get element_id for map lookup
            raw_element_id = html_node.get("data-docgen-id")
            element_id_str: str | None = None
            if isinstance(raw_element_id, list):
                if raw_element_id:  # Check if list is not empty
                    element_id_str = str(raw_element_id[0])
            elif isinstance(raw_element_id, str):
                element_id_str = raw_element_id

            if element_id_str:
                element_data = self.elements_map.get(element_id_str)
                if element_data and element_data.get("is_hidden"):
                    logger.debug(
                        f"Skip hidden inline {element_id_str} ({html_node.name})"
                    )
                    return  # Skip this hidden element

            tag_name = html_node.name.lower()

            # MODIFIED: Ignore <button> tags and their content
            if tag_name == "button":
                logger.debug(
                    f"Ignoring <button> tag and its content: {str(html_node)[:50]}"
                )
                return

            if tag_name == "br":
                docx_parent_paragraph.add_run().add_break()
                return

            if tag_name == "sup":
                sup_text = (
                    html_node.get_text().strip()
                )  # Get all text within <sup>
                if sup_text:  # Only add run if there's text
                    run = docx_parent_paragraph.add_run(sup_text)
                    run.font.superscript = True
                    # Apply any inherited formatting from parent tags
                    for fmt_tag in active_format_tags:
                        self._apply_formatting_to_run(run, fmt_tag)
                    # Apply any direct styling on the <sup> tag itself
                    self._apply_formatting_to_run(run, html_node)
                return  # Consumed <sup> tag and its content

            if tag_name in ["img", "svg"]:
                # MODIFIED: Safely get element_id for map lookup
                raw_img_id = html_node.get("data-docgen-id")
                img_id_str: str | None = None
                if isinstance(raw_img_id, list):
                    if raw_img_id:  # Check if list is not empty
                        img_id_str = str(raw_img_id[0])
                elif isinstance(raw_img_id, str):
                    img_id_str = raw_img_id

                if img_id_str:
                    element_map_data = self.elements_map.get(img_id_str, {})
                    if element_map_data.get("geometry"):
                        self._add_element_as_image(
                            img_id_str, docx_parent_paragraph
                        )
                    else:
                        logger.debug(
                            f"Skip inline img/svg {img_id_str}, no geometry."
                        )
                else:
                    logger.error(
                        "Skip inline <%s> no data-docgen-id: %.30s",
                        tag_name,
                        str(html_node),
                    )
                return  # Consumed img/svg (or skipped)

            current_active_tags = list(active_format_tags)
            is_inline_formatting_provider = tag_name in [
                "b",
                "strong",
                "i",
                "em",
                "u",
                "s",
                "strike",
                "del",
                "span",
                "font",
                "a",
            ]
            if is_inline_formatting_provider:
                current_active_tags.append(html_node)

            if tag_name == "a":
                href = html_node.get("href")
                link_text = "".join(
                    map(str, html_node.find_all(string=True, recursive=True))
                ).strip()  # Ensure strings
                if href and link_text:
                    try:
                        h_run = docx_parent_paragraph.add_hyperlink(
                            href, link_text, is_external=True
                        )
                        for fmt_tag in current_active_tags:
                            self._apply_formatting_to_run(h_run, fmt_tag)
                    except Exception as e:
                        logger.error(
                            "Failed to add hyperlink for %s: %s. "
                            "Adding as text.",
                            href,
                            e,
                        )
                        for i, child in enumerate(html_node.children):
                            self._process_inline_content(
                                child,
                                docx_parent_paragraph,
                                current_active_tags,
                                first=(i == 0),
                                is_dt_content=False,
                                current_paragraph_classes=current_paragraph_classes,
                            )
                    return
                # Fallback for 'a' if no href/text or error
                for i, child in enumerate(html_node.children):
                    self._process_inline_content(
                        child,
                        docx_parent_paragraph,
                        current_active_tags,
                        first=(i == 0),
                        is_dt_content=False,
                        current_paragraph_classes=current_paragraph_classes,
                    )
            else:
                for i, child in enumerate(html_node.children):
                    self._process_inline_content(
                        child,
                        docx_parent_paragraph,
                        current_active_tags,
                        first=(i == 0),
                        is_dt_content=False,
                        current_paragraph_classes=current_paragraph_classes,
                    )

    # --- Table Handlers (largely unchanged but verify context for
    # image processing if any) ---
    def _set_cell_shading(self, cell, color_str: str):
        color = self._get_color(color_str)
        if color and color_str.lower() != "transparent":
            try:
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), str(color))  # RGBColor.__str__ gives hex
                shd.set(qn("w:val"), "clear")
                tcPr = cell._tc.get_or_add_tcPr()
                for existing_shd in tcPr.xpath("./w:shd"):
                    tcPr.remove(existing_shd)
                tcPr.append(shd)
            except Exception as e:
                logger.error(
                    "Error applying cell shading %s: %s",
                    color_str,
                    e,
                )

    def _set_cell_border_color(
        self,
        border_side_element: OxmlElementType,
        color_rgb: tuple[int, int, int],  # MODIFIED: Expect (R,G,B) tuple
        size_pt: int = 4,  # This is w:sz unit (eighths of a point)
        alpha: float = 1.0,  # Opacity (0.0 to 1.0)
    ):
        r, g, b = color_rgb
        actual_r, actual_g, actual_b = r, g, b

        if alpha < 1.0 and alpha >= 0.0:  # Apply opacity by blending with white
            actual_r = int(r * alpha + 255 * (1 - alpha))
            actual_g = int(g * alpha + 255 * (1 - alpha))
            actual_b = int(b * alpha + 255 * (1 - alpha))

        final_color_obj = RGBColor(
            max(0, min(actual_r, 255)),
            max(0, min(actual_g, 255)),
            max(0, min(actual_b, 255)),
        )

        border_side_element.set(qn("w:val"), "single")
        border_side_element.set(qn("w:sz"), str(size_pt))
        border_side_element.set(qn("w:color"), str(final_color_obj))

    def _apply_cell_borders(
        self,
        cell,
        cell_styles: dict,
        cell_classes: list[str],
        table_classes: list[str],
    ):
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = tcPr.first_child_found_in("w:tcBorders")  # type: ignore # mypy issue with lxml-based find
        if tcBorders is None:
            tcBorders = OxmlElement("w:tcBorders")
            tcPr.append(tcBorders)

        for border_tag_to_clear in [
            "top",
            "left",
            "bottom",
            "right",
            "insideH",
            "insideV",
        ]:
            existing = tcBorders.find(qn(f"w:{border_tag_to_clear}"))  # type: ignore # mypy issue with lxml-based find
            if existing is not None:
                tcBorders.remove(existing)

        base_r, base_g, base_b = DEFAULT_BORDER_COLOR_RGB

        if (
            "border-success" in cell_classes
            or "border-success" in table_classes
        ):
            base_r, base_g, base_b = BORDER_COLOR_SUCCESS_RGB

        border_opacity = cell_styles.get("border_opacity", 1.0)
        if not isinstance(border_opacity, (float, int)) or not (
            0.0 <= border_opacity <= 1.0
        ):
            border_opacity = 1.0

        sides_to_border = ["top", "bottom", "left", "right"]
        apply_default_bordered = "table-bordered" in table_classes

        for side in sides_to_border:
            border_definition_from_style = cell_styles.get(f"border-{side}")
            apply_this_side = False
            parsed_width_val = DEFAULT_BORDER_WIDTH_PT

            # MODIFIED: If table-bordered, always apply border for the side,
            # ignoring cell-specific border-style unless it explicitly says none.
            if apply_default_bordered:
                apply_this_side = True
                # If cell explicitly sets this border to none, respect that even if table is bordered
                if border_definition_from_style and (
                    "none" in border_definition_from_style
                    or "0px" in border_definition_from_style
                    or "0pt" in border_definition_from_style
                ):
                    apply_this_side = False
            elif border_definition_from_style:
                # Not table-bordered, but cell has a specific border style
                if (
                    "none" in border_definition_from_style
                    or "0px" in border_definition_from_style
                    or "0pt" in border_definition_from_style
                ):
                    apply_this_side = False
                else:
                    apply_this_side = True
                    # TODO: More detailed parsing of border-{side} for width, color etc.
                    # For now, if style exists and is not none, it uses default width/calculated color.

            if apply_this_side:
                if border_opacity < 0.05:  # Effectively transparent, skip
                    continue

                border_el = OxmlElement(f"w:{side}")
                border_sz = max(1, int(parsed_width_val * 8))
                self._set_cell_border_color(
                    border_el,
                    (base_r, base_g, base_b),
                    size_pt=border_sz,
                    alpha=border_opacity,
                )
                tcBorders.append(border_el)

    def _handle_table(self, table_element: Tag, parent_docx_object):
        table_styles, table_classes = self._parse_styles(
            table_element
        )  # Get table classes

        html_grid: list[list[Tag | str | None]] = []
        html_rows: list[Tag] = []

        # MODIFIED: Break down list comprehensions for extend to avoid line
        # length errors
        thead = table_element.find("thead", recursive=False)
        if thead and isinstance(thead, Tag):
            for tag in thead.find_all("tr", recursive=False):
                if isinstance(tag, Tag):
                    html_rows.append(tag)

        tbody_elements = table_element.find_all("tbody", recursive=False)
        if tbody_elements:
            for tbody in tbody_elements:
                if isinstance(tbody, Tag):
                    for tag in tbody.find_all("tr", recursive=False):
                        if isinstance(tag, Tag):
                            html_rows.append(tag)
        else:
            if not thead:
                for tag in table_element.find_all("tr", recursive=False):
                    if isinstance(tag, Tag):
                        html_rows.append(tag)

        tfoot = table_element.find("tfoot", recursive=False)
        if tfoot and isinstance(tfoot, Tag):
            for tag in tfoot.find_all("tr", recursive=False):
                if isinstance(tag, Tag):
                    html_rows.append(tag)

        if not html_rows and not (
            thead or tbody_elements or tfoot
        ):  # Final fallback if only direct tr children
            for tag in table_element.find_all("tr", recursive=False):
                if isinstance(tag, Tag):
                    html_rows.append(tag)

        max_cols = 0
        for r_idx, tr_element_maybe_str in enumerate(html_rows):
            if not isinstance(tr_element_maybe_str, Tag):
                continue
            tr_element: Tag = tr_element_maybe_str

            html_grid.append([])
            current_col_idx = 0
            if not isinstance(tr_element, Tag):
                continue

            for td_th_element in tr_element.find_all(
                ["td", "th"], recursive=False
            ):
                if not isinstance(td_th_element, Tag):
                    continue
                while (
                    len(html_grid[r_idx]) > current_col_idx
                    and html_grid[r_idx][current_col_idx] is not None
                ):
                    current_col_idx += 1

                colspan = self._get_attribute_as_int(
                    td_th_element, "colspan", 1
                )
                rowspan = self._get_attribute_as_int(
                    td_th_element, "rowspan", 1
                )

                for i in range(rowspan):
                    target_r = r_idx + i
                    while len(html_grid) <= target_r:
                        html_grid.append([])
                    while len(html_grid[target_r]) < current_col_idx:
                        html_grid[target_r].append(None)
                    for j in range(colspan):
                        while len(html_grid[target_r]) <= current_col_idx + j:
                            html_grid[target_r].append(None)
                        if i == 0 and j == 0:
                            html_grid[target_r][
                                current_col_idx + j
                            ] = td_th_element
                        else:
                            html_grid[target_r][current_col_idx + j] = "SPAN"
                current_col_idx += colspan
            if current_col_idx > max_cols:
                max_cols = current_col_idx

        num_logical_rows = len(html_grid)
        for r_list in html_grid:
            while len(r_list) < max_cols:
                r_list.append(None)

        if num_logical_rows == 0 or max_cols == 0:
            return

        doc_table = parent_docx_object.add_table(
            rows=num_logical_rows, cols=max_cols
        )
        # Apply table-level styles like table-layout: fixed if needed (not
        # requested yet) doc_table.autofit = False doc_table.layout_type =
        # WD_TABLE_LAYOUT.FIXED

        for r_idx in range(num_logical_rows):
            for c_idx in range(max_cols):
                html_cell_content = html_grid[r_idx][c_idx]
                if html_cell_content is None or html_cell_content == "SPAN":
                    continue
                if not isinstance(html_cell_content, Tag):
                    continue
                html_cell_element: Tag = html_cell_content
                doc_cell = doc_table.cell(r_idx, c_idx)

                colspan = self._get_attribute_as_int(
                    html_cell_element, "colspan", 1
                )
                rowspan = self._get_attribute_as_int(
                    html_cell_element, "rowspan", 1
                )

                if rowspan > 1 or colspan > 1:
                    end_r_idx = min(r_idx + rowspan - 1, num_logical_rows - 1)
                    end_c_idx = min(c_idx + colspan - 1, max_cols - 1)
                    if end_r_idx > r_idx or end_c_idx > c_idx:
                        try:
                            doc_cell.merge(doc_table.cell(end_r_idx, end_c_idx))
                        except Exception as e:
                            logger.warning(f"Cell merge failed: {e}")

                # Clear default empty paragraph if cell is truly empty before content processing
                if doc_cell.paragraphs and doc_cell.paragraphs[0].text == "":
                    p_element = doc_cell.paragraphs[0]._element
                    p_element.getparent().remove(p_element)

                cell_styles, cell_classes = self._parse_styles(
                    html_cell_element
                )

                # Table striping and background color
                is_striped_table = "table-striped" in table_classes
                if is_striped_table and (r_idx % 2 != 0):
                    if not cell_styles.get("background-color"):
                        shade_color = RGBColor(*TABLE_STRIPED_BG_COLOR_RGB)
                        self._set_cell_shading(doc_cell, str(shade_color))
                bg_color_str = cell_styles.get("background-color")
                if bg_color_str:
                    self._set_cell_shading(doc_cell, bg_color_str)

                # Apply borders to the primary cell
                self._apply_cell_borders(
                    doc_cell, cell_styles, cell_classes, table_classes
                )

                # --- START MODIFIED CONTENT PROCESSING ---
                # Populate the cell with content from html_cell_element
                if html_cell_element and hasattr(html_cell_element, "children"):
                    # Children will inherit styles from html_cell_element (the <td> or <th>)
                    # if html_cell_element is passed as an active_format_tag.
                    active_tags_for_cell_content = [html_cell_element]

                    for child_node in html_cell_element.children:
                        # parent_docx_object is doc_cell, so content goes into the cell.
                        # No explicit indent_level_inches for direct cell content.
                        self._process_block_element(
                            child_node, doc_cell, active_tags_for_cell_content
                        )
                # --- END MODIFIED CONTENT PROCESSING ---

                # CORRECTED PROPAGATE SIDE BORDERS FOR ROWSPAN TO CONTINUED CELLS
                if rowspan > 1:
                    main_left_border_el = None
                    main_right_border_el = None

                    main_tcPr = doc_cell._tc.get_or_add_tcPr()
                    main_tcBorders_list = main_tcPr.xpath("./w:tcBorders")
                    if main_tcBorders_list:
                        main_tcBorders = main_tcBorders_list[0]
                        main_left_border_el = main_tcBorders.find(qn("w:left"))  # type: ignore[arg-type]
                        main_right_border_el = main_tcBorders.find(qn("w:right"))  # type: ignore[arg-type]

                    # Only proceed if the main cell actually has these borders defined
                    if (
                        main_left_border_el is not None
                        or main_right_border_el is not None
                    ):
                        for i in range(1, rowspan):
                            current_row_in_span = r_idx + i
                            # Ensure we don't go out of bounds for the table's logical rows
                            if current_row_in_span < num_logical_rows:
                                # Get the "continued" cell in the DOCX table
                                # This cell should have its vMerge property set to None (or not 'restart')
                                # by the earlier merge operation's effect on html_grid processing.
                                cont_cell = doc_table.cell(
                                    current_row_in_span, c_idx
                                )

                                # Access its properties and add/clone borders
                                cont_tcPr = cont_cell._tc.get_or_add_tcPr()

                                # Ensure vMerge is present (it should be, from the initial merge logic)
                                vMerge_el = cont_tcPr.find(qn("w:vMerge"))  # type: ignore[arg-type]
                                if vMerge_el is None:
                                    vMerge_el = OxmlElement("w:vMerge")
                                    cont_tcPr.append(
                                        vMerge_el
                                    )  # Add it if missing
                                vMerge_el.set(
                                    qn("w:val"), "continue"
                                )  # Explicitly set if needed, though often just presence is enough

                                current_cont_tcBorders = cont_tcPr.find(qn("w:tcBorders"))  # type: ignore[arg-type]
                                if current_cont_tcBorders is None:
                                    current_cont_tcBorders = OxmlElement(
                                        "w:tcBorders"
                                    )
                                    # Try to insert tcBorders before vMerge if
                                    # vMerge exists and we can do it This is to
                                    # keep tcPr child order somewhat standard,
                                    # though often not strictly necessary

                                    if vMerge_el is not None and hasattr(
                                        vMerge_el, "addprevious"
                                    ):  # type: ignore[no-untyped-call]
                                        vMerge_el.addprevious(
                                            current_cont_tcBorders
                                        )  # type: ignore[no-untyped-call]
                                    else:
                                        cont_tcPr.append(current_cont_tcBorders)

                                if main_left_border_el is not None:
                                    existing_left = current_cont_tcBorders.find(
                                        qn("w:left")
                                    )  # type: ignore[arg-type]
                                    if existing_left is not None:
                                        current_cont_tcBorders.remove(
                                            existing_left
                                        )
                                    cloned_left_border = deepcopy(
                                        main_left_border_el
                                    )
                                    current_cont_tcBorders.append(
                                        cloned_left_border
                                    )

                                if main_right_border_el is not None:
                                    existing_right = (
                                        current_cont_tcBorders.find(
                                            qn("w:right")
                                        )
                                    )  # type: ignore[arg-type]
                                    if existing_right is not None:
                                        current_cont_tcBorders.remove(
                                            existing_right
                                        )
                                    cloned_right_border = deepcopy(
                                        main_right_border_el
                                    )
                                    current_cont_tcBorders.append(
                                        cloned_right_border
                                    )

    def _process_block_element(
        self,
        element: Tag | NavigableString,
        parent_docx_object,
        active_format_tags: list[Tag],
        indent_level_inches: float | None = None,
        current_paragraph_classes: list[str] | None = None,
    ):
        current_paragraph: Any = None

        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                target_p = None
                # If parent is a cell and has paragraphs, append to the last one.
                if (
                    hasattr(parent_docx_object, "_tc")
                    and parent_docx_object.paragraphs
                ):
                    target_p = parent_docx_object.paragraphs[-1]
                else:
                    # Otherwise, create a new paragraph in the parent_docx_object.
                    target_p = self._create_paragraph_for_block(
                        parent_docx_object, indent_level_inches
                    )

                run = target_p.add_run(text)
                for fmt_tag in active_format_tags:
                    self._apply_formatting_to_run(run, fmt_tag)
            return

        if not isinstance(element, Tag):
            return

        # Check if element should be skipped based on d-none
        # MODIFIED: Safely get element_id for map lookup
        raw_element_id_block = element.get("data-docgen-id")
        element_id_block_str: str | None = None
        if isinstance(raw_element_id_block, list):
            if raw_element_id_block:  # Check if list is not empty
                element_id_block_str = str(raw_element_id_block[0])
        elif isinstance(raw_element_id_block, str):
            element_id_block_str = raw_element_id_block

        if element_id_block_str:
            element_data = self.elements_map.get(element_id_block_str)
            if element_data and element_data.get("is_hidden"):
                logger.debug(
                    f"Skip hidden block {element_id_block_str} ({element.name})"
                )
                return  # Skip this hidden element

        tag_name = element.name.lower()

        # MODIFIED: Ignore <button> tags and their content
        if tag_name == "button":
            logger.debug(
                f"Ignoring <button> tag and its content in block context: {str(element)[:50]}"
            )
            return

        if tag_name in ["img", "svg"]:
            # MODIFIED: Safely get element_id for map lookup
            raw_img_id_block = element.get("data-docgen-id")
            img_id_block_str: str | None = None
            if isinstance(raw_img_id_block, list):
                if raw_img_id_block:  # Check if list is not empty
                    img_id_block_str = str(raw_img_id_block[0])
            elif isinstance(raw_img_id_block, str):
                img_id_block_str = raw_img_id_block

            if img_id_block_str:
                element_map_data = self.elements_map.get(img_id_block_str, {})
                if element_map_data.get("geometry"):
                    target_for_image = None
                    if hasattr(
                        parent_docx_object, "add_paragraph"
                    ) and not isinstance(parent_docx_object, DocumentObject):
                        target_for_image = parent_docx_object
                    elif hasattr(parent_docx_object, "add_run"):
                        target_for_image = parent_docx_object
                    else:
                        target_for_image = self.doc
                    self._add_element_as_image(
                        img_id_block_str, target_for_image
                    )
                else:
                    logger.debug(
                        f"Skip block img/svg {img_id_block_str}, no geometry."
                    )
            else:
                logger.error(
                    "Skip block <%s> no data-docgen-id: %.30s",
                    tag_name,
                    str(element),
                )
            return  # Consumed img/svg or skipped

        if tag_name in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]:
            current_paragraph = self._create_paragraph_for_block(
                parent_docx_object, indent_level_inches
            )

            if tag_name.startswith("h"):
                try:
                    current_paragraph.style = f"Heading {int(tag_name[1])}"
                except (ValueError, IndexError):
                    pass

            # MODIFIED: Get styles and classes for the block element itself
            element_styles, element_classes = self._parse_styles(element)
            new_active_tags = list(active_format_tags)
            # DIVs can provide formatting context via styles/classes
            if tag_name == "div":
                new_active_tags.append(element)
                # Still useful for style inheritance if not using classes
                # directly here

            for i, child in enumerate(element.children):
                self._process_inline_content(
                    child,
                    current_paragraph,
                    new_active_tags,
                    first=(i == 0),
                    is_dt_content=False,
                    current_paragraph_classes=element_classes,
                )

        elif tag_name in ["ul", "ol"]:
            for item in element.find_all("li", recursive=False):
                if not isinstance(item, Tag):
                    continue
                style = "ListBullet" if tag_name == "ul" else "ListNumber"
                # Content of <li> processed into this new paragraph
                li_paragraph = self.doc.add_paragraph(style=style)
                if indent_level_inches:
                    li_paragraph.paragraph_format.left_indent = Inches(
                        indent_level_inches
                    )
                for i, child_content in enumerate(item.children):
                    self._process_inline_content(
                        child_content,
                        li_paragraph,
                        active_format_tags,
                        first=(i == 0),
                        is_dt_content=False,
                        current_paragraph_classes=current_paragraph_classes,
                    )

        elif tag_name == "dl":
            self._handle_dl_element(
                element,
                parent_docx_object,
                active_format_tags,
                indent_level_inches,
                current_paragraph_classes=current_paragraph_classes,
            )

        elif tag_name == "table":
            # MODIFIED: Pass table classes from _parse_styles to _handle_table
            # _handle_table itself will call _parse_styles for the table element
            self._handle_table(element, parent_docx_object)

        elif tag_name == "hr":
            p = self.doc.add_paragraph()
            if indent_level_inches:
                p.paragraph_format.left_indent = Inches(indent_level_inches)
            pPr = p._p.get_or_add_pPr()
            pBdr, bottom = OxmlElement("w:pBdr"), OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "auto")
            pBdr.append(bottom)
            pPr.append(pBdr)

        else:
            # Unrecognized block tags, or inline tags found at block level
            new_active_tags = list(active_format_tags)
            if element.name.lower() in ["span", "font", "div"]:
                new_active_tags.append(element)

            # For children, decide if they are block (recursive call) or inline
            # (needs paragraph)
            created_para_for_inline = None
            for i, child in enumerate(element.children):
                if isinstance(child, Tag) and child.name.lower() in [
                    "p",
                    "div",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                    "ul",
                    "ol",
                    "table",
                    "img",
                    "svg",
                    "hr",
                    "dl",
                ]:
                    self._process_block_element(
                        child,
                        parent_docx_object,
                        new_active_tags,
                        indent_level_inches=indent_level_inches,
                        current_paragraph_classes=current_paragraph_classes,
                    )
                    created_para_for_inline = (
                        None  # Reset: next inline content needs new para
                    )
                elif isinstance(child, (NavigableString, Tag)):
                    # Inline or text found at block level, needs a paragraph context.
                    if created_para_for_inline is None:
                        # If parent_docx_object is a cell with existing paragraphs,
                        # and the current element (wrapper like <sup>) is inline,
                        # use the cell's last paragraph.
                        is_inline_wrapper = element.name.lower() in [
                            "sup",
                            "sub",
                            "span",
                            "font",
                            "b",
                            "i",
                            "strong",
                            "em",
                            "u",
                            "s",
                            "a",
                            "del",
                            "strike",
                        ]
                        if (
                            hasattr(parent_docx_object, "_tc")
                            and parent_docx_object.paragraphs
                            and is_inline_wrapper
                        ):
                            created_para_for_inline = (
                                parent_docx_object.paragraphs[-1]
                            )
                        else:
                            # Element is some other unknown block-ish wrapper,
                            # or parent is not a cell / has no paras / element is not inline wrapper.
                            created_para_for_inline = (
                                self._create_paragraph_for_block(
                                    parent_docx_object, indent_level_inches
                                )
                            )

                    self._process_inline_content(
                        child,
                        created_para_for_inline,
                        new_active_tags,
                        first=(i == 0),
                        is_dt_content=False,
                        current_paragraph_classes=current_paragraph_classes,
                    )

    def _create_paragraph_for_block(
        self, parent_docx_object: Any, indent_level_inches: float | None
    ):
        """Helper to create a paragraph, typically for a new block element,
        applying indentation.
        """
        para = None
        if hasattr(parent_docx_object, "add_paragraph") and not isinstance(
            parent_docx_object, DocumentObject
        ):
            para = parent_docx_object.add_paragraph()  # Usually a Cell
        else:
            # Document object, or parent is already a paragraph (less common
            # for new block)
            para = self.doc.add_paragraph()

        if indent_level_inches is not None and indent_level_inches > 0:
            para.paragraph_format.left_indent = Inches(indent_level_inches)
        return para

    def _handle_dl_element(
        self,
        dl_element: Tag,
        parent_docx_object: Any,
        active_format_tags: list[Tag],
        current_indent_inches: float | None,
        current_paragraph_classes: list[str] | None = None,
    ):
        """Handles <dl> elements: styled <dt> and indented <dd> blocks."""
        for child_node in dl_element.children:
            if not isinstance(child_node, Tag):
                continue

            child_tag_name = child_node.name.lower()

            if child_tag_name == "dt":
                # Create a paragraph for DT, apply current indent (if any, e.g.
                # nested DL)
                p_dt = self._create_paragraph_for_block(
                    parent_docx_object, current_indent_inches
                )
                # Process DT's children as bold inline content
                for i, dt_content_child in enumerate(child_node.children):
                    self._process_inline_content(
                        dt_content_child,
                        p_dt,
                        active_format_tags,
                        first=(i == 0),
                        is_dt_content=True,
                        current_paragraph_classes=current_paragraph_classes,
                    )

            elif child_tag_name == "dd":
                # Calculate indentation for DD's content
                dd_children_indent_val = (
                    current_indent_inches or 0
                ) + 0.25  # Standard indent for DD

                if not list(child_node.children):  # If DD is empty, skip
                    continue

                # Process each child of DD as a block element with the new
                # indentation
                for dd_content_child in child_node.children:
                    self._process_block_element(  # type: ignore
                        dd_content_child,  # type: ignore
                        parent_docx_object,
                        active_format_tags,
                        indent_level_inches=dd_children_indent_val,
                        current_paragraph_classes=current_paragraph_classes,
                    )

    def _get_attribute_as_int(
        self, element: Tag, attr_name: str, default_val: int = 1
    ) -> int:
        """Helper to safely get an attribute value as an integer."""
        attr_val = element.get(attr_name)
        if attr_val is None:
            return default_val

        val_to_convert = attr_val
        if isinstance(attr_val, list):
            if not attr_val:  # Empty list
                return default_val
            val_to_convert = str(attr_val[0])  # Take first item if list
        else:
            val_to_convert = str(attr_val)

        try:
            return int(val_to_convert)
        except ValueError:
            logger.warning(
                f"Invalid value for attribute {attr_name}: {val_to_convert}. Using default {default_val}."
            )
            return default_val
