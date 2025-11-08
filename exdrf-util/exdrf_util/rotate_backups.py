import logging
import os
import shutil

logger = logging.getLogger(__name__)


def rotate_backups(file_path: str, max_backups: int = 5) -> bool:
    """Rotate up to ``max_backups`` copies of the file.

    The pattern is ``<file>.backup-N<ext>`` where N is in ``[1..max_backups]``.

    Args:
        file_path: The path to the file to rotate.
        max_backups: The maximum number of backups to keep.

    Returns:
        True if the file was rotated successfully, False otherwise.
    """
    root, ext = os.path.splitext(file_path)

    # Remove oldest
    oldest = f"{root}.backup-{max_backups}{ext}"
    try:
        if os.path.exists(oldest):
            os.remove(oldest)
    except Exception:
        logger.exception("Failed removing oldest backup: %s", oldest)

    # Shift existing backups
    for i in range(max_backups - 1, 0, -1):
        src = f"{root}.backup-{i}{ext}"
        dst = f"{root}.backup-{i + 1}{ext}"
        if os.path.exists(src):
            try:
                os.replace(src, dst)
            except Exception:
                try:
                    shutil.move(src, dst)
                except Exception:
                    logger.exception(
                        "Failed rotating backup from %s to %s", src, dst
                    )

    # Create newest from current file
    try:
        if os.path.exists(file_path):
            newest = f"{root}.backup-1{ext}"
            shutil.copy2(file_path, newest)
            return True
    except Exception:
        logger.exception("Failed creating newest backup for: %s", file_path)
    return False
