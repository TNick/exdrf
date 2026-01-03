import logging
import os
from typing import Any

from attrs import define

from exdrf_qt.local_settings import LocalSettings

logger = logging.getLogger(__name__)


@define
class TranslateCollector(LocalSettings):
    """Used in development to collect strings to translate."""

    def settings_file(self) -> str:
        """Get the path to the settings file."""
        file_path = os.environ.get("EXDRF_TRANSLATE_COLLECTOR_FILE", None)
        if not file_path:
            raise RuntimeError(
                "The environment variable 'EXDRF_TRANSLATE_COLLECTOR_FILE' "
                "is not set. Please set it to the path to the file to "
                "collect strings to translate."
            )

        if not os.path.exists(file_path):
            par_dir = os.path.dirname(file_path)
            if not os.path.exists(par_dir):
                try:
                    os.makedirs(par_dir)
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to create directory {par_dir}: {e}"
                    )

            with open(file_path, "w") as f:
                f.write("{}")
        return file_path

    def t(self, key: str, d: str, **kwargs: Any) -> str:
        """Translates a string"""
        result = d.format(**kwargs)
        existing = self.get_setting(key, None)
        if existing is None:
            try:
                self.set_setting(key, result)
            except Exception as e:
                if isinstance(e, AttributeError) and (
                    "'str' object has no attribute 'get'" in str(e)
                ):
                    logger.error("Duplicate root translation string %s", key)
                else:
                    logger.error(
                        "Failed to save translation string %s: %s",
                        key,
                        e,
                        exc_info=True,
                    )
        return result
