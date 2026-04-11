"""Tests for ``exdrf_pd.model_import``."""

from __future__ import annotations

import sys
import types

import pytest

from exdrf_pd import model_import


def test_load_pydantic_modules_skips_empty_and_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only entries are skipped; valid modules are imported."""

    created: list[str] = []

    def fake_import_module(name: str) -> types.ModuleType:
        created.append(name)
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod

    monkeypatch.setattr(
        model_import.importlib, "import_module", fake_import_module
    )
    result = model_import.load_pydantic_modules(["  ", "a.b", "  c.d  ", ""])
    assert result == ["a.b", "c.d"]
    assert created == ["a.b", "c.d"]
    for name in created:
        sys.modules.pop(name, None)


def test_load_pydantic_modules_from_env_prefers_exdrf_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``EXDRF_PYDANTIC_MODELS_MODULES`` wins when set."""

    monkeypatch.delenv("EXDRF_PYDANTIC_MODELS_MODULES", raising=False)
    monkeypatch.delenv("RESI_PYDANTIC_MODELS_MODULES", raising=False)
    monkeypatch.setenv("EXDRF_PYDANTIC_MODELS_MODULES", "mod_a")
    monkeypatch.setenv("RESI_PYDANTIC_MODELS_MODULES", "mod_b")

    imported: list[str] = []

    def fake_import(name: str) -> types.ModuleType:
        imported.append(name)
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    monkeypatch.setattr(model_import.importlib, "import_module", fake_import)
    model_import.load_pydantic_modules_from_env()
    assert imported == ["mod_a"]
    sys.modules.pop("mod_a", None)


def test_load_pydantic_modules_from_env_resi_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``EXDRF_*`` is empty, ``RESI_*`` is used."""

    monkeypatch.delenv("EXDRF_PYDANTIC_MODELS_MODULES", raising=False)
    monkeypatch.setenv("RESI_PYDANTIC_MODELS_MODULES", "legacy_mod")

    imported: list[str] = []

    def fake_import(name: str) -> types.ModuleType:
        imported.append(name)
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    monkeypatch.setattr(model_import.importlib, "import_module", fake_import)
    model_import.load_pydantic_modules_from_env()
    assert imported == ["legacy_mod"]
    sys.modules.pop("legacy_mod", None)
