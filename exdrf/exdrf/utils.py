from textwrap import wrap
from typing import List

import inflect

inflect_e = inflect.engine()


def doc_lines(text: str) -> List[str]:
    """Get the docstring as a set of lines."""
    docs = (text or "").split("\n")
    result = []
    for i, d in enumerate(docs):
        if i > 0:
            result.append("")
        result.extend(wrap(d.strip(), width=70))
    return result
