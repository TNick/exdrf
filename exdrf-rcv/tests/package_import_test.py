"""Smoke tests for the ``exdrf_rcv`` package."""


def test_exdrf_rcv_importable() -> None:
    """The package root module loads without side effects."""

    import exdrf_rcv

    for name in (
        "RcvPlan",
        "RcvField",
        "RcvPlanCache",
        "RcvPlanCacheKey",
        "clear_rcv_plan_overrides",
        "default_rcv_plan_cache",
        "register_rcv_plan_override",
        "resolve_rcv_plan",
        "unregister_rcv_plan_override",
    ):
        assert name in exdrf_rcv.__all__
