from exdrf.utils import doc_lines


def test_doc_lines_single_line():
    text = "This is a single line of text."
    expected = ["This is a single line of text."]
    assert doc_lines(text) == expected


def test_doc_lines_multiple_lines():
    text = "This is the first line.\nThis is the second line."
    expected = ["This is the first line.", "", "This is the second line."]
    assert doc_lines(text) == expected


def test_doc_lines_wrapping():
    text = (
        "This is a very long line of text that should be wrapped into "
        "multiple lines because it exceeds the width limit."
    )
    expected = [
        "This is a very long line of text that should be wrapped into multiple",
        "lines because it exceeds the width limit.",
    ]
    assert doc_lines(text) == expected


def test_doc_lines_empty_string():
    text = ""
    expected = []
    assert doc_lines(text) == expected


def test_doc_lines_with_leading_and_trailing_whitespace():
    text = "   This line has leading and trailing spaces.   "
    expected = ["This line has leading and trailing spaces."]
    assert doc_lines(text) == expected


def test_doc_lines_with_blank_lines():
    text = "Line one.\n\nLine three."
    expected = ["Line one.", "", "", "Line three."]
    assert doc_lines(text) == expected
