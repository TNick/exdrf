"""Tests for ``resolve_rcv_plan``, cache, and overrides."""

import shutil
import sys
import textwrap
from pathlib import Path

import pytest

from exdrf_rcv.models import RcvPlan
from exdrf_rcv.plan_resolve import (
    RcvPlanCache,
    RcvPlanCacheKey,
    clear_rcv_plan_overrides,
    default_rcv_plan_cache,
    register_rcv_plan_override,
    resolve_rcv_plan,
    unregister_rcv_plan_override,
)


@pytest.fixture()
def tmp_rcv_pkg(tmp_path: Path) -> Path:
    """Lay out ``dyn_rcv_pkg.cat`` with ``res_rcv_paths.get_def``."""

    root = tmp_path / "dyn_rcv_pkg"
    cat = root / "cat"
    cat.mkdir(parents=True)
    (root / "__init__.py").write_text("", encoding="utf-8")
    (cat / "__init__.py").write_text("", encoding="utf-8")
    mod = cat / "res_rcv_paths.py"
    mod.write_text(
        textwrap.dedent(
            """
            RCV_RENDER_TYPE = "table"

            def get_def():
                return [
                    {
                        "name": "n",
                        "kind": "string",
                        "required": True,
                        "data": {"max_length": 5},
                    },
                ]
            """
        ).strip(),
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    yield root
    sys.path.remove(str(tmp_path))
    shutil.rmtree(tmp_path)


class TestResolveRcvPlan:
    """``resolve_rcv_plan`` imports generated modules and validates fields."""

    def test_resolve_category_path(self, tmp_rcv_pkg: Path) -> None:
        """Dotted category + resource resolves to ``get_def``."""

        cache = RcvPlanCache()
        plan = resolve_rcv_plan(
            import_root="dyn_rcv_pkg",
            category="cat",
            resource="res",
            record_id=7,
            view_type="detail",
            cache=cache,
        )
        assert isinstance(plan, RcvPlan)
        assert plan.render_type == "table"
        assert plan.record_id == 7
        assert plan.fields[0].name == "n"
        again = resolve_rcv_plan(
            import_root="dyn_rcv_pkg",
            category="cat",
            resource="res",
            record_id=99,
            view_type="detail",
            cache=cache,
        )
        assert again.record_id == 99

    def test_uncategorized_module(self, tmp_path: Path) -> None:
        """Empty ``category`` maps to ``import_root.{resource}_rcv_paths``."""

        root = tmp_path / "flat_pkg"
        root.mkdir()
        (root / "__init__.py").write_text("", encoding="utf-8")
        (root / "solo_rcv_paths.py").write_text(
            textwrap.dedent(
                """
                RCV_RENDER_TYPE = "default"

                def get_def():
                    return [
                        {
                            "name": "x",
                            "kind": "integer",
                            "required": False,
                            "data": {},
                        },
                    ]
                """
            ).strip(),
            encoding="utf-8",
        )
        sys.path.insert(0, str(tmp_path))
        try:
            plan = resolve_rcv_plan(
                import_root="flat_pkg",
                category="",
                resource="solo",
                record_id=None,
                view_type="list",
                cache=RcvPlanCache(),
            )
            assert plan.fields[0].kind == "integer"
        finally:
            sys.path.remove(str(tmp_path))


class TestRcvPlanOverrides:
    """Override registry clears cache and mutates plans."""

    def test_override_chain(self, tmp_rcv_pkg: Path) -> None:
        """Registered overrides run in registration order."""

        clear_rcv_plan_overrides()
        default_rcv_plan_cache().clear()
        key = RcvPlanCacheKey(
            import_root="dyn_rcv_pkg",
            category="cat",
            resource="res",
            view_type="detail",
        )

        def bump_title(p: RcvPlan) -> RcvPlan:
            f0 = p.fields[0].model_copy(update={"title": "T"})
            return p.model_copy(update={"fields": [f0, *p.fields[1:]]})

        register_rcv_plan_override(key, bump_title)
        try:
            plan = resolve_rcv_plan(
                import_root=key.import_root,
                category=key.category,
                resource=key.resource,
                record_id=None,
                view_type=key.view_type,
                cache=RcvPlanCache(),
            )
            assert plan.fields[0].title == "T"
        finally:
            unregister_rcv_plan_override(key, bump_title)
            clear_rcv_plan_overrides()


class TestSanitize:
    """Invalid import segments are rejected."""

    def test_bad_segment(self) -> None:
        """Uppercase segment raises ``ValueError``."""

        with pytest.raises(ValueError):
            resolve_rcv_plan(
                import_root="dyn_rcv_pkg",
                category="Cat",
                resource="res",
                record_id=None,
                view_type="v",
                cache=RcvPlanCache(),
            )
