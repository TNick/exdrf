import os
from io import BytesIO
from typing import List


def merge_pdf_files(
    file_list: List[str],
    out_path: str,
    no_toc: bool = False,
    creator: str = "",
    producer: str = "",
    title: str = "",
    author: str = "",
    subject: str = "",
    keywords: str = "",
    adjust_image: bool = False,
):
    import fitz
    from PIL import Image, ImageOps

    c_date = fitz.get_pdf_now()
    pdf_out: fitz.Document = fitz.open()  # empty new PDF document
    aus_nr = 0  # current page number in output
    pdf_out.set_metadata(
        {
            "creator": creator,
            "producer": producer,
            "creationDate": c_date,
            "modDate": c_date,
            "title": title,
            "author": author,
            "subject": subject,
            "keywords": keywords,
        }
    )  # put in meta data
    total_toc = []  # initialize TOC

    for file_path in file_list:
        # Open the document and see how many pages it has.
        doc: fitz.Document = fitz.open(file_path)
        doc_len = len(doc)

        # The input list can also contain page interval (0 based) and rotation
        # angle. first > last means reversing the order of pages
        if isinstance(file_path, (list, tuple)):
            file_path, first, last, rot, bookmark = file_path
        else:
            first, last, rot, bookmark = (
                0,
                doc_len,
                doc[0].rotation,
                os.path.basename(file_path).replace(".pdf", ""),
            )

        # Make sure that the interval is in range.
        first = min(max(0, first), doc_len - 1)
        last = min(max(0, last), doc_len - 1)
        rot = int(rot)

        if adjust_image:
            zoom = 1.0
            mat = fitz.Matrix(zoom, zoom)
            for i, page in enumerate(doc):
                if i < first or i > last:
                    continue
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes(
                    "RGB", [pix.width, pix.height], pix.samples
                )
                gray_image = ImageOps.grayscale(img)
                imagefile = BytesIO()
                gray_image.save(imagefile, format="png")
                # gray_image.save(imagefile, format='jpeg')

                # open it as a PyMuPDF document
                img_pdf = fitz.open(stream=imagefile, filetype="png")
                pdfbytes = img_pdf.convert_to_pdf()
                img_pdf.close()
                # open stream as PDF
                img_pdf = fitz.open("pdf", pdfbytes)

                page = pdf_out.new_page(
                    width=pix.width, height=pix.height  # new page with ...
                )  # pic dimension
                r1 = fitz.Rect(0, 0, img.width, img.height)
                page.show_pdf_page(r1, img_pdf)  # image fills the page
        else:
            # now copy the page range
            pdf_out.insert_pdf(doc, from_page=first, to_page=last, rotate=rot)

        # no ToC wanted - get next file
        if no_toc:
            continue

        # standard increment for page range
        incr = 1
        if last < first:
            incr = -1  # increment for reversed sequence

        # list of page numbers in range
        pno_range = list(range(first, last + incr, incr))

        # insert standard bookmark ahead of any page range
        total_toc.append([1, bookmark, aus_nr + 1])

        # get file's TOC
        toc = doc.get_toc(simple=False)

        # immunize against hierarchy gaps
        last_lvl = 1
        for t in toc:
            lnk_type = t[3]["kind"]  # if "goto", page must be in range
            if (t[2] - 1) not in pno_range and lnk_type == fitz.LINK_GOTO:
                continue
            if lnk_type == fitz.LINK_GOTO:
                pno = pno_range.index(t[2] - 1) + aus_nr + 1
            else:
                pno = None

            # repair hierarchy gaps by filler bookmarks
            while t[0] > last_lvl + 1:
                total_toc.append([last_lvl + 1, "<>", pno, t[3]])
                last_lvl += 1
            last_lvl = t[0]
            t[2] = pno
            total_toc.append(t)

        aus_nr += len(pno_range)  # increase output counter
        doc.close()
        doc = None

    if total_toc:
        pdf_out.set_toc(total_toc)
    pdf_out.save(out_path)
    pdf_out.close()
