"""Tests for branched Alembic head detection in DbVer."""

from unittest.mock import MagicMock, patch

from exdrf_al.db_ver.db_ver import DbVer


class TestDbVerHeadDetection:
    """Tests for multi-head migration helpers."""

    def test_needs_migration_when_one_branch_head_missing(self) -> None:
        """A single recorded head must not hide a parallel branch."""

        dbv = DbVer(engine=MagicMock(), migrations="/tmp/migrations")
        with (
            patch.object(
                DbVer,
                "get_head_revisions",
                return_value=["aa11bb22cc33", "mm33nn44oo55"],
            ),
            patch.object(
                DbVer,
                "get_current_versions",
                return_value=["aa11bb22cc33"],
            ),
        ):
            assert dbv.needs_migration() is True

    def test_needs_migration_false_when_all_heads_recorded(self) -> None:
        """Every configured head must be present in the version table."""

        dbv = DbVer(engine=MagicMock(), migrations="/tmp/migrations")
        with (
            patch.object(
                DbVer,
                "get_head_revisions",
                return_value=["aa11bb22cc33", "mm33nn44oo55"],
            ),
            patch.object(
                DbVer,
                "get_current_versions",
                return_value=["aa11bb22cc33", "mm33nn44oo55"],
            ),
        ):
            assert dbv.needs_migration() is False

    def test_get_latest_version_joins_multiple_heads(self) -> None:
        """Display label should list every configured head."""

        dbv = DbVer(engine=MagicMock(), migrations="/tmp/migrations")
        with patch.object(
            DbVer,
            "get_head_revisions",
            return_value=["aa11bb22cc33", "mm33nn44oo55"],
        ):
            assert dbv.get_latest_version() == "aa11bb22cc33, mm33nn44oo55"
