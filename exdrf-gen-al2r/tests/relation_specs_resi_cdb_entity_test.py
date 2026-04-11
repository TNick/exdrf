"""Integration guard: ``Entity`` relation-sync metadata from ``resi_cdb``.

These tests are skipped when ``resi_cdb`` is not importable (for example in
minimal ``exdrf-gen-al2r`` CI installs). Run them from an environment that
includes the CadPlatf backend packages (same layout as ``exdrf_gen al2r``).
"""

from __future__ import annotations

from typing import cast

import pytest
from exdrf.field_types.ref_base import RefBaseField
from exdrf_gen_al2pd.field_partition import partition_fields

from exdrf_gen_al2r.relation_specs import build_al2r_relation_sync_specs


def test_entity_relation_sync_specs_covers_all_list_refs() -> None:
    """Every ``Entity`` list relation must get a supported al2r sync spec."""

    pytest.importorskip("resi_cdb.api")

    from exdrf.dataset import ExDataset
    from exdrf_al.loader import dataset_from_sqlalchemy
    from resi_cdb.api import Base

    d_set = ExDataset()
    dataset_from_sqlalchemy(d_set, Base)
    entity = next(r for r in d_set.resources if r.name == "Entity")

    _, _, ref_fields = partition_fields(entity)
    list_refs = [f for f in ref_fields if cast(RefBaseField, f).is_list]

    specs, all_supported = build_al2r_relation_sync_specs(entity)

    assert len(list_refs) == 18
    assert all_supported is True
    assert len(specs) == 18
