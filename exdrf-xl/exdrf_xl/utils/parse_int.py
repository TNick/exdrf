from typing import Any


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        if text.startswith("-") and text[1:].isdigit():
            return int(text)
        if text.startswith("+") and text[1:].isdigit():
            return int(text)
        if text.isdigit():
            return int(text)
        return None
    return None
