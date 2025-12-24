def normalize_rgb_color(value: str) -> str:
    """Normalize a color string into an 8-digit ARGB hex format.

    Args:
        value: A hex color value, in "RGB", "RRGGBB" or "AARRGGBB" format.
            The leading "#" is optional.

    Returns:
        An 8-digit ARGB hex string (e.g., "FFFF0000").

    Raises:
        ValueError: If the provided value is not a supported hex color format.
    """
    normalized = value.strip().lstrip("#").upper()
    # Check that all characters are valid hex digits
    if not all(c in "0123456789ABCDEF" for c in normalized):
        raise ValueError(
            f"Invalid color {value!r}; contains non-hexadecimal characters"
        )

    # Accept 3-character (shorthand) hex colors by expanding them, e.g., 'ABC' -> 'AABBCC'
    if len(normalized) == 3:
        return "FF" + "".join([c * 2 for c in normalized])

    if len(normalized) == 6:
        return "FF" + normalized

    if len(normalized) == 8:
        return normalized

    raise ValueError(
        "Invalid color value %r; expected RRGGBB or AARRGGBB" % value
    )
