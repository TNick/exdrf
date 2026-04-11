"""Fill ``ua_*`` diacritic-stripped companions on create/edit payload mappings."""

from __future__ import annotations

from typing import Any, MutableMapping, Sequence

from unidecode import unidecode

_MISSING = object()


def apply_ua_companion_fields(
    payload: MutableMapping[str, Any],
    source_target_pairs: Sequence[tuple[str, str]],
) -> None:
    """Copy plain string fields into ``ua_*`` search columns using ``unidecode``.

    For each ``(source_key, target_key)`` pair: if ``source_key`` is absent
    from ``payload``, nothing is done. If it is present (even when the value
    is ``None``), ``target_key`` is set to ``None`` or to the lowercased
    unidecoded string form of the source value.

    Args:
        payload: Mapping from a Pydantic ``model_dump``; updated in place.
        source_target_pairs: ``(plain_field, ua_field)`` name pairs for this
            resource.

    Returns:
        ``None``; ``payload`` is mutated in place.
    """

    for src_key, tgt_key in source_target_pairs:
        src_val = payload.get(src_key, _MISSING)

        if src_val is _MISSING:
            continue

        if src_val is None:
            payload[tgt_key] = None
        else:
            payload[tgt_key] = unidecode(str(src_val).lower())
