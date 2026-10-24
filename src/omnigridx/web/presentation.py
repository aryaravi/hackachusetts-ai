"""Deterministic human and JSON exports for the immutable judge report."""

from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from omnigridx.application.reporting import JudgeReport

_ENVIRONMENT = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape(("html",)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_TEMPLATE = _ENVIRONMENT.get_template("report.html")
_ALTERNATIVE_TITLES = {
    "existing": "Existing operation",
    "rule_based": "Solar-first rule",
    "optimized": "Optimized dispatch",
}


def _quantity(value: dict[str, str] | None) -> str:
    return "N/A" if value is None else f"{value['value']} {value['unit']}"


def _percentage(value: str | None) -> str:
    if value is None:
        return "N/A"
    return f"{(Decimal(value) * 100).normalize():f}%"


class ReportPresenter:
    """Render an already-calculated report without changing its values."""

    def render_json(self, report: JudgeReport) -> str:
        return report.to_json()

    def render_html(self, report: JudgeReport) -> str:
        document: dict[str, Any] = report.to_dict()
        return _TEMPLATE.render(
            report=document,
            titles=_ALTERNATIVE_TITLES,
            quantity=_quantity,
            percentage=_percentage,
        )
