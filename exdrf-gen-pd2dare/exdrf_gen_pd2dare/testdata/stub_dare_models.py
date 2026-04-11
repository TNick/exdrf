"""Minimal ``ExModel`` subclasses for ``pd2dare`` tests."""

from exdrf_pd import ExModel


class WidgetEx(ExModel):
    """Example resource for DARE TS smoke tests."""

    id: int
    label: str = ""
