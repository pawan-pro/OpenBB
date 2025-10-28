"""Reports Router."""
from openbb_core.app.router import Router
from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query


router = Router(prefix="", description="Financial reports.")

@router.command(
    description="Generate a daily investment report.",
)
def daily(file_path: str = "daily_investment_report.html") -> OBBject:
    """Generate a daily investment report."""
    from .reports_api import generate_daily_report

    generate_daily_report(file_path=file_path)
    return OBBject(results={"message": f"Report generated at {file_path}"})
