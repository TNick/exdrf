"""CLI smoke tests for ``openapi2rtk``."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from exdrf_gen.plugin_support import load_plugins
from exdrf_gen.cli_base import cli


@pytest.fixture(scope="module", autouse=True)
def _load_plugins() -> None:
    """Attach ``openapi2rtk`` (and sibling) commands to the shared CLI."""

    load_plugins()


def test_openapi2rtk_writes_route_files(tmp_path: Path) -> None:
    """``openapi2rtk`` emits ``widgets.ts``, ``index.ts``, and shared helpers."""

    fixture = (
        Path(__file__).resolve().parent / "fixtures" / "minimal_openapi.json"
    )
    routes = tmp_path / "routes"
    routes.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "openapi2rtk",
            str(routes),
            "--openapi-file",
            str(fixture),
            "--types-import",
            "@demo/models",
            "--base-api-profile",
            "minimal",
        ],
    )
    detail = result.output + (result.exception and str(result.exception) or "")
    assert result.exit_code == 0, detail
    assert (routes / "widgets.ts").is_file()
    assert (routes / "index.ts").is_file()
    assert (tmp_path / "base-api.ts").is_file()
    assert (tmp_path / "cacheUtils.ts").is_file()
    assert (tmp_path / "list-query-contract.ts").is_file()
    body = (routes / "widgets.ts").read_text(encoding="utf-8")
    assert "@demo/models" in body
    assert "useListWidgetsQuery" in body
