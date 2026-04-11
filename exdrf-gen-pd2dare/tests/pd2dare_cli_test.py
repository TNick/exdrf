"""CLI tests for ``pd2dare``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner
from exdrf_gen import plugin_support
from exdrf_gen.cli_base import cli


def test_pd2dare_writes_dataset_and_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pd2dare`` emits ``dataset.ts`` and ``index.ts``."""

    out = tmp_path / "dare_out"
    out.mkdir()
    monkeypatch.setenv(
        "EXDRF_PYDANTIC_MODELS_MODULES",
        "exdrf_gen_pd2dare.testdata.stub_dare_models",
    )
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")

    plugin_support.load_plugins()
    runner = CliRunner()
    result = runner.invoke(cli, ["pd2dare", str(out)], env=env)
    assert result.exit_code == 0, result.output
    assert (out / "index.ts").is_file()
    assert (out / "dataset.ts").is_file()
    dare = (out / "dataset.ts").read_text(encoding="utf-8")
    assert "export " in dare
    assert "automatically generated" in dare.lower()
