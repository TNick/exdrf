"""Profile display helpers for generated Qt widgets."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exdrf_dev.db.api import Profile


def profile_label(profile: "Profile") -> str:
    """Return a short label for a loaded profile row.

    Args:
        profile: SQLAlchemy profile instance.

    Returns:
        Bio snippet when present, otherwise id-based fallback text.
    """

    bio = profile.bio
    if bio:
        stripped = bio.strip()
        if len(stripped) > 48:
            return "%s..." % stripped[:45]
        if stripped:
            return stripped
    return "Profile %s" % profile.id
