import logging

logger = logging.getLogger(__name__)
VERBOSE = 1


def toposort_tables(
    table_names: list[str],
    deps: dict[str, set[str]],
) -> list[str]:
    """Topologically sort tables by their dependencies.

    The dependency direction is: `deps[A]` contains tables that must be inserted
    before `A` (i.e. `A` depends on them).

    Cycles are handled gracefully: any remaining cyclic nodes are appended in
    the original order.

    Args:
        table_names: Canonical table names in original order.
        deps: Dependency mapping.

    Returns:
        A list of table names in a best-effort insertion order.
    """
    order_index = {name: idx for idx, name in enumerate(table_names)}
    remaining = set(table_names)

    # Compute in-degrees.
    in_deg: dict[str, int] = {n: 0 for n in table_names}
    for n in table_names:
        for d in deps.get(n, set()):
            if d in in_deg and d != n:
                in_deg[n] += 1

    # Sort key: prioritize by dependency count, then original order.
    def sort_key(x: str) -> tuple[int, int]:
        return (len(deps.get(x, set())), order_index[x])

    # Kahn's algorithm (prioritize by dependency count, then original order).
    ready = sorted(
        [n for n in table_names if in_deg[n] == 0],
        key=sort_key,
    )
    out: list[str] = []
    while ready:
        n = ready.pop(0)
        if n not in remaining:
            continue
        remaining.remove(n)
        out.append(n)

        for m in table_names:
            if n not in deps.get(m, set()):
                continue
            if in_deg[m] <= 0:
                continue
            in_deg[m] -= 1
            if in_deg[m] == 0 and m in remaining:
                ready.append(m)
                ready.sort(key=sort_key)

    # Cycle fallback.
    if remaining:
        cyclic = sorted(list(remaining), key=sort_key)
        logger.log(
            VERBOSE,
            (
                "FK topo-sort found cyclic or unresolved dependencies; falling "
                "back to original order for: %r"
            ),
            cyclic,
        )
        out.extend(cyclic)

    return out
